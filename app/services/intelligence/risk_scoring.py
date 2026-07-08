"""
Deterministic Risk Scoring Engine — Country Instability Index (CII).
Ported from WorldMonitor's get-risk-scores.ts.

Produces the same score every time for the same inputs. No LLM randomness.
Fully explainable — each component visible in the response.

CII = baseline(40%) + events(60%) + signal_boosts
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RiskScore:
    """Risk score with full component breakdown."""
    country_code: str
    country_name: str = ""
    score: float = 0.0
    components: dict = field(default_factory=dict)
    war_floor_applied: bool = False
    conflict_floor_applied: bool = False
    active_conflicts: list = field(default_factory=list)
    top_events: list = field(default_factory=list)


class RiskScoringEngine:
    """
    Country Instability Index (CII) — deterministic, explainable, no LLM needed.

    Formula:
        CII = baseline(40%) + events(60%) + climate_boost + cyber_boost + fire_boost
        events = normalize(sum(event_count_by_type × weight) × country_multiplier)
        War floor: if UCDP intensity == 2, CII >= 70
        Minor conflict floor: if UCDP intensity == 1, CII >= 50
    """

    # Baseline risk per country (historical/structural instability)
    COUNTRY_BASELINES = {
        # Active conflict zones
        "SY": 85, "YE": 80, "SO": 75, "AF": 80, "IQ": 65,
        "UA": 70, "SD": 70, "SS": 75, "LY": 60, "MM": 65,
        # High tension regions
        "ML": 55, "BF": 55, "NE": 50, "CD": 60, "CF": 60,
        "MZ": 45, "ET": 50, "NG": 45, "KE": 35, "CM": 40,
        "PK": 45, "LB": 55, "PS": 65, "HT": 55,
        # Moderate tension
        "IR": 50, "KP": 55, "VE": 40, "TH": 30, "PH": 30,
        "IN": 25, "EG": 35, "TN": 30, "DZ": 30,
        "RU": 35, "CN": 25, "TW": 25, "IL": 40,
        "TR": 30, "MX": 35, "CO": 35, "BR": 25,
        # Stable nations
        "US": 15, "GB": 12, "JP": 10, "DE": 12, "FR": 15,
        "CA": 10, "AU": 10, "NZ": 8, "SE": 8, "NO": 8,
        "FI": 8, "DK": 8, "NL": 10, "CH": 6, "SG": 8,
        "KR": 15, "IT": 12, "ES": 12, "PT": 10, "PL": 12,
        "IE": 8, "AT": 8, "BE": 10, "CZ": 10,
    }

    # ACLED event type weights
    EVENT_WEIGHTS = {
        "battles": 3.0,
        "explosions_remote_violence": 2.5,
        "violence_against_civilians": 2.5,
        "riots": 2.0,
        "protests": 1.0,
        "strategic_developments": 0.5,
    }

    # Country-specific sensitivity multipliers
    COUNTRY_MULTIPLIERS = {
        "KP": 3.0, "IR": 2.5, "CN": 2.5, "RU": 2.0,
        "TW": 2.0, "IL": 2.0, "PK": 1.5, "IN": 1.3,
        "US": 1.5, "SA": 1.5, "UA": 1.5,
    }

    # Country name mapping
    COUNTRY_NAMES = {
        "US": "United States", "GB": "United Kingdom", "FR": "France",
        "DE": "Germany", "JP": "Japan", "CN": "China", "RU": "Russia",
        "UA": "Ukraine", "IR": "Iran", "IL": "Israel", "TW": "Taiwan",
        "KP": "North Korea", "KR": "South Korea", "IN": "India",
        "PK": "Pakistan", "SA": "Saudi Arabia", "IQ": "Iraq",
        "SY": "Syria", "YE": "Yemen", "AF": "Afghanistan", "SD": "Sudan",
        "SS": "South Sudan", "SO": "Somalia", "LY": "Libya", "MM": "Myanmar",
        "ET": "Ethiopia", "NG": "Nigeria", "ML": "Mali", "BF": "Burkina Faso",
        "CD": "DR Congo", "CF": "Central African Republic", "MZ": "Mozambique",
        "LB": "Lebanon", "PS": "Palestine", "HT": "Haiti", "VE": "Venezuela",
        "MX": "Mexico", "CO": "Colombia", "BR": "Brazil", "TR": "Turkey",
        "EG": "Egypt", "TH": "Thailand", "PH": "Philippines",
    }

    def calculate_cii(
        self,
        country_code: str,
        acled_events: list[dict],
        ucdp_conflicts: list[dict],
        climate_severity: float = 0,
        cyber_count: int = 0,
        fire_detections: int = 0,
        market_volatility: float = 0,
    ) -> RiskScore:
        """
        Calculate Country Instability Index.

        Args:
            country_code: ISO 2-letter country code
            acled_events: ACLED events for this country (pre-filtered)
            ucdp_conflicts: UCDP conflicts for this country
            climate_severity: Climate anomaly severity (0-10)
            cyber_count: Number of cyber incidents
            fire_detections: Number of active fire detections
            market_volatility: Market volatility indicator (0-100)

        Returns:
            RiskScore with full component breakdown
        """
        baseline = self.COUNTRY_BASELINES.get(country_code, 30)
        multiplier = self.COUNTRY_MULTIPLIERS.get(country_code, 1.0)

        # Calculate event score from ACLED data
        event_score = 0
        event_breakdown = {}
        for event in acled_events:
            etype = event.get("event_type", "")
            weight = self.EVENT_WEIGHTS.get(etype, 1.0)
            event_score += weight
            event_breakdown[etype] = event_breakdown.get(etype, 0) + 1

        # Apply country multiplier and normalize to 0-100
        event_score = min(event_score * multiplier, 100)

        # Composite CII
        cii = (baseline * 0.4) + (event_score * 0.6)

        # Signal boosts (capped)
        climate_boost = min(climate_severity * 5, 10)
        cyber_boost = min(cyber_count * 3, 10)
        fire_boost = min(fire_detections * 0.5, 5)
        market_boost = min(market_volatility * 0.1, 5)

        cii += climate_boost + cyber_boost + fire_boost + market_boost

        # War floor enforcement
        war_floor = False
        conflict_floor = False
        active_conflicts = []

        for conflict in ucdp_conflicts:
            cc = conflict.get("country_code", "")
            if cc == country_code or cc[:2] == country_code:
                intensity = conflict.get("intensity_level", 0)
                active_conflicts.append(conflict.get("conflict_name", "Unknown"))
                if intensity >= 2:
                    cii = max(cii, 70)
                    war_floor = True
                elif intensity >= 1:
                    cii = max(cii, 50)
                    conflict_floor = True

        # Clamp to 0-100
        cii = max(0, min(100, cii))

        # Top events for explanation
        top_events = sorted(
            event_breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return RiskScore(
            country_code=country_code,
            country_name=self.COUNTRY_NAMES.get(country_code, country_code),
            score=round(cii, 1),
            components={
                "baseline": baseline,
                "baseline_weighted": round(baseline * 0.4, 1),
                "event_score": round(event_score, 1),
                "event_score_weighted": round(event_score * 0.6, 1),
                "country_multiplier": multiplier,
                "climate_boost": round(climate_boost, 1),
                "cyber_boost": round(cyber_boost, 1),
                "fire_boost": round(fire_boost, 1),
                "market_boost": round(market_boost, 1),
                "total_events": len(acled_events),
                "event_breakdown": dict(top_events),
            },
            war_floor_applied=war_floor,
            conflict_floor_applied=conflict_floor,
            active_conflicts=active_conflicts,
            top_events=[{"type": t, "count": c} for t, c in top_events],
        )

    def calculate_batch(
        self,
        acled_by_country: dict,
        ucdp_conflicts: list[dict],
        country_codes: Optional[list[str]] = None,
        **kwargs,
    ) -> dict[str, RiskScore]:
        """
        Calculate CII for multiple countries.

        Args:
            acled_by_country: Dict of country_code -> aggregated event data
            ucdp_conflicts: List of all UCDP conflicts
            country_codes: Optional list of specific countries to score

        Returns:
            Dict of country_code -> RiskScore
        """
        # If no specific countries requested, score all with data + all baseline countries
        if country_codes is None:
            country_codes = list(
                set(acled_by_country.keys()) | set(self.COUNTRY_BASELINES.keys())
            )

        results = {}
        for cc in country_codes:
            # Get ACLED events for this country
            country_data = acled_by_country.get(cc, {})

            # Build flat event list from aggregated data
            acled_events = []
            for etype in self.EVENT_WEIGHTS:
                count = country_data.get(etype, 0)
                for _ in range(count):
                    acled_events.append({"event_type": etype, "country_code": cc})

            results[cc] = self.calculate_cii(
                country_code=cc,
                acled_events=acled_events,
                ucdp_conflicts=ucdp_conflicts,
                **kwargs,
            )

        return results

    def get_risk_summary(self, scores: dict[str, RiskScore]) -> dict:
        """Generate a summary of risk scores for API response."""
        sorted_scores = sorted(
            scores.values(),
            key=lambda s: s.score,
            reverse=True
        )

        critical = [s for s in sorted_scores if s.score >= 80]
        high = [s for s in sorted_scores if 60 <= s.score < 80]
        elevated = [s for s in sorted_scores if 40 <= s.score < 60]
        normal = [s for s in sorted_scores if s.score < 40]

        return {
            "total_countries": len(scores),
            "critical_count": len(critical),
            "high_count": len(high),
            "elevated_count": len(elevated),
            "normal_count": len(normal),
            "top_risk": [
                {
                    "country_code": s.country_code,
                    "country_name": s.country_name,
                    "score": s.score,
                    "war_floor": s.war_floor_applied,
                    "top_events": s.top_events[:3],
                }
                for s in sorted_scores[:10]
            ],
            "scores": {
                s.country_code: {
                    "score": s.score,
                    "name": s.country_name,
                    "components": s.components,
                }
                for s in sorted_scores
            },
        }
