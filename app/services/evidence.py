"""Evidence contract: every data source declares whether it actually answered.

MarketPulse degrades gracefully everywhere — services catch upstream failures
and return a fully-shaped payload of zeros. That is right for a dashboard that
must not crash, and wrong the moment anything averages those payloads: a dead
source spends its weight and drags the composite toward a confident neutral.

This module makes failure part of the payload. A source that could not answer
returns available=False and says why, so downstream code can exclude it rather
than average it in.

Amends osint-research.md section 5.5, whose degradation chain terminated in a
silent null.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# Below this fraction of live weight, an aggregate may not express a direction.
MIN_COVERAGE = 0.5

INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class SourceResult:
    """What one data source returned, including the fact that it returned nothing."""

    source_id: str
    available: bool
    data: Any = None
    error: str | None = None
    fetched_at: float = field(default_factory=time.time)
    as_of: float | None = None
    origin: str | None = None

    @classmethod
    def ok(cls, source_id: str, data: Any, *, as_of: float | None = None,
           origin: str | None = None) -> "SourceResult":
        return cls(source_id=source_id, available=True, data=data,
                   as_of=as_of, origin=origin)

    @classmethod
    def dead(cls, source_id: str, error: str, *,
             origin: str | None = None) -> "SourceResult":
        return cls(source_id=source_id, available=False, error=error, origin=origin)

    def age(self, now: float | None = None) -> float | None:
        """Seconds since the underlying fact was true — not since we fetched it.

        A two-year-old filing pulled from cache a second ago is fresh-fetched
        and stale-fact. Only this number can tell them apart.
        """
        if self.as_of is None:
            return None
        return (now if now is not None else time.time()) - self.as_of

    def is_stale(self, max_age: float, now: float | None = None) -> bool:
        age = self.age(now)
        # Unknown age counts as stale: if we cannot prove it is current, we do
        # not get to claim it is.
        return age is None or age > max_age


# ponytail: process-local ledger. Move to Redis if we ever run >1 uvicorn
# worker, otherwise each worker reports only the sources it happened to serve.
_LAST: dict[str, SourceResult] = {}


def record(result: SourceResult) -> SourceResult:
    """Remember this source's latest outcome, and hand it straight back."""
    _LAST[result.source_id] = result
    return result


def snapshot() -> dict[str, SourceResult]:
    """Last known outcome for every source that has reported."""
    return dict(_LAST)
