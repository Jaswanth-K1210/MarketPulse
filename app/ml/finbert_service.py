"""
Task 1.6 — FinBERT sentiment + event_type + severity
Replaces direct Gemini zero-shot classification in classification_service.py.
Uses ProsusAI/finbert from HuggingFace (free, runs CPU-only).
Falls back to keyword scoring if model fails to load.
"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Event keyword patterns for fallback + event_type extraction
_EVENT_PATTERNS = {
    "production_halt":          r"halt|shutdown|closure|suspend|stop.?produc",
    "factory_fire":             r"fire|explosion|blaze|burn",
    "natural_disaster":         r"earthquake|flood|typhoon|hurricane|tsunami|disaster",
    "supply_chain_disruption":  r"supply.?chain|shortage|bottleneck|backlog|disruption",
    "trade_restriction":        r"tariff|sanction|ban|export.?control|embargo",
    "chip_shortage":            r"chip.?short|semicond.*short|wafer|fab.?capac",
    "geopolitical_event":       r"war|conflict|tension|invasion|geopolit",
    "regulatory_action":        r"regulat|fine|penalt|lawsuit|antitrust|compliance",
    "acquisition":              r"acqui|merger|takeover|buyout|purchase",
    "partnership":              r"partner|joint.?venture|alliance|collaborat|deal",
    "earnings_report":          r"earning|revenue|profit|loss|quarterly|EPS|guidance",
    "product_launch":           r"launch|release|announce.*product|new.*product|introduc",
    "technology_breakthrough":  r"breakthrough|innovation|patent|AI|quantum",
}

_NEGATIVE_WORDS = {
    "halt", "shutdown", "fire", "explosion", "shortage", "sanction", "ban", "conflict",
    "war", "invasion", "fine", "penalty", "lawsuit", "disruption", "recall", "fraud",
    "collapse", "crisis", "default", "downgrade", "cut", "miss", "loss", "decline",
}
_POSITIVE_WORDS = {
    "growth", "record", "beat", "partnership", "launch", "innovation", "profit", "surge",
    "expand", "upgrade", "award", "deal", "acquisition", "breakthrough", "strong", "gain",
}


def _keyword_sentiment(text: str) -> Dict:
    tokens = set(re.findall(r"\b\w+\b", text.lower()))
    neg_hits = len(tokens & _NEGATIVE_WORDS)
    pos_hits = len(tokens & _POSITIVE_WORDS)
    total = neg_hits + pos_hits or 1
    score = (pos_hits - neg_hits) / total  # -1 to 1
    label = "positive" if score > 0.1 else ("negative" if score < -0.1 else "neutral")
    return {"label": label, "score": round(score, 3), "confidence": 0.6}


def _detect_event_type(text: str) -> str:
    text_lower = text.lower()
    for event, pattern in _EVENT_PATTERNS.items():
        if re.search(pattern, text_lower):
            return event
    return "market_sentiment"


def _severity_from_score(score: float) -> str:
    abs_score = abs(score)
    if abs_score >= 0.7:
        return "high"
    if abs_score >= 0.4:
        return "medium"
    return "low"


class FinBERTService:
    """
    Wraps ProsusAI/finbert for financial sentiment classification.
    Exposes classify(title, content) → {sentiment, score, event_type, severity, confidence}.
    """

    def __init__(self):
        self._pipeline = None
        self._load_model()

    def _load_model(self):
        try:
            from transformers import pipeline as hf_pipeline
            self._pipeline = hf_pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                device=-1,  # CPU
                truncation=True,
                max_length=512,
            )
            logger.info("FinBERT loaded (ProsusAI/finbert, CPU mode)")
        except Exception as e:
            logger.warning("FinBERT failed to load (%s) — using keyword fallback", e)
            self._pipeline = None

    def classify(self, title: str, content: str = "") -> Dict:
        """
        Returns:
            sentiment:  positive | negative | neutral
            score:      float in [-1, 1]
            event_type: string from EVENT_PATTERNS
            severity:   low | medium | high
            confidence: float in [0, 1]
        """
        text = f"{title}. {content[:400]}"
        event_type = _detect_event_type(text)

        if self._pipeline is not None:
            try:
                result = self._pipeline(text[:512])[0]
                label = result["label"].lower()   # positive/negative/neutral
                conf = round(float(result["score"]), 3)
                score_map = {"positive": conf, "negative": -conf, "neutral": 0.0}
                score = score_map.get(label, 0.0)
                return {
                    "sentiment": label,
                    "score": round(score, 3),
                    "event_type": event_type,
                    "severity": _severity_from_score(score),
                    "confidence": conf,
                    "source": "finbert",
                }
            except Exception as e:
                logger.warning("FinBERT inference failed: %s — falling back", e)

        # Keyword fallback
        kw = _keyword_sentiment(text)
        return {
            "sentiment": kw["label"],
            "score": kw["score"],
            "event_type": event_type,
            "severity": _severity_from_score(kw["score"]),
            "confidence": kw["confidence"],
            "source": "keyword",
        }

    def classify_batch(self, articles: List[Dict]) -> List[Dict]:
        """Classify a list of {title, content} dicts. Returns list of classification results."""
        results = []
        for art in articles:
            try:
                result = self.classify(art.get("title", ""), art.get("content", ""))
                results.append({**art, **result})
            except Exception as e:
                logger.warning("classify_batch item failed: %s", e)
                results.append({**art, "sentiment": "neutral", "score": 0.0, "event_type": "market_sentiment", "severity": "low", "confidence": 0.0})
        return results


# Singleton
finbert_service = FinBERTService()
