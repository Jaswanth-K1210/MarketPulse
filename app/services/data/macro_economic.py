"""
Macro Economic Data Service — FRED, CoinGecko, Yahoo Finance commodities/ETFs.
Provides broader market context beyond individual stock prices.
"""

import os
import logging
import aiohttp
import asyncio
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# FRED Series IDs
FRED_SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "unemployment": "UNRATE",
    "gdp": "GDP",
    "consumer_sentiment": "UMCSENT",
    "treasury_2y": "DGS2",
    "treasury_10y": "DGS10",
    "treasury_30y": "DGS30",
    "vix": "VIXCLS",
    "housing_starts": "HOUST",
    "retail_sales": "RSXFS",
    "industrial_production": "INDPRO",
    "pce_inflation": "PCEPI",
}

# Yahoo Finance commodity/index symbols
COMMODITY_SYMBOLS = {
    "crude_oil": "CL=F",
    "gold": "GC=F",
    "silver": "SI=F",
    "natural_gas": "NG=F",
    "wheat": "ZW=F",
    "corn": "ZC=F",
    "copper": "HG=F",
    "platinum": "PL=F",
}

SECTOR_ETFS = {
    "energy": "XLE",
    "financials": "XLF",
    "technology": "XLK",
    "healthcare": "XLV",
    "industrials": "XLI",
    "materials": "XLB",
    "utilities": "XLU",
    "real_estate": "XLRE",
    "consumer_discretionary": "XLY",
    "consumer_staples": "XLP",
    "communication": "XLC",
}

INDEX_SYMBOLS = {
    "sp500": "^GSPC",
    "dow_jones": "^DJI",
    "nasdaq": "^IXIC",
    "russell_2000": "^RUT",
    "vix": "^VIX",
    "dxy": "DX-Y.NYB",
}

CRYPTO_IDS = ["bitcoin", "ethereum", "solana"]


class MacroEconomicService:
    """Fetches macro economic data from multiple sources."""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ============================================================
    # FRED API
    # ============================================================

    async def get_fred_series(self, series_id: str, limit: int = 10) -> Optional[dict]:
        """
        Fetch a single FRED series.
        Returns latest observations with metadata.
        """
        if not FRED_API_KEY:
            logger.debug("FRED_API_KEY not configured")
            return None

        session = await self._get_session()
        params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }

        try:
            async with session.get(FRED_BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"FRED API error for {series_id}: {resp.status}")
                    return None
                data = await resp.json()
                observations = data.get("observations", [])
                if not observations:
                    return None

                # Parse values (filter out "." which means no data)
                values = []
                for obs in observations:
                    if obs["value"] != ".":
                        values.append({
                            "date": obs["date"],
                            "value": float(obs["value"]),
                        })

                if not values:
                    return None

                return {
                    "series_id": series_id,
                    "latest_value": values[0]["value"],
                    "latest_date": values[0]["date"],
                    "history": values[:limit],
                    "change": (values[0]["value"] - values[1]["value"]) if len(values) > 1 else 0,
                }
        except Exception as e:
            logger.warning(f"FRED fetch error for {series_id}: {e}")
            return None

    async def get_fred_snapshot(self) -> dict:
        """Fetch all key FRED indicators in parallel."""
        tasks = {
            name: self.get_fred_series(series_id)
            for name, series_id in FRED_SERIES.items()
        }

        results = {}
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for name, result in zip(tasks.keys(), gathered):
            if isinstance(result, Exception):
                logger.debug(f"FRED {name} failed: {result}")
                continue
            if result:
                results[name] = result

        return results

    # ============================================================
    # CoinGecko API (Crypto)
    # ============================================================

    async def get_crypto_data(self) -> Optional[list[dict]]:
        """Fetch crypto market data from CoinGecko."""
        session = await self._get_session()
        params = {
            "ids": ",".join(CRYPTO_IDS),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        }

        try:
            url = f"{COINGECKO_BASE_URL}/simple/price"
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"CoinGecko error: {resp.status}")
                    return None
                data = await resp.json()

                results = []
                for coin_id in CRYPTO_IDS:
                    if coin_id in data:
                        coin = data[coin_id]
                        results.append({
                            "id": coin_id,
                            "symbol": coin_id[:3].upper(),
                            "price_usd": coin.get("usd", 0),
                            "change_24h": coin.get("usd_24h_change", 0),
                            "market_cap": coin.get("usd_market_cap", 0),
                            "volume_24h": coin.get("usd_24h_vol", 0),
                        })
                return results
        except Exception as e:
            logger.warning(f"CoinGecko fetch error: {e}")
            return None

    # ============================================================
    # Yahoo Finance (Commodities, ETFs, Indices via yfinance)
    # ============================================================

    async def get_commodities(self) -> dict:
        """Fetch commodity prices using yfinance."""
        import yfinance as yf

        results = {}
        for name, symbol in COMMODITY_SYMBOLS.items():
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="2d")
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    results[name] = {
                        "symbol": symbol,
                        "price": round(current, 2),
                        "change": round(current - prev, 2),
                        "change_pct": round((current - prev) / prev * 100, 2) if prev else 0,
                    }
            except Exception as e:
                logger.debug(f"Commodity {name} fetch error: {e}")
                continue

        return results

    async def get_sector_etfs(self) -> dict:
        """Fetch sector ETF performance."""
        import yfinance as yf

        results = {}
        symbols = list(SECTOR_ETFS.values())

        try:
            tickers = yf.Tickers(" ".join(symbols))
            for sector_name, symbol in SECTOR_ETFS.items():
                try:
                    hist = tickers.tickers[symbol].history(period="2d")
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                        results[sector_name] = {
                            "symbol": symbol,
                            "price": round(current, 2),
                            "change_pct": round((current - prev) / prev * 100, 2) if prev else 0,
                        }
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Sector ETF batch fetch error: {e}")

        return results

    async def get_indices(self) -> dict:
        """Fetch major market indices."""
        import yfinance as yf

        results = {}
        for name, symbol in INDEX_SYMBOLS.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    results[name] = {
                        "symbol": symbol,
                        "price": round(current, 2),
                        "change": round(current - prev, 2),
                        "change_pct": round((current - prev) / prev * 100, 2) if prev else 0,
                    }
            except Exception:
                continue

        return results

    # ============================================================
    # Unified Snapshot
    # ============================================================

    async def get_macro_snapshot(self) -> dict:
        """
        Complete macro economic snapshot for dashboard and AI context injection.
        Fetches all data sources in parallel.
        """
        fred_task = self.get_fred_snapshot()
        crypto_task = self.get_crypto_data()
        commodities_task = self.get_commodities()
        sectors_task = self.get_sector_etfs()
        indices_task = self.get_indices()

        results = await asyncio.gather(
            fred_task, crypto_task, commodities_task, sectors_task, indices_task,
            return_exceptions=True
        )

        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "fred": results[0] if not isinstance(results[0], Exception) else {},
            "crypto": results[1] if not isinstance(results[1], Exception) else [],
            "commodities": results[2] if not isinstance(results[2], Exception) else {},
            "sectors": results[3] if not isinstance(results[3], Exception) else {},
            "indices": results[4] if not isinstance(results[4], Exception) else {},
        }

        return snapshot

    def generate_ai_context(self, snapshot: dict) -> str:
        """
        Generate a compact text summary for injection into LLM prompts.
        Grounds the AI in real market data.
        """
        lines = ["[MACRO ECONOMIC CONTEXT]"]

        # Indices
        indices = snapshot.get("indices", {})
        if indices:
            idx_parts = []
            for name, data in indices.items():
                idx_parts.append(f"{name}: {data.get('change_pct', 0):+.1f}%")
            lines.append(f"Indices: {', '.join(idx_parts)}")

        # Key FRED data
        fred = snapshot.get("fred", {})
        if fred:
            key_indicators = []
            if "fed_funds_rate" in fred:
                key_indicators.append(f"Fed Rate: {fred['fed_funds_rate']['latest_value']}%")
            if "vix" in fred:
                key_indicators.append(f"VIX: {fred['vix']['latest_value']}")
            if "unemployment" in fred:
                key_indicators.append(f"Unemployment: {fred['unemployment']['latest_value']}%")
            if key_indicators:
                lines.append(f"Macro: {', '.join(key_indicators)}")

        # Commodities
        commodities = snapshot.get("commodities", {})
        if commodities:
            comm_parts = []
            for name, data in list(commodities.items())[:4]:
                comm_parts.append(f"{name}: ${data.get('price', 0)} ({data.get('change_pct', 0):+.1f}%)")
            lines.append(f"Commodities: {', '.join(comm_parts)}")

        # Crypto
        crypto = snapshot.get("crypto", [])
        if crypto:
            crypto_parts = []
            for coin in crypto[:3]:
                crypto_parts.append(f"{coin['symbol']}: ${coin['price_usd']:,.0f} ({coin['change_24h']:+.1f}%)")
            lines.append(f"Crypto: {', '.join(crypto_parts)}")

        return "\n".join(lines)

    async def get_snapshot(self) -> dict:
        """
        Return flat dict for the intelligence API router and frontend.
        Maps nested get_macro_snapshot() → {fed_funds_rate, cpi, sector_etfs, ...}
        """
        raw = await self.get_macro_snapshot()
        fred = raw.get("fred", {})
        commodities = raw.get("commodities", {})
        sectors = raw.get("sectors", {})

        def _latest(series_dict):
            if isinstance(series_dict, dict):
                return series_dict.get("latest_value")
            return None

        sector_etfs = {}
        for sector, data in sectors.items():
            sector_etfs[sector] = {
                "ticker": data.get("ticker", ""),
                "price": data.get("price"),
                "change_pct": data.get("change_pct", 0),
            }

        return {
            "fed_funds_rate": _latest(fred.get("fed_funds_rate")),
            "treasury_2y": _latest(fred.get("treasury_2y")),
            "treasury_10y": _latest(fred.get("treasury_10y")),
            "treasury_30y": _latest(fred.get("treasury_30y")),
            "cpi": _latest(fred.get("cpi")),
            "core_cpi": _latest(fred.get("core_cpi")),
            "unemployment": _latest(fred.get("unemployment")),
            "gdp_growth": _latest(fred.get("gdp")),
            "vix": _latest(fred.get("vix")),
            "gold": commodities.get("gold", {}).get("price"),
            "crude_oil": commodities.get("crude_oil", {}).get("price"),
            "natural_gas": commodities.get("natural_gas", {}).get("price"),
            "copper": commodities.get("copper", {}).get("price"),
            "wheat": commodities.get("wheat", {}).get("price"),
            "silver": commodities.get("silver", {}).get("price"),
            "sector_etfs": sector_etfs,
            "timestamp": raw.get("timestamp"),
        }
