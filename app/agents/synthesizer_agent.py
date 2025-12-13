"""
Synthesizer Agent
Combines insights from all agents and generates final recommendations
"""

from typing import Dict, Any, List
import logging
from datetime import datetime
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SynthesizerAgent(BaseAgent):
    """Agent specialized in synthesizing insights and generating recommendations"""

    def __init__(self):
        super().__init__(
            name="Synthesizer Agent",
            description="Insight synthesis and recommendation generation specialist"
        )

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize all agent outputs into final recommendation

        Args:
            input_data: {
                "analysis_result": dict,      # From analyst
                "research_result": dict,      # From researcher
                "calculation_result": dict,   # From calculator
                "article_title": str,
                "article_url": str
            }

        Returns:
            {
                "success": bool,
                "recommendation": str,
                "explanation": str,
                "confidence": float,
                "action_items": list,
                "risk_assessment": str
            }
        """
        try:
            # Validate input
            required = ["analysis_result", "calculation_result", "article_title"]
            if not self.validate_input(input_data, required):
                return {"success": False, "error": "Missing required agent results"}

            self.log_action("Starting synthesis", "Combining insights from all agents")

            analysis = input_data["analysis_result"]
            calculation = input_data["calculation_result"]
            research = input_data.get("research_result", {})

            # Generate recommendation
            recommendation = self._generate_recommendation(
                analysis,
                calculation,
                research
            )

            # Create explanation
            explanation = self._create_explanation(
                analysis,
                calculation,
                research,
                input_data.get("article_title", "")
            )

            # Generate action items
            action_items = self._generate_action_items(
                analysis,
                calculation
            )

            # Assess risk
            risk_assessment = self._assess_risk(
                analysis,
                calculation,
                research
            )

            # Calculate overall confidence
            confidence = self._calculate_confidence(
                analysis,
                calculation
            )

            self.log_action("Synthesis complete", f"Recommendation: {recommendation}")

            return {
                "success": True,
                "recommendation": recommendation,
                "explanation": explanation,
                "confidence": confidence,
                "action_items": action_items,
                "risk_assessment": risk_assessment,
                "agent": self.name
            }

        except Exception as e:
            return self.handle_error(e, "process")

    def _generate_recommendation(
        self,
        analysis: Dict[str, Any],
        calculation: Dict[str, Any],
        research: Dict[str, Any]
    ) -> str:
        """
        Generate action recommendation

        Args:
            analysis: Analyst results
            calculation: Calculator results
            research: Researcher results

        Returns:
            Recommendation string
        """
        try:
            sentiment = analysis.get("sentiment", "neutral")
            impact_pct = calculation.get("portfolio_impact_percent", 0.0)
            severity = calculation.get("severity", "low")

            # Determine recommendation based on sentiment and impact
            if sentiment == "positive":
                if impact_pct > 2.0:
                    return "Strong Buy Signal - Consider increasing positions"
                elif impact_pct > 0.5:
                    return "Buy Signal - Consider accumulating shares"
                else:
                    return "Hold - Monitor for entry opportunity"

            elif sentiment == "negative":
                if impact_pct < -2.0:
                    return "Strong Sell Signal - Consider reducing positions immediately"
                elif impact_pct < -0.5:
                    return "Sell Signal - Consider reducing exposure"
                else:
                    return "Hold - Monitor situation closely"

            else:  # neutral
                if severity == "high":
                    return "Monitor Closely - High volatility expected"
                else:
                    return "Hold - No immediate action required"

        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return "Hold - Further analysis required"

    def _create_explanation(
        self,
        analysis: Dict[str, Any],
        calculation: Dict[str, Any],
        research: Dict[str, Any],
        article_title: str
    ) -> str:
        """
        Create detailed explanation

        Args:
            analysis: Analyst results
            calculation: Calculator results
            research: Researcher results
            article_title: Article title

        Returns:
            Explanation string
        """
        try:
            sentiment = analysis.get("sentiment", "neutral")
            impact_pct = calculation.get("portfolio_impact_percent", 0.0)
            impact_dollar = calculation.get("portfolio_impact_dollar", 0.0)
            key_insights = analysis.get("key_insights", [])

            explanation_parts = []

            # News context
            explanation_parts.append(f"Recent news: {article_title}.")

            # Sentiment analysis
            explanation_parts.append(
                f"Market sentiment is {sentiment} with an estimated portfolio impact of {impact_pct:+.2f}% (${impact_dollar:,.2f})."
            )

            # Key insights
            if key_insights:
                insights_text = " ".join(key_insights)
                explanation_parts.append(f"Key factors: {insights_text}")

            # Historical context
            related_events = research.get("related_events", [])
            if related_events:
                explanation_parts.append(
                    f"This follows {len(related_events)} related event(s) in the past week."
                )

            return " ".join(explanation_parts)

        except Exception as e:
            logger.error(f"Error creating explanation: {e}")
            return "Analysis based on current market conditions and portfolio composition."

    def _generate_action_items(
        self,
        analysis: Dict[str, Any],
        calculation: Dict[str, Any]
    ) -> List[str]:
        """
        Generate actionable items

        Args:
            analysis: Analyst results
            calculation: Calculator results

        Returns:
            List of action items
        """
        try:
            action_items = []

            sentiment = analysis.get("sentiment", "neutral")
            impact_pct = calculation.get("portfolio_impact_percent", 0.0)
            severity = calculation.get("severity", "low")
            affected_holdings = calculation.get("affected_holdings", [])

            # Add monitoring action
            if severity in ["high", "medium"]:
                action_items.append("Monitor affected positions closely")

            # Add position-specific actions
            if sentiment == "negative" and impact_pct < -1.0:
                action_items.append("Review stop-loss orders on affected holdings")
                action_items.append("Consider hedging strategies")

            elif sentiment == "positive" and impact_pct > 1.0:
                action_items.append("Evaluate opportunity to increase positions")
                action_items.append("Check for optimal entry points")

            # Add rebalancing action if needed
            if len(affected_holdings) > 0:
                max_weight = max([h.get("portfolio_weight", 0) for h in affected_holdings])
                if max_weight > 30:
                    action_items.append("Consider rebalancing portfolio to reduce concentration risk")

            # Default action if no specific actions
            if not action_items:
                action_items.append("Continue monitoring market developments")

            return action_items

        except Exception as e:
            logger.error(f"Error generating action items: {e}")
            return ["Monitor situation"]

    def _assess_risk(
        self,
        analysis: Dict[str, Any],
        calculation: Dict[str, Any],
        research: Dict[str, Any]
    ) -> str:
        """
        Assess overall risk level

        Args:
            analysis: Analyst results
            calculation: Calculator results
            research: Researcher results

        Returns:
            Risk assessment string
        """
        try:
            severity = calculation.get("severity", "low")
            confidence = analysis.get("confidence", 0.5)
            affected_holdings = calculation.get("affected_holdings", [])

            # Calculate risk factors
            risk_factors = []

            if severity == "high":
                risk_factors.append("high market impact")

            if confidence < 0.6:
                risk_factors.append("uncertain analysis")

            if len(affected_holdings) > 2:
                risk_factors.append("multiple holdings affected")

            # Price trends
            price_trends = research.get("price_trends", {})
            volatile_stocks = sum(
                1 for trend in price_trends.values()
                if "Strong" in trend
            )
            if volatile_stocks > 1:
                risk_factors.append("high volatility")

            # Construct risk assessment
            if len(risk_factors) >= 3:
                return f"High risk: {', '.join(risk_factors)}"
            elif len(risk_factors) >= 1:
                return f"Moderate risk: {', '.join(risk_factors)}"
            else:
                return "Low risk: stable market conditions"

        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            return "Risk level: undetermined"

    def _calculate_confidence(
        self,
        analysis: Dict[str, Any],
        calculation: Dict[str, Any]
    ) -> float:
        """
        Calculate overall confidence score

        Args:
            analysis: Analyst results
            calculation: Calculator results

        Returns:
            Confidence score (0-1)
        """
        try:
            # Get individual confidences
            analysis_confidence = analysis.get("confidence", 0.5)

            # Adjust based on severity and impact clarity
            impact_pct = abs(calculation.get("portfolio_impact_percent", 0.0))

            # Higher impact = higher confidence (clearer signal)
            impact_factor = min(impact_pct / 5.0, 1.0)  # Cap at 5%

            # Weighted average
            overall_confidence = (analysis_confidence * 0.7) + (impact_factor * 0.3)

            return round(overall_confidence, 2)

        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5


# Create singleton instance
synthesizer_agent = SynthesizerAgent()
