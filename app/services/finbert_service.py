"""
FinBERT Sentiment Service
Uses ProsusAI/finbert — a BERT model fine-tuned on financial news.
Runs entirely on CPU; ~50ms per article after the first warm-up call.
The model (~440 MB) is downloaded once by HuggingFace and cached in ~/.cache.

Falls back to keyword heuristics if transformers / torch are not available.
"""
import logging
import threading
from typing import Dict, List

logger = logging.getLogger(__name__)

_SCORE_MAP = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}

# Keyword fallback lists (finance-specific)
_NEG_WORDS = {
    "crash", "fail", "loss", "decline", "drop", "risk", "warning", "shortage",
    "disruption", "ban", "sanction", "recall", "halt", "default", "bankruptcy",
    "downgrade", "miss", "cut", "layoff", "investigation", "lawsuit", "tariff",
    "inflation", "recession", "deficit", "downfall", "penalty",
}
_POS_WORDS = {
    "growth", "beat", "surge", "profit", "gain", "record", "breakthrough",
    "expansion", "recovery", "strong", "upgrade", "raise", "acquisition",
    "partnership", "approval", "dividend", "buyback", "bullish", "outperform",
    "exceed", "launch", "milestone", "innovative", "momentum",
}


def _keyword_score(text: str) -> Dict:
    words = set(text.lower().split())
    neg   = len(words & _NEG_WORDS)
    pos   = len(words & _POS_WORDS)
    total = neg + pos or 1
    raw   = (pos - neg) / total
    label = "positive" if raw > 0.1 else "negative" if raw < -0.1 else "neutral"
    return {"label": label, "score": round(raw, 4), "confidence": 0.55, "source": "keyword"}


class FinBERTService:
    """
    Lazy-loads ProsusAI/finbert on first use so startup is instant.
    Thread-safe: a lock prevents duplicate downloads.
    """

    MODEL_ID = "ProsusAI/finbert"

    def __init__(self):
        self._pipeline  = None
        self._available = False
        self._lock      = threading.Lock()
        self._load_thread = threading.Thread(target=self._load, daemon=True, name="finbert-load")
        self._load_thread.start()

    def _load(self):
        try:
            from transformers import pipeline as hf_pipeline
            import torch

            logger.info("Loading FinBERT (%s) — first run downloads ~440 MB…", self.MODEL_ID)
            pipe = hf_pipeline(
                "text-classification",
                model=self.MODEL_ID,
                tokenizer=self.MODEL_ID,
                device=-1,           # CPU
                truncation=True,
                max_length=512,
            )
            # Warm-up call so the first real call is fast
            pipe("Market is stable.")
            with self._lock:
                self._pipeline  = pipe
                self._available = True
            logger.info("✅ FinBERT ready")
        except Exception as exc:
            logger.warning("FinBERT unavailable (%s) — using keyword fallback", exc)
            self._available = False

    # ── Public API ────────────────────────────────────────────────────────────

    def score(self, text: str) -> Dict:
        """Score a single piece of text. Returns dict with label/score/confidence."""
        with self._lock:
            pipe = self._pipeline

        if pipe is None:
            return _keyword_score(text)

        try:
            result = pipe(text[:512])[0]
            raw    = _SCORE_MAP.get(result["label"], 0.0) * result["score"]
            return {
                "label":      result["label"],
                "score":      round(raw, 4),
                "confidence": round(result["score"], 4),
                "source":     "finbert",
            }
        except Exception as exc:
            logger.debug("FinBERT score error: %s", exc)
            return _keyword_score(text)

    def score_batch(self, texts: List[str]) -> List[Dict]:
        """
        Score multiple texts in a single forward pass (much faster than looping).
        """
        with self._lock:
            pipe = self._pipeline

        if pipe is None:
            return [_keyword_score(t) for t in texts]

        try:
            truncated = [t[:512] for t in texts]
            results   = pipe(truncated)
            return [
                {
                    "label":      r["label"],
                    "score":      round(_SCORE_MAP.get(r["label"], 0.0) * r["score"], 4),
                    "confidence": round(r["score"], 4),
                    "source":     "finbert",
                }
                for r in results
            ]
        except Exception as exc:
            logger.error("FinBERT batch error: %s", exc)
            return [_keyword_score(t) for t in texts]

    @property
    def ready(self) -> bool:
        return self._available


# ── Module-level singleton ────────────────────────────────────────────────────
finbert = FinBERTService()
