"""Where each company actually is.

Nothing in MarketPulse knew a company's domicile — SUPPLY_CHAIN_COMPANIES maps
names to tickers and stops there. yfinance's .info carries both `country` and
`city`, which is enough to answer "what is in this country" without adding a
dependency or a paid feed.

Lookups are effectively static (a company's domicile does not move), so they are
cached for a day. A lookup that fails returns available=False with a reason
rather than a guessed country — an incorrectly placed company is worse than an
absent one.
"""
from __future__ import annotations

import asyncio
import logging
import time

import pycountry

from app.config import SUPPLY_CHAIN_COMPANIES
from app.services.evidence import SourceResult, record

logger = logging.getLogger(__name__)

# A domicile does not change week to week.
_TTL_SECONDS = 86_400
_cache: dict[str, tuple[float, dict | None]] = {}


def country_to_iso2(name: str | None) -> str | None:
    """Map a country name from yfinance onto ISO-3166 alpha-2."""
    if not name:
        return None
    try:
        return pycountry.countries.lookup(name).alpha_2
    except LookupError:
        logger.debug("no ISO2 for country name %r", name)
        return None


def _lookup_sync(ticker: str) -> dict | None:
    """Blocking yfinance call. Returns None when the domicile is unknown."""
    import yfinance as yf

    info = yf.Ticker(ticker).info or {}
    country = info.get("country")
    iso2 = country_to_iso2(country)
    if not iso2:
        return None
    return {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "country": country,
        "iso2": iso2,
        "city": info.get("city"),
        "exchange": info.get("exchange"),
    }


async def get_company_location(ticker: str) -> SourceResult:
    """Resolve one ticker's domicile."""
    now = time.time()
    hit = _cache.get(ticker)
    if hit and now - hit[0] < _TTL_SECONDS:
        cached_at, value = hit
        if value is None:
            return SourceResult.dead(f"company_geo:{ticker}",
                                     "no domicile reported for this ticker")
        return SourceResult.ok(f"company_geo:{ticker}", value, as_of=cached_at)

    try:
        value = await asyncio.to_thread(_lookup_sync, ticker)
    except Exception as e:
        logger.warning("company_geo lookup failed for %s: %s", ticker, e)
        return record(SourceResult.dead(f"company_geo:{ticker}", str(e)))

    _cache[ticker] = (now, value)
    if value is None:
        return record(SourceResult.dead(
            f"company_geo:{ticker}", "no domicile reported for this ticker"))
    return record(SourceResult.ok(f"company_geo:{ticker}", value, as_of=now))


def known_universe() -> list[str]:
    """Tickers we can place on a map. Deduplicated, since the supply-chain map
    holds several aliases per company (TSMC and Taiwan Semiconductor both -> TSM).
    """
    return sorted(set(SUPPLY_CHAIN_COMPANIES.values()))


async def companies_in_country(iso2: str, extra_tickers: list[str] | None = None) -> SourceResult:
    """Every known company domiciled in `iso2`.

    An empty list with available=True means the universe genuinely holds no
    company there. available=False means we could not resolve the universe at
    all — a distinction the panel depends on.
    """
    tickers = sorted(set(known_universe() + list(extra_tickers or [])))
    results = await asyncio.gather(*(get_company_location(t) for t in tickers))

    live = [r for r in results if r.available]
    if not live:
        reasons = {r.source_id.split(":", 1)[-1]: r.error for r in results}
        return record(SourceResult.dead(
            "companies_in_country",
            f"could not resolve any of {len(tickers)} tickers: "
            f"{next(iter(reasons.values()), 'unknown error')}"))

    matches = [r.data for r in live if r.data["iso2"] == iso2.upper()]
    return record(SourceResult.ok("companies_in_country", matches, as_of=time.time()))
