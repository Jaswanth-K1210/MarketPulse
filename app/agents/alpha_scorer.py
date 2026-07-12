"""
Alpha Score Agent — LangGraph agent node.
Combines FinBERT + insider activity + options flow + retail sentiment into alpha score.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def agent_alpha_scorer(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("---EXECUTING AGENT: ALPHA SCORER---")

    classified = state.get("classified_articles", [])
    portfolio = state.get("portfolio", [])

    base_score = 0.0
    signals = []
    alpha_details = []

    for article in classified:
        ticker = article.get("ticker", "")
        sentiment = article.get("sentiment_score", 0)
        confidence = article.get("confidence", 0.5)
        factor = article.get("factor_name", "")

        weighted = sentiment * confidence * 2
        base_score += weighted

        signals.append({
            "ticker": ticker,
            "sentiment_alpha": round(weighted, 3),
            "factor": factor,
            "confidence": confidence,
        })

        if abs(weighted) > 1.0:
            alpha_details.append(f"{ticker}: {weighted:+.2f} alpha from '{factor}'")

    if portfolio:
        from app.services.intelligence.alpha_aggregator import alpha_aggregator
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(1) as pool:
                    ticker_alphas = {}
                    def fetch_alpha(t):
                        try:
                            return asyncio.run(alpha_aggregator.get_alpha_score(t))
                        except Exception:
                            return None
                    for t in portfolio[:5]:
                        fut = pool.submit(fetch_alpha, t)
                        try:
                            result = fut.result(timeout=15)
                            if result:
                                ticker_alphas[t] = result
                        except Exception:
                            continue
            else:
                ticker_alphas = {}
                for t in portfolio[:5]:
                    try:
                        result = loop.run_until_complete(alpha_aggregator.get_alpha_score(t))
                        if result:
                            ticker_alphas[t] = result
                    except Exception:
                        continue
        except Exception:
            ticker_alphas = {}

        for t, result in ticker_alphas.items():
            alpha_val = result.get("alpha_score", 0)
            base_score += alpha_val * 0.3
            signals.append({
                "ticker": t,
                "alpha_score": alpha_val,
                "signal": result.get("signal", "NEUTRAL"),
            })
            if abs(alpha_val) > 3:
                alpha_details.append(f"{t}: Alpha={alpha_val:+.1f} ({result.get('signal', 'NEUTRAL')})")

    alpha_total = max(-10.0, min(10.0, base_score))

    convergence_signals = []
    if len(signals) >= 3:
        tickers_with_sentiment = set(s["ticker"] for s in signals if "sentiment_alpha" in s)
        tickers_with_alpha = set(s["ticker"] for s in signals if "alpha_score" in s)
        converging = tickers_with_sentiment & tickers_with_alpha
        for t in converging:
            convergence_signals.append(f"Signal convergence detected on {t}")

    return {
        "alpha_score_total": round(alpha_total, 2),
        "alpha_signal": "STRONG_BUY" if alpha_total >= 5 else
                       "BUY" if alpha_total >= 2 else
                       "NEUTRAL" if alpha_total >= -2 else
                       "SELL" if alpha_total >= -5 else
                       "STRONG_SELL",
        "alpha_details": alpha_details[:5],
        "alpha_convergence_signals": convergence_signals,
        "workflow_status": f"Alpha score calculated: {alpha_total:+.1f} ({len(signals)} signals)",
    }
