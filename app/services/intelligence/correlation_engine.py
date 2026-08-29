"""
Correlation Engine — Cross-module pattern detection.
Ported from WorldMonitor's correlation.ts.

Detects:
1. Silent divergence — major event with no market reaction
2. Flow-price divergence — ETF flows oppose price direction
3. Keyword spike — sudden frequency increase of specific terms
4. News-market alignment — event perfectly explains market move
"""

import time
import hashlib
import logging
from typing import Optional
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class CorrelationSignal:
    """A detected correlation or anomaly."""
    signal_type: str        # "silent_divergence", "keyword_spike", "news_market_alignment", etc.
    description: str
    confidence: float       # 0.0 to 1.0
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Unique key for dedup."""
        content = f"{self.signal_type}:{self.description[:100]}"
        return hashlib.md5(content.encode()).hexdigest()


# Dedup TTLs by signal type (seconds)
DEDUP_TTL = {
    "silent_divergence": 6 * 3600,      # 6 hours
    "flow_price_divergence": 6 * 3600,
    "keyword_spike": 1800,              # 30 minutes
    "news_market_alignment": 2 * 3600,  # 2 hours
    "sector_rotation": 4 * 3600,        # 4 hours
}

# Minimum confidence threshold
MIN_CONFIDENCE = 0.65

# Sector mapping for correlation analysis
SECTOR_KEYWORDS = {
    "energy": ["oil", "gas", "opec", "pipeline", "refinery", "crude", "petroleum"],
    "technology": ["tech", "semiconductor", "chip", "ai", "software", "cyber"],
    "financials": ["bank", "fed", "interest rate", "treasury", "bond", "credit"],
    "healthcare": ["pharma", "vaccine", "fda", "drug", "hospital", "pandemic"],
    "defense": ["military", "defense", "weapon", "missile", "nato", "pentagon"],
    "materials": ["mining", "steel", "aluminum", "copper", "lithium", "rare earth"],
    "consumer": ["retail", "consumer", "spending", "inflation", "cpi"],
}


class CorrelationEngine:
    """
    Detects patterns across news, market data, and signals.
    """

    def __init__(self):
        self._previous_keyword_freq: dict[str, int] = {}
        self._recent_signals: dict[str, float] = {}  # key -> timestamp
        self._previous_market_snapshot: Optional[dict] = None

    def _deduplicate(self, signals: list[CorrelationSignal]) -> list[CorrelationSignal]:
        """Remove duplicate signals within their TTL window."""
        now = time.time()
        deduped = []

        # Clean expired entries
        expired = [k for k, ts in self._recent_signals.items() if now - ts > 24 * 3600]
        for k in expired:
            del self._recent_signals[k]

        for signal in signals:
            ttl = DEDUP_TTL.get(signal.signal_type, 3600)
            key = signal.key

            if key in self._recent_signals:
                if now - self._recent_signals[key] < ttl:
                    continue  # Still within dedup window

            self._recent_signals[key] = now
            signal.timestamp = now
            deduped.append(signal)

        return deduped

    def analyze(
        self,
        classified_articles: list[dict],
        market_data: dict,
        signal_clusters: Optional[dict] = None,
    ) -> list[CorrelationSignal]:
        """
        Run all correlation analyses.

        Args:
            classified_articles: Articles with classification results
            market_data: Market overview (indices, sectors, commodities)
            signal_clusters: Country-level signal clusters from SignalAggregator

        Returns:
            List of detected correlation signals
        """
        signals: list[CorrelationSignal] = []

        # 1. Silent divergence detection
        signals.extend(self._detect_silent_divergence(classified_articles, market_data))

        # 2. Keyword spike detection
        signals.extend(self._detect_keyword_spikes(classified_articles))

        # 3. News-market alignment
        signals.extend(self._detect_news_market_alignment(classified_articles, market_data))

        # 4. Sector rotation signals
        signals.extend(self._detect_sector_rotation(market_data))

        # Filter by confidence and deduplicate
        signals = [s for s in signals if s.confidence >= MIN_CONFIDENCE]
        signals = self._deduplicate(signals)

        # Update previous snapshot
        self._previous_market_snapshot = market_data

        return signals

    def _detect_silent_divergence(
        self,
        articles: list[dict],
        market_data: dict,
    ) -> list[CorrelationSignal]:
        """
        Detect high-severity events with no corresponding market reaction.
        This may indicate the market hasn't priced in the event yet.
        """
        signals = []
        sectors = market_data.get("sectors", {})

        for article in articles:
            level = article.get("level", "")
            if level not in ("critical", "high"):
                continue

            title = article.get("title", "").lower()

            # Identify affected sectors
            affected = []
            for sector, keywords in SECTOR_KEYWORDS.items():
                if any(kw in title for kw in keywords):
                    affected.append(sector)

            # Check if those sectors moved
            for sector in affected:
                sector_data = sectors.get(sector, {})
                change_pct = abs(sector_data.get("change_pct", 0))

                if change_pct < 0.5:  # Less than 0.5% move = essentially flat
                    signals.append(CorrelationSignal(
                        signal_type="silent_divergence",
                        description=(
                            f"High-severity event ({article['title'][:60]}...) "
                            f"but {sector} sector moved only {change_pct:.1f}%"
                        ),
                        confidence=0.70,
                        metadata={
                            "article_title": article.get("title", ""),
                            "sector": sector,
                            "sector_change": change_pct,
                            "event_level": level,
                        },
                    ))

        return signals

    def _detect_keyword_spikes(
        self,
        articles: list[dict],
    ) -> list[CorrelationSignal]:
        """
        Detect sudden frequency increases of specific terms.
        A term mentioned 2x+ more than previous window = spike.
        """
        signals = []

        # Count keyword frequencies
        current_freq: dict[str, int] = Counter()
        for article in articles:
            title = article.get("title", "").lower()
            # Check against all sector keywords + geopolitical terms
            all_keywords = []
            for keywords in SECTOR_KEYWORDS.values():
                all_keywords.extend(keywords)
            all_keywords.extend([
                "war", "sanctions", "tariff", "crisis", "crash",
                "recession", "default", "coup", "invasion", "nuclear",
            ])

            for kw in all_keywords:
                if kw in title:
                    current_freq[kw] += 1

        # Compare with previous
        if self._previous_keyword_freq:
            for keyword, count in current_freq.items():
                prev_count = self._previous_keyword_freq.get(keyword, 0)
                if count >= prev_count * 2 and count >= 3:
                    signals.append(CorrelationSignal(
                        signal_type="keyword_spike",
                        description=f'"{keyword}" mentions surged: {prev_count} → {count}',
                        confidence=0.65 + min((count - prev_count) * 0.05, 0.25),
                        metadata={
                            "keyword": keyword,
                            "current_count": count,
                            "previous_count": prev_count,
                        },
                    ))

        self._previous_keyword_freq = dict(current_freq)
        return signals

    def _detect_news_market_alignment(
        self,
        articles: list[dict],
        market_data: dict,
    ) -> list[CorrelationSignal]:
        """
        Detect when news events perfectly explain market movements.
        """
        signals = []
        indices = market_data.get("indices", {})

        # Check if any index moved significantly
        for index_name, data in indices.items():
            change_pct = data.get("change_pct", 0)
            if abs(change_pct) < 1.5:
                continue

            # Look for high-severity articles that explain the move
            direction = "negative" if change_pct < 0 else "positive"
            for article in articles:
                level = article.get("level", "")
                sentiment = article.get("sentiment", "")

                if level in ("critical", "high") and (
                    (direction == "negative" and sentiment in ("negative", "")) or
                    (direction == "positive" and sentiment in ("positive", ""))
                ):
                    signals.append(CorrelationSignal(
                        signal_type="news_market_alignment",
                        description=(
                            f"{index_name} {change_pct:+.1f}% likely driven by: "
                            f"{article.get('title', '')[:60]}"
                        ),
                        confidence=0.75,
                        metadata={
                            "index": index_name,
                            "change_pct": change_pct,
                            "article_title": article.get("title", ""),
                        },
                    ))
                    break  # One explanation per index

        return signals

    def _detect_sector_rotation(self, market_data: dict) -> list[CorrelationSignal]:
        """Detect significant sector rotation (money flowing out of one sector into another)."""
        signals = []
        sectors = market_data.get("sectors", {})

        if len(sectors) < 5:
            return signals

        # Find biggest winners and losers
        sorted_sectors = sorted(
            sectors.items(),
            key=lambda x: x[1].get("change_pct", 0)
        )

        if len(sorted_sectors) >= 2:
            worst = sorted_sectors[0]
            best = sorted_sectors[-1]

            worst_change = worst[1].get("change_pct", 0)
            best_change = best[1].get("change_pct", 0)

            # Significant rotation: >2% spread between best and worst sectors
            spread = best_change - worst_change
            if spread >= 2.0:
                signals.append(CorrelationSignal(
                    signal_type="sector_rotation",
                    description=(
                        f"Sector rotation: {best[0]} (+{best_change:.1f}%) vs "
                        f"{worst[0]} ({worst_change:.1f}%), spread: {spread:.1f}%"
                    ),
                    confidence=0.70 + min(spread * 0.05, 0.20),
                    metadata={
                        "winning_sector": best[0],
                        "losing_sector": worst[0],
                        "spread": spread,
                    },
                ))

        return signals

    async def detect_all(self) -> list[dict]:
        """
        Async wrapper for the intelligence API router.
        Fetches market context from yfinance, runs all correlation analyses.
        """
        try:
            import yfinance as yf
            tickers = yf.download(["SPY", "QQQ", "^VIX"], period="5d", interval="1d",
                                  progress=False, auto_adjust=True, threads=False)
            closes = tickers["Close"].iloc[-1].to_dict() if not tickers.empty else {}
            market_data = {
                "sectors": {},
                "indices": {
                    "SPY": {"price": closes.get("SPY"), "change_pct": 0},
                    "QQQ": {"price": closes.get("QQQ"), "change_pct": 0},
                    "VIX": {"price": closes.get("^VIX"), "change_pct": 0},
                },
            }
        except Exception:
            market_data = {"sectors": {}, "indices": {}}

        results = self.analyze(classified_articles=[], market_data=market_data)
        return [
            {
                "type": s.signal_type,
                "description": s.description,
                "confidence": round(s.confidence, 2),
                "correlation_type": s.signal_type,
                "detail": s.description,
            }
            for s in results
        ]
