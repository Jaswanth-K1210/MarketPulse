"""
Multi-Layer Cache Manager — 4-layer caching with request coalescing.
Ported from WorldMonitor's distributed caching architecture.

Layers:
  L0: Bootstrap seed (JSON files on disk) — instant first load
  L1: In-memory (Python dict with timestamps) — zero latency
  L2: Redis (shared across workers/restarts) — cross-process
  L3: Stale fallback (separate Redis key) — served when upstream fails
"""

import json
import time
import asyncio
import logging
from typing import Any, Callable, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Negative sentinel value — cached to prevent request storms on failed upstreams
NEGATIVE_SENTINEL = "__MP_NEG__"
NEGATIVE_TTL = 120  # seconds


@dataclass
class TTLConfig:
    """TTL configuration for a cache entry."""
    memory_ttl: int = 300        # L1: in-memory (seconds)
    redis_ttl: int = 900         # L2: Redis (seconds)
    stale_ttl: int = 3600        # L3: stale fallback (seconds)


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    data: Any
    timestamp: float
    source: str = "fresh"

    def is_expired(self, ttl: int) -> bool:
        return (time.time() - self.timestamp) > ttl


@dataclass
class CacheResult:
    """Result from cache lookup."""
    data: Any
    source: str  # "memory", "redis", "stale", "bootstrap", "fresh", "miss", "negative"
    age_seconds: float = 0


# Default TTL configs by data type
TTL_CONFIGS = {
    "news": TTLConfig(memory_ttl=300, redis_ttl=900, stale_ttl=3600),
    "market": TTLConfig(memory_ttl=60, redis_ttl=300, stale_ttl=1800),
    "macro": TTLConfig(memory_ttl=480, redis_ttl=3600, stale_ttl=7200),
    "conflict": TTLConfig(memory_ttl=600, redis_ttl=1800, stale_ttl=3600),
    "risk_scores": TTLConfig(memory_ttl=600, redis_ttl=900, stale_ttl=3600),
    "signals": TTLConfig(memory_ttl=300, redis_ttl=600, stale_ttl=1800),
    "classification": TTLConfig(memory_ttl=86400, redis_ttl=86400, stale_ttl=172800),
    "default": TTLConfig(memory_ttl=300, redis_ttl=900, stale_ttl=3600),
}


class CacheManager:
    """
    4-layer cache manager with request coalescing and negative sentinels.
    """

    def __init__(self, redis_client=None, bootstrap_path: Optional[str] = None):
        self.memory: dict[str, CacheEntry] = {}
        self.redis = redis_client
        self.bootstrap: dict[str, Any] = {}
        self._inflight: dict[str, asyncio.Future] = {}
        self._stats = {
            "hits_memory": 0, "hits_redis": 0, "hits_stale": 0,
            "hits_bootstrap": 0, "misses": 0, "negative_hits": 0,
        }

        if bootstrap_path:
            self._load_bootstrap(bootstrap_path)

    def _load_bootstrap(self, path: str) -> None:
        """Load bootstrap seed data from JSON file."""
        try:
            bootstrap_file = Path(path)
            if bootstrap_file.exists():
                with open(bootstrap_file) as f:
                    self.bootstrap = json.load(f)
                logger.info(f"Bootstrap seed loaded: {len(self.bootstrap)} keys")
        except Exception as e:
            logger.warning(f"Could not load bootstrap seed: {e}")

    def get_ttl_config(self, data_type: str) -> TTLConfig:
        """Get TTL config for a data type."""
        return TTL_CONFIGS.get(data_type, TTL_CONFIGS["default"])

    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        data_type: str = "default",
        ttl_config: Optional[TTLConfig] = None,
    ) -> CacheResult:
        """
        Get data from cache or fetch from upstream.

        Resolution order: L1 (memory) → L2 (Redis) → fetch → L3 (stale) → L0 (bootstrap)
        """
        config = ttl_config or self.get_ttl_config(data_type)

        # L1: In-memory cache
        memory_result = self._check_memory(key, config)
        if memory_result:
            return memory_result

        # L2: Redis cache
        redis_result = await self._check_redis(key, config)
        if redis_result:
            return redis_result

        # Request coalescing
        if key in self._inflight:
            try:
                return await self._inflight[key]
            except Exception:
                pass

        # Fetch from upstream
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._inflight[key] = future

        try:
            if asyncio.iscoroutinefunction(fetch_fn):
                data = await fetch_fn()
            else:
                data = fetch_fn()

            if data is not None:
                result = CacheResult(data=data, source="fresh", age_seconds=0)
                self._store(key, data, config)
                if not future.done():
                    future.set_result(result)
                return result

        except Exception as e:
            logger.warning(f"Cache fetch failed for '{key}': {e}")
            # Store negative sentinel to prevent storms
            await self._store_negative(key)

        finally:
            self._inflight.pop(key, None)

        # L3: Stale fallback
        stale_result = await self._check_stale(key)
        if stale_result:
            if not future.done():
                future.set_result(stale_result)
            return stale_result

        # L0: Bootstrap seed
        if key in self.bootstrap:
            self._stats["hits_bootstrap"] += 1
            result = CacheResult(data=self.bootstrap[key], source="bootstrap")
            if not future.done():
                future.set_result(result)
            return result

        self._stats["misses"] += 1
        miss_result = CacheResult(data=None, source="miss")
        if not future.done():
            future.set_result(miss_result)
        return miss_result

    def _check_memory(self, key: str, config: TTLConfig) -> Optional[CacheResult]:
        """Check L1 in-memory cache."""
        entry = self.memory.get(key)
        if entry and not entry.is_expired(config.memory_ttl):
            self._stats["hits_memory"] += 1
            return CacheResult(
                data=entry.data,
                source="memory",
                age_seconds=time.time() - entry.timestamp
            )
        return None

    async def _check_redis(self, key: str, config: TTLConfig) -> Optional[CacheResult]:
        """Check L2 Redis cache."""
        if not self.redis:
            return None
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            if raw == NEGATIVE_SENTINEL:
                self._stats["negative_hits"] += 1
                return CacheResult(data=None, source="negative")

            data = json.loads(raw) if isinstance(raw, str) else raw
            # Populate memory cache
            self.memory[key] = CacheEntry(data=data, timestamp=time.time(), source="redis")
            self._stats["hits_redis"] += 1
            return CacheResult(data=data, source="redis")
        except Exception as e:
            logger.debug(f"Redis check failed for '{key}': {e}")
            return None

    async def _check_stale(self, key: str) -> Optional[CacheResult]:
        """Check L3 stale fallback."""
        if not self.redis:
            # Fallback: check memory with relaxed TTL
            entry = self.memory.get(key)
            if entry and not entry.is_expired(3600):
                self._stats["hits_stale"] += 1
                return CacheResult(
                    data=entry.data, source="stale",
                    age_seconds=time.time() - entry.timestamp
                )
            return None

        try:
            raw = await self.redis.get(f"stale:{key}")
            if raw and raw != NEGATIVE_SENTINEL:
                data = json.loads(raw) if isinstance(raw, str) else raw
                self._stats["hits_stale"] += 1
                return CacheResult(data=data, source="stale")
        except Exception:
            pass
        return None

    def _store(self, key: str, data: Any, config: TTLConfig) -> None:
        """Store data in all cache layers."""
        # L1: Memory
        self.memory[key] = CacheEntry(data=data, timestamp=time.time(), source="fresh")

        # L2 + L3: Redis (fire and forget in background)
        if self.redis:
            asyncio.ensure_future(self._store_redis(key, data, config))

    async def _store_redis(self, key: str, data: Any, config: TTLConfig) -> None:
        """Store in Redis (L2 + L3)."""
        try:
            serialized = json.dumps(data)
            await self.redis.set(key, serialized, ex=config.redis_ttl)
            await self.redis.set(f"stale:{key}", serialized, ex=config.stale_ttl)
        except Exception as e:
            logger.debug(f"Redis store failed for '{key}': {e}")

    async def _store_negative(self, key: str) -> None:
        """Store negative sentinel to prevent retry storms."""
        if self.redis:
            try:
                await self.redis.set(key, NEGATIVE_SENTINEL, ex=NEGATIVE_TTL)
            except Exception:
                pass

    def invalidate(self, key: str) -> None:
        """Remove a key from all cache layers."""
        self.memory.pop(key, None)
        if self.redis:
            asyncio.ensure_future(self._invalidate_redis(key))

    async def _invalidate_redis(self, key: str) -> None:
        try:
            await self.redis.delete(key)
            await self.redis.delete(f"stale:{key}")
        except Exception:
            pass

    def get_stats(self) -> dict:
        """Return cache hit/miss statistics."""
        return {
            **self._stats,
            "memory_entries": len(self.memory),
            "bootstrap_entries": len(self.bootstrap),
        }

    def clear_expired(self) -> int:
        """Remove expired entries from memory cache. Returns count removed."""
        now = time.time()
        expired_keys = [
            k for k, v in self.memory.items()
            if (now - v.timestamp) > 7200  # Remove anything older than 2 hours
        ]
        for k in expired_keys:
            del self.memory[k]
        return len(expired_keys)


# Global cache manager instance (initialized in app startup)
cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create the global cache manager."""
    global cache_manager
    if cache_manager is None:
        bootstrap_path = str(Path(__file__).parent.parent.parent.parent / "data" / "bootstrap_seed.json")
        cache_manager = CacheManager(bootstrap_path=bootstrap_path)
    return cache_manager
