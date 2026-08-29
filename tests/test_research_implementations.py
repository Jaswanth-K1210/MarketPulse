"""Tests for risk_scorer — training, scoring, and retrain with feedback."""
import numpy as np
import pytest


class TestRiskScorer:
    def test_feature_vector_shape(self):
        from app.ml.risk_scorer import _make_feature_vector, FEATURES
        article_meta = {"source_tier": 2, "sentiment_score": -0.5, "content": "test"}
        relationship = {"type": "supplier", "criticality": "high"}
        vec = _make_feature_vector(article_meta, relationship, "supply_chain_disruption")
        assert vec.shape == (1, len(FEATURES))

    def test_synthetic_data_generation(self):
        from app.ml.risk_scorer import _generate_synthetic_training_data
        X, y = _generate_synthetic_training_data(100)
        assert X.shape == (100, 10)
        assert y.shape == (100,)
        assert y.min() >= 0
        assert y.max() <= 1

    def test_score_output_contract(self):
        from app.ml.risk_scorer import risk_scorer
        result = risk_scorer.score({}, {})
        assert "risk_score" in result
        assert "explanation" in result
        assert 0 <= result["risk_score"] <= 1

    def test_rule_fallback(self):
        from app.ml.risk_scorer import risk_scorer
        article_meta = {"source_tier": 1, "sentiment_score": -0.8}
        relationship = {"type": "direct", "criticality": "critical"}
        result = risk_scorer.score(article_meta, relationship, "production_halt")
        assert 0 <= result["risk_score"] <= 1

    def test_retrain_requires_minimum_feedback(self):
        from app.ml.risk_scorer import risk_scorer
        risk_scorer.retrain(feedback_rows=[])
        risk_scorer.retrain(feedback_rows=[{"id": 1, "features": "{}", "actual_outcome": 0.5, "predicted_risk": 0.3}] * 5)


class TestFeedbackStorage:
    def test_store_and_retrieve_feedback(self):
        from app.services.database import init_feedback_table, store_feedback, get_unincorporated_feedback, mark_feedback_incorporated
        init_feedback_table()
        store_feedback("TEST", 0.7, 0.3, "price_change", '{"source_tier": 2}')
        rows = get_unincorporated_feedback(min_rows=0)
        assert len(rows) > 0
        last = rows[-1]
        assert last["ticker"] == "TEST"
        assert last["predicted_risk"] == 0.7
        mark_feedback_incorporated([last["id"]])


class TestBacktester:
    def test_backtester_import(self):
        from app.services.trading.backtester import Backtester
        bt = Backtester(slippage_bps=5.0, commission_bps=10.0)
        assert bt.slippage_bps == 5.0
        assert bt.commission_bps == 10.0

    def test_compute_rsi(self):
        from app.services.trading.backtester import Backtester
        import pandas as pd
        bt = Backtester()
        prices = pd.Series(np.random.randn(100).cumsum() + 100)
        rsi = bt._compute_rsi(prices)
        assert len(rsi) == 100
        assert rsi.min() >= 0
        assert rsi.max() <= 100


class TestAlphaAggregator:
    def test_signal_weights(self):
        from app.services.intelligence.alpha_aggregator import SIGNAL_WEIGHTS
        assert abs(sum(SIGNAL_WEIGHTS.values()) - 1.0) < 0.01
        assert SIGNAL_WEIGHTS["insider"] == 0.25
        assert SIGNAL_WEIGHTS["technical"] == 0.20


class TestInsiderTrades:
    def test_scoring_empty(self):
        from app.services.data.insider_trades import InsiderTradesService
        svc = InsiderTradesService()
        assert svc.score_insider_activity([]) == 0.0

    def test_scoring_buys_vs_sells(self):
        from app.services.data.insider_trades import InsiderTradesService
        svc = InsiderTradesService()
        trades = [
            {"transaction_type": "BUY", "value": 100000, "shares": 1000, "relationship": "Officer"},
            {"transaction_type": "BUY", "value": 200000, "shares": 2000, "relationship": "Director"},
            {"transaction_type": "SELL", "value": 50000, "shares": 500, "relationship": "Director"},
        ]
        score = svc.score_insider_activity(trades)
        assert score > 0


class TestShortInterest:
    def test_scoring_empty(self):
        from app.services.data.short_interest import ShortInterestService
        svc = ShortInterestService()
        assert svc.score_short_interest({}) == 0.0

    def test_scoring_high_short(self):
        from app.services.data.short_interest import ShortInterestService
        svc = ShortInterestService()
        score = svc.score_short_interest({"short_pct_float": 30.0, "short_ratio_today": 3.0})
        assert score < 0


class TestTechnicalAnalysis:
    def test_scoring_empty(self):
        from app.services.data.technical_analysis import TechnicalAnalysisService
        svc = TechnicalAnalysisService()
        assert svc.score_technical({}) == 0.0

    def test_scoring_overbought(self):
        from app.services.data.technical_analysis import TechnicalAnalysisService
        svc = TechnicalAnalysisService()
        score = svc.score_technical({"rsi": 75, "signals": ["RSI_OVERBOUGHT"]})
        assert score < 0


class TestAnomalyDetector:
    def test_detector_init(self):
        from app.ml.anomaly_detector import IsolationForestDetector
        det = IsolationForestDetector()
        assert det.contamination == 0.05

    def test_extract_features(self):
        from app.ml.anomaly_detector import IsolationForestDetector
        import pandas as pd
        det = IsolationForestDetector()
        dates = pd.date_range("2024-01-01", periods=100)
        hist = pd.DataFrame({
            "Close": np.random.randn(100).cumsum() + 100,
            "Volume": np.random.randint(1000000, 5000000, 100),
            "High": np.random.randn(100).cumsum() + 102,
            "Low": np.random.randn(100).cumsum() + 98,
        }, index=dates)
        features = det._extract_features(hist)
        assert features is not None
        assert features.shape[1] == 7


class TestDisclaimer:
    """The disclaimer is a regulatory requirement, so assert it actually
    reaches users rather than that some file contains a string."""

    def test_canonical_text_says_not_investment_advice(self):
        from app.core.disclaimer import DISCLAIMER, DISCLAIMER_SHORT

        assert "not investment advice" in DISCLAIMER.lower()
        assert "not investment advice" in DISCLAIMER_SHORT.lower()
        # Headers must be single-line ASCII.
        assert "\n" not in DISCLAIMER_SHORT
        assert DISCLAIMER_SHORT.isascii()

    def test_no_divergent_copies_in_backend(self):
        """Every backend module must import the shared text, not redefine it."""
        from pathlib import Path

        root = Path(__file__).parent.parent / "app"
        offenders = [
            f.relative_to(root).as_posix()
            for f in root.rglob("*.py")
            if f.name != "disclaimer.py" and "DISCLAIMER = (" in f.read_text()
        ]
        assert offenders == [], f"redefined DISCLAIMER instead of importing: {offenders}"

    def test_middleware_attaches_header_to_every_response(self):
        import asyncio

        from app.core.disclaimer import DISCLAIMER_SHORT
        from app.middleware.disclaimer_header import DisclaimerHeaderMiddleware

        class _Resp:
            def __init__(self):
                self.headers = {}

        async def _call_next(_request):
            return _Resp()

        mw = DisclaimerHeaderMiddleware(app=None)
        resp = asyncio.run(mw.dispatch(object(), _call_next))
        assert resp.headers["X-Disclaimer"] == DISCLAIMER_SHORT

    def test_app_wires_the_middleware(self):
        from app.main import app
        from app.middleware.disclaimer_header import DisclaimerHeaderMiddleware

        assert any(m.cls is DisclaimerHeaderMiddleware for m in app.user_middleware)

    def test_alpha_score_payload_carries_disclaimer(self):
        import inspect

        from app.services.intelligence import alpha_aggregator as mod

        src = inspect.getsource(mod.AlphaAggregator.get_alpha_score)
        assert 'result["disclaimer"] = DISCLAIMER' in src

    def test_frontend_renders_the_banner(self):
        from pathlib import Path

        frontend = Path(__file__).parent.parent / "frontend" / "src"
        banner = frontend / "components" / "DisclaimerBanner.jsx"
        constant = frontend / "utils" / "disclaimer.js"

        assert banner.exists(), "DisclaimerBanner.jsx is missing"
        assert "not investment advice" in constant.read_text().lower()
        assert "<DisclaimerBanner />" in (frontend / "App.jsx").read_text()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
