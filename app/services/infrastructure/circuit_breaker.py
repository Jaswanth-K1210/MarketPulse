"""
Circuit Breaker — Failure tracking, cooldown periods, and stale data fallback.
Ported from WorldMonitor's resilience patterns.
"""

import time
import logging
import asyncio
from typing import Any, Callable, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # In cooldown, rejecting calls
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitStats:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    stale_served: int = 0
    cooldown_rejections: int = 0


@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    source: str = "fresh"


class CircuitBreaker:
    """
    Circuit breaker with stale-while-revalidate fallback.

    States:
    - CLOSED: Normal operation, tracking failures
    - OPEN: In cooldown, serving stale data
    - HALF_OPEN: Testing recovery with single request

    Features:
    - Failure counting per key
    - Configurable cooldown period
    - Stale data serving during outages
    - Request coalescing (multiple callers share single upstream fetch)
    - Statistics tracking
    """

    def __init__(
        self,
        name: str,
        max_failures: int = 3,
        cooldown_seconds: int = 300,
        max_stale_age_seconds: int = 3600,
    ):
        self.name = name
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self.max_stale_age = max_stale_age_seconds

        self._failures: dict[str, int] = {}
        self._cooldown_until: dict[str, float] = {}
        self._stale_cache: dict[str, CacheEntry] = {}
        self._inflight: dict[str, asyncio.Future] = {}
        self._stats = CircuitStats()

    @property
    def status(self) -> str:
        """Overall circuit status."""
        open_keys = [k for k, v in self._cooldown_until.items() if time.time() < v]
        if open_keys:
            return "open"
        return "closed"

    @property
    def failure_count(self) -> int:
        return sum(self._failures.values())

    @property
    def stats(self) -> CircuitStats:
        return self._stats

    def get_state(self, key: str) -> CircuitState:
        """Get circuit state for a specific key."""
        cooldown = self._cooldown_until.get(key, 0)
        if time.time() < cooldown:
            return CircuitState.OPEN
        elif self._failures.get(key, 0) >= self.max_failures:
            # Cooldown expired, try half-open
            return CircuitState.HALF_OPEN
        return CircuitState.CLOSED

    def _is_in_cooldown(self, key: str) -> bool:
        cooldown = self._cooldown_until.get(key, 0)
        return time.time() < cooldown

    def _record_success(self, key: str) -> None:
        self._failures[key] = 0
        self._cooldown_until.pop(key, None)
        self._stats.successful_calls += 1

    def _record_failure(self, key: str) -> None:
        count = self._failures.get(key, 0) + 1
        self._failures[key] = count
        self._stats.failed_calls += 1

        if count >= self.max_failures:
            self._cooldown_until[key] = time.time() + self.cooldown_seconds
            logger.warning(
                f"Circuit breaker [{self.name}] OPEN for key '{key}' "
                f"({count} failures). Cooldown: {self.cooldown_seconds}s"
            )

    def _get_stale(self, key: str) -> Optional[Any]:
        entry = self._stale_cache.get(key)
        if entry is None:
            return None
        age = time.time() - entry.timestamp
        if age > self.max_stale_age:
            del self._stale_cache[key]
            return None
        return entry.data

    def _update_stale(self, key: str, data: Any) -> None:
        self._stale_cache[key] = CacheEntry(
            data=data,
            timestamp=time.time(),
            source="stale"
        )

    async def call(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        fallback: Optional[Any] = None,
    ) -> Optional[Any]:
        """
        Execute a function with circuit breaker protection.

        Args:
            key: Unique identifier for this operation (e.g., "newsapi:tech")
            fetch_fn: Async or sync callable to execute
            fallback: Default value if all recovery fails

        Returns:
            Fresh data, stale data, or fallback value
        """
        self._stats.total_calls += 1

        # Check cooldown
        if self._is_in_cooldown(key):
            self._stats.cooldown_rejections += 1
            stale = self._get_stale(key)
            if stale is not None:
                self._stats.stale_served += 1
                logger.debug(f"Circuit [{self.name}] serving stale for '{key}'")
                return stale
            return fallback

        # Request coalescing — if another caller is fetching same key, wait
        if key in self._inflight:
            try:
                return await self._inflight[key]
            except Exception:
                return self._get_stale(key) or fallback

        # Execute
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._inflight[key] = future

        try:
            # Support both sync and async callables
            if asyncio.iscoroutinefunction(fetch_fn):
                result = await fetch_fn()
            else:
                result = fetch_fn()

            # Success
            self._record_success(key)
            self._update_stale(key, result)

            if not future.done():
                future.set_result(result)
            return result

        except Exception as e:
            self._record_failure(key)
            logger.warning(
                f"Circuit [{self.name}] failure for '{key}': {type(e).__name__}: {e}"
            )

            # Try stale fallback
            stale = self._get_stale(key)
            if stale is not None:
                self._stats.stale_served += 1
                if not future.done():
                    future.set_result(stale)
                return stale

            if not future.done():
                future.set_exception(e)
            return fallback

        finally:
            self._inflight.pop(key, None)

    def call_sync(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        fallback: Optional[Any] = None,
    ) -> Optional[Any]:
        """Synchronous version of call() for non-async contexts."""
        self._stats.total_calls += 1

        if self._is_in_cooldown(key):
            self._stats.cooldown_rejections += 1
            stale = self._get_stale(key)
            if stale is not None:
                self._stats.stale_served += 1
                return stale
            return fallback

        try:
            result = fetch_fn()
            self._record_success(key)
            self._update_stale(key, result)
            return result
        except Exception as e:
            self._record_failure(key)
            logger.warning(f"Circuit [{self.name}] sync failure for '{key}': {e}")
            stale = self._get_stale(key)
            if stale is not None:
                self._stats.stale_served += 1
                return stale
            return fallback

    def reset(self, key: Optional[str] = None) -> None:
        """Reset circuit state for a key or all keys."""
        if key:
            self._failures.pop(key, None)
            self._cooldown_until.pop(key, None)
        else:
            self._failures.clear()
            self._cooldown_until.clear()


# ============================================================
# Pre-configured circuit breaker instances
# ============================================================
news_circuit = CircuitBreaker("news", max_failures=3, cooldown_seconds=300)
market_circuit = CircuitBreaker("market", max_failures=3, cooldown_seconds=180)
llm_circuit = CircuitBreaker("llm", max_failures=5, cooldown_seconds=600)
conflict_circuit = CircuitBreaker("conflict", max_failures=3, cooldown_seconds=300)
macro_circuit = CircuitBreaker("macro", max_failures=3, cooldown_seconds=600)
