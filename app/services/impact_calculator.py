import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ImpactCalculatorService:
    def __init__(self):
        # Propagation factors from Section 8 of spec
        self.TIER1_DIRECT_MODIFIER = 1.0
        self.TIER2_SUPPLIER_MODIFIER = 0.65
        self.TIER3_CUSTOMER_MODIFIER = 0.45

    def calculate_propagation_impact(self, 
                                   sentiment_score: float, 
                                   relationship: Dict[str, Any],
                                   factor_name: str = "") -> float:
        """
        Calculate impact with Historical Precedent Matching (Spec 3.0).
        """
        rel_type = relationship.get("type", "").lower()
        criticality = relationship.get("criticality", "medium").lower()
        
        # 1. Base Multipliers
        criticality_map = {"critical": 1.2, "high": 1.0, "medium": 0.8, "low": 0.5}
        crit_multiplier = criticality_map.get(criticality, 0.8)
        
        tier_multiplier = self.TIER1_DIRECT_MODIFIER
        if rel_type == "supplier": tier_multiplier = self.TIER2_SUPPLIER_MODIFIER
        elif rel_type == "customer": tier_multiplier = self.TIER3_CUSTOMER_MODIFIER
        
        # 2. Historical Precedent Adjustment
        precedent_adjustment = 1.0
        try:
            from app.services.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            # Search for similar historical events by factor_name
            cursor.execute("SELECT impact_magnitude FROM historical_precedents WHERE event_type LIKE ?", (f"%{factor_name}%",))
            precedents = cursor.fetchall()
            conn.close()
            
            if precedents:
                # Average historical impact as a dampening/amplifying factor
                avg_hist = sum(p['impact_magnitude'] for p in precedents) / len(precedents)
                precedent_adjustment = avg_hist / 2.0 # Normalized adjustment
                print(f"Historical Precedent found for {factor_name}: Adjusting impact by {precedent_adjustment:.2f}")
        except:
            pass
            
        return sentiment_score * tier_multiplier * crit_multiplier * precedent_adjustment

    def aggregate_portfolio_impact(self, stock_impacts: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate all stock impacts into a single portfolio impact score."""
        if not stock_impacts:
            return {"impact_usd": 0.0, "impact_pct": 0.0}
            
        # Calculate sum of absolute impacts for severity, and raw sum for direction
        total_pct = sum(s["impact_pct"] for s in stock_impacts)
        avg_pct = total_pct / len(stock_impacts)
        
        # Assuming average portfolio value of $1,000,000 for realistic institutional demo
        portfolio_value = 1000000.0
        impact_usd = (avg_pct / 100.0) * portfolio_value
        
        return {
            "impact_usd": round(impact_usd, 2),
            "impact_pct": round(avg_pct, 2)
        }

impact_calculator_service = ImpactCalculatorService()
