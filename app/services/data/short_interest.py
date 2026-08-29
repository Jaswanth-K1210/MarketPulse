"""
Short Interest Service — FINRA short interest data.
Sources FINRA's public CDN for bi-monthly short interest and daily short volume.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

FINRA_BASE = "https://cdn.finra.org/equity/regsho"
FINRA_SHORT_INTEREST = "https://www.finra.org/finra-data/browse-catalog/short-interest"

class ShortInterestService:
    async def get_short_interest(self, ticker: str) -> dict:
        """Get short interest data for a ticker."""
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "short_interest_shares": None,
            "days_to_cover": None,
            "short_pct_float": None,
            "short_volume_today": None,
            "total_volume_today": None,
            "short_ratio_today": None,
            "sources": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        source = await self._get_yfinance_short_data(ticker)
        if source:
            result.update(source)
            result["sources"].append("yfinance")
        else:
            source = await self._get_finra_daily_short_volume(ticker)
            if source:
                result.update(source)
                result["sources"].append("finra_daily")

        return result

    async def _get_yfinance_short_data(self, ticker: str) -> Optional[dict]:
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info

            short_pct = info.get("shortPercentOfFloat")
            short_ratio = info.get("shortRatio")
            shares_short = info.get("sharesShort")

            if short_pct is None and shares_short is None:
                return None

            return {
                "short_interest_shares": shares_short,
                "days_to_cover": short_ratio,
                "short_pct_float": short_pct * 100 if short_pct else None,
            }
        except Exception as e:
            logger.debug(f"yfinance short data failed for {ticker}: {e}")
            return None

    async def _get_finra_daily_short_volume(self, ticker: str) -> Optional[dict]:
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            url = f"{FINRA_BASE}/DailyShortSaleVolume/DailyShortSaleVolume_{date_str}.json"

            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=15)
                if resp.status_code != 200:
                    return None

                data = resp.json()
                for entry in data:
                    if entry.get("symbol", "").upper() == ticker:
                        short_vol = int(entry.get("shortVolume", 0))
                        total_vol = int(entry.get("totalVolume", 0))
                        ratio = short_vol / total_vol if total_vol > 0 else 0

                        return {
                            "short_volume_today": short_vol,
                            "total_volume_today": total_vol,
                            "short_ratio_today": round(ratio, 4),
                        }

            return None
        except Exception as e:
            logger.debug(f"FINRA daily short volume failed for {ticker}: {e}")
            return None

    def score_short_interest(self, data: dict) -> float:
        """Score short interest from -5 (very bearish) to +5 (very bullish).
        High short interest = bearish sentiment, but can also signal squeeze.
        """
        short_pct = data.get("short_pct_float")
        short_ratio = data.get("short_ratio_today")
        days_to_cover = data.get("days_to_cover")

        if short_pct is None and short_ratio is None:
            return 0.0

        score = 0.0

        if short_pct is not None:
            if short_pct > 40:
                score = -4.0
            elif short_pct > 25:
                score = -2.5
            elif short_pct > 15:
                score = -1.0
            elif short_pct > 8:
                score = -0.5
            elif short_pct > 3:
                score = 1.0
            else:
                score = 2.0

        if short_ratio is not None:
            if short_ratio > 5:
                score = min(score, -3.0)
            elif short_ratio > 2:
                score = min(score, -1.0)

        return max(-5.0, min(5.0, score))


short_interest_service = ShortInterestService()
