"""Tests for the evidence contract.

A source that fails must say so. These tests exist so a dead upstream can
never again be mistaken for a genuine neutral reading.
"""
import asyncio
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


import httpx


class TestEvidenceHealthEndpoint:
    """Drives the real ASGI app.

    starlette 0.27 predates httpx 0.28's removal of the `app=` shortcut, so
    TestClient cannot construct here. ASGITransport exercises the same routing
    without pinning either package.
    """

    def _get(self, path):
        from app.main import app

        async def call():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport,
                                         base_url="http://test") as client:
                return await client.get(path)

        return asyncio.run(call())

    def test_health_lists_dead_sources_with_their_reason(self):
        record(SourceResult.dead("health_dead", "no API key"))
        body = self._get("/api/evidence/health").json()
        entry = body["sources"]["health_dead"]
        assert entry["available"] is False
        assert entry["error"] == "no API key"

    def test_health_reports_fact_age_not_fetch_age(self):
        now = time.time()
        record(SourceResult.ok("health_old", {"x": 1}, as_of=now - 3600))
        entry = self._get("/api/evidence/health").json()["sources"]["health_old"]
        assert entry["age_seconds"] >= 3600

    def test_health_counts_live_against_total(self):
        record(SourceResult.ok("health_live", {"x": 1}))
        record(SourceResult.dead("health_dead2", "down"))
        body = self._get("/api/evidence/health").json()
        assert body["live_count"] < body["total_count"]


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


from app.services.evidence import record_reported


class TestRecordReported:
    """Cached responses skip the fetch, so liveness must be replayable.

    Without this the health endpoint reports 0/0 after a restart even though
    every cached payload knows exactly which sources were dead.
    """

    def test_cached_payload_restores_liveness(self):
        record_reported({
            "replay_dead": {"available": False, "error": "no key", "as_of": None},
            "replay_live": {"available": True, "error": None, "as_of": 123.0},
        })
        snap = snapshot()
        assert snap["replay_dead"].available is False
        assert snap["replay_dead"].error == "no key"
        assert snap["replay_live"].available is True
        assert snap["replay_live"].as_of == 123.0

    def test_junk_entries_are_skipped(self):
        record_reported({"replay_junk": "not a dict"})
        assert "replay_junk" not in snapshot()

    def test_empty_input_is_harmless(self):
        record_reported({})
        record_reported(None)
