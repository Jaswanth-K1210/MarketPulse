"""
Classification Service — FinBERT-first, LLMRouter-fallback pipeline.

Flow:
  1. FinBERT: sentiment + event_type + confidence
  2. Keyword fast-path: confidence >= 0.7 + keyword match → return (~80% articles)
  3. Ambiguous: llm_router.call("fast", prompt) for lightweight JSON completion
  4. Heuristic fallback
"""
import logging
import json
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _get_finbert():
    try:
        from app.ml.finbert_service import finbert_service
        return finbert_service
    except Exception as e:
        logger.debug("FinBERT unavailable: %s", e)
        return None


def _get_llm_router():
    try:
        from app.ml.llm_router import llm_router
        return llm_router
    except Exception as e:
        logger.debug("LLMRouter unavailable: %s", e)
        return None


def _keyword_factor_match(text: str):
    try:
        from app.models.factors import MarketFactor, FACTOR_METADATA
        text_lower = text.lower()
        for factor, meta in FACTOR_METADATA.items():
            if any(kw.lower() in text_lower for kw in meta.get("keywords", [])):
                return factor, FACTOR_METADATA
    except Exception:
        pass
    return None, {}


def _sentiment_from_score(score: float) -> str:
    if score > 0.1:
        return "positive"
    if score < -0.1:
        return "negative"
    return "neutral"


def _heuristic_fallback(title: str, content: str) -> Dict[str, Any]:
    try:
        from app.models.factors import MarketFactor, FACTOR_METADATA
    except Exception:
        return {"factor_type": "market_sentiment", "factor_name": "Market Sentiment",
                "sentiment": "neutral", "sentiment_score": 0.0,
                "reasoning": "Heuristic fallback", "confidence": 0.4, "affected_sectors": []}
    text = f"{title} {content}".lower()
    factor, meta_map = _keyword_factor_match(text)
    if factor is None:
        factor = MarketFactor.MARKET_SENTIMENT
        meta_map = FACTOR_METADATA
    if any(x in text for x in ["halt", "shutdown", "shortage", "crash", "fire", "war", "sanction", "collapse"]):
        sentiment, score = "negative", -0.7
    elif any(x in text for x in ["growth", "launch", "partnership", "breakthrough", "record", "surge"]):
        sentiment, score = "positive", 0.5
    else:
        sentiment, score = "neutral", 0.0
    return {
        "factor_type": factor.value,
        "factor_name": meta_map[factor]["name"],
        "sentiment": sentiment,
        "sentiment_score": score,
        "reasoning": f"Heuristic fallback: {factor.name}",
        "confidence": 0.45,
        "affected_sectors": [],
    }


class ClassificationService:
    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client  # kept for backward compat

    def classify_article(self, title: str, content: str) -> Dict[str, Any]:
        text = f"{title} {content}"

        # Step 1: FinBERT
        finbert_result = self._run_finbert(title, content)
        if finbert_result:
            confidence = finbert_result.get("confidence", 0.0)
            score = finbert_result.get("score", 0.0)
            event_type = finbert_result.get("event_type", "")
            matched_factor, meta_map = _keyword_factor_match(text)

            # Step 2: fast-path (no LLM)
            if confidence >= 0.7 and matched_factor is not None:
                return {
                    "factor_type": matched_factor.value,
                    "factor_name": meta_map[matched_factor]["name"],
                    "sentiment": _sentiment_from_score(score),
                    "sentiment_score": round(score, 4),
                    "reasoning": f"FinBERT fast-path (conf={confidence:.2f}, event={event_type})",
                    "confidence": confidence,
                    "affected_sectors": [],
                }

        # Step 3: LLM for ambiguous articles
        llm_result = self._run_llm(title, content)
        if llm_result:
            return llm_result

        return _heuristic_fallback(title, content)

    def _run_finbert(self, title: str, content: str) -> Optional[Dict]:
        svc = _get_finbert()
        if svc is None:
            return None
        try:
            return svc.classify(title, content)
        except Exception as e:
            logger.warning("FinBERT failed: %s", e)
            return None

    def _run_llm(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        router = _get_llm_router()
        if router is None:
            return None
        try:
            from app.models.factors import MarketFactor, FACTOR_METADATA
            factor_names = [v["name"] for v in FACTOR_METADATA.values()]
            prompt = (
                f"Classify this news into ONE market factor. "
                f"Factors: {json.dumps(factor_names)}. "
                f"Title: {title[:200]}. Content: {content[:500]}. "
                f'Return JSON only: {{"factor_name":"...", "sentiment_score":<-1 to 1>, "confidence":<0 to 1>}}'
            )
            raw = router.call("fast", prompt)
            cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            score = float(data.get("sentiment_score", 0.0))
            confidence = float(data.get("confidence", 0.6))
            factor_name = data.get("factor_name", "")
            matched = MarketFactor.MARKET_SENTIMENT
            for k, v in FACTOR_METADATA.items():
                if v["name"].lower() == factor_name.lower():
                    matched = k
                    break
            return {
                "factor_type": matched.value,
                "factor_name": FACTOR_METADATA[matched]["name"],
                "sentiment": _sentiment_from_score(score),
                "sentiment_score": round(score, 4),
                "reasoning": f"LLMRouter fast-tier (conf={confidence:.2f})",
                "confidence": confidence,
                "affected_sectors": [],
            }
        except Exception as e:
            logger.error("LLMRouter classification failed: %s", e)
            return None


try:
    from app.services.gemini_client import GeminiClient
    _gemini = GeminiClient()
except Exception:
    _gemini = None

classification_service = ClassificationService(_gemini)
