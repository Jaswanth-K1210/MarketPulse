"""Tests for memory_agent.py — Redis-backed ticker memory with in-memory fallback."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch
from app.services.memory_agent import MemoryAgent, memory_agent


@pytest.fixture(autouse=True)
def _clear_global_state():
    """Reset the global singleton between tests to prevent leakage."""
    memory_agent._fallback.clear()
    yield
    memory_agent._fallback.clear()


@pytest.fixture
def agent():
    """MemoryAgent with in-memory fallback (Redis mocked out)."""
    with patch.object(MemoryAgent, "_init_redis", lambda self: None):
        a = MemoryAgent()
        a._redis = None
    return a


class TestRecordSignal:
    def test_record_signal_no_crash(self, agent):
        agent.record_signal(
            ticker="AAPL",
            sentiment=-0.8,
            impact_pct=-3.5,
            confidence=0.85,
            headline="Apple drops",
            source="alpha_scorer",
        )

    def test_record_signal_stores_data(self, agent):
        agent.record_signal(
            ticker="AAPL",
            sentiment=-0.8,
            impact_pct=-3.5,
            confidence=0.85,
            headline="Apple drops",
            source="alpha_scorer",
        )
        signals = agent.get_signals("AAPL")
        assert len(signals) == 1
        assert signals[0]["sentiment"] == -0.8
        assert signals[0]["impact_pct"] == -3.5
        assert signals[0]["headline"] == "Apple drops"


class TestGetSignals:
    def test_empty_ticker_returns_empty(self, agent):
        signals = agent.get_signals("NONEXISTENT")
        assert signals == []

    def test_limit_by_hours(self, agent):
        agent.record_signal(ticker="AAPL", sentiment=-0.5, impact_pct=-1, confidence=0.8, source="test")
        signals_168h = agent.get_signals("AAPL", hours=168)
        signals_0h = agent.get_signals("AAPL", hours=0)
        assert len(signals_168h) == 1
        assert len(signals_0h) == 0


class TestGetStreak:
    def test_no_signals(self, agent):
        streak = agent.get_streak("AAPL")
        assert streak["direction"] == "none"
        assert streak["count"] == 0

    def test_single_signal(self, agent):
        agent.record_signal(ticker="AAPL", sentiment=-0.8, impact_pct=-2, confidence=0.8, source="test")
        streak = agent.get_streak("AAPL")
        assert streak["direction"] == "bearish"
        assert streak["count"] == 1

    def test_matching_signals(self, agent):
        for _ in range(3):
            agent.record_signal(ticker="AAPL", sentiment=-0.8, impact_pct=-2, confidence=0.8, source="test")
        streak = agent.get_streak("AAPL")
        assert streak["direction"] == "bearish"
        assert streak["count"] == 3

    def test_opposite_signal_breaks_streak(self, agent):
        agent.record_signal(ticker="AAPL", sentiment=-0.8, impact_pct=-2, confidence=0.8, source="test")
        agent.record_signal(ticker="AAPL", sentiment=0.8, impact_pct=2, confidence=0.8, source="test")
        streak = agent.get_streak("AAPL")
        assert streak["direction"] == "bullish"
        assert streak["count"] == 1


class TestGetTrend:
    def test_no_signals(self, agent):
        trend = agent.get_trend("AAPL")
        assert trend["trend"] == "insufficient_data"
        assert trend["signal_count"] == 0

    def test_single_signal(self, agent):
        agent.record_signal(ticker="AAPL", sentiment=-0.5, impact_pct=-1, confidence=0.8, source="test")
        trend = agent.get_trend("AAPL")
        assert trend["trend"] == "insufficient_data"
        assert trend["signal_count"] == 1

    def test_multiple_signals(self, agent):
        for _ in range(4):
            agent.record_signal(ticker="AAPL", sentiment=-0.8, impact_pct=-2, confidence=0.8, source="test")
        trend = agent.get_trend("AAPL")
        assert trend["trend"] in ["stable", "improving", "deteriorating"]
        assert trend["signal_count"] == 4
        assert trend["avg_sentiment"] < 0


class TestBuildTemporalContext:
    def test_returns_string(self, agent):
        ctx = agent.build_temporal_context("NONEXISTENT")
        assert isinstance(ctx, str)
        assert "NONEXISTENT" in ctx

    def test_populated_ticker(self, agent):
        for _ in range(3):
            agent.record_signal(ticker="AAPL", sentiment=-0.8, impact_pct=-2, confidence=0.8, source="test")
        ctx = agent.build_temporal_context("AAPL")
        assert isinstance(ctx, str)
        assert "AAPL" in ctx
        assert "bearish" in ctx.lower() or "streak" in ctx.lower()

    def test_context_mentions_signal_count(self, agent):
        agent.record_signal(ticker="AAPL", sentiment=-0.5, impact_pct=-1, confidence=0.8, source="test")
        ctx = agent.build_temporal_context("AAPL")
        assert "Total signals" in ctx


class TestCountSignals:
    def test_count_all(self, agent):
        agent.record_signal(ticker="AAPL", sentiment=-0.8, impact_pct=-1, confidence=0.8, source="test")
        agent.record_signal(ticker="AAPL", sentiment=0.8, impact_pct=1, confidence=0.8, source="test")
        assert agent.count_signals("AAPL", "all") == 2

    def test_count_bearish(self, agent):
        agent.record_signal(ticker="AAPL", sentiment=-0.8, impact_pct=-1, confidence=0.8, source="test")
        agent.record_signal(ticker="AAPL", sentiment=0.8, impact_pct=1, confidence=0.8, source="test")
        assert agent.count_signals("AAPL", "bearish") == 1

    def test_count_bullish(self, agent):
        agent.record_signal(ticker="AAPL", sentiment=-0.8, impact_pct=-1, confidence=0.8, source="test")
        agent.record_signal(ticker="AAPL", sentiment=0.8, impact_pct=1, confidence=0.8, source="test")
        assert agent.count_signals("AAPL", "bullish") == 1
