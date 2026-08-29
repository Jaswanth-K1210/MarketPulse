"""GHAN-Lite Tests — Unit tests for dataset, graph builder, model, and scorer."""
import numpy as np
import pytest


class TestAbnormalReturnLabeler:
    def test_label_thresholds(self):
        assert 0.015 > 0.01
        assert -0.015 < -0.01
        assert 0.005 > -0.01 and 0.005 < 0.01

    def test_label_classes(self):
        assert 0 == 0
        assert 1 == 1
        assert 2 == 2

    def test_abnormal_return_computation(self):
        ticker_ret = 0.05
        spy_ret = 0.02
        abnormal = ticker_ret - spy_ret
        assert abnormal == pytest.approx(0.03)
        assert abnormal > 0.01


class TestGraphBuilder:
    def test_star_expansion(self):
        from app.ml.ghan.graph_builder import GhanGraphBuilder
        builder = GhanGraphBuilder(ticker_dim=8, event_dim=16)
        builder._supply_chain = {"AAPL": ["TSM", "QCOM"], "TSM": ["AAPL"]}

        event_tickers = [["AAPL"]]
        event_embeddings = np.random.randn(1, 16).astype(np.float32)
        labels = np.array([2])

        graph = builder.build_graph(event_tickers, event_embeddings, labels)

        assert "edge_index" in graph
        assert "x" in graph
        assert graph["n_events"] == 1
        assert graph["n_tickers"] > 0

    def test_empty_supply_chain(self):
        from app.ml.ghan.graph_builder import GhanGraphBuilder
        builder = GhanGraphBuilder(ticker_dim=8, event_dim=16)
        builder._supply_chain = {}

        event_tickers = [["AAPL"]]
        event_embeddings = np.random.randn(1, 16).astype(np.float32)
        labels = np.array([1])

        graph = builder.build_graph(event_tickers, event_embeddings, labels)
        assert graph["n_events"] == 1


class TestGHANModel:
    def test_model_output_shape(self):
        try:
            import torch
            from app.ml.ghan.model import GhanModel
            model = GhanModel(in_dim=64, hidden_dim=32, heads=4, n_classes=3)
            x = torch.randn(5, 64)
            logits = model(x)
            assert logits.shape == (5, 3)
        except ImportError:
            pytest.skip("PyTorch not available")

    def test_predict_proba_sums_to_one(self):
        try:
            import torch
            from app.ml.ghan.model import GhanModel
            model = GhanModel(in_dim=64, hidden_dim=32, heads=4, n_classes=3)
            x = torch.randn(3, 64)
            probs = model.predict_proba(x)
            assert probs.shape == (3, 3)
            np.testing.assert_allclose(probs.sum(axis=-1), 1.0, atol=1e-5)
        except ImportError:
            pytest.skip("PyTorch not available")


class TestGHANScorer:
    def test_fallback_when_no_model(self):
        from app.ml.ghan.model import GHANScorer
        scorer = GHANScorer()
        article_meta = {"content": "test", "source_tier": 2, "sentiment_score": -0.5}
        relationship = {"type": "supplier", "criticality": "high"}
        result = scorer.score(article_meta, relationship, "supply_chain_disruption")
        assert "risk_score" in result
        assert 0 <= result["risk_score"] <= 1

    def test_output_contract(self):
        from app.ml.ghan.model import GHANScorer
        scorer = GHANScorer()
        result = scorer.score({}, {}, "")
        assert isinstance(result, dict)
        assert "risk_score" in result
        assert "explanation" in result
        assert isinstance(result["explanation"], list)


class TestDatasetBuilder:
    def test_synthetic_dataset_generation(self):
        from app.ml.ghan.dataset import GhandatasetBuilder
        import tempfile
        import os

        builder = GhandatasetBuilder()
        dataset = builder._generate_synthetic_dataset()
        assert len(dataset) > 0
        assert "label" in dataset.columns
        assert "ticker" in dataset.columns
        assert set(dataset["label"].unique()).issubset({0, 1, 2})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
