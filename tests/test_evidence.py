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
