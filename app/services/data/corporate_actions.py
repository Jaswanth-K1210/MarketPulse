"""
Corporate Actions Calendar — Dividends, splits, M&A from Yahoo Finance.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class CorporateActionsService:
    async def get_actions(self, ticker: str, days_ahead: int = 90) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "dividends": [],
            "splits": [],
            "upcoming_events": [],
            "ex_dividend_date": None,
            "next_earnings_date": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            result["next_earnings_date"] = info.get("earningsDate", [None])[0] if info.get("earningsDate") else None
            ex_div = info.get("exDividendDate")
            if ex_div:
                result["ex_dividend_date"] = datetime.fromtimestamp(ex_div).isoformat() if isinstance(ex_div, (int, float)) else str(ex_div)

            divs = stock.dividends
            if divs is not None and not divs.empty:
                recent_divs = divs.tail(12)
                result["dividends"] = [
                    {"date": str(idx.date()) if hasattr(idx, "date") else str(idx), "amount": round(float(val), 4)}
                    for idx, val in recent_divs.items()
                ]

            splits = stock.splits
            if splits is not None and not splits.empty:
                recent_splits = splits.tail(5)
                result["splits"] = [
                    {"date": str(idx.date()) if hasattr(idx, "date") else str(idx), "ratio": round(float(val), 4)}
                    for idx, val in recent_splits.items()
                ]

            cal = stock.calendar
            if cal is not None and not cal.empty:
                if "Earnings Date" in cal.index:
                    result["next_earnings_date"] = str(cal.loc["Earnings Date"].iloc[0])
                if "Ex-Dividend Date" in cal.index:
                    result["ex_dividend_date"] = str(cal.loc["Ex-Dividend Date"].iloc[0])

        except Exception as e:
            logger.warning(f"Corporate actions fetch failed for {ticker}: {e}")

        return result

    def score_corporate_actions(self, data: dict) -> float:
        score = 0.0
        dividends = data.get("dividends", [])

        if dividends:
            recent = dividends[-4:]
            if len(recent) >= 4:
                amounts = [d.get("amount", 0) for d in recent]
                if len(amounts) >= 2 and amounts[-1] > amounts[0]:
                    score += 1.0

        splits = data.get("splits", [])
        if splits:
            score += 0.5

        if data.get("ex_dividend_date"):
            score += 0.5

        return max(-5.0, min(5.0, score))


corporate_actions_service = CorporateActionsService()
