"""
Alpha Aggregator — Combines multiple OSINT signals into a single Alpha Score.
Score ranges from -10 (Strong Sell) to +10 (Strong Buy).

Sources fail independently and often (rate limits, retired endpoints, missing
API keys). The aggregator therefore tracks which components actually returned
data and renormalises the weights over those, so a dead source cannot silently
drag the composite toward zero. Below MIN_COVERAGE the score is reported but
the BUY/SELL signal is withheld.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.disclaimer import DISCLAIMER

logger = logging.getLogger(__name__)

SIGNAL_WEIGHTS = {
    "insider": 0.25,
    "short_interest": 0.15,
    "sentiment": 0.15,
    "technical": 0.20,
    "fundamentals": 0.25,
}

from app.services.evidence import MIN_COVERAGE, SourceResult, aggregate


def _has_data(component: str, raw) -> bool:
    """Did this source actually return anything, as opposed to failing quietly?"""
    if raw is None:
        return False
    if component == "insider":
        return bool(raw)
    if not isinstance(raw, dict):
        return False
    if raw.get("error"):
        return False
    if component == "short_interest":
        return bool(raw.get("sources")) and raw.get("short_pct_float") is not None
    if component == "sentiment":
        return bool(raw.get("sources")) and (raw.get("total_mentions") or 0) > 0
    if component == "technical":
        return raw.get("price") is not None and raw.get("rsi") is not None
    if component == "fundamentals":
        return any(
            raw.get(k) is not None
            for k in ("pe_ratio", "revenue_growth", "market_cap", "profit_margin")
        )
    return bool(raw)


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
            "coverage": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        from app.services.data.insider_trades import insider_trades_service
        from app.services.data.short_interest import short_interest_service
        from app.services.data.retail_sentiment import retail_sentiment_service
        from app.services.data.technical_analysis import technical_analysis_service
        from app.services.data.financial_fundamentals import financial_fundamentals_service

        # Fetch concurrently — these are independent network calls and running
        # them in series made the endpoint several times slower than necessary.
        raw = await asyncio.gather(
            insider_trades_service.get_insider_trades(ticker),
            short_interest_service.get_short_interest(ticker),
            retail_sentiment_service.get_sentiment(ticker),
            technical_analysis_service.get_indicators(ticker),
            financial_fundamentals_service.get_fundamentals(ticker),
            return_exceptions=True,
        )
        insider_raw, short_raw, sent_raw, tech_raw, fund_raw = [
            None if isinstance(r, BaseException) else r for r in raw
        ]
        for name, r in zip(SIGNAL_WEIGHTS, raw):
            if isinstance(r, BaseException):
                logger.warning("Alpha component %s failed for %s: %s", name, ticker, r)

        insider_score = insider_trades_service.score_insider_activity(insider_raw or [])
        short_score = short_interest_service.score_short_interest(short_raw or {})
        sent_score = retail_sentiment_service.score_sentiment(sent_raw or {})
        tech_score = technical_analysis_service.score_technical(tech_raw or {})
        fund_score = financial_fundamentals_service.score_fundamentals(fund_raw or {})

        live = {
            "insider": _has_data("insider", insider_raw),
            "short_interest": _has_data("short_interest", short_raw),
            "sentiment": _has_data("sentiment", sent_raw),
            "technical": _has_data("technical", tech_raw),
            "fundamentals": _has_data("fundamentals", fund_raw),
        }

        result["components"] = {
            "insider": {
                "score": round(insider_score, 2),
                "available": live["insider"],
                "trades_count": len(insider_raw or []),
                "details": (insider_raw or [])[:5],
            },
            "short_interest": {
                "score": round(short_score, 2),
                "available": live["short_interest"],
                "details": short_raw or {},
            },
            "sentiment": {
                "score": round(sent_score, 2),
                "available": live["sentiment"],
                "bullish_pct": (sent_raw or {}).get("bullish_pct", 0),
                "bearish_pct": (sent_raw or {}).get("bearish_pct", 0),
                "total_mentions": (sent_raw or {}).get("total_mentions", 0),
            },
            "technical": {
                "score": round(tech_score, 2),
                "available": live["technical"],
                "price": (tech_raw or {}).get("price"),
                "rsi": (tech_raw or {}).get("rsi"),
                "signals": (tech_raw or {}).get("signals", []),
            },
            "fundamentals": {
                "score": round(fund_score, 2),
                "available": live["fundamentals"],
                "pe_ratio": (fund_raw or {}).get("pe_ratio"),
                "revenue_growth": (fund_raw or {}).get("revenue_growth"),
            },
        }

        scores = {
            "insider": insider_score,
            "short_interest": short_score,
            "sentiment": sent_score,
            "technical": tech_score,
            "fundamentals": fund_score,
        }

        # Wrap each component in the shared evidence contract. Sources that
        # already return a SourceResult pass straight through; the rest are
        # judged by _has_data until they are converted.
        raws = {
            "insider": insider_raw,
            "short_interest": short_raw,
            "sentiment": sent_raw,
            "technical": tech_raw,
            "fundamentals": fund_raw,
        }
        results = {}
        for name, raw in raws.items():
            if isinstance(raw, SourceResult):
                results[name] = raw
            elif _has_data(name, raw):
                results[name] = SourceResult.ok(name, raw)
            else:
                reason = "no data returned"
                if isinstance(raw, dict) and raw.get("error"):
                    reason = str(raw["error"])
                results[name] = SourceResult.dead(name, reason)

        agg = aggregate(results, self.weights, scores=scores,
                        min_coverage=MIN_COVERAGE)
        result["coverage"] = agg["coverage"]
        result["oldest_as_of"] = agg["oldest_as_of"]

        alpha = agg["value"] if agg["value"] is not None else 0.0
        result["alpha_score"] = round(alpha, 2)

        if not result["coverage"]["sufficient"]:
            result["signal"] = "INSUFFICIENT_DATA"
            result["signal_note"] = agg["reason"]
        elif alpha >= 5:
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
        if live["insider"] and insider_score > 2:
            active_signals.append(f"Insider buying active (+{insider_score:.1f})")
        elif live["insider"] and insider_score < -2:
            active_signals.append(f"Insider selling active ({insider_score:.1f})")

        if live["sentiment"] and sent_score > 2:
            active_signals.append(f"Retail bullish (+{sent_score:.1f})")
        elif live["sentiment"] and sent_score < -2:
            active_signals.append(f"Retail bearish ({sent_score:.1f})")

        if live["technical"] and tech_score > 2:
            active_signals.append(f"Technical bullish (+{tech_score:.1f})")
        elif live["technical"] and tech_score < -2:
            active_signals.append(f"Technical bearish ({tech_score:.1f})")

        if live["fundamentals"] and fund_score > 2:
            active_signals.append(f"Strong fundamentals (+{fund_score:.1f})")

        result["active_signals"] = active_signals
        result["disclaimer"] = DISCLAIMER
        return result

alpha_aggregator = AlphaAggregator()
