"""
Signal Convergence Agent — LangGraph agent node (TOOL-FIRST).

Detects multi-source convergence across:
- News sentiment (FinBERT)
- Technical indicators (RSI, MACD, Bollinger)
- Options flow (put/call, unusual activity)
- Insider activity (Form 4 filings)
- Correlation engine signals (silent divergence, keyword spikes)
- Alpha signals from different categories

FinSphere insight: convergence across INDEPENDENT signal categories
is the strongest predictor of actionable intelligence.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _get_tool_direction(tool_data: dict) -> str:
    """Determine bullish/bearish/neutral direction from a tool's score."""
    if isinstance(tool_data, dict) and "error" not in tool_data:
        score = tool_data.get("score", 0.0)
        if score > 1.0:
            return "bullish"
        elif score < -1.0:
            return "bearish"
    return "neutral"


def agent_convergence_detector(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    TOOL-FIRST convergence detection:
    1. Extract directions from each quantitative tool category
    2. Compare with news sentiment direction
    3. Check correlation engine for structural patterns
    4. Compute convergence zones where 3+ independent sources agree
    """
    logger.info("---EXECUTING AGENT: SIGNAL CONVERGENCE DETECTOR (TOOL-FIRST)---")

    classified = state.get("classified_articles", [])
    quant_data = state.get("quant_tool_data", {})
    correlation_raw = state.get("correlation_signals", [])
    regime = state.get("market_regime", "sideways")

    convergence_zones = []
    confidence_boost = 0.0
    total_signals = 0

    # ── Build per-ticker signal vectors ──────────────────────────────────────
    # Each ticker gets a dict of {category: direction}
    ticker_signals: Dict[str, Dict[str, str]] = {}

    # 1. News sentiment → direction per ticker
    for article in classified:
        ticker = article.get("ticker", "")
        if not ticker or ticker == "UNKNOWN":
            continue
        if ticker not in ticker_signals:
            ticker_signals[ticker] = {}
        sentiment = article.get("sentiment_score", 0)
        if sentiment > 0.3:
            ticker_signals[ticker]["news"] = "bullish"
        elif sentiment < -0.3:
            ticker_signals[ticker]["news"] = "bearish"
        else:
            ticker_signals[ticker].setdefault("news", "neutral")

    # 2. Quant tool signals → direction per ticker per category
    TOOL_CATEGORIES = ["technical", "options_flow", "insider", "fundamentals", "short_interest", "retail_sentiment"]
    for ticker, tools in quant_data.items():
        if ticker not in ticker_signals:
            ticker_signals[ticker] = {}
        for category in TOOL_CATEGORIES:
            tool_data = tools.get(category, {})
            direction = _get_tool_direction(tool_data)
            ticker_signals[ticker][category] = direction

    # ── Detect convergence per ticker ────────────────────────────────────────
    for ticker, directions in ticker_signals.items():
        categories = list(directions.keys())
        if len(categories) < 2:
            continue

        bullish_sources = [c for c, d in directions.items() if d == "bullish"]
        bearish_sources = [c for c, d in directions.items() if d == "bearish"]
        neutral_sources = [c for c, d in directions.items() if d == "neutral"]

        # STRONG convergence: 3+ sources same direction
        if len(bullish_sources) >= 3:
            strength = "high" if len(bullish_sources) >= 4 else "medium"
            convergence_zones.append({
                "ticker": ticker,
                "type": "multi_source_convergence",
                "strength": strength,
                "direction": "bullish",
                "sources": bullish_sources,
                "description": (
                    f"{len(bullish_sources)} independent sources bullish on {ticker}: "
                    f"{', '.join(bullish_sources)}"
                ),
            })
            confidence_boost += 0.15 if strength == "high" else 0.10
            total_signals += 1

        elif len(bearish_sources) >= 3:
            strength = "high" if len(bearish_sources) >= 4 else "medium"
            convergence_zones.append({
                "ticker": ticker,
                "type": "multi_source_convergence",
                "strength": strength,
                "direction": "bearish",
                "sources": bearish_sources,
                "description": (
                    f"{len(bearish_sources)} independent sources bearish on {ticker}: "
                    f"{', '.join(bearish_sources)}"
                ),
            })
            confidence_boost += 0.15 if strength == "high" else 0.10
            total_signals += 1

        # MEDIUM convergence: news + at least one quant tool agree
        elif len(bullish_sources) >= 2 or len(bearish_sources) >= 2:
            direction = "bullish" if len(bullish_sources) > len(bearish_sources) else "bearish"
            sources = bullish_sources if direction == "bullish" else bearish_sources
            convergence_zones.append({
                "ticker": ticker,
                "type": "dual_source_convergence",
                "strength": "medium",
                "direction": direction,
                "sources": sources,
                "description": (
                    f"{len(sources)} sources {direction} on {ticker}: {', '.join(sources)}"
                ),
            })
            confidence_boost += 0.05
            total_signals += 1

        # CONTRADICTION: tools disagree → flag it, reduce confidence
        if bullish_sources and bearish_sources:
            convergence_zones.append({
                "ticker": ticker,
                "type": "signal_contradiction",
                "strength": "warning",
                "direction": "mixed",
                "sources": categories,
                "description": (
                    f"Contradictory signals on {ticker}: "
                    f"bullish({', '.join(bullish_sources)}) vs "
                    f"bearish({', '.join(bearish_sources)})"
                ),
            })
            confidence_boost -= 0.05
            total_signals += 1

    # ── Correlation engine signals ───────────────────────────────────────────
    for corr in correlation_raw:
        sig_type = corr.get("type", corr.get("signal_type", ""))
        description = corr.get("description", corr.get("detail", ""))
        confidence = corr.get("confidence", 0.7)

        if sig_type in ("silent_divergence", "sector_rotation", "news_market_alignment"):
            convergence_zones.append({
                "ticker": "PORTFOLIO",
                "type": f"correlation_{sig_type}",
                "strength": "high" if confidence > 0.8 else "medium",
                "direction": "mixed",
                "sources": ["correlation_engine"],
                "description": description,
            })
            confidence_boost += 0.10
            total_signals += 1

    # ── Regime alignment bonus ───────────────────────────────────────────────
    if regime and regime != "sideways":
        regime_aligned = 0
        for ticker, directions in ticker_signals.items():
            # In bull regime, bullish convergence gets a boost
            if regime == "bull" and len([d for d in directions.values() if d == "bullish"]) >= 2:
                regime_aligned += 1
            elif regime == "bear" and len([d for d in directions.values() if d == "bearish"]) >= 2:
                regime_aligned += 1

        if regime_aligned > 0:
            convergence_zones.append({
                "ticker": "PORTFOLIO",
                "type": "regime_alignment",
                "strength": "medium",
                "direction": regime,
                "sources": ["regime_detector"],
                "description": f"{regime_aligned} tickers have signals aligned with {regime} regime",
            })
            confidence_boost += 0.05
            total_signals += 1

    # ── Compute final confidence ─────────────────────────────────────────────
    old_confidence = state.get("confidence_score", 0.5)
    new_confidence = min(1.0, max(0.0, old_confidence + confidence_boost))

    return {
        "convergence_zones": convergence_zones,
        "confidence_score": round(new_confidence, 3),
        "confidence_boost": round(confidence_boost, 3),
        "converged_signals_count": total_signals,
        "workflow_status": (
            f"Convergence: {len(convergence_zones)} zones "
            f"({total_signals} signals), conf boost {confidence_boost:+.2f}"
        ),
    }
