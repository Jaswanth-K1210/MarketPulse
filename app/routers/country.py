"""Everything known about one country, with each section declaring its liveness.

Six sections a trader asks for on clicking a country. Four are backed today;
two are not, and say so rather than rendering empty. That distinction is the
whole point — an empty "military tensions" card that does not explain itself
reads as peace.
"""
import asyncio
import logging

import pycountry
from fastapi import APIRouter

from app.services.evidence import SourceResult, aggregate, record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/country", tags=["country"])

# Each section counts equally toward coverage: none is more "the answer" than
# the others, and a trader reading 4/6 wants to know which four.
SECTION_WEIGHTS = {
    "companies": 1.0, "insiders": 1.0, "news": 1.0,
    "markets": 1.0, "tensions": 1.0, "shipping": 1.0,
}

# Headline index per country, for the markets section. signal_aggregator pins
# market signals to "US" wholesale, so country-level market context needs its
# own mapping. Deliberately short: extend as countries are actually used.
COUNTRY_INDEX = {
    "US": "^GSPC", "TW": "^TWII", "KR": "^KS11", "JP": "^N225",
    "NL": "^AEX", "GB": "^FTSE", "DE": "^GDAXI", "FR": "^FCHI",
    "CN": "000001.SS", "HK": "^HSI", "IN": "^NSEI", "CA": "^GSPTSE",
}


async def _companies(iso2: str) -> SourceResult:
    from app.services.data.company_geo import companies_in_country
    return await companies_in_country(iso2)


async def _insiders(tickers: list[str]) -> SourceResult:
    """Insider filings for the country's companies.

    SEC Form 4 covers US-listed filings only, so for a foreign company this is
    its ADR activity, not local insider dealing. The note travels with the data
    so the UI cannot imply otherwise.
    """
    if not tickers:
        return SourceResult.dead("insiders", "no companies resolved for this country")
    try:
        from app.services.data.insider_trades import insider_trades_service
        results = await asyncio.gather(
            *(insider_trades_service.get_insider_trades(t) for t in tickers),
            return_exceptions=True,
        )
    except Exception as e:
        return record(SourceResult.dead("insiders", str(e)))

    trades, errors = [], []
    for ticker, result in zip(tickers, results):
        if isinstance(result, Exception):
            errors.append(f"{ticker}: {result}")
            continue
        for trade in result or []:
            trades.append({**trade, "ticker": ticker})

    if errors and not trades:
        return record(SourceResult.dead("insiders", "; ".join(errors)[:200]))
    return record(SourceResult.ok("insiders", trades))


async def _news(iso2: str) -> SourceResult:
    """News signals already tagged to this country by signal_aggregator.

    Deliberately NOT gated on get_signals_with_evidence()["available"]: that
    flag reports the conflict feeds (ACLED/UCDP) only. News arrives through the
    104-source news aggregator, an entirely separate path, and letting a dead
    ACLED key mark the news section dead is exactly the miscoupling this layer
    exists to prevent.
    """
    try:
        from app.services.intelligence.signal_aggregator import SignalAggregator
        agg = SignalAggregator()
        out = await agg.get_signals_with_evidence()
        news_signals = [s for s in out["signals"] if s.get("signal_type") == "news"]
        if not news_signals:
            return record(SourceResult.dead(
                "news", "news aggregator has not produced any classified signals yet"))
        matching = [s for s in news_signals
                    if (s.get("country") or "").upper() == iso2]
        return record(SourceResult.ok("news", matching))
    except Exception as e:
        logger.warning("country news failed: %s", e)
        return record(SourceResult.dead("news", str(e)))


async def _markets(iso2: str) -> SourceResult:
    symbol = COUNTRY_INDEX.get(iso2)
    if not symbol:
        return record(SourceResult.dead(
            "markets", f"no headline index mapped for {iso2}"))
    try:
        from app.services.stock_data import stock_data_service
        quotes = await asyncio.to_thread(stock_data_service.get_live_prices, [symbol])
        data = (quotes or {}).get(symbol)
        if not data:
            return record(SourceResult.dead("markets", f"no quote for {symbol}"))
        # stock_data falls back to a hardcoded Dec-2024 price table when the
        # API fails, and labels it. Never pass that off as a live quote.
        if data.get("data_source") == "static_fallback":
            return record(SourceResult.dead(
                "markets", f"{symbol} served from the static fallback table, not live"))
        if data.get("error"):
            return record(SourceResult.dead("markets", str(data["error"])))
        return record(SourceResult.ok("markets", {"index": symbol, **data}))
    except Exception as e:
        logger.warning("country markets failed: %s", e)
        return record(SourceResult.dead("markets", str(e)))


async def _tensions(iso2: str) -> SourceResult:
    """Conflict/military activity. Currently no live source — see the spec."""
    try:
        from app.services.data.conflict_data import ConflictDataService
        svc = ConflictDataService()
        try:
            snapshot = await svc.get_conflict_snapshot(country_codes=[iso2])
        finally:
            await svc.close()
        dead = [f"{n}: {r.error}" for n, r in svc.source_results.items()
                if not r.available]
        if dead and not snapshot.get("acled_events") and not snapshot.get("ucdp_conflicts"):
            return record(SourceResult.dead("tensions", "; ".join(dead)[:200]))
        return record(SourceResult.ok("tensions", {
            "events": snapshot.get("acled_events", []),
            "conflicts": snapshot.get("ucdp_conflicts", []),
        }))
    except Exception as e:
        return record(SourceResult.dead("tensions", str(e)))


async def _shipping(iso2: str) -> SourceResult:
    # Stated rather than faked: live AIS/vessel tracking is a paid feed and
    # nothing in this repo provides it.
    return record(SourceResult.dead(
        "shipping", "no shipping data source configured (live AIS is a paid feed)"))


@router.get("/{iso2}")
async def get_country(iso2: str) -> dict:
    iso2 = iso2.upper()
    try:
        name = pycountry.countries.get(alpha_2=iso2).name
    except (AttributeError, LookupError):
        name = iso2

    companies = await _companies(iso2)
    tickers = [c["ticker"] for c in (companies.data or [])] if companies.available else []

    insiders, news, markets, tensions, shipping = await asyncio.gather(
        _insiders(tickers), _news(iso2), _markets(iso2),
        _tensions(iso2), _shipping(iso2),
    )

    results = {
        "companies": companies, "insiders": insiders, "news": news,
        "markets": markets, "tensions": tensions, "shipping": shipping,
    }
    summary = aggregate(results, SECTION_WEIGHTS, min_coverage=0.5)

    sections = {
        name_: {
            "available": r.available,
            "data": r.data,
            "error": r.error,
            "as_of": r.as_of,
        }
        for name_, r in results.items()
    }
    sections["insiders"]["note"] = "SEC Form 4 — US-listed filings only"

    return {
        "country": {"iso2": iso2, "name": name},
        "sections": sections,
        "coverage": summary["coverage"],
    }
