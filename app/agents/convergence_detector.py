"""
Signal Convergence Agent — LangGraph agent node.
Detects multi-source convergence to boost/lower confidence.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def agent_convergence_detector(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("---EXECUTING AGENT: SIGNAL CONVERGENCE DETECTOR---")

    classified = state.get("classified_articles", [])
    alpha_details = state.get("alpha_details", [])
    alpha_convergence = state.get("alpha_convergence_signals", [])
    stock_impacts = state.get("stock_impacts", [])

    convergence_zones = []
    confidence_boost = 0.0
    total_signals = 0

    for article in classified:
        ticker = article.get("ticker", "")
        sentiment = article.get("sentiment_score", 0)
        factor = article.get("factor_name", "")
        event_type = article.get("event_type", "")

        matching_impacts = [s for s in stock_impacts if s.get("ticker") == ticker]

        if matching_impacts and abs(sentiment) > 0.3:
            avg_impact = sum(s.get("impact_pct", 0) for s in matching_impacts) / len(matching_impacts)
            direction_match = (sentiment > 0 and avg_impact > 0) or (sentiment < 0 and avg_impact < 0)

            if direction_match:
                convergence_zones.append({
                    "ticker": ticker,
                    "type": "sentiment_impact",
                    "strength": "high" if abs(sentiment) > 0.6 else "medium",
                    "description": f"Sentiment ({sentiment:+.2f}) aligned with impact ({avg_impact:+.2f}%)",
                })
                confidence_boost += 0.1
                total_signals += 1

        if ticker and factor:
            convergence_zones.append({
                "ticker": ticker,
                "type": "news_factor",
                "strength": "medium",
                "description": f"News classified as '{factor}' for {ticker}",
            })
            total_signals += 1

    for signal in alpha_convergence:
        convergence_zones.append({
            "ticker": signal.split(" on ")[-1] if " on " in signal else "",
            "type": "multi_signal_convergence",
            "strength": "high",
            "description": signal,
        })
        confidence_boost += 0.15
        total_signals += 1

    if len(classified) >= 3:
        factors = set(a.get("factor_name", "") for a in classified if a.get("factor_name"))
        if len(factors) >= 2:
            convergence_zones.append({
                "ticker": "PORTFOLIO",
                "type": "multi_factor",
                "strength": "medium",
                "description": f"{len(factors)} distinct factors detected: {', '.join(factors)}",
            })
            confidence_boost += 0.05

    old_confidence = state.get("confidence_score", 0.5)
    new_confidence = min(1.0, old_confidence + confidence_boost)

    return {
        "convergence_zones": convergence_zones,
        "confidence_score": round(new_confidence, 3),
        "confidence_boost": round(confidence_boost, 3),
        "converged_signals_count": total_signals,
        "workflow_status": f"Convergence: {len(convergence_zones)} zones, conf boost {confidence_boost:+.2f}",
    }
