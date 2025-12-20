import logging
import json
import re
from typing import Dict, Any, List
from app.models.factors import MarketFactor, FACTOR_METADATA
from app.services.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class ClassificationService:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    def classify_article(self, title: str, content: str) -> Dict[str, Any]:
        """Classify article using high-intelligence Gemini LLM (Spec 3.0)."""
        prompt = f"""
        Analyze the following news article and classify it into EXACTLY ONE of these 10 market factors.
        Provide a sentiment score from -1.0 (extremely negative/disruptive) to +1.0 (extremely positive/growth).
        
        Factors & Definitions:
        {json.dumps({k.name: v["name"] for k, v in FACTOR_METADATA.items()}, indent=2)}
        
        Article Title: {title}
        Article Content Summary: {content[:1500]}
        
        RETURN ONLY A VALID JSON OBJECT:
        {{
            "factor_name": "Exact Factor Name",
            "sentiment": "positive|negative|neutral",
            "sentiment_score": float,
            "reasoning": "Detailed 1-2 sentence explanation of the impact and factor choice",
            "confidence": 0.0-1.0,
            "affected_sectors": ["sector1", "sector2"]
        }}
        """
        
        try:
            response = self.gemini_client.generate_content(prompt)
            raw_text = response.text.strip()
            
            # Clean JSON from markdown if necessary
            json_text = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.MULTILINE)
            result = json.loads(json_text)
            
            # Map name back to type
            factor_type = MarketFactor.MARKET_SENTIMENT.value # Default
            for k, v in FACTOR_METADATA.items():
                if v["name"].lower() == result.get("factor_name", "").lower():
                    factor_type = k.value
                    break
            
            return {
                "factor_type": factor_type,
                "factor_name": result.get("factor_name"),
                "sentiment": result.get("sentiment"),
                "sentiment_score": result.get("sentiment_score", 0.0),
                "reasoning": result.get("reasoning", "LLM Analysis Complete"),
                "confidence": result.get("confidence", 0.85),
                "affected_sectors": result.get("affected_sectors", [])
            }
        except Exception as e:
            logger.error(f"Gemini Classification Failed: {e}. Falling back to heuristic.")
            # Heuristic Fallback
            text = f"{title} {content}".lower()
            potential_factors = [k for k, v in FACTOR_METADATA.items() if any(kw.lower() in text for kw in v["keywords"])]
            primary_factor = potential_factors[0] if potential_factors else MarketFactor.MARKET_SENTIMENT
            
            sentiment = "negative" if any(x in text for x in ["halt", "shutdown", "shortage", "crash"]) else "positive" if "growth" in text else "neutral"
            return {
                "factor_type": primary_factor.value,
                "factor_name": FACTOR_METADATA[primary_factor]["name"],
                "sentiment": sentiment,
                "sentiment_score": -0.7 if sentiment == "negative" else 0.5 if sentiment == "positive" else 0.0,
                "reasoning": f"Heuristic fallback (Gemini error): {primary_factor.name}",
                "confidence": 0.5,
                "affected_sectors": []
            }

classification_service = ClassificationService(GeminiClient())
