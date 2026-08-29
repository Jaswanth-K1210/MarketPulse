"""Tests for coverage-aware alpha aggregation and the repaired data sources.

A dead upstream must never look like a genuine neutral reading — that was the
defect these tests exist to prevent regressing.
"""
import asyncio

import pytest

from app.services.intelligence.alpha_aggregator import (
    MIN_COVERAGE,
    SIGNAL_WEIGHTS,
    AlphaAggregator,
    _has_data,
)


class TestHasData:
    def test_insider_empty_list_is_not_data(self):
        assert _has_data("insider", []) is False
        assert _has_data("insider", [{"ticker": "AAPL"}]) is True

    def test_none_is_never_data(self):
        for component in SIGNAL_WEIGHTS:
            assert _has_data(component, None) is False

    def test_explicit_error_marks_source_dead(self):
        assert _has_data("technical", {"price": 1.0, "rsi": 50, "error": "boom"}) is False

    def test_technical_needs_price_and_rsi(self):
        assert _has_data("technical", {"price": None, "rsi": None}) is False
        assert _has_data("technical", {"price": 309.35, "rsi": 57.1}) is True

    def test_sentiment_needs_a_source_and_mentions(self):
        assert _has_data("sentiment", {"sources": [], "total_mentions": 0}) is False
        assert _has_data("sentiment", {"sources": ["reddit"], "total_mentions": 3}) is True

    def test_short_interest_needs_a_populated_field(self):
        assert _has_data("short_interest", {"sources": [], "short_pct_float": None}) is False
        assert _has_data("short_interest", {"sources": ["yfinance"], "short_pct_float": 0.97}) is True


def _run(agg, ticker="AAPL"):
    return asyncio.run(agg.get_alpha_score(ticker))


@pytest.fixture
def stub(monkeypatch):
    """Replace every upstream with a controllable stub."""

    def apply(insider=None, short=None, sent=None, tech=None, fund=None):
        import app.services.data.financial_fundamentals as f
        import app.services.data.insider_trades as i
        import app.services.data.retail_sentiment as r
        import app.services.data.short_interest as s
        import app.services.data.technical_analysis as t

        async def _const(value):
            return value

        monkeypatch.setattr(i.insider_trades_service, "get_insider_trades",
                            lambda *a, **k: _const(insider if insider is not None else []))
        monkeypatch.setattr(s.short_interest_service, "get_short_interest",
                            lambda *a, **k: _const(short or {"sources": [], "short_pct_float": None}))
        monkeypatch.setattr(r.retail_sentiment_service, "get_sentiment",
                            lambda *a, **k: _const(sent or {"sources": [], "total_mentions": 0}))
        monkeypatch.setattr(t.technical_analysis_service, "get_indicators",
                            lambda *a, **k: _const(tech or {"price": None, "rsi": None}))
        monkeypatch.setattr(f.financial_fundamentals_service, "get_fundamentals",
                            lambda *a, **k: _const(fund or {"pe_ratio": None, "revenue_growth": None}))

    return apply


class TestCoverage:
    def test_all_sources_dead_yields_insufficient_data(self, stub):
        stub()
        out = _run(AlphaAggregator())
        assert out["signal"] == "INSUFFICIENT_DATA"
        assert out["coverage"]["live_count"] == 0
        assert out["coverage"]["sufficient"] is False
        assert "0 of 5" in out["signal_note"]

    def test_single_live_source_is_below_the_floor(self, stub):
        # insider alone carries 0.25 of the weight, under MIN_COVERAGE.
        stub(insider=[{"transaction_type": "BUY", "value": 1_000_000}])
        out = _run(AlphaAggregator())
        assert out["coverage"]["live"] == ["insider"]
        assert out["coverage"]["weight_fraction"] == pytest.approx(0.25)
        assert out["coverage"]["weight_fraction"] < MIN_COVERAGE
        assert out["signal"] == "INSUFFICIENT_DATA"

    def test_dead_sources_do_not_dilute_the_score(self, stub):
        """The defect: a dead source scored 0 and still spent its weight,
        dragging a strong reading toward neutral."""
        strong_tech = {"price": 100.0, "rsi": 25.0, "signals": []}
        stub(tech=strong_tech,
             fund={"pe_ratio": 12.0, "revenue_growth": 0.3, "market_cap": 1e12})

        agg = AlphaAggregator()
        out = _run(agg)

        live = out["coverage"]["live"]
        assert set(live) == {"technical", "fundamentals"}

        # Score must equal the weighted mean over live sources only.
        live_weight = sum(SIGNAL_WEIGHTS[n] for n in live)
        expected = sum(
            out["components"][n]["score"] * SIGNAL_WEIGHTS[n] for n in live
        ) / live_weight
        assert out["alpha_score"] == pytest.approx(round(expected, 2))

        # And that is strictly larger than the old dilute-by-zero behaviour.
        diluted = sum(out["components"][n]["score"] * SIGNAL_WEIGHTS[n] for n in live)
        assert abs(out["alpha_score"]) > abs(diluted)

    def test_active_signals_never_cite_a_dead_source(self, stub):
        stub()
        out = _run(AlphaAggregator())
        assert out["active_signals"] == []

    def test_component_availability_is_reported(self, stub):
        stub(tech={"price": 10.0, "rsi": 50.0})
        out = _run(AlphaAggregator())
        assert out["components"]["technical"]["available"] is True
        assert out["components"]["insider"]["available"] is False

    def test_upstream_exception_is_contained(self, monkeypatch, stub):
        stub(tech={"price": 10.0, "rsi": 50.0})

        import app.services.data.insider_trades as i

        async def _boom(*a, **k):
            raise RuntimeError("upstream exploded")

        monkeypatch.setattr(i.insider_trades_service, "get_insider_trades", _boom)

        out = _run(AlphaAggregator())
        assert "insider" in out["coverage"]["missing"]
        assert out["components"]["insider"]["available"] is False


class TestClinicalTrialsV2Normalisation:
    def test_phase_enums_become_readable(self):
        from app.services.data.fda_trials import _norm_phases

        assert _norm_phases(["PHASE3"]) == "Phase 3"
        assert _norm_phases(["PHASE2", "PHASE3"]) == "Phase 2/Phase 3"
        assert _norm_phases(["NA"]) == "N/A"
        assert _norm_phases([]) == ""

    def test_status_enums_match_what_the_scorer_expects(self):
        from app.services.data.fda_trials import _norm_status, fda_trials_service

        assert _norm_status("ACTIVE_NOT_RECRUITING") == "Active, not recruiting"
        assert _norm_status("COMPLETED") == "Completed"

        # The scorer keys off these exact strings.
        data = {
            "trials": [
                {"phase": "Phase 3", "status": "Completed"},
                {"phase": "Phase 3", "status": "Recruiting"},
            ],
            "total_trials": 2,
        }
        assert fda_trials_service.score_fda_pipeline(data) > 0


class TestHonestDegradation:
    def test_patents_reports_why_it_is_unavailable(self):
        from app.services.data.patents import patents_service

        out = asyncio.run(patents_service.get_patents("Apple Inc"))
        if not out["available"]:
            assert out.get("error"), "unavailable sources must explain themselves"
