"""
Calculator Agent
Quantifies portfolio impact and calculates financial metrics
"""

from typing import Dict, Any, List
import logging
from app.agents.base_agent import BaseAgent
from app.services.portfolio import portfolio_service
from app.config import SEVERITY_THRESHOLDS

logger = logging.getLogger(__name__)


class CalculatorAgent(BaseAgent):
    """Agent specialized in portfolio impact calculation"""

    def __init__(self):
        super().__init__(
            name="Calculator Agent",
            description="Portfolio impact quantification specialist"
        )

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate portfolio impact from analysis

        Args:
            input_data: {
                "affected_companies": list,
                "sentiment_score": float,
                "estimated_impact_percent": float (optional)
            }

        Returns:
            {
                "success": bool,
                "portfolio_impact_percent": float,
                "portfolio_impact_dollar": float,
                "affected_holdings": list,
                "severity": str,
                "total_portfolio_value": float
            }
        """
        try:
            # Validate input
            required = ["affected_companies", "sentiment_score"]
            if not self.validate_input(input_data, required):
                return {"success": False, "error": "Missing required fields"}

            companies = input_data["affected_companies"]
            sentiment_score = input_data["sentiment_score"]
            estimated_impact = input_data.get("estimated_impact_percent", None)

            self.log_action("Calculating impact", f"Companies: {companies}, Sentiment: {sentiment_score}")

            # Calculate impact
            impact_result = self._calculate_portfolio_impact(
                companies,
                sentiment_score,
                estimated_impact
            )

            if not impact_result:
                return {"success": False, "error": "Impact calculation failed"}

            # Determine severity
            severity = self._determine_severity(impact_result["portfolio_impact_percent"])

            self.log_action(
                "Calculation complete",
                f"Impact: {impact_result['portfolio_impact_percent']:+.2f}%, Severity: {severity}"
            )

            return {
                "success": True,
                "portfolio_impact_percent": impact_result["portfolio_impact_percent"],
                "portfolio_impact_dollar": impact_result["portfolio_impact_dollar"],
                "affected_holdings": impact_result["affected_holdings"],
                "severity": severity,
                "total_portfolio_value": impact_result["total_portfolio_value"],
                "agent": self.name
            }

        except Exception as e:
            return self.handle_error(e, "process")

    def _calculate_portfolio_impact(
        self,
        companies: List[str],
        sentiment_score: float,
        estimated_impact: float = None
    ) -> Dict[str, Any]:
        """
        Calculate portfolio impact from sentiment

        Args:
            companies: Affected companies
            sentiment_score: Sentiment score (-1 to +1)
            estimated_impact: Pre-estimated impact percent (optional)

        Returns:
            Impact calculation results
        """
        try:
            portfolio = portfolio_service.get_portfolio()
            total_value = portfolio["total_value"]

            affected_holdings = []
            total_impact_dollar = 0.0

            for company in companies:
                # Get holding info
                holding = portfolio_service.get_holding(company)

                if holding:
                    # Calculate impact for this holding
                    if estimated_impact is not None:
                        # Use provided estimate
                        impact_pct = estimated_impact
                    else:
                        # Estimate from sentiment
                        # Sentiment score of -1 to +1 maps to ~-5% to +5% impact
                        impact_pct = sentiment_score * 5.0

                    # Calculate dollar impact for this holding
                    holding_value = holding["quantity"] * holding["current_price"]
                    impact_dollar = (impact_pct / 100.0) * holding_value

                    # Portfolio weight
                    portfolio_weight = holding_value / total_value

                    # Contribution to total portfolio impact
                    portfolio_impact_pct = impact_pct * portfolio_weight

                    affected_holdings.append({
                        "company": company,
                        "ticker": holding["ticker"],
                        "quantity": holding["quantity"],
                        "current_price": holding["current_price"],
                        "holding_value": holding_value,
                        "impact_percent": impact_pct,
                        "impact_dollar": impact_dollar,
                        "portfolio_weight": portfolio_weight * 100  # As percentage
                    })

                    total_impact_dollar += impact_dollar

            # Calculate total portfolio impact percent
            portfolio_impact_percent = (total_impact_dollar / total_value) * 100 if total_value > 0 else 0.0

            return {
                "portfolio_impact_percent": portfolio_impact_percent,
                "portfolio_impact_dollar": total_impact_dollar,
                "affected_holdings": affected_holdings,
                "total_portfolio_value": total_value
            }

        except Exception as e:
            logger.error(f"Error calculating portfolio impact: {e}")
            return None

    def _determine_severity(self, impact_percent: float) -> str:
        """
        Determine alert severity from impact

        Args:
            impact_percent: Portfolio impact percentage

        Returns:
            Severity level
        """
        abs_impact = abs(impact_percent)

        if abs_impact >= SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif abs_impact >= SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    def calculate_risk_metrics(self, holdings: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate additional risk metrics

        Args:
            holdings: List of affected holdings

        Returns:
            Risk metrics
        """
        try:
            if not holdings:
                return {}

            # Calculate concentration risk
            weights = [h["portfolio_weight"] for h in holdings]
            max_concentration = max(weights) if weights else 0.0

            # Calculate total exposure
            total_exposure = sum(weights)

            # Calculate diversification score (simplified)
            diversification = 1.0 - (max_concentration / 100.0) if total_exposure > 0 else 0.0

            return {
                "max_concentration": max_concentration,
                "total_exposure": total_exposure,
                "diversification_score": diversification
            }

        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {}


# Create singleton instance
calculator_agent = CalculatorAgent()
