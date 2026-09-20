# Evidence & Liveness Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every MarketPulse data source declare whether it actually answered, so a dead feed can never read as a confident neutral value.

**Architecture:** One new module, `app/services/evidence.py`, holding a `SourceResult` dataclass, an `aggregate()` helper that renormalises weights over live sources only, and a process-local ledger of the last result per source. Existing services are converted incrementally; `alpha_aggregator` already implements this pattern correctly for one aggregate and becomes the first consumer, with its bespoke `_has_data` branches retired as sources convert.

**Tech Stack:** Python 3.13, FastAPI, pytest (no pytest-asyncio — async code is driven with `asyncio.run()` inside sync tests, matching `tests/test_osint_coverage.py`), React 18 + Vite frontend.

**Spec:** `docs/superpowers/specs/2026-09-20-trader-second-brain-design.md`

## Global Constraints

- Run tests with `venv/bin/python -m pytest` — **not** `.venv/`, and never bare `pytest`. Console scripts in both venvs carry a dead shebang from the project's former `~/Desktop` path; only `python -m` works. `venv/` is the complete environment.
- Async tests use `asyncio.run(coro)` inside a normal `def test_...`. Do not add `@pytest.mark.asyncio`; pytest-asyncio is not configured.
- Do **not** use `fastapi.testclient.TestClient`: this venv has starlette 0.27.0 against httpx 0.28.1, and httpx 0.28 removed the `app=` shortcut TestClient relies on, so it raises `TypeError` on construction. Drive the ASGI app with `httpx.ASGITransport(app=app)` instead — same routing, no dependency change. (The venv has drifted again: requirements.txt asks for fastapi>=0.109.0, 0.104.1 is installed.)
- A failing source returns `available=False` with an `error` string. It must never return a zero-valued or empty-but-healthy payload. This is the entire point of the sub-project.
- `as_of` means "when the underlying fact was true". `fetched_at` means "when we retrieved it". Never use one to compute the other.
- Existing behaviour of `alpha_aggregator.get_alpha_score` is the regression baseline: `tests/test_osint_coverage.py` (15 tests) must stay green after every task.
- Follow the existing code's voice: module docstrings explain *why* the defence exists, not just what the code does.

---

### Task 1: `SourceResult` and the liveness ledger

**Files:**
- Create: `app/services/evidence.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SourceResult` (dataclass with `source_id: str`, `available: bool`, `data: Any`, `error: str | None`, `fetched_at: float`, `as_of: float | None`, `origin: str | None`); classmethods `SourceResult.ok(source_id, data, *, as_of=None, origin=None)` and `SourceResult.dead(source_id, error, *, origin=None)`; methods `age(now=None) -> float | None` and `is_stale(max_age, now=None) -> bool`; module functions `record(result) -> SourceResult` and `snapshot() -> dict[str, SourceResult]`; constants `MIN_COVERAGE = 0.5` and `INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_evidence.py`:

```python
"""Tests for the evidence contract.

A source that fails must say so. These tests exist so a dead upstream can
never again be mistaken for a genuine neutral reading.
"""
import time

from app.services.evidence import SourceResult, record, snapshot


class TestSourceResult:
    def test_ok_is_available_and_carries_data(self):
        r = SourceResult.ok("acled", [{"id": 1}], origin="https://api.acleddata.com")
        assert r.available is True
        assert r.data == [{"id": 1}]
        assert r.error is None
        assert r.origin == "https://api.acleddata.com"

    def test_dead_is_unavailable_and_explains_why(self):
        r = SourceResult.dead("acled", "ACLED_API_KEY not configured")
        assert r.available is False
        assert r.data is None
        assert r.error == "ACLED_API_KEY not configured"

    def test_fetched_at_defaults_to_now(self):
        before = time.time()
        r = SourceResult.ok("finnhub", {"x": 1})
        assert before <= r.fetched_at <= time.time()

    def test_age_measures_the_fact_not_the_fetch(self):
        # Fetched one second ago, but the fact is a day old.
        now = 1_000_000.0
        r = SourceResult.ok("edgar", {"x": 1}, as_of=now - 86400)
        r.fetched_at = now - 1
        assert r.age(now) == 86400

    def test_age_is_unknown_without_as_of(self):
        assert SourceResult.ok("x", {}).age() is None

    def test_unknown_age_counts_as_stale(self):
        # Honest default: if we cannot prove it is current, do not claim it is.
        assert SourceResult.ok("x", {}).is_stale(60) is True

    def test_is_stale_compares_against_as_of(self):
        now = 1_000_000.0
        fresh = SourceResult.ok("x", {}, as_of=now - 30)
        old = SourceResult.ok("x", {}, as_of=now - 3600)
        assert fresh.is_stale(60, now) is False
        assert old.is_stale(60, now) is True


class TestLedger:
    def test_record_returns_the_result_it_was_given(self):
        r = SourceResult.dead("ucdp", "timeout")
        assert record(r) is r

    def test_snapshot_reports_last_result_per_source(self):
        record(SourceResult.ok("ledger_test", {"v": 1}))
        record(SourceResult.dead("ledger_test", "went down"))
        entry = snapshot()["ledger_test"]
        assert entry.available is False
        assert entry.error == "went down"

    def test_snapshot_is_a_copy(self):
        record(SourceResult.ok("copy_test", {}))
        snapshot().clear()
        assert "copy_test" in snapshot()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_evidence.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.evidence'`

- [ ] **Step 3: Write minimal implementation**

Create `app/services/evidence.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_evidence.py -q`
Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
git add app/services/evidence.py tests/test_evidence.py
git commit -m "feat: add SourceResult evidence contract and liveness ledger"
```

---

### Task 2: `aggregate()` — renormalise over live sources only

**Files:**
- Modify: `app/services/evidence.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `SourceResult`, `MIN_COVERAGE`, `INSUFFICIENT_EVIDENCE` from Task 1.
- Produces: `aggregate(results: dict[str, SourceResult], weights: dict[str, float], scores: dict[str, float] | None = None, *, min_coverage: float = MIN_COVERAGE) -> dict`. Returns keys `coverage` (itself a dict with `live`, `missing`, `live_count`, `total_count`, `weight_fraction`, `sufficient`), `oldest_as_of`, and `sufficient`. When `scores` is supplied it additionally returns `value` (float or `None`), plus `verdict` and `reason` when coverage is insufficient.

**The `coverage` shape is not free-form — it is the existing contract.** `alpha_aggregator` already emits exactly these keys and `tests/test_osint_coverage.py` asserts them: `coverage["live"]` is a **sorted list of live source names** (line 88, 103) and `coverage["live_count"]`, `["weight_fraction"]`, `["sufficient"]` are read directly (lines 80-90). `aggregate()` must reproduce them or Task 6 breaks the 15-test baseline. The one deliberate change is `missing`: a sorted list becomes a `{name: reason}` dict. This is safe for the existing assertions — `"insider" in coverage["missing"]` (line 139) matches dict keys, and `", ".join(missing)` joins keys — and it is what carries the failure reason to the UI.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_evidence.py`:

```python
from app.services.evidence import INSUFFICIENT_EVIDENCE, aggregate

WEIGHTS = {"insider": 0.5, "sentiment": 0.3, "technical": 0.2}


class TestAggregate:
    def test_dead_source_never_spends_its_weight(self):
        results = {
            "insider": SourceResult.ok("insider", [{"x": 1}]),
            "sentiment": SourceResult.dead("sentiment", "rate limited"),
            "technical": SourceResult.ok("technical", {"rsi": 50}),
        }
        out = aggregate(results, WEIGHTS, scores={"insider": 10.0, "sentiment": 0.0,
                                                  "technical": 0.0})
        # Live weight is 0.7; the dead sentiment source contributes nothing at all.
        assert out["value"] == 10.0 * 0.5 / 0.7
        assert out["coverage"]["weight_fraction"] == 0.7

    def test_coverage_lists_live_sources_sorted(self):
        # alpha_aggregator's existing tests read coverage["live"] as a sorted
        # list of names; aggregate() must keep emitting it.
        results = {
            "technical": SourceResult.ok("technical", {}),
            "insider": SourceResult.ok("insider", [{"x": 1}]),
            "sentiment": SourceResult.dead("sentiment", "down"),
        }
        assert aggregate(results, WEIGHTS)["coverage"]["live"] == ["insider", "technical"]

    def test_coverage_counts_and_names_missing_sources(self):
        results = {
            "insider": SourceResult.ok("insider", [{"x": 1}]),
            "sentiment": SourceResult.dead("sentiment", "rate limited"),
            "technical": SourceResult.dead("technical", "no API key"),
        }
        cov = aggregate(results, WEIGHTS)["coverage"]
        assert cov["live_count"] == 1
        assert cov["total_count"] == 3
        assert cov["missing"] == {"sentiment": "rate limited", "technical": "no API key"}

    def test_source_absent_entirely_is_reported_not_ignored(self):
        results = {"insider": SourceResult.ok("insider", [{"x": 1}])}
        cov = aggregate(results, WEIGHTS)["coverage"]
        assert cov["missing"]["sentiment"] == "source not reported"

    def test_below_min_coverage_refuses_to_give_a_direction(self):
        results = {
            "insider": SourceResult.dead("insider", "down"),
            "sentiment": SourceResult.dead("sentiment", "down"),
            "technical": SourceResult.ok("technical", {"rsi": 50}),
        }
        out = aggregate(results, WEIGHTS, scores={"technical": 9.0})
        assert out["sufficient"] is False
        assert out["verdict"] == INSUFFICIENT_EVIDENCE
        assert "2 of 3" not in out["reason"]  # 1 of 3 returned data
        assert "1 of 3" in out["reason"]
        assert "insider" in out["reason"]

    def test_sufficient_coverage_gives_a_value_and_no_verdict(self):
        results = {k: SourceResult.ok(k, {}) for k in WEIGHTS}
        out = aggregate(results, WEIGHTS, scores={"insider": 1.0, "sentiment": 1.0,
                                                  "technical": 1.0})
        assert out["sufficient"] is True
        assert out["value"] == 1.0
        assert "verdict" not in out

    def test_all_dead_yields_no_value(self):
        results = {k: SourceResult.dead(k, "down") for k in WEIGHTS}
        out = aggregate(results, WEIGHTS, scores={k: 5.0 for k in WEIGHTS})
        assert out["value"] is None
        assert out["coverage"]["weight_fraction"] == 0.0

    def test_composite_reports_its_oldest_contributing_fact(self):
        now = 1_000_000.0
        results = {
            "insider": SourceResult.ok("insider", {}, as_of=now - 10),
            "sentiment": SourceResult.ok("sentiment", {}, as_of=now - 5000),
            "technical": SourceResult.dead("technical", "down"),
        }
        # The dead source must not set the staleness floor.
        assert aggregate(results, WEIGHTS)["oldest_as_of"] == now - 5000

    def test_without_scores_there_is_no_value_key(self):
        results = {k: SourceResult.ok(k, {}) for k in WEIGHTS}
        assert "value" not in aggregate(results, WEIGHTS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_evidence.py -q`
Expected: FAIL — `ImportError: cannot import name 'aggregate'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/services/evidence.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_evidence.py -q`
Expected: PASS, 18 tests.

- [ ] **Step 5: Commit**

```bash
git add app/services/evidence.py tests/test_evidence.py
git commit -m "feat: aggregate() renormalises weights over live sources only"
```

---

### Task 3: Cache results declare their own liveness

**Files:**
- Modify: `app/services/infrastructure/cache_manager.py:46-50` (the `CacheResult` dataclass)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `CacheResult.available -> bool` property, and module-level constants `LIVE_CACHE_SOURCES: set[str]` and `DEAD_CACHE_SOURCES: set[str]` in `cache_manager`.

**Why this task exists:** `get_or_fetch` already computes exactly the information we need — its `CacheResult.source` is one of `memory|redis|stale|bootstrap|fresh|miss|negative`, where `bootstrap`, `miss` and `negative` all mean "this is not live data". That distinction is then thrown away at the router. Surfacing it upgrades every cached endpoint at once.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_evidence.py`:

```python
from app.services.infrastructure.cache_manager import CacheResult


class TestCacheResultLiveness:
    def test_real_data_is_available(self):
        for source in ("fresh", "memory", "redis"):
            assert CacheResult(data={"x": 1}, source=source).available is True

    def test_stale_cache_is_still_real_data(self):
        # Stale data was genuinely fetched once; age is reported separately via
        # as_of, not by pretending the source is dead.
        assert CacheResult(data={"x": 1}, source="stale", age_seconds=9999).available is True

    def test_bootstrap_seed_is_not_live_data(self):
        assert CacheResult(data={"x": 1}, source="bootstrap").available is False

    def test_miss_and_negative_are_not_live_data(self):
        assert CacheResult(data=None, source="miss").available is False
        assert CacheResult(data=None, source="negative").available is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_evidence.py::TestCacheResultLiveness -q`
Expected: FAIL — `AttributeError: 'CacheResult' object has no attribute 'available'`

- [ ] **Step 3: Write minimal implementation**

In `app/services/infrastructure/cache_manager.py`, replace the `CacheResult` dataclass:

```python
# Cache layers that hold data some upstream really returned. "stale" belongs
# here: it was live once, and its age is reported separately.
LIVE_CACHE_SOURCES = {"fresh", "memory", "redis", "stale"}
# Layers that hold no upstream answer at all. Bootstrap seed data is shipped in
# the repo, not fetched — treating it as live is how a dead feed starts looking
# like a calm market.
DEAD_CACHE_SOURCES = {"bootstrap", "miss", "negative"}


@dataclass
class CacheResult:
    """Result from cache lookup."""
    data: Any
    source: str  # "memory", "redis", "stale", "bootstrap", "fresh", "miss", "negative"
    age_seconds: float = 0

    @property
    def available(self) -> bool:
        """Did any upstream actually produce this, at any point?"""
        return self.source in LIVE_CACHE_SOURCES
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_evidence.py tests/test_osint_coverage.py -q`
Expected: PASS — new liveness tests green, and all 15 existing coverage tests still green.

- [ ] **Step 5: Commit**

```bash
git add app/services/infrastructure/cache_manager.py tests/test_evidence.py
git commit -m "feat: CacheResult reports whether its data came from a live source"
```

---

### Task 4: `/api/evidence/health` endpoint

**Files:**
- Create: `app/routers/evidence.py`
- Modify: `app/main.py` (register the router alongside the existing ones)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `snapshot()`, `SourceResult`, `record()` from Task 1.
- Produces: `GET /api/evidence/health` returning `{"sources": {<source_id>: {"available": bool, "error": str | None, "as_of": float | None, "fetched_at": float, "age_seconds": float | None, "origin": str | None}}, "live_count": int, "total_count": int}`. Also produces `app/routers/evidence.py::router` (a `fastapi.APIRouter` with prefix `/api/evidence`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_evidence.py`:

```python
from fastapi.testclient import TestClient


class TestEvidenceHealthEndpoint:
    def _client(self):
        from app.main import app
        return TestClient(app)

    def test_health_lists_dead_sources_with_their_reason(self):
        record(SourceResult.dead("health_dead", "no API key"))
        body = self._client().get("/api/evidence/health").json()
        entry = body["sources"]["health_dead"]
        assert entry["available"] is False
        assert entry["error"] == "no API key"

    def test_health_reports_fact_age_not_fetch_age(self):
        now = time.time()
        record(SourceResult.ok("health_old", {"x": 1}, as_of=now - 3600))
        entry = self._client().get("/api/evidence/health").json()["sources"]["health_old"]
        assert entry["age_seconds"] >= 3600

    def test_health_counts_live_against_total(self):
        record(SourceResult.ok("health_live", {"x": 1}))
        record(SourceResult.dead("health_dead2", "down"))
        body = self._client().get("/api/evidence/health").json()
        assert body["live_count"] < body["total_count"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_evidence.py::TestEvidenceHealthEndpoint -q`
Expected: FAIL — 404, since the route does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `app/routers/evidence.py`:

```python
"""Liveness of every data source, in one call.

The point of this endpoint is that a dead feed becomes visible in a glance
rather than by someone noticing a suspiciously round zero on a dashboard.
"""
import time

from fastapi import APIRouter

from app.services.evidence import snapshot

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("/health")
async def evidence_health() -> dict:
    now = time.time()
    sources = {}
    for source_id, result in snapshot().items():
        sources[source_id] = {
            "available": result.available,
            "error": result.error,
            "as_of": result.as_of,
            "fetched_at": result.fetched_at,
            "age_seconds": result.age(now),
            "origin": result.origin,
        }
    return {
        "sources": sources,
        "live_count": sum(1 for s in sources.values() if s["available"]),
        "total_count": len(sources),
    }
```

In `app/main.py`, find where the existing routers are included (search for `include_router`) and add alongside them:

```python
from app.routers import evidence as evidence_router
app.include_router(evidence_router.router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_evidence.py -q`
Expected: PASS.

Then confirm against the running server:

```bash
curl -s localhost:8000/api/evidence/health | head -c 400
```
Expected: a JSON object with `sources`, `live_count`, `total_count`.

- [ ] **Step 5: Commit**

```bash
git add app/routers/evidence.py app/main.py tests/test_evidence.py
git commit -m "feat: add /api/evidence/health source liveness endpoint"
```

---

### Task 5: Stop `/api/intelligence/signals` lying about an empty world

**Files:**
- Modify: `app/services/data/conflict_data.py:45-60` (ACLED credential guard) and `app/services/data/conflict_data.py:255-264` (snapshot return)
- Modify: `app/services/intelligence/signal_aggregator.py:371-398` (`get_signals`)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `SourceResult`, `record()` from Task 1.
- Produces: `ConflictDataService.source_results: dict[str, SourceResult]` — populated by `get_conflict_snapshot()`, keyed `"acled"` and `"ucdp"`. `SignalAggregator.get_signals()` keeps returning `list[dict]`; new `SignalAggregator.get_signals_with_evidence() -> dict` returns `{"signals": [...], "sources": {...}, "available": bool}`.

**Why this task exists.** Three defects compound here:

1. `.env` has no `ACLED_API_KEY`/`ACLED_EMAIL`, so `get_acled_events` returns `[]` at line 58 with only a `logger.debug`.
2. `get_signals` ingests **only** `acled_events` (line 380-382). `ucdp_conflicts` is fetched in the same snapshot, is keyless, carries real `latitude`/`longitude`, and is then thrown away.
3. `get_signals` wraps everything in `except Exception: pass` (line 383-384), so a genuine failure and an empty world are indistinguishable.

Net effect, reproducible right now: `curl localhost:8000/api/intelligence/signals` returns `{"status":"bootstrap","signals":[],...}`, which a trader reads as calm markets.

**Note on UCDP country codes:** UCDP's `country_id` is a UCDP-internal numeric id, **not** ISO-3166 alpha-2, but `conflict_data.py:147` maps it onto the `country_code` field. `SignalAggregator` groups by ISO2. Do not pass it through as ISO2. Use the `country` name field for the signal title and leave `country_code` empty when the value is numeric.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_evidence.py`:

```python
import asyncio

from app.services.data.conflict_data import ConflictDataService
from app.services.intelligence.signal_aggregator import SignalAggregator


class TestConflictSourceLiveness:
    def test_unkeyed_acled_reports_why_it_is_dead(self, monkeypatch):
        monkeypatch.setattr("app.services.data.conflict_data.ACLED_API_KEY", "")
        monkeypatch.setattr("app.services.data.conflict_data.ACLED_EMAIL", "")
        svc = ConflictDataService()
        result = asyncio.run(svc.get_acled_events())
        assert result == []
        assert svc.source_results["acled"].available is False
        assert "ACLED_API_KEY" in svc.source_results["acled"].error


UCDP_EVENT = {
    "id": "u1", "conflict_name": "Test conflict", "country": "Taiwan",
    "country_code": "713", "latitude": 23.7, "longitude": 121.0,
    "intensity_level": 2, "best_estimate": 12, "source": "ucdp",
}


def _patch_snapshot(monkeypatch, *, ucdp=(), sources=None):
    """Replace get_conflict_snapshot, setting source_results on the instance.

    source_results is assigned in __init__, so patching it as a class attribute
    would be overwritten the moment get_signals_with_evidence constructs the
    service. Setting it from inside the patched method is what actually sticks.
    """
    async def fake(self, *args, **kwargs):
        self.source_results = sources or {}
        return {"acled_events": [], "ucdp_conflicts": list(ucdp)}

    monkeypatch.setattr(ConflictDataService, "get_conflict_snapshot", fake)


class TestSignalsEvidence:
    def test_empty_signals_are_explained_not_silent(self, monkeypatch):
        _patch_snapshot(monkeypatch, sources={
            "acled": SourceResult.dead("acled", "ACLED_API_KEY not configured"),
            "ucdp": SourceResult.dead("ucdp", "timeout"),
        })
        out = asyncio.run(SignalAggregator().get_signals_with_evidence())
        assert out["available"] is False
        assert out["sources"]["acled"]["error"] == "ACLED_API_KEY not configured"

    def test_ucdp_events_become_signals(self, monkeypatch):
        _patch_snapshot(monkeypatch, ucdp=[UCDP_EVENT],
                        sources={"ucdp": SourceResult.ok("ucdp", [{}])})
        out = asyncio.run(SignalAggregator().get_signals_with_evidence())
        assert out["available"] is True
        assert any(s["source"] == "ucdp" for s in out["signals"])

    def test_numeric_ucdp_country_id_is_not_passed_off_as_iso2(self, monkeypatch):
        _patch_snapshot(monkeypatch, ucdp=[UCDP_EVENT],
                        sources={"ucdp": SourceResult.ok("ucdp", [{}])})
        out = asyncio.run(SignalAggregator().get_signals_with_evidence())
        signal = next(s for s in out["signals"] if s["source"] == "ucdp")
        assert signal["country"] != "713"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_evidence.py::TestConflictSourceLiveness tests/test_evidence.py::TestSignalsEvidence -q`
Expected: FAIL — `AttributeError: 'ConflictDataService' object has no attribute 'source_results'`

- [ ] **Step 3: Write minimal implementation**

In `app/services/data/conflict_data.py`, add to the top imports:

```python
from app.services.evidence import SourceResult, record
```

In `ConflictDataService.__init__`, add:

```python
self.source_results: dict[str, SourceResult] = {}
```

Replace the ACLED credential guard (currently lines 57-59):

```python
        if not ACLED_API_KEY or not ACLED_EMAIL:
            self.source_results["acled"] = record(SourceResult.dead(
                "acled",
                "ACLED_API_KEY / ACLED_EMAIL not configured — register free at "
                "https://developer.acleddata.com",
                origin=ACLED_BASE_URL,
            ))
            return []
```

At the end of the successful ACLED fetch, before returning the event list, add:

```python
        self.source_results["acled"] = record(SourceResult.ok(
            "acled", events, as_of=time.time(), origin=ACLED_BASE_URL))
```

Apply the same pattern in `get_ucdp_conflicts`: on the `except Exception as e` branch (line 161-163) record `SourceResult.dead("ucdp", str(e), origin=UCDP_BASE_URL)`, and on success record `SourceResult.ok("ucdp", results, as_of=time.time(), origin=UCDP_BASE_URL)`.

Add `import time` to `conflict_data.py` if it is not already imported.

In `app/services/intelligence/signal_aggregator.py`, add a UCDP ingestion method next to `ingest_conflict_signals`:

```python
    def ingest_ucdp_signals(self, conflicts: list[dict]) -> int:
        """Turn UCDP conflict events into signals.

        UCDP's country_code is a UCDP-internal numeric id, not ISO-3166 alpha-2,
        so it is deliberately not used as one — the country name carries the
        location instead.
        """
        self.clear_type("ucdp_conflict")
        count = 0
        for event in conflicts:
            intensity = event.get("intensity_level", 0)
            deaths = event.get("best_estimate", 0)
            if deaths >= 25 or intensity >= 2:
                severity = "critical"
            elif deaths >= 5:
                severity = "high"
            else:
                severity = "medium"

            raw_cc = str(event.get("country_code", ""))
            country_code = raw_cc if raw_cc.isalpha() and len(raw_cc) == 2 else ""

            self.signals.append(Signal(
                id=f"ucdp_{event.get('id', count)}",
                signal_type="ucdp_conflict",
                country_code=country_code,
                severity=severity,
                title=f"{event.get('conflict_name', 'Conflict')}: {event.get('country', '')}",
                description=f"{event.get('side_a', '')} vs {event.get('side_b', '')}",
                latitude=event.get("latitude", 0),
                longitude=event.get("longitude", 0),
                timestamp=time.time(),
                source="ucdp",
                metadata={"deaths": deaths, "intensity_level": intensity,
                          "country": event.get("country", "")},
            ))
            count += 1
        return count
```

Replace `get_signals` and add the evidence-carrying variant:

```python
    async def get_signals_with_evidence(self) -> dict:
        """Signals plus the liveness of every source that fed them.

        An empty signal list means one of two very different things — a quiet
        world, or dead feeds. This reports which.
        """
        sources: dict = {}
        try:
            from app.services.data.conflict_data import ConflictDataService
            svc = ConflictDataService()
            snapshot = await svc.get_conflict_snapshot()
            self.ingest_conflict_signals(snapshot.get("acled_events", []))
            self.ingest_ucdp_signals(snapshot.get("ucdp_conflicts", []))
            sources = {
                name: {"available": r.available, "error": r.error, "as_of": r.as_of}
                for name, r in svc.source_results.items()
            }
        except Exception as e:
            logger.warning("conflict ingestion failed: %s", e)
            sources = {"conflict": {"available": False, "error": str(e), "as_of": None}}

        self._prune_stale()
        return {
            "signals": await self.get_signals(),
            "sources": sources,
            "available": any(s["available"] for s in sources.values()) if sources else False,
        }
```

Keep the existing `get_signals` as-is apart from also ingesting UCDP, so current callers are unaffected:

```python
            acled = snapshot.get("acled_events", [])
            if acled:
                self.ingest_conflict_signals(acled)
            ucdp = snapshot.get("ucdp_conflicts", [])
            if ucdp:
                self.ingest_ucdp_signals(ucdp)
```

Finally, in `app/routers/intelligence.py`, change the `/signals` fetch function to use the evidence variant so the endpoint stops reporting a healthy empty world:

```python
        try:
            from app.services.intelligence.signal_aggregator import SignalAggregator
            agg = SignalAggregator()
            out = await agg.get_signals_with_evidence()
            return {
                "status": "live" if out["available"] else "sources_unavailable",
                "signals": out["signals"],
                "sources": out["sources"],
                "total": len(out["signals"]),
                "timestamp": _now(),
            }
        except Exception as e:
            logger.warning("signals fetch failed: %s", e)
            return None
```

Remove the bootstrap fall-through that overwrites an empty-but-explained result (currently the `if not data or not data.get("signals"):` branch), replacing it with a bootstrap fallback only when `data` is `None`:

```python
    if data is None:
        data = _bootstrap("signals:all") or {
            "status": "bootstrap", "signals": [], "timestamp": _now()}
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_evidence.py tests/test_osint_coverage.py -q`
Expected: PASS, all green.

Then verify the real defect is gone against the running server:

```bash
curl -s localhost:8000/api/intelligence/signals | python3 -m json.tool | head -20
```
Expected: `"status": "sources_unavailable"` with a `sources.acled.error` naming the missing key — **not** a silent `"bootstrap"` with an empty list.

- [ ] **Step 5: Commit**

```bash
git add app/services/data/conflict_data.py app/services/intelligence/signal_aggregator.py app/routers/intelligence.py tests/test_evidence.py
git commit -m "fix: signals endpoint reports dead sources instead of an empty world

Also ingests UCDP conflicts, which were fetched and discarded. UCDP's numeric
country_id is no longer passed off as an ISO-3166 alpha-2 code."
```

---

### Task 6: `alpha_aggregator` consumes the shared contract

**Files:**
- Modify: `app/services/intelligence/alpha_aggregator.py:28-56` (`_has_data`, `MIN_COVERAGE`) and `:140-185` (coverage block)
- Test: `tests/test_osint_coverage.py`

**Interfaces:**
- Consumes: `aggregate()`, `MIN_COVERAGE`, `SourceResult` from Tasks 1-2.
- Produces: no public signature change. `AlphaAggregator.get_alpha_score(ticker)` keeps returning the same dict shape, now with `coverage.missing` as a `{name: reason}` dict rather than a list of names, and a new `oldest_as_of` key.

**Why this task exists:** `_has_data` infers liveness downstream with a bespoke branch per component. Every new source needs another branch, and every other consumer re-invents the guess. This retires it in favour of sources declaring their own state — but incrementally: `_has_data` stays as the fallback for sources not yet converted.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_osint_coverage.py`:

```python
class TestSharedAggregateContract:
    def test_missing_names_carry_their_reason(self, stub):
        stub(insider=[{"transaction_type": "BUY", "value": 1_000_000}])
        missing = _run(AlphaAggregator())["coverage"]["missing"]
        assert isinstance(missing, dict)
        assert "sentiment" in missing
        for reason in missing.values():
            assert isinstance(reason, str) and reason

    def test_composite_reports_oldest_contributing_fact(self, stub):
        stub(insider=[{"transaction_type": "BUY", "value": 1_000_000}])
        assert "oldest_as_of" in _run(AlphaAggregator())

    def test_live_list_survives_the_refactor(self, stub):
        stub(insider=[{"transaction_type": "BUY", "value": 1_000_000}])
        assert _run(AlphaAggregator())["coverage"]["live"] == ["insider"]
```

Note: `_run` is the existing helper at `tests/test_osint_coverage.py:43`, and its signature is `_run(agg, ticker="AAPL")` — it takes the **aggregator instance** first, so call it as `_run(AlphaAggregator())`. `stub` is the existing fixture at line 47 that replaces every upstream; pass it as a test argument and call it to configure which sources are live. Reuse both; do not redefine them.

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_osint_coverage.py::TestSharedAggregateContract -q`
Expected: FAIL — `missing` is currently a list, and `oldest_as_of` does not exist.

- [ ] **Step 3: Write minimal implementation**

In `app/services/intelligence/alpha_aggregator.py`, import the shared contract and delegate:

```python
from app.services.evidence import MIN_COVERAGE, SourceResult, aggregate
```

Delete the local `MIN_COVERAGE = 0.5` definition (it now comes from `evidence`).

Keep `_has_data` for now — it is the fallback for sources that do not yet return a `SourceResult`. Wrap each component's raw result before aggregating:

```python
        raws = {
            "insider": insider_raw,
            "short_interest": short_raw,
            "sentiment": sent_raw,
            "technical": tech_raw,
            "fundamentals": fund_raw,
        }
        results = {}
        for name, raw in raws.items():
            if isinstance(raw, SourceResult):
                results[name] = raw            # already converted
            elif _has_data(name, raw):
                results[name] = SourceResult.ok(name, raw)
            else:
                reason = "no data returned"
                if isinstance(raw, dict) and raw.get("error"):
                    reason = str(raw["error"])
                results[name] = SourceResult.dead(name, reason)

        agg = aggregate(results, self.weights, scores=scores,
                        min_coverage=MIN_COVERAGE)
        result["coverage"] = agg["coverage"]
        result["oldest_as_of"] = agg["oldest_as_of"]

        # alpha_score stays a rounded float and stays 0.0 when nothing is live —
        # tests/test_osint_coverage.py reads it directly.
        alpha = agg["value"] if agg["value"] is not None else 0.0
        result["alpha_score"] = round(alpha, 2)
```

Then leave the **existing signal ladder untouched**, including its `signal_note`:

```python
        if not result["coverage"]["sufficient"]:
            result["signal"] = "INSUFFICIENT_DATA"
            result["signal_note"] = agg["reason"]
        elif alpha >= 5:
            result["signal"] = "STRONG_BUY"
        elif alpha >= 2:
            result["signal"] = "BUY"
        ...
```

Replace only the hand-rolled `live_weight` / `total_weight` / `coverage` computation and the `alpha` weighted-mean — **not** the signal ladder below it.

Three details that will silently break the baseline if missed:

- The key is `signal_note`, not `reason`. `tests/test_osint_coverage.py:82` asserts `"0 of 5" in out["signal_note"]`. `aggregate()`'s `reason` string already produces that wording, so assigning it across is enough.
- The key is `alpha_score`, not `score`, and it must be `round(..., 2)`.
- When every source is dead, `alpha_score` must be `0.0`, not `None` — `aggregate()` returns `value=None` in that case, hence the fallback above.

Keep the `"INSUFFICIENT_DATA"` string rather than switching to `INSUFFICIENT_EVIDENCE`; renaming it is Task 7's concern, not this one.

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_osint_coverage.py tests/test_evidence.py -q`
Expected: PASS — all 15 original coverage tests plus the new ones. Any regression in the original 15 means the refactor changed behaviour and must be fixed, not accommodated.

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/alpha_aggregator.py tests/test_osint_coverage.py
git commit -m "refactor: alpha_aggregator uses shared evidence aggregate()"
```

---

### Task 7: Surface coverage in the UI

**Files:**
- Modify: `frontend/src/services/api.js` (add the fetch call)
- Modify: `frontend/src/components/BackendStatus.jsx`
- Modify: `frontend/src/pages/CompanyDetail.jsx:95`
- Modify: `frontend/src/pages/Dashboard.jsx:501`
- Modify: `frontend/src/components/SectorHeatmap.jsx:48`
- Create: `frontend/src/components/SourceCoverage.jsx`

**The same defect exists in the UI, in pixels.** Two places turn "no evidence" into a confident neutral, and they must be fixed here or the backend work is invisible:

- `Dashboard.jsx:501` renders the alpha badge only when `alpha_score != null && alpha_score !== 0`. An `INSUFFICIENT_DATA` result scores exactly `0.0`, so the badge silently vanishes — the trader sees nothing at all rather than "not enough evidence".
- `SectorHeatmap.jsx:48` does `alphaScores[t] || 0`, so a missing score renders as a mid-range neutral cell, indistinguishable from a genuine neutral reading.

**Interfaces:**
- Consumes: `GET /api/evidence/health` from Task 4.
- Produces: `SourceCoverage` React component, default export, props `{ compact?: boolean }`. Fetches on mount and every 60s.

**Note:** There is no frontend test runner configured in `frontend/package.json` (scripts are `dev`, `build`, `preview` only). Do not add one for this task — verify in the browser, as the steps below describe.

- [ ] **Step 1: Add the API call**

In `frontend/src/services/api.js`, following the existing export style in that file, add:

```javascript
export const getEvidenceHealth = () =>
  fetch('/api/evidence/health').then(r => r.json())
```

- [ ] **Step 2: Create the component**

Create `frontend/src/components/SourceCoverage.jsx`:

```jsx
import React, { useEffect, useState } from 'react'
import { getEvidenceHealth } from '../services/api'
import { T as C } from '../theme'

// A dead feed should be visible at a glance, not inferred from a suspicious zero.
const dot = (available) => ({
  display: 'inline-block', width: 8, height: 8, borderRadius: 4,
  background: available ? C.green : C.red, marginRight: 6,
})

export default function SourceCoverage({ compact = false }) {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    const load = () => getEvidenceHealth().then(setHealth).catch(() => setHealth(null))
    load()
    const id = setInterval(load, 60000)
    return () => clearInterval(id)
  }, [])

  if (!health) return null
  const { live_count: live, total_count: total, sources } = health

  if (compact) {
    return (
      <span style={{ color: live < total ? C.orange : C.green }}>
        {live}/{total} sources live
      </span>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 6, color: live < total ? C.orange : C.green }}>
        {live}/{total} sources live
      </div>
      {Object.entries(sources).map(([id, s]) => (
        <div key={id} title={s.error || s.origin || ''}>
          <span style={dot(s.available)} />
          {id}
          {!s.available && s.error ? ` — ${s.error}` : ''}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Mount it in BackendStatus**

In `frontend/src/components/BackendStatus.jsx`, import and render the compact form alongside the existing status indicator:

```jsx
import SourceCoverage from './SourceCoverage'
```

and inside the rendered output, next to the existing backend indicator:

```jsx
<SourceCoverage compact />
```

- [ ] **Step 4: Render insufficient evidence as a state, not a zero**

In `frontend/src/pages/CompanyDetail.jsx`, replace the score line at line 95 so an
unbacked score says so instead of printing a number:

```jsx
{alpha.signal === 'INSUFFICIENT_DATA' ? (
  <span title={alpha.signal_note} style={{ color: C.orange }}>
    Insufficient evidence ({alpha.coverage?.live_count ?? 0}/{alpha.coverage?.total_count ?? 0} sources)
  </span>
) : (
  <>Score: {alpha.alpha_score != null ? `${alpha.alpha_score >= 0 ? '+' : ''}${alpha.alpha_score}` : '--'}</>
)}
```

In `frontend/src/pages/Dashboard.jsx`, change the badge guard at line 501 so a
zero score no longer hides the badge — drop the `&& pipelineResult.alpha_score !== 0`
clause and branch on the signal instead:

```jsx
{pipelineResult.alpha_score != null && (
  pipelineResult.signal === 'INSUFFICIENT_DATA'
    ? <span title={pipelineResult.signal_note} style={{ color: C.orange }}>α n/a</span>
    : <>α {pipelineResult.alpha_score > 0 ? '+' : ''}{typeof pipelineResult.alpha_score === 'number' ? pipelineResult.alpha_score.toFixed(1) : pipelineResult.alpha_score}</>
)}
```

In `frontend/src/components/SectorHeatmap.jsx`, stop coercing a missing score to
neutral. Replace line 48:

```jsx
const sectorScores = sector.companies
  .map(t => alphaScores[t])
  .filter(s => typeof s === 'number')
```

and render a sector with no remaining scores in a muted "no data" style rather
than at the neutral midpoint. If `sectorScores` is empty, skip the average and
render the cell with `background: C.dim` (or the nearest existing muted token in
`theme.js`) and the label `no data`.

- [ ] **Step 5: Verify in the browser**

With both servers running (`venv/bin/python run.py` and `cd frontend && npm run dev`):

1. Open http://localhost:5173
2. Confirm the header shows an `N/M sources live` readout.
3. Confirm the count is **not** `M/M` — ACLED is unkeyed, so at least one source must report dead. A full-marks readout means liveness is not actually being recorded.
4. Open a company detail page and confirm a low-coverage ticker reads "Insufficient evidence (N/M sources)" rather than a number or a blank.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/SourceCoverage.jsx frontend/src/components/BackendStatus.jsx frontend/src/services/api.js frontend/src/pages/CompanyDetail.jsx frontend/src/components/SectorHeatmap.jsx
git commit -m "feat: show per-source liveness and render insufficient evidence explicitly"
```

---

## Done when

- `curl localhost:8000/api/intelligence/signals` explains *why* it is empty instead of reporting a calm world.
- `curl localhost:8000/api/evidence/health` lists every reporting source with its availability and the age of its underlying facts.
- `venv/bin/python -m pytest tests/test_evidence.py tests/test_osint_coverage.py -q` is green, with the original 15 coverage tests unchanged.
- The dashboard header shows a live source count that is honestly less than the total.
- A low-coverage ticker reads "Insufficient evidence", and a sector with no scores reads "no data" — neither renders as a neutral zero.

## Deliberately not in this plan

- Converting the remaining ~25 services to `SourceResult`. The contract and two consumers prove it; the rest is mechanical and belongs in follow-up work, highest-value sources first (`short_interest`, `retail_sentiment`, `insider`, `technical`, `fundamentals`).
- Wiring `osint-research.md` §5.4 Gold/Silver/Bronze reliability tiers into `aggregate()` weights. Noted in the spec so it is not reinvented.
- Per-source staleness thresholds from §5.2. `is_stale()` exists and is tested; applying the specific limits per source comes with each source's conversion.
