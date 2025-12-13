"""
Analyst Agent
Performs market analysis and sentiment analysis on news articles
"""

from typing import Dict, Any
import logging
from app.agents.base_agent import BaseAgent
from app.services.gemini_client import gemini_client

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """Agent specialized in market analysis and sentiment detection"""

    def __init__(self):
        super().__init__(
            name="Analyst Agent",
            description="Market analysis and sentiment detection specialist"
        )

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze news article for market sentiment and implications

        Args:
            input_data: {
                "article_title": str,
                "article_content": str,
                "companies_mentioned": list
            }

        Returns:
            {
                "success": bool,
                "sentiment": str,  # positive/negative/neutral
                "sentiment_score": float,  # -1 to +1
                "key_insights": list,
                "market_implications": str,
                "confidence": float
            }
        """
        try:
            # Validate input
            required = ["article_title", "article_content", "companies_mentioned"]
            if not self.validate_input(input_data, required):
                return {"success": False, "error": "Missing required fields"}

            self.log_action("Starting market analysis", f"Companies: {input_data['companies_mentioned']}")

            # Analyze sentiment using Gemini
            analysis = self._analyze_sentiment(
                input_data["article_title"],
                input_data["article_content"],
                input_data["companies_mentioned"]
            )

            if not analysis:
                return {"success": False, "error": "Sentiment analysis failed"}

            self.log_action("Analysis complete", f"Sentiment: {analysis.get('sentiment', 'unknown')}")

            return {
                "success": True,
                "sentiment": analysis.get("sentiment", "neutral"),
                "sentiment_score": analysis.get("sentiment_score", 0.0),
                "key_insights": analysis.get("key_insights", []),
                "market_implications": analysis.get("market_implications", ""),
                "confidence": analysis.get("confidence", 0.5),
                "agent": self.name
            }

        except Exception as e:
            return self.handle_error(e, "process")

    def _analyze_sentiment(self, title: str, content: str, companies: list) -> Dict[str, Any]:
        """
        Perform sentiment analysis using Gemini

        Args:
            title: Article title
            content: Article content
            companies: Companies mentioned

        Returns:
            Analysis results
        """
        try:
            # Use Gemini to analyze sentiment
            prompt = f"""Analyze this news for market sentiment:

Title: {title}
Content: {content[:500]}
Companies: {', '.join(companies)}

Return JSON:
{{
  "sentiment": "positive/negative/neutral",
  "sentiment_score": 0.5,
  "key_insights": ["insight 1", "insight 2"],
  "market_implications": "Brief analysis",
  "confidence": 0.8
}}

Rules:
- sentiment_score: -1 (very negative) to +1 (very positive)
- key_insights: 2-3 bullet points
- confidence: 0 to 1"""

            import google.generativeai as genai

            response = gemini_client.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                    response_mime_type="application/json"
                )
            )

            result = gemini_client._parse_json_response(response.text)

            if result:
                return result

            # Fallback
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "key_insights": ["Analysis unavailable"],
                "market_implications": "Unable to determine market impact",
                "confidence": 0.3
            }

        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return None


# Create singleton instance
analyst_agent = AnalystAgent()
