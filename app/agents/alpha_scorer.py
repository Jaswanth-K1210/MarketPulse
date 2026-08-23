"""
Alpha Score Agent — LangGraph agent node (TOOL-FIRST).

FinSphere insight: the LLM's job is to SYNTHESITE tool outputs, not reason from raw text.
This node reads pre-computed quantitative tool data from state (dispatched by quant_tool_dispatcher),
computes a weighted composite score, and optionally calls LLM for nuanced synthesis.
"""
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _format_news_for_alpha(classified_articles: List[Dict], ticker: str) -> str:
    """Extract news sentiment signals relevant to this ticker."""
    relevant = [a for a in classified_articles if a.get("ticker") == ticker]
    if not relevant:
        return "No relevant news articles."

    lines = []
    for a in relevant[:5]:
        sentiment = a.get("sentiment_score", 0)
        factor = a.get("factor_name", "unknown")
        confidence = a.get("confidence", 0.5)
        lines.append(f"- {factor}: sentiment={sentiment:+.3f}, confidence={confidence:.2f}")
    return "\n".join(lines)


def agent_alpha_scorer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    TOOL-FIRST alpha scoring:
    1. Read pre-computed tool data from state (from quant_tool_dispatcher)
    2. Compute weighted composite from tool scores
    3. If tools disagree or data is sparse, call LLM to synthesize
    4. Always produce structured output
    """
    logger.info("---EXECUTING AGENT: ALPHA SCORER (TOOL-FIRST)---")

    classified = state.get("classified_articles", [])
    portfolio = state.get("portfolio", [])
    quant_data = state.get("quant_tool_data", {})
    regime = state.get("market_regime", "sideways")

    # ── Collect all unique tickers to score ───────────────────────────────────
    tickers = set()
    for article in classified:
        t = article.get("ticker", "")
        if t and t != "UNKNOWN":
            tickers.add(t)
    for t in portfolio:
        if t:
            tickers.add(t)
    tickers = list(tickers)[:10]  # Cap at 10 to avoid LLM token explosion

    signals = []
    alpha_details = []
    llm_synthesis = ""

    for ticker in tickers:
        ticker_quant = quant_data.get(ticker, {})
        composite = ticker_quant.get("composite_scores", {})

        # ── Primary: Use composite score from tools ──────────────────────────
        if composite and composite.get("tools_succeeded", 0) >= 2:
            tool_alpha = composite.get("alpha_score", 0.0)
            tool_signal = composite.get("signal", "NEUTRAL")
            agreement = composite.get("agreement", "insufficient_data")
            coverage = composite.get("data_coverage", 0)

            # Weight by data coverage (low coverage = less confidence)
            coverage_weight = min(1.0, coverage / 80.0)
            weighted_alpha = tool_alpha * coverage_weight

            signals.append({
                "ticker": ticker,
                "tool_alpha": tool_alpha,
                "weighted_alpha": round(weighted_alpha, 3),
                "tool_signal": tool_signal,
                "agreement": agreement,
                "coverage": coverage,
                "source": "quant_tools",
            })

            if abs(weighted_alpha) > 1.5:
                alpha_details.append(
                    f"{ticker}: {weighted_alpha:+.2f} alpha "
                    f"(tools: {tool_signal}, agreement: {agreement}, coverage: {coverage}%)"
                )

        # ── Secondary: News sentiment contribution ───────────────────────────
        news_sentiment = 0.0
        news_count = 0
        for article in classified:
            if article.get("ticker") == ticker:
                news_sentiment += article.get("sentiment_score", 0) * article.get("confidence", 0.5)
                news_count += 1

        if news_count > 0:
            avg_news = news_sentiment / news_count
            # News gets 30% weight in final score
            signals.append({
                "ticker": ticker,
                "news_sentiment": round(avg_news, 3),
                "news_count": news_count,
                "source": "news",
            })

    # ── Compute final alpha score ────────────────────────────────────────────
    tool_signals = [s for s in signals if s.get("source") == "quant_tools"]
    news_signals = [s for s in signals if s.get("source") == "news"]

    base_score = 0.0
    if tool_signals:
        # Average of tool-weighted alphas
        base_score = sum(s["weighted_alpha"] for s in tool_signals) / len(tool_signals)

    if news_signals:
        avg_news = sum(s["news_sentiment"] for s in news_signals) / len(news_signals)
        # Blend: 70% tools, 30% news
        base_score = base_score * 0.7 + avg_news * 5.0 * 0.3  # scale news to [-5, +5] range

    alpha_total = max(-10.0, min(10.0, base_score))

    # ── LLM synthesis when tools disagree ────────────────────────────────────
    has_disagreement = any(s.get("agreement") == "mixed" for s in tool_signals)
    low_coverage = any(s.get("coverage", 0) < 50 for s in tool_signals)

    ticks = [s["ticker"] for s in tool_signals][:3]
    if (has_disagreement or low_coverage) and ticks:
        try:
            from app.ml.llm_router import llm_router
            from app.ml.prompts import ALPHA_SCORER_SYNTHESIS, SYSTEM_PREFIX

            for ticker in ticks:
                ticker_data = quant_data.get(ticker, {})
                if not ticker_data:
                    continue

                tool_summary = _format_tool_output_for_llm(ticker, ticker_data)
                news_summary = _format_news_for_alpha(classified, ticker)

                prompt = ALPHA_SCORER_SYNTHESIS.format(
                    system_prefix=SYSTEM_PREFIX,
                    ticker=ticker,
                    tool_output=f"{tool_summary}\n\nNEWS:\n{news_summary}",
                    regime=regime or "unknown",
                )

                raw = llm_router.call("fast", prompt, retries=1)
                if raw:
                    # Try to extract JSON from LLM response
                    clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.MULTILINE)
                    parsed = json.loads(clean)
                    llm_alpha = parsed.get("alpha_score", alpha_total)
                    llm_synthesis = raw[:500]

                    # Blend LLM synthesis with tool composite (LLM gets 30% weight when available)
                    alpha_total = alpha_total * 0.7 + llm_alpha * 0.3
                    alpha_total = max(-10.0, min(10.0, alpha_total))
                    break
        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e} — using tool composite only")

    # ── Convergence detection ────────────────────────────────────────────────
    convergence_signals = []
    tickers_with_tools = set(s["ticker"] for s in tool_signals)
    tickers_with_news = set(s["ticker"] for s in news_signals)
    converging = tickers_with_tools & tickers_with_news
    for t in converging:
        convergence_signals.append(f"Signal convergence detected on {t}")

    # ── Build signal label ───────────────────────────────────────────────────
    if alpha_total >= 5:
        signal = "STRONG_BUY"
    elif alpha_total >= 2:
        signal = "BUY"
    elif alpha_total >= -2:
        signal = "NEUTRAL"
    elif alpha_total >= -5:
        signal = "SELL"
    else:
        signal = "STRONG_SELL"

    return {
        "alpha_score_total": round(alpha_total, 2),
        "alpha_signal": signal,
        "alpha_details": alpha_details[:5],
        "alpha_convergence_signals": convergence_signals,
        "alpha_llm_synthesis": llm_synthesis,
        "workflow_status": (
            f"Alpha score calculated: {alpha_total:+.1f} ({signal}) "
            f"from {len(tool_signals)} tool sets + {len(news_signals)} news signals"
        ),
    }


def _format_tool_output_for_llm(ticker: str, data: dict) -> str:
    """Format tool data into a concise string for LLM consumption."""
    from app.services.data.quant_tools import quant_tool_dispatcher
    return quant_tool_dispatcher.format_for_llm(ticker, data)
