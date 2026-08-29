"""
Quality Evaluator — FinSphere's AnalyScore adapted for MarketPulse.

5 dimensions scored by lightweight heuristics (no LLM call):
  1. Accuracy — do tools agree with each other?
  2. Relevance — is the alert about the user's portfolio?
  3. Depth — how many data sources contributed?
  4. Timeliness — how fresh is the data?
  5. Actionability — does the alert recommend a specific action?

Scores stored in alerts table → enables dashboard "confidence meter."
Periodic batch eval with LLM-as-judge for deeper quality checks.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QualityEvaluator:
    """
    Evaluates alert quality on 5 dimensions.
    Run automatically after every alert generation.
    """

    def evaluate(
        self,
        state: Dict[str, Any],
        alert_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Score alert quality across 5 dimensions.
        Returns {dimensions: {...}, overall_score: float, grade: str}
        """
        dimensions = {}

        # ── 1. Accuracy: tool agreement ──────────────────────────────────────
        dimensions["accuracy"] = self._score_accuracy(state)

        # ── 2. Relevance: portfolio coverage ─────────────────────────────────
        dimensions["relevance"] = self._score_relevance(state)

        # ── 3. Depth: data source diversity ──────────────────────────────────
        dimensions["depth"] = self._score_depth(state)

        # ── 4. Timeliness: data freshness ────────────────────────────────────
        dimensions["timeliness"] = self._score_timeliness(state)

        # ── 5. Actionability: clear recommendation ───────────────────────────
        dimensions["actionability"] = self._score_actionability(state)

        # ── Overall score (weighted average) ─────────────────────────────────
        weights = {"accuracy": 0.25, "relevance": 0.15, "depth": 0.25, "timeliness": 0.15, "actionability": 0.20}
        overall = sum(dimensions[d]["score"] * weights[d] for d in weights)
        overall = round(max(0.0, min(1.0, overall)), 3)

        grade = (
            "A" if overall >= 0.8 else
            "B" if overall >= 0.6 else
            "C" if overall >= 0.4 else
            "D" if overall >= 0.2 else
            "F"
        )

        return {
            "dimensions": dimensions,
            "overall_score": overall,
            "grade": grade,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _score_accuracy(self, state: Dict) -> Dict[str, Any]:
        """Tool agreement = accuracy proxy."""
        quant_data = state.get("quant_tool_data", {})
        if not quant_data:
            return {"score": 0.3, "detail": "No quantitative tools dispatched"}

        agreeing = 0
        total = 0
        for ticker, tools in quant_data.items():
            composite = tools.get("composite_scores", {})
            agreement = composite.get("agreement", "insufficient_data")
            if agreement == "strong_agreement":
                agreeing += 2
            elif agreement == "partial":
                agreeing += 1
            total += 2

        if total == 0:
            return {"score": 0.3, "detail": "No tool data"}

        score = agreeing / total
        return {"score": round(score, 3), "detail": f"{agreeing}/{total} agreement units"}

    def _score_relevance(self, state: Dict) -> Dict[str, Any]:
        """Portfolio coverage = relevance proxy."""
        portfolio = set(state.get("portfolio", []))
        classified = state.get("classified_articles", [])
        stock_impacts = state.get("stock_impacts", [])

        if not portfolio:
            return {"score": 0.5, "detail": "No portfolio defined"}

        # How many portfolio tickers had impacts?
        impacted_tickers = set(s.get("ticker") for s in stock_impacts)
        coverage = len(impacted_tickers & portfolio) / len(portfolio)

        return {
            "score": round(min(1.0, coverage + 0.3), 3),  # Base 0.3 + coverage
            "detail": f"{len(impacted_tickers & portfolio)}/{len(portfolio)} portfolio tickers impacted",
        }

    def _score_depth(self, state: Dict) -> Dict[str, Any]:
        """Data source diversity = depth proxy."""
        sources_used = set()

        # News articles
        if state.get("classified_articles"):
            sources_used.add("news")

        # Quant tools
        quant_data = state.get("quant_tool_data", {})
        for ticker, tools in quant_data.items():
            for tool_name in ["technical", "options_flow", "insider", "fundamentals", "short_interest", "retail_sentiment"]:
                tool_data = tools.get(tool_name, {})
                if isinstance(tool_data, dict) and "error" not in tool_data:
                    sources_used.add(f"quant_{tool_name}")

        # Correlation engine
        if state.get("correlation_signals"):
            sources_used.add("correlation_engine")

        # GNN
        if state.get("gnn_results"):
            sources_used.add("gnn")

        # Monte Carlo
        if state.get("monte_carlo"):
            sources_used.add("monte_carlo")

        # Knowledge graph
        if state.get("kg_context"):
            sources_used.add("knowledge_graph")

        # Memory
        if state.get("temporal_context"):
            sources_used.add("memory")

        max_sources = 10
        score = min(1.0, len(sources_used) / max_sources)
        return {
            "score": round(score, 3),
            "detail": f"{len(sources_used)} data sources: {', '.join(sorted(sources_used)[:5])}",
        }

    def _score_timeliness(self, state: Dict) -> Dict[str, Any]:
        """Data freshness = timeliness proxy."""
        last_fetch = state.get("last_fetch_time", "")
        if not last_fetch:
            return {"score": 0.3, "detail": "No fetch timestamp"}

        try:
            fetch_time = datetime.fromisoformat(last_fetch)
            if fetch_time.tzinfo is None:
                fetch_time = fetch_time.replace(tzinfo=timezone.utc)
            age_minutes = (datetime.now(timezone.utc) - fetch_time).total_seconds() / 60

            if age_minutes < 5:
                score = 1.0
            elif age_minutes < 15:
                score = 0.8
            elif age_minutes < 60:
                score = 0.6
            else:
                score = 0.3

            return {"score": round(score, 3), "detail": f"Data age: {age_minutes:.0f} minutes"}
        except Exception:
            return {"score": 0.5, "detail": "Timestamp parse error"}

    def _score_actionability(self, state: Dict) -> Dict[str, Any]:
        """Has a clear recommendation = actionability proxy."""
        alpha_signal = state.get("alpha_signal", "NEUTRAL")
        confidence = state.get("confidence_score", 0)
        has_impact = bool(state.get("stock_impacts"))
        has_alert = state.get("alert_created", False)

        score = 0.0
        if alpha_signal != "NEUTRAL":
            score += 0.3
        if confidence >= 0.7:
            score += 0.2
        if has_impact:
            score += 0.2
        if has_alert:
            score += 0.3

        return {
            "score": round(min(1.0, score), 3),
            "detail": f"Signal: {alpha_signal}, confidence: {confidence:.2f}, alert: {has_alert}",
        }


# Singleton
quality_evaluator = QualityEvaluator()
