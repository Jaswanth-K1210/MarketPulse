"""
Impact Calculator — uses LightGBM risk_scorer instead of hardcoded multipliers.
Falls back to rule-based multipliers if ML scorer unavailable.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _get_risk_scorer():
    try:
        from app.ml.risk_scorer import risk_scorer
        return risk_scorer
    except Exception:
        return None


class ImpactCalculatorService:
    TIER1_DIRECT_MODIFIER = 1.0
    TIER2_SUPPLIER_MODIFIER = 0.65
    TIER3_CUSTOMER_MODIFIER = 0.45

    def calculate_propagation_impact(
        self,
        sentiment_score: float,
        relationship: Dict[str, Any],
        factor_name: str = "",
        article_meta: Dict[str, Any] = None,
    ) -> float:
        """
        Calculate impact using risk_scorer (LightGBM) when available,
        else fall back to hardcoded tier multipliers.
        """
        scorer = _get_risk_scorer()
        if scorer is not None and article_meta:
            try:
                result = scorer.score(article_meta, relationship, factor_name)
                risk = result["risk_score"]
                # Convert risk [0,1] → signed impact via sentiment direction
                direction = 1.0 if sentiment_score >= 0 else -1.0
                return direction * risk
            except Exception as e:
                logger.warning("risk_scorer failed, using rule fallback: %s", e)

        # Rule-based fallback
        rel_type = relationship.get("type", "").lower()
        criticality = relationship.get("criticality", "medium").lower()
        criticality_map = {"critical": 1.2, "high": 1.0, "medium": 0.8, "low": 0.5}
        crit_mult = criticality_map.get(criticality, 0.8)

        if rel_type == "supplier":
            tier_mult = self.TIER2_SUPPLIER_MODIFIER
        elif rel_type == "customer":
            tier_mult = self.TIER3_CUSTOMER_MODIFIER
        else:
            tier_mult = self.TIER1_DIRECT_MODIFIER

        precedent_adjustment = 1.0
        try:
            from app.services.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT impact_magnitude FROM historical_precedents WHERE event_type LIKE ?",
                (f"%{factor_name}%",),
            )
            precedents = cursor.fetchall()
            conn.close()
            if precedents:
                avg_hist = sum(p["impact_magnitude"] for p in precedents) / len(precedents)
                precedent_adjustment = avg_hist / 2.0
        except Exception as e:
            logger.warning("Historical precedent lookup failed: %s", e)

        return sentiment_score * tier_mult * crit_mult * precedent_adjustment

    def aggregate_portfolio_impact(self, stock_impacts: List[Dict[str, Any]]) -> Dict[str, float]:
        if not stock_impacts:
            return {"impact_usd": 0.0, "impact_pct": 0.0}
        total_pct = sum(s["impact_pct"] for s in stock_impacts)
        avg_pct = total_pct / len(stock_impacts)
        portfolio_value = 1_000_000.0
        return {
            "impact_usd": round((avg_pct / 100.0) * portfolio_value, 2),
            "impact_pct": round(avg_pct, 2),
        }


impact_calculator_service = ImpactCalculatorService()
