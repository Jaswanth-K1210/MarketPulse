"""
Memory Agent — Redis-backed cross-run ticker memory.

Orchestration paper insight: a shared memory agent that persists state across runs
is what makes multi-agent coherent. Without it, each pipeline run is stateless —
the system can't say "this is the third bearish signal on NVDA this week."

Architecture:
  - Redis sorted sets per ticker: score = timestamp, value = signal JSON
  - Auto-expires entries older than 30 days
  - Query functions for temporal patterns (streaks, frequency, trend)
  - Falls back to in-memory dict when Redis is unavailable
"""
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MEMORY_PREFIX = "mp:memory:"
MEMORY_TTL_DAYS = 30


class MemoryAgent:
    """
    Cross-run memory for tickers. Stores signal history and provides
    temporal query functions that make the system feel intelligent.
    """

    def __init__(self):
        self._redis = None
        self._fallback: Dict[str, List[dict]] = {}  # in-memory fallback
        self._init_redis()

    def _init_redis(self):
        try:
            import redis
            self._redis = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=3)
            self._redis.ping()
            logger.info("MemoryAgent: Redis connected")
        except Exception as e:
            logger.warning(f"MemoryAgent: Redis unavailable ({e}), using in-memory fallback")
            self._redis = None

    def _key(self, ticker: str) -> str:
        return f"{MEMORY_PREFIX}{ticker.upper()}"

    # ── Store signals ────────────────────────────────────────────────────────

    def record_signal(
        self,
        ticker: str,
        sentiment: float,
        impact_pct: float,
        confidence: float,
        headline: str = "",
        source: str = "pipeline",
    ) -> None:
        """Record a signal for a ticker. Called after each pipeline run."""
        ticker = ticker.upper()
        entry = {
            "sentiment": round(sentiment, 4),
            "impact_pct": round(impact_pct, 4),
            "confidence": round(confidence, 4),
            "headline": headline[:200],
            "source": source,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        score = time.time()  # Redis sorted set score = unix timestamp
        value = json.dumps(entry)

        if self._redis:
            try:
                key = self._key(ticker)
                self._redis.zadd(key, {value: score})
                # Trim to last 30 days
                cutoff = time.time() - MEMORY_TTL_DAYS * 86400
                self._redis.zremrangebyscore(key, "-inf", cutoff)
                self._redis.expire(key, MEMORY_TTL_DAYS * 86400)
            except Exception as e:
                logger.debug(f"MemoryAgent Redis write failed: {e}")
                self._fallback_store(ticker, entry)
        else:
            self._fallback_store(ticker, entry)

    def _fallback_store(self, ticker: str, entry: dict) -> None:
        if ticker not in self._fallback:
            self._fallback[ticker] = []
        self._fallback[ticker].append(entry)
        # Keep last 200 entries in memory
        self._fallback[ticker] = self._fallback[ticker][-200:]

    # ── Query signals ────────────────────────────────────────────────────────

    def get_signals(self, ticker: str, hours: int = 168) -> List[dict]:
        """Get all signals for a ticker within the last N hours (default: 7 days)."""
        ticker = ticker.upper()
        cutoff = time.time() - hours * 3600

        if self._redis:
            try:
                key = self._key(ticker)
                raw = self._redis.zrangebyscore(key, cutoff, "+inf")
                return [json.loads(r) for r in raw]
            except Exception:
                pass

        # Fallback
        entries = self._fallback.get(ticker, [])
        cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            e for e in entries
            if e.get("ts", "") >= cutoff_dt.isoformat()
        ]

    def count_signals(self, ticker: str, direction: str = "all", hours: int = 168) -> int:
        """Count signals for a ticker. direction: 'bullish', 'bearish', 'all'."""
        signals = self.get_signals(ticker, hours)
        if direction == "all":
            return len(signals)
        return sum(
            1 for s in signals
            if (direction == "bullish" and s.get("sentiment", 0) > 0.2)
            or (direction == "bearish" and s.get("sentiment", 0) < -0.2)
        )

    def get_streak(self, ticker: str, hours: int = 168) -> Dict[str, Any]:
        """
        Detect consecutive signal streak. Returns:
        {direction: 'bullish'|'bearish'|'mixed', count: int, total_impact: float}
        """
        signals = self.get_signals(ticker, hours)
        if not signals:
            return {"direction": "none", "count": 0, "total_impact": 0.0}

        # Walk backwards from most recent
        streak_dir = None
        streak_count = 0
        total_impact = 0.0

        for sig in reversed(signals):
            sent = sig.get("sentiment", 0)
            current_dir = "bullish" if sent > 0.2 else "bearish" if sent < -0.2 else "neutral"

            if streak_dir is None:
                streak_dir = current_dir
                streak_count = 1
                total_impact = sig.get("impact_pct", 0)
            elif current_dir == streak_dir or current_dir == "neutral":
                streak_count += 1
                total_impact += sig.get("impact_pct", 0)
            else:
                break

        return {
            "direction": streak_dir or "mixed",
            "count": streak_count,
            "total_impact": round(total_impact, 4),
        }

    def get_trend(self, ticker: str, hours: int = 168) -> Dict[str, Any]:
        """
        Compute sentiment trend over time. Returns:
        {trend: 'improving'|'deteriorating'|'stable', avg_sentiment: float, signal_count: int}
        """
        signals = self.get_signals(ticker, hours)
        if len(signals) < 2:
            return {"trend": "insufficient_data", "avg_sentiment": 0.0, "signal_count": len(signals)}

        sentiments = [s.get("sentiment", 0) for s in signals]
        avg = sum(sentiments) / len(sentiments)

        # Compare first half vs second half
        mid = len(sentiments) // 2
        first_half = sum(sentiments[:mid]) / max(mid, 1)
        second_half = sum(sentiments[mid:]) / max(len(sentiments) - mid, 1)

        diff = second_half - first_half
        if diff > 0.1:
            trend = "improving"
        elif diff < -0.1:
            trend = "deteriorating"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "avg_sentiment": round(avg, 4),
            "signal_count": len(signals),
            "momentum": round(diff, 4),
        }

    def build_temporal_context(self, ticker: str) -> str:
        """
        Build a natural-language temporal context string for LLM prompts.
        This is what makes agents say "third bearish signal this week."
        """
        streak = self.get_streak(ticker)
        trend = self.get_trend(ticker)
        bearish_count = self.count_signals(ticker, "bearish")
        bullish_count = self.count_signals(ticker, "bullish")
        total = self.count_signals(ticker, "all")

        lines = [f"=== TEMPORAL MEMORY: {ticker} (7-day) ==="]
        lines.append(f"Total signals: {total} ({bullish_count} bullish, {bearish_count} bearish)")

        if streak["count"] >= 2:
            lines.append(
                f"Active streak: {streak['count']} consecutive {streak['direction']} signals "
                f"(cumulative impact: {streak['total_impact']:+.2f}%)"
            )

        if trend["trend"] != "insufficient_data":
            lines.append(
                f"Sentiment trend: {trend['trend']} "
                f"(avg: {trend['avg_sentiment']:+.3f}, momentum: {trend['momentum']:+.3f})"
            )

        return "\n".join(lines)

    # ── Bulk operations ──────────────────────────────────────────────────────

    def record_pipeline_results(self, state: dict) -> None:
        """
        Called after a full pipeline run to record all signals.
        Reads from LangGraph state and stores per-ticker.
        """
        portfolio = state.get("portfolio", [])
        classified = state.get("classified_articles", [])
        stock_impacts = state.get("stock_impacts", [])
        confidence = state.get("confidence_score", 0.5)

        # Record from classified articles
        for article in classified:
            ticker = article.get("ticker", "")
            if not ticker or ticker == "UNKNOWN":
                continue
            self.record_signal(
                ticker=ticker,
                sentiment=article.get("sentiment_score", 0),
                impact_pct=next(
                    (s.get("impact_pct", 0) for s in stock_impacts if s.get("ticker") == ticker),
                    0.0,
                ),
                confidence=confidence,
                headline=article.get("title", "")[:200],
                source="pipeline",
            )

        logger.info(f"MemoryAgent: Recorded signals for {len(classified)} articles")


# Singleton
memory_agent = MemoryAgent()
