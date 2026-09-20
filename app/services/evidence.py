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


def aggregate(
    results: dict[str, SourceResult],
    weights: dict[str, float],
    scores: dict[str, float] | None = None,
    *,
    min_coverage: float = MIN_COVERAGE,
) -> dict:
    """Combine sources, counting only the ones that actually answered.

    Weights are renormalised over live sources, so a dead source cannot spend
    its weight pulling the result toward neutral. Below `min_coverage` the
    aggregate refuses to express a direction at all — saying "not enough
    evidence" is a real answer, not a failure to produce one.
    """
    total_weight = sum(weights.values())
    live = {name: r for name, r in results.items() if name in weights and r.available}
    live_weight = sum(weights[name] for name in live)
    coverage = live_weight / total_weight if total_weight else 0.0
    sufficient = coverage >= min_coverage

    missing = {}
    for name in weights:
        if name in live:
            continue
        result = results.get(name)
        missing[name] = result.error if result is not None else "source not reported"

    as_ofs = [r.as_of for r in live.values() if r.as_of is not None]

    out: dict = {
        "coverage": {
            # Key names and types match what alpha_aggregator already emits and
            # tests/test_osint_coverage.py already asserts. Do not rename them.
            "live": sorted(live),
            "missing": missing,
            "live_count": len(live),
            "total_count": len(weights),
            "weight_fraction": round(coverage, 3),
            "sufficient": sufficient,
        },
        "oldest_as_of": min(as_ofs) if as_ofs else None,
        "sufficient": sufficient,
    }

    if scores is None:
        return out

    if live_weight > 0:
        out["value"] = sum(
            scores[name] * weights[name] for name in live if name in scores
        ) / live_weight
    else:
        out["value"] = None

    if not sufficient:
        out["verdict"] = INSUFFICIENT_EVIDENCE
        out["reason"] = (
            f"Only {len(live)} of {len(weights)} sources returned data "
            f"({coverage:.0%} of weight). Missing: {', '.join(sorted(missing))}."
        )
    return out
