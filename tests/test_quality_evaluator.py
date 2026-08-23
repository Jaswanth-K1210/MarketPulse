"""Tests for quality_evaluator.py — AnalyScore 5-dimension rubric."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.quality_evaluator import QualityEvaluator


class TestQualityEvaluator:
    @pytest.fixture
    def evaluator(self):
        return QualityEvaluator()

    @pytest.fixture
    def good_state(self):
        return {
            "alerts": [{"ticker": "AAPL", "sentiment": "bearish", "confidence": 0.9}],
            "news_articles": [{"title": "Test", "source": "reuters"}],
            "classified_articles": [
                {"ticker": "AAPL", "classification": "earnings"},
                {"ticker": "AAPL", "classification": "guidance"},
                {"ticker": "AAPL", "classification": "macro"},
            ],
            "stock_impacts": [{"ticker": "AAPL", "impact_score": -3.5}],
            "discovered_relationships": [{"from_node": "AAPL", "to_node": "MSFT", "relationship": "competitor"}],
            "confidence_score": 0.88,
            "portfolio_total_impact": -2.1,
            "validation_decision": "ALERT",
            "alpha_score_total": 0.75,
            "alpha_signal": "BEARISH",
            "convergence_zones": [{"ticker": "AAPL", "sources": 3}],
            "temporal_context": {"AAPL": {"streak_count": 2}},
            "kg_context": {"AAPL": {"sector": "Technology"}},
            "audit_summary": {"total_time_ms": 4500, "nodes": {}},
            "portfolio": ["AAPL", "MSFT"],
        }

    def test_evaluate_returns_required_keys(self, evaluator, good_state):
        result = evaluator.evaluate(good_state)
        assert "overall_score" in result
        assert "grade" in result
        assert "dimensions" in result
        for dim in ["accuracy", "relevance", "depth", "timeliness", "actionability"]:
            assert dim in result["dimensions"]

    def test_evaluate_perfect_state(self, evaluator, good_state):
        result = evaluator.evaluate(good_state)
        assert result["overall_score"] >= 0.4
        assert result["grade"] in ["A", "B", "C", "D", "F"]

    def test_evaluate_empty_state(self, evaluator):
        result = evaluator.evaluate({})
        assert result["overall_score"] < 0.5
        assert result["grade"] in ["C", "D", "F"]

    def test_grade_boundaries(self, evaluator):
        # Test grading thresholds through evaluate
        # Empty state should be low
        result_empty = evaluator.evaluate({})
        assert result_empty["grade"] in ["C", "D", "F"]

        # State with quant tool data should boost accuracy
        state_with_tools = {
            "quant_tool_data": {
                "AAPL": {
                    "composite_scores": {"agreement": "strong_agreement"}
                }
            }
        }
        result_tools = evaluator.evaluate(state_with_tools)
        assert result_tools["dimensions"]["accuracy"]["score"] >= 0.8

    def test_actionability_with_signal(self, evaluator):
        state = {"alpha_signal": "BEARISH", "confidence_score": 0.8, "alert_created": True, "stock_impacts": [{"ticker": "AAPL"}]}
        result = evaluator.evaluate(state)
        assert result["dimensions"]["actionability"]["score"] >= 0.7

    def test_actionability_neutral(self, evaluator):
        state = {"alpha_signal": "NEUTRAL", "confidence_score": 0.3}
        result = evaluator.evaluate(state)
        assert result["dimensions"]["actionability"]["score"] < 0.5

    def test_depth_with_multiple_sources(self, evaluator, good_state):
        result = evaluator.evaluate(good_state)
        assert result["dimensions"]["depth"]["score"] >= 0.3

    def test_relevance_with_portfolio(self, evaluator, good_state):
        result = evaluator.evaluate(good_state)
        assert result["dimensions"]["relevance"]["score"] >= 0.3

    def test_relevance_no_portfolio(self, evaluator):
        result = evaluator.evaluate({})
        assert result["dimensions"]["relevance"]["score"] == 0.5  # default
