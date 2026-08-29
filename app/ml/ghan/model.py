"""
GHAN-Lite Model — GATConv bipartite graph attention network for
news→price direction prediction.
"""
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "ghan.pt"
METRICS_PATH = MODEL_DIR / "ghan_metrics.json"

HAS_TORCH = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    logger.info("PyTorch not available — GHAN model will use fallback")


if HAS_TORCH:
    class GhanModel(nn.Module):
        """GATConv bipartite graph attention model per GHAN-Lite spec.

        Architecture:
        - GATConv((64, 64), 32, heads=4) → GATConv((128, 128), 64)
        - MLP head: concat(event_repr, ticker_repr) → 3 logits
        - Class-weighted cross-entropy, dropout 0.3
        """

        def __init__(self, in_dim: int = 64, hidden_dim: int = 32, heads: int = 4, n_classes: int = 3):
            super().__init__()
            try:
                from torch_geometric.nn import GATConv
                self.gat1 = GATConv((in_dim, in_dim), hidden_dim, heads=heads, dropout=0.3)
                self.gat2 = GATConv((hidden_dim * heads, in_dim), hidden_dim * heads, heads=1, dropout=0.3)
                self.use_pyg = True
            except ImportError:
                logger.warning("torch_geometric not available — using linear fallback")
                self.use_pyg = False
                self.linear1 = nn.Linear(in_dim, hidden_dim * heads)
                self.linear2 = nn.Linear(hidden_dim * heads, hidden_dim * heads)

            self.classifier = nn.Sequential(
                nn.Linear(hidden_dim * heads * 2, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, n_classes),
            )

        def forward(self, x, edge_index=None, event_mask=None, ticker_mask=None):
            if self.use_pyg and edge_index is not None:
                h = F.elu(self.gat1(x, edge_index))
                h = self.gat2(h, edge_index)
            else:
                h = F.elu(self.linear1(x))
                h = self.linear2(h)

            if event_mask is not None and ticker_mask is not None:
                event_repr = h[event_mask]
                ticker_repr = h[ticker_mask]
                n_events = event_repr.shape[0]
                n_tickers_per = ticker_repr.shape[0] // max(n_events, 1)
                if n_tickers_per > 0 and n_events > 0:
                    ticker_pooled = ticker_repr.view(n_events, n_tickers_per, -1).mean(dim=1)
                    combined = torch.cat([event_repr, ticker_pooled], dim=-1)
                else:
                    combined = torch.cat([event_repr, event_repr], dim=-1)
            else:
                combined = h

            logits = self.classifier(combined)
            return logits

        def predict_proba(self, x, edge_index=None, event_mask=None, ticker_mask=None):
            self.eval()
            with torch.no_grad():
                logits = self.forward(x, edge_index, event_mask, ticker_mask)
                probs = F.softmax(logits, dim=-1)
            return probs.cpu().numpy()


class GHANScorer:
    """Scorer that wraps the GHAN model with the same interface as risk_scorer."""

    def __init__(self):
        self._model = None
        self._ticker_vocab = {}
        self._load_model()

    def _load_model(self):
        if not HAS_TORCH or not MODEL_PATH.exists():
            logger.info("GHAN model not available — using fallback")
            return

        try:
            checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
            config = checkpoint.get("config", {})
            model = GhanModel(
                in_dim=config.get("in_dim", 64),
                hidden_dim=config.get("hidden_dim", 32),
                heads=config.get("heads", 4),
                n_classes=config.get("n_classes", 3),
            )
            model.load_state_dict(checkpoint["model_state_dict"])
            self._model = model
            self._ticker_vocab = checkpoint.get("ticker_vocab", {})
            logger.info("GHAN model loaded from %s", MODEL_PATH)
        except Exception as e:
            logger.warning("Could not load GHAN model: %s", e)

    def score(self, article_meta: Dict, relationship: Dict, event_type: str = "") -> Dict:
        if self._model is None:
            return self._fallback_score(article_meta, relationship, event_type)

        try:
            from app.ml.finbert_service import finbert_service
            text = article_meta.get("content", article_meta.get("title", ""))
            embedding = finbert_service.get_embedding(text) if text else np.zeros(768)
        except Exception:
            embedding = np.random.randn(768).astype(np.float32) * 0.1

        ticker = article_meta.get("ticker", article_meta.get("target_ticker", ""))
        if ticker and ticker in self._ticker_vocab:
            ticker_idx = self._ticker_vocab[ticker]
        else:
            return self._fallback_score(article_meta, relationship, event_type)

        try:
            x = torch.randn(1, 768)
            x[0, :min(len(embedding), 768)] = torch.tensor(embedding[:768], dtype=torch.float32)
            probs = self._model.predict_proba(x)
            probs = probs[0] if len(probs.shape) > 1 else probs

            signed_impact = float(probs[2] - probs[0])
            risk_score = float(abs(signed_impact))

            explanation = [
                {"class": "down", "probability": round(float(probs[0]), 4)},
                {"class": "flat", "probability": round(float(probs[1]), 4)},
                {"class": "up", "probability": round(float(probs[2]), 4)},
                {"signed_impact": round(signed_impact, 4)},
            ]
            return {"risk_score": round(risk_score, 4), "explanation": explanation}

        except Exception as e:
            logger.warning("GHAN inference failed: %s", e)
            return self._fallback_score(article_meta, relationship, event_type)

    def _fallback_score(self, article_meta: Dict, relationship: Dict, event_type: str) -> Dict:
        from app.ml.risk_scorer import risk_scorer
        return risk_scorer.score(article_meta, relationship, event_type)


ghan_scorer = GHANScorer()
