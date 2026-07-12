"""
Alpha Aggregator — Combines multiple OSINT signals into a single Alpha Score.
Score ranges from -10 (Strong Sell) to +10 (Strong Buy).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

SIGNAL_WEIGHTS = {
    "insider": 0.25,
    "short_interest": 0.15,
    "sentiment": 0.15,
    "technical": 0.20,
    "fundamentals": 0.25,
}


class AlphaAggregator:
    def __init__(self):
        self.weights = SIGNAL_WEIGHTS

    async def get_alpha_score(self, ticker: str) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "alpha_score": 0.0,
            "signal": "NEUTRAL",
            "components": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        from app.services.data.insider_trades import insider_trades_service
        from app.services.data.short_interest import short_interest_service
        from app.services.data.retail_sentiment import retail_sentiment_service
        from app.services.data.technical_analysis import technical_analysis_service
        from app.services.data.financial_fundamentals import financial_fundamentals_service

        insider_raw = await insider_trades_service.get_insider_trades(ticker)
        insider_score = insider_trades_service.score_insider_activity(insider_raw)
        result["components"]["insider"] = {
            "score": round(insider_score, 2),
            "trades_count": len(insider_raw),
            "details": insider_raw[:5],
        }

        short_raw = await short_interest_service.get_short_interest(ticker)
        short_score = short_interest_service.score_short_interest(short_raw)
        result["components"]["short_interest"] = {
            "score": round(short_score, 2),
            "details": short_raw,
        }

        sent_raw = await retail_sentiment_service.get_sentiment(ticker)
        sent_score = retail_sentiment_service.score_sentiment(sent_raw)
        result["components"]["sentiment"] = {
            "score": round(sent_score, 2),
            "bullish_pct": sent_raw.get("bullish_pct", 0),
            "bearish_pct": sent_raw.get("bearish_pct", 0),
            "total_mentions": sent_raw.get("total_mentions", 0),
        }

        tech_raw = await technical_analysis_service.get_indicators(ticker)
        tech_score = technical_analysis_service.score_technical(tech_raw)
        result["components"]["technical"] = {
            "score": round(tech_score, 2),
            "price": tech_raw.get("price"),
            "rsi": tech_raw.get("rsi"),
            "signals": tech_raw.get("signals", []),
        }

        fund_raw = await financial_fundamentals_service.get_fundamentals(ticker)
        fund_score = financial_fundamentals_service.score_fundamentals(fund_raw)
        result["components"]["fundamentals"] = {
            "score": round(fund_score, 2),
            "pe_ratio": fund_raw.get("pe_ratio"),
            "revenue_growth": fund_raw.get("revenue_growth"),
        }

        alpha = (
            insider_score * self.weights["insider"]
            + short_score * self.weights["short_interest"]
            + sent_score * self.weights["sentiment"]
            + tech_score * self.weights["technical"]
            + fund_score * self.weights["fundamentals"]
        )

        result["alpha_score"] = round(alpha, 2)

        if alpha >= 5:
            result["signal"] = "STRONG_BUY"
        elif alpha >= 2:
            result["signal"] = "BUY"
        elif alpha >= -2:
            result["signal"] = "NEUTRAL"
        elif alpha >= -5:
            result["signal"] = "SELL"
        else:
            result["signal"] = "STRONG_SELL"

        active_signals = []
        if insider_score > 2:
            active_signals.append(f"Insider buying active (+{insider_score:.1f})")
        elif insider_score < -2:
            active_signals.append(f"Insider selling active ({insider_score:.1f})")

        if sent_score > 2:
            active_signals.append(f"Retail bullish (+{sent_score:.1f})")
        elif sent_score < -2:
            active_signals.append(f"Retail bearish ({sent_score:.1f})")

        if tech_score > 2:
            active_signals.append(f"Technical bullish (+{tech_score:.1f})")
        elif tech_score < -2:
            active_signals.append(f"Technical bearish ({tech_score:.1f})")

        if fund_score > 2:
            active_signals.append(f"Strong fundamentals (+{fund_score:.1f})")

        result["active_signals"] = active_signals
        return result


alpha_aggregator = AlphaAggregator()
