"""
Classification Pipeline — Orchestrates 3-tier classification:
  1. Keyword classifier (instant, free)
  2. Rule engine (pattern-based, free)
  3. LLM fallback (costs money, slower)
"""

import logging
from typing import Optional
from .keyword_classifier import classify_by_keywords

logger = logging.getLogger(__name__)

# Valid severity levels (whitelist for enum validation)
VALID_LEVELS = {"critical", "high", "medium", "low", "info"}

# Valid categories
VALID_CATEGORIES = {
    "conflict", "geopolitical", "economic", "natural_disaster",
    "cyber", "health", "supply_chain", "technology", "energy",
    "market_sentiment", "government_policy", "general", "entertainment",
}


async def classify_article(
    article: dict,
    llm_classify_fn=None,
) -> dict:
    """
    3-tier classification pipeline.

    Args:
        article: Dict with at least 'title' key
        llm_classify_fn: Optional async function for LLM classification fallback

    Returns:
        Classification result dict with level, category, confidence, source
    """
    title = article.get("title", "")
    content = article.get("content", "") or article.get("description", "")

    # Tier 1: Keyword classifier (FREE, instant)
    result = classify_by_keywords(title)
    if result is not None:
        return result

    # Tier 2: Content keyword check (still free, checks body text)
    if content:
        result = classify_by_keywords(content[:200])  # Check first 200 chars of body
        if result is not None:
            result["source"] = "keyword_content"
            result["confidence"] *= 0.9  # Slightly lower confidence for body-match
            return result

    # Tier 3: LLM fallback (costs money)
    if llm_classify_fn:
        try:
            result = await llm_classify_fn(article)
            if result and _validate_classification(result):
                result["source"] = "llm"
                return result
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")

    # Ultimate fallback: return low/general
    return {
        "level": "low",
        "category": "general",
        "confidence": 0.3,
        "source": "fallback",
    }


def _validate_classification(result: dict) -> bool:
    """Validate LLM classification result against whitelists."""
    if not isinstance(result, dict):
        return False

    level = result.get("level", "").lower()
    category = result.get("category", "").lower()

    if level and level not in VALID_LEVELS:
        logger.warning(f"Invalid classification level: '{level}'")
        return False

    if category and category not in VALID_CATEGORIES:
        logger.warning(f"Invalid classification category: '{category}'")
        return False

    return True
