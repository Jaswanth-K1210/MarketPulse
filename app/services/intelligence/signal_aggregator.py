"""
Signal Aggregator — Country-level signal clustering, convergence detection, AI context generation.
Ported from WorldMonitor's signal-aggregator.ts.

Collects multi-domain signals, clusters by country/region,
scores convergence, and generates context for LLM prompts.
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

# Sliding window for signal freshness
SIGNAL_WINDOW_HOURS = 24

# Predefined regions for convergence detection
REGIONS = {
    "Middle East": ["IR", "IQ", "SY", "YE", "SA", "IL", "PS", "LB", "JO", "KW", "BH", "QA", "AE", "OM"],
    "East Asia": ["CN", "TW", "JP", "KR", "KP", "MN"],
    "South Asia": ["IN", "PK", "BD", "AF", "LK", "NP"],
    "Southeast Asia": ["MM", "TH", "VN", "PH", "ID", "MY", "SG", "LA", "KH"],
    "Eastern Europe": ["UA", "RU", "BY", "MD", "GE", "AM", "AZ"],
    "Sub-Saharan Africa": ["SD", "SS", "SO", "ET", "NG", "ML", "BF", "NE", "TD", "CD", "CF", "MZ", "KE"],
    "North Africa": ["LY", "EG", "TN", "DZ", "MA"],
    "Latin America": ["VE", "CO", "MX", "BR", "AR", "CL", "PE", "EC", "CU", "HT"],
    "Europe": ["GB", "FR", "DE", "IT", "ES", "PL", "NL", "BE", "SE", "NO", "FI", "DK"],
    "North America": ["US", "CA"],
}


@dataclass
class Signal:
    """A single intelligence signal from any data source."""
    id: str
    signal_type: str          # "conflict", "market", "news", "protest", "cyber", "climate", "infrastructure"
    country_code: str         # ISO 2-letter
    severity: str             # "critical", "high", "medium", "low"
    title: str
    description: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    timestamp: float = 0.0    # Unix timestamp
    source: str = ""          # Data source name
    metadata: dict = field(default_factory=dict)


@dataclass
class CountryCluster:
    """Aggregated signals for a single country."""
    country_code: str
    country_name: str = ""
    signals: list = field(default_factory=list)
    signal_types: set = field(default_factory=set)
    score: float = 0.0

    def compute_score(self) -> float:
        """
        Cluster score formula:
        score = (type_count × 20) + (signal_count × 5) + (high_severity_count × 10)
        """
        type_count = len(self.signal_types)
        signal_count = len(self.signals)
        high_count = sum(
            1 for s in self.signals
            if s.severity in ("critical", "high")
        )
        self.score = (type_count * 20) + (signal_count * 5) + (high_count * 10)
        return self.score


@dataclass
class ConvergenceZone:
    """Region where multiple signal types converge."""
    region: str
    countries: list[str]
    signal_types: set
    total_signals: int
    priority: str  # "critical", "high", "medium"
    description: str = ""


class SignalAggregator:
    """
    Collects multi-domain signals, clusters by country/region,
    scores convergence, and generates AI context for LLM prompts.
    """

    def __init__(self):
        self.signals: list[Signal] = []
        self._country_names: dict[str, str] = {}

    def _prune_stale(self) -> None:
        """Remove signals older than the window."""
        cutoff = time.time() - (SIGNAL_WINDOW_HOURS * 3600)
        self.signals = [s for s in self.signals if s.timestamp > cutoff]

    def clear_type(self, signal_type: str) -> None:
        """Clear all signals of a specific type (before re-ingesting fresh data)."""
        self.signals = [s for s in self.signals if s.signal_type != signal_type]

    # ============================================================
    # Ingest methods — Convert various data sources into signals
    # ============================================================

    def ingest_news_signals(self, classified_articles: list[dict]) -> int:
        """Convert classified news articles into signals."""
        self.clear_type("news")
        count = 0

        for article in classified_articles:
            level = article.get("level", "low")
            if level in ("info", "entertainment"):
                continue

            country = article.get("country_code", "")
            if not country:
                # Try to infer country from content
                country = self._infer_country(
                    article.get("title", "") + " " + article.get("content", "")[:200]
                )

            if country:
                self.signals.append(Signal(
                    id=f"news_{hash(article.get('title', ''))}",
                    signal_type="news",
                    country_code=country,
                    severity=level,
                    title=article.get("title", "")[:200],
                    timestamp=time.time(),
                    source=article.get("source", "news"),
                ))
                count += 1

        return count

    def ingest_conflict_signals(self, acled_events: list[dict]) -> int:
        """Convert ACLED/UCDP conflict events into signals."""
        self.clear_type("conflict")
        count = 0
        # Cap at 50 per country to prevent unbounded growth
        country_counts: dict[str, int] = defaultdict(int)

        for event in acled_events:
            cc = event.get("country_code", "")[:2]
            if not cc or country_counts[cc] >= 50:
                continue

            etype = event.get("event_type", "")
            severity = "high" if etype in ("battles", "explosions_remote_violence", "violence_against_civilians") else "medium"
            fatalities = event.get("fatalities", 0)
            if fatalities >= 10:
                severity = "critical"
            elif fatalities >= 5:
                severity = "high"

            self.signals.append(Signal(
                id=event.get("id", f"conflict_{count}"),
                signal_type="conflict",
                country_code=cc,
                severity=severity,
                title=f"{etype}: {event.get('location', '')}",
                description=event.get("notes", "")[:200],
                latitude=event.get("latitude", 0),
                longitude=event.get("longitude", 0),
                timestamp=time.time(),
                source="acled",
                metadata={"fatalities": fatalities, "event_type": etype},
            ))
            country_counts[cc] += 1
            count += 1

        return count

    def ingest_market_signals(self, market_data: dict) -> int:
        """Convert significant market moves into signals."""
        self.clear_type("market")
        count = 0

        # Check indices for significant moves
        for name, data in market_data.get("indices", {}).items():
            change_pct = abs(data.get("change_pct", 0))
            if change_pct >= 2:
                severity = "critical" if change_pct >= 5 else "high" if change_pct >= 3 else "medium"
                direction = "drops" if data.get("change_pct", 0) < 0 else "surges"
                self.signals.append(Signal(
                    id=f"market_{name}",
                    signal_type="market",
                    country_code="US",  # Most indices are US
                    severity=severity,
                    title=f"{name} {direction} {data.get('change_pct', 0):+.1f}%",
                    timestamp=time.time(),
                    source="market",
                ))
                count += 1

        # Check commodities for significant moves
        for name, data in market_data.get("commodities", {}).items():
            change_pct = abs(data.get("change_pct", 0))
            if change_pct >= 3:
                severity = "high" if change_pct >= 5 else "medium"
                self.signals.append(Signal(
                    id=f"commodity_{name}",
                    signal_type="market",
                    country_code="GLOBAL",
                    severity=severity,
                    title=f"{name} moves {data.get('change_pct', 0):+.1f}%",
                    timestamp=time.time(),
                    source="commodities",
                ))
                count += 1

        return count

    # ============================================================
    # Clustering and Analysis
    # ============================================================

    def get_country_clusters(self) -> dict[str, CountryCluster]:
        """Group signals by country and compute cluster scores."""
        self._prune_stale()

        clusters: dict[str, CountryCluster] = {}
        for signal in self.signals:
            cc = signal.country_code
            if not cc:
                continue

            if cc not in clusters:
                clusters[cc] = CountryCluster(
                    country_code=cc,
                    country_name=self._country_names.get(cc, cc),
                )
            cluster = clusters[cc]
            cluster.signals.append(signal)
            cluster.signal_types.add(signal.signal_type)

        # Compute scores
        for cluster in clusters.values():
            cluster.compute_score()

        return clusters

    def get_convergence_zones(self) -> list[ConvergenceZone]:
        """
        Detect regions where multiple signal types converge.
        3+ different signal types in same region = convergence alert.
        """
        clusters = self.get_country_clusters()
        zones = []

        for region_name, country_codes in REGIONS.items():
            region_signal_types: set = set()
            region_countries: list[str] = []
            total_signals = 0

            for cc in country_codes:
                if cc in clusters:
                    cluster = clusters[cc]
                    region_signal_types.update(cluster.signal_types)
                    region_countries.append(cc)
                    total_signals += len(cluster.signals)

            if len(region_signal_types) >= 3:
                # Determine priority
                if len(region_signal_types) >= 4 or total_signals >= 20:
                    priority = "critical"
                elif len(region_signal_types) >= 3 or total_signals >= 10:
                    priority = "high"
                else:
                    priority = "medium"

                zones.append(ConvergenceZone(
                    region=region_name,
                    countries=region_countries,
                    signal_types=region_signal_types,
                    total_signals=total_signals,
                    priority=priority,
                    description=f"{len(region_signal_types)} signal types across {len(region_countries)} countries",
                ))

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2}
        zones.sort(key=lambda z: (priority_order.get(z.priority, 3), -z.total_signals))

        return zones

    def generate_ai_context(self) -> str:
        """
        Generate markdown context string for injection into LLM prompts.
        Grounds the AI in real signals, preventing hallucination about current events.
        """
        clusters = self.get_country_clusters()
        zones = self.get_convergence_zones()

        if not clusters and not zones:
            return ""

        lines = ["[GEOGRAPHIC SIGNALS]"]

        # Top 5 countries by cluster score
        top_countries = sorted(
            clusters.values(),
            key=lambda c: c.score,
            reverse=True
        )[:5]

        for cluster in top_countries:
            types_str = ", ".join(sorted(cluster.signal_types))
            lines.append(
                f"- {cluster.country_code}: {len(cluster.signal_types)} signal types "
                f"({types_str}), score: {cluster.score:.0f}, "
                f"{len(cluster.signals)} events"
            )

        # Convergence zones
        if zones:
            lines.append("[CONVERGENCE ZONES]")
            for zone in zones[:3]:
                types_str = " + ".join(sorted(zone.signal_types))
                lines.append(
                    f"- {zone.region}: {types_str} ({zone.priority.upper()} priority, "
                    f"{zone.total_signals} signals)"
                )

        return "\n".join(lines)

    # ============================================================
    # Helpers
    # ============================================================

    # Basic country inference from text (not exhaustive, just common patterns)
    _COUNTRY_PATTERNS = {
        "US": ["united states", "u.s.", "america", "washington", "pentagon", "white house"],
        "CN": ["china", "chinese", "beijing", "prc"],
        "RU": ["russia", "russian", "moscow", "kremlin"],
        "UA": ["ukraine", "ukrainian", "kyiv", "kiev"],
        "IR": ["iran", "iranian", "tehran"],
        "IL": ["israel", "israeli", "tel aviv", "jerusalem", "idf"],
        "TW": ["taiwan", "taiwanese", "taipei"],
        "KP": ["north korea", "pyongyang", "dprk"],
        "KR": ["south korea", "seoul"],
        "JP": ["japan", "japanese", "tokyo"],
        "IN": ["india", "indian", "new delhi", "mumbai"],
        "PK": ["pakistan", "pakistani", "islamabad"],
        "SA": ["saudi", "riyadh"],
        "SY": ["syria", "syrian", "damascus"],
        "IQ": ["iraq", "iraqi", "baghdad"],
        "AF": ["afghanistan", "afghan", "kabul", "taliban"],
        "MM": ["myanmar", "burma"],
        "YE": ["yemen", "yemeni", "houthi"],
        "LY": ["libya", "libyan", "tripoli"],
        "SD": ["sudan", "sudanese", "khartoum"],
        "GB": ["britain", "british", "uk", "london", "england"],
        "FR": ["france", "french", "paris"],
        "DE": ["germany", "german", "berlin"],
    }

    def _infer_country(self, text: str) -> str:
        """Basic country inference from text."""
        lower = text.lower()
        for cc, patterns in self._COUNTRY_PATTERNS.items():
            for pattern in patterns:
                if pattern in lower:
                    return cc
        return ""

    async def get_signals(self) -> list[dict]:
        """
        Return current signals as plain dicts for the intelligence API router.
        Pulls live conflict data if available, falls back to in-memory signals.
        """
        try:
            from app.services.data.conflict_data import ConflictDataService
            svc = ConflictDataService()
            snapshot = await svc.get_conflict_snapshot()
            acled = snapshot.get("acled_events", [])
            if acled:
                self.ingest_conflict_signals(acled)
        except Exception:
            pass

        self._prune_stale()
        return [
            {
                "title": s.title,
                "description": s.description,
                "severity": s.severity,
                "country": s.country_code,
                "source": s.source,
                "signal_type": s.signal_type,
                "timestamp": s.timestamp,
            }
            for s in self.signals
        ]
