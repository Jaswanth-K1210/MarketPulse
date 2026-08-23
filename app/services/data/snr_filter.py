"""
SNR Filter — Signal-to-Noise Ratio filtering for financial news.

FinGPT core insight: data quality beats model quality.
Raw news → LLM directly is the mistake FinGPT warns about.
This filter scores and rejects low-quality articles BEFORE they hit any LLM call.

Scoring dimensions:
1. Source tier weight (Tier 1 = Reuters/Bloomberg → high, Tier 4 = blogs → low)
2. Recency decay (older articles lose signal)
3. Content quality (length, boilerplate detection, paywall markers)
4. Portfolio relevance (mentions tickers in user's portfolio)
5. Near-duplicate detection (same story from 5 sources → keep best 1)
"""
import logging
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Source tier weights ──────────────────────────────────────────────────────
# Tier 1 = official/regulatory (Reuters, Bloomberg, FT, WSJ, Fed, SEC)
# Tier 2 = major financial (CNBC, Forbes, MarketWatch, Seeking Alpha)
# Tier 3 = industry/specialized (TechCrunch, Supply Chain Dive, etc.)
# Tier 4 = community/alternative (blogs, aggregators)
SOURCE_TIER_WEIGHT = {
    1: 1.0,
    2: 0.80,
    3: 0.55,
    4: 0.30,
}

# State-affiliated sources get a discount (propaganda risk)
STATE_AFFILIATED_DISCOUNT = 0.70

# ── Content quality heuristics ──────────────────────────────────────────────
MIN_TITLE_LENGTH = 15
MIN_CONTENT_LENGTH = 100
MAX_CONTENT_LENGTH = 50000  # Trim anything beyond this

# Paywall / boilerplate indicators that reduce signal
PAYWALL_MARKERS = [
    "subscribe to read", "subscription required", "premium content",
    "members only", "sign in to read", "create an account",
    "cookie policy", "privacy policy", "terms of service",
    "advertisement", "sponsored content", "paid partnership",
]

# High-signal financial keywords (boost score)
FINANCIAL_KEYWORDS = [
    "earnings", "revenue", "profit", "loss", "guidance", "outlook",
    "merger", "acquisition", "takeover", "buyout", "ipo", "spac",
    "sec filing", "10-k", "10-q", "8-k", "form 4", "insider",
    "tariff", "sanction", "embargo", "trade war", "export control",
    "supply chain", "shortage", "disruption", "halt", "shutdown",
    "rate cut", "rate hike", "fomc", "inflation", "gdp", "recession",
    "semiconductor", "chip", "ai", "data center", "cloud",
    "oil", "opec", "crude", "natural gas", "lng",
    "fda", "clinical trial", "drug approval", "patent",
    "bankruptcy", "default", "downgrade", "upgrade",
    "ipo", "buyback", "dividend", "split",
]

# ── Recency decay ───────────────────────────────────────────────────────────
# Articles lose signal over time. Fresh = full weight, stale = discounted.
RECENCY_HALF_LIFE_HOURS = 6  # After 6 hours, score is halved


class SNRFilter:
    """
    Scores and filters news articles by signal-to-noise ratio.
    Run this AFTER ingestion but BEFORE any LLM processing.
    """

    def __init__(self):
        self._title_hashes: Dict[str, float] = {}  # hash → timestamp for dedup
        self._dedup_window = 3600  # 1 hour dedup window

    def filter_articles(
        self,
        articles: list,
        portfolio: Optional[List[str]] = None,
        min_score: float = 0.30,
        max_articles: int = 10,
    ) -> Tuple[list, Dict]:
        """
        Score and filter articles. Returns (filtered_articles, stats).

        Args:
            articles: List of Article objects or dicts
            portfolio: User's portfolio tickers (for relevance boost)
            min_score: Minimum SNR score to keep (0.0-1.0)
            max_articles: Maximum articles to return (ranked by score)

        Returns:
            (filtered_articles, stats_dict)
        """
        if not articles:
            return [], {"total": 0, "kept": 0, "filtered": 0}

        portfolio_set = set(t.upper() for t in (portfolio or []))
        scored = []

        for article in articles:
            score, breakdown = self._score_article(article, portfolio_set)
            if score >= min_score:
                scored.append((article, score, breakdown))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Near-duplicate removal: if two articles have >80% title overlap, keep higher-scored one
        deduped = self._remove_near_duplicates(scored)

        # Cap at max_articles
        final = deduped[:max_articles]

        stats = {
            "total": len(articles),
            "kept": len(final),
            "filtered": len(articles) - len(final),
            "avg_score": round(sum(s for _, s, _ in final) / len(final), 3) if final else 0,
            "min_score_kept": round(final[-1][1], 3) if final else 0,
            "dedup_removed": len(scored) - len(deduped),
        }

        logger.info(
            f"SNR Filter: {stats['total']} → {stats['kept']} articles "
            f"(filtered {stats['filtered']}, dedup removed {stats['dedup_removed']}, "
            f"avg score {stats['avg_score']})"
        )

        return [article for article, _, _ in final], stats

    def _score_article(self, article, portfolio_set: set) -> Tuple[float, Dict]:
        """
        Score a single article on [0, 1] scale.
        Returns (score, breakdown_dict).
        """
        breakdown = {}
        score = 0.5  # Base score

        # 1. Source tier weight
        tier = getattr(article, "priority", None) or 2
        tier_weight = SOURCE_TIER_WEIGHT.get(tier, 0.5)
        score *= tier_weight
        breakdown["source_tier"] = tier_weight

        # 2. State-affiliated discount
        source = getattr(article, "source", "") or ""
        # Heuristic: certain sources are state-affiliated
        state_sources = {"xinhua", "cgtn", "rt", "sputnik", "press tv", "al mayadeen"}
        if any(s in source.lower() for s in state_sources):
            score *= STATE_AFFILIATED_DISCOUNT
            breakdown["state_affiliated"] = True

        # 3. Content quality
        title = getattr(article, "title", "") or ""
        content = getattr(article, "content", "") or ""
        content_len = len(content)

        # Title too short = likely boilerplate
        if len(title) < MIN_TITLE_LENGTH:
            score *= 0.3
            breakdown["title_too_short"] = True

        # Content length signal
        if content_len < MIN_CONTENT_LENGTH:
            score *= 0.4
            breakdown["content_too_short"] = True
        elif content_len > 1000:
            # Longer content = more signal (up to a point)
            length_bonus = min(1.2, 1.0 + (content_len - 1000) / 10000)
            score *= length_bonus
            breakdown["content_length_bonus"] = round(length_bonus, 3)

        # Paywall / boilerplate detection
        content_lower = (title + " " + content).lower()
        paywall_hits = sum(1 for marker in PAYWALL_MARKERS if marker in content_lower)
        if paywall_hits > 0:
            paywall_penalty = max(0.3, 1.0 - paywall_hits * 0.2)
            score *= paywall_penalty
            breakdown["paywall_penalty"] = round(paywall_penalty, 3)

        # 4. Recency decay
        published = getattr(article, "published_at", None)
        if published:
            if isinstance(published, str):
                try:
                    published = datetime.fromisoformat(published)
                except Exception:
                    published = None

            if published:
                if published.tzinfo is None:
                    now = datetime.now(timezone.utc)
                else:
                    now = datetime.now(timezone.utc)
                    published = published.replace(tzinfo=timezone.utc) if published.tzinfo is None else published

                age_hours = max(0, (now - published).total_seconds() / 3600)
                recency = 0.5 ** (age_hours / RECENCY_HALF_LIFE_HOURS)
                score *= max(0.1, recency)  # Never go below 0.1 from recency alone
                breakdown["recency"] = round(recency, 3)
                breakdown["age_hours"] = round(age_hours, 1)

        # 5. Portfolio relevance boost
        companies = getattr(article, "companies_mentioned", []) or []
        if isinstance(companies, str):
            companies = [companies]

        mentioned_tickers = set(c.upper() for c in companies if c)
        overlap = mentioned_tickers & portfolio_set
        if overlap:
            relevance_boost = min(1.5, 1.0 + len(overlap) * 0.15)
            score *= relevance_boost
            breakdown["portfolio_relevance"] = round(relevance_boost, 3)
            breakdown["matched_tickers"] = list(overlap)
        else:
            # No portfolio overlap → still keep if it has financial keywords
            kw_hits = sum(1 for kw in FINANCIAL_KEYWORDS if kw in content_lower)
            if kw_hits >= 3:
                score *= 1.1  # Small boost for keyword-rich articles
                breakdown["keyword_boost"] = True

        # 6. Financial keyword density (signal richness)
        total_words = max(1, len(content_lower.split()))
        kw_hits = sum(1 for kw in FINANCIAL_KEYWORDS if kw in content_lower)
        kw_density = kw_hits / total_words * 100
        if kw_density > 2.0:
            score *= 1.15
            breakdown["keyword_density"] = round(kw_density, 2)

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))
        breakdown["final_score"] = round(score, 3)

        return score, breakdown

    def _remove_near_duplicates(self, scored_articles: list) -> list:
        """
        Remove near-duplicate articles. If two titles are >80% similar
        (Jaccard on word tokens), keep the higher-scored one.
        """
        if len(scored_articles) <= 1:
            return scored_articles

        keep = []
        seen_signatures = []

        for article, score, breakdown in scored_articles:
            title = getattr(article, "title", "") or ""
            words = set(re.findall(r'\w+', title.lower()))
            if not words:
                keep.append((article, score, breakdown))
                continue

            # Check against already-kept articles
            is_dup = False
            for sig_words in seen_signatures:
                if not sig_words:
                    continue
                intersection = len(words & sig_words)
                union = len(words | sig_words)
                jaccard = intersection / union if union > 0 else 0
                if jaccard > 0.75:
                    is_dup = True
                    break

            if not is_dup:
                keep.append((article, score, breakdown))
                seen_signatures.append(words)

        return keep

    def get_article_hash(self, article) -> str:
        """Generate a dedup hash from title + source."""
        title = getattr(article, "title", "") or ""
        source = getattr(article, "source", "") or ""
        return hashlib.md5(f"{title.lower().strip()}:{source.lower().strip()}".encode()).hexdigest()


# Singleton
snr_filter = SNRFilter()
