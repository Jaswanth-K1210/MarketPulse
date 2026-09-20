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
