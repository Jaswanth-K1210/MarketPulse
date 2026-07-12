"""
Financial Fundamentals Service — Key financial metrics from yfinance.
Provides PE, EPS, revenue, profit margins, and growth metrics.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class FinancialFundamentalsService:
    async def get_fundamentals(self, ticker: str) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "market_cap": None,
            "pe_ratio": None,
            "forward_pe": None,
            "eps": None,
            "eps_growth": None,
            "revenue": None,
            "revenue_growth": None,
            "profit_margin": None,
            "debt_to_equity": None,
            "current_ratio": None,
            "dividend_yield": None,
            "beta": None,
            "52w_high": None,
            "52w_low": None,
            "price_to_book": None,
            "free_cash_flow": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info:
                return result

            result["market_cap"] = info.get("marketCap")
            result["pe_ratio"] = info.get("trailingPE")
            result["forward_pe"] = info.get("forwardPE")
            result["eps"] = info.get("trailingEps")
            result["eps_growth"] = info.get("earningsGrowth")
            result["revenue"] = info.get("totalRevenue")
            result["revenue_growth"] = info.get("revenueGrowth")
            result["profit_margin"] = info.get("profitMargins")
            result["debt_to_equity"] = info.get("debtToEquity")
            result["current_ratio"] = info.get("currentRatio")
            result["dividend_yield"] = info.get("dividendYield")
            result["beta"] = info.get("beta")
            result["52w_high"] = info.get("fiftyTwoWeekHigh")
            result["52w_low"] = info.get("fiftyTwoWeekLow")
            result["price_to_book"] = info.get("priceToBook")
            result["free_cash_flow"] = info.get("freeCashflow")

        except Exception as e:
            logger.warning(f"Fundamentals fetch failed for {ticker}: {e}")

        return result

    def score_fundamentals(self, data: dict) -> float:
        """Score fundamentals from -5 (very bearish) to +5 (very bullish)."""
        score = 0.0
        pe = data.get("pe_ratio")
        forward_pe = data.get("forward_pe")
        earnings_growth = data.get("eps_growth")
        revenue_growth = data.get("revenue_growth")
        profit_margin = data.get("profit_margin")
        beta = data.get("beta")

        if pe is not None:
            if 10 < pe < 20:
                score += 1.5
            elif 20 <= pe < 30:
                score += 0.5
            elif 30 <= pe < 50:
                score -= 0.5
            elif pe > 50:
                score -= 1.5
            elif 0 < pe <= 10:
                score += 2.0
            elif pe < 0:
                score -= 1.0

        if forward_pe is not None and pe is not None:
            if forward_pe < pe:
                score += 1.0

        if earnings_growth is not None:
            if earnings_growth > 0.2:
                score += 2.0
            elif earnings_growth > 0.1:
                score += 1.0
            elif earnings_growth < -0.1:
                score -= 1.5
            elif earnings_growth < 0:
                score -= 0.5

        if revenue_growth is not None:
            if revenue_growth > 0.2:
                score += 1.5
            elif revenue_growth > 0.1:
                score += 0.5
            elif revenue_growth < 0:
                score -= 1.0

        if profit_margin is not None:
            if profit_margin > 0.2:
                score += 1.0
            elif profit_margin > 0.1:
                score += 0.5
            elif profit_margin < 0:
                score -= 1.0

        if beta is not None:
            if 0.8 < beta < 1.2:
                score += 0.5
            elif beta > 2.0:
                score -= 0.5

        return max(-5.0, min(5.0, score))


financial_fundamentals_service = FinancialFundamentalsService()
