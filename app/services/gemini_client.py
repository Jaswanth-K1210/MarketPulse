"""
Gemini Client Service
Wrapper around Google Generative AI for relationship extraction, cascade inference, and explanations
"""

import google.generativeai as genai
import logging
import json
from typing import Dict, List, Optional, Any
import requests
from app.config import (
    GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE, GEMINI_DAILY_BUDGET,
    OPENROUTER_API_KEY, OPENROUTER_MODEL
)

logger = logging.getLogger(__name__)

# Budget tracking (imports at module level to avoid circular dependency)
def track_gemini_call():
    """Track LLM API call for budget management"""
    try:
        from app.services.news_aggregator import NewsIngestionLayer
        # Ingestion layer tracks budget
        # konceptually it tracks any LLM call
        pass 
    except Exception as e:
        logger.warning(f"Could not track LLM budget: {e}")


class GeminiClient:
    """Client for interacting with Google Gemini API or OpenRouter"""

    def __init__(self):
        """Initialize LLM client"""
        self.use_openrouter = bool(OPENROUTER_API_KEY)
        
        if self.use_openrouter:
            self.api_key = OPENROUTER_API_KEY
            self.model_name = OPENROUTER_MODEL
            self.base_url = "https://openrouter.ai/api/v1"
            logger.info(f"OpenRouter client initialized with model: {self.model_name}")
        else:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
            logger.info(f"Gemini client initialized with model: {GEMINI_MODEL}")

    def generate_content(self, prompt: str, **kwargs) -> Any:
        """Generic content generation wrapper"""
        if self.use_openrouter:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://marketpulse.ai", # Optional
                    "X-Title": "MarketPulse-X" # Optional
                }
                payload = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": kwargs.get("temperature", GEMINI_TEMPERATURE)
                }
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                
                # Create a mock response object to match Gemini's interface (.text)
                class MockResponse:
                    def __init__(self, text):
                        self.text = text
                
                return MockResponse(data['choices'][0]['message']['content'])
            except Exception as e:
                logger.error(f"OpenRouter generate_content error: {e}")
                raise
        else:
            try:
                return self.model.generate_content(prompt, **kwargs)
            except Exception as e:
                logger.error(f"Gemini generate_content error: {e}")
                raise

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Robust JSON parsing with fallback handling
        """
        try:
            # Clean the response
            text = response_text.strip()

            # Extract JSON from markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            # Try to parse
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}. Attempting to fix...")

            # Try to fix common issues
            text = response_text.strip()

            # Remove markdown
            if "```" in text:
                parts = text.split("```")
                for part in parts:
                    if "{" in part and "}" in part:
                        text = part.strip()
                        break

            # Try again
            try:
                return json.loads(text)
            except:
                logger.error(f"Could not parse: {text[:200]}")
                return None

    def extract_relationships(self, article_text: str, article_title: str) -> Optional[Dict]:
        """
        Extract company relationships from article text - OPTIMIZED FOR SHORT CONTENT
        HACKATHON MODE: Tracks Gemini budget usage
        """
        max_retries = 1
        
        for attempt in range(max_retries):
            try:
                # SIMPLIFIED PROMPT for short content
                prompt = f"""Analyze: "{article_title}"
Content: {article_text[:500]}

Find supply chain relationships between these companies: Apple, NVIDIA, AMD, Intel, Broadcom, TSMC, Samsung, MediaTek, ARM, ASML

Return ONLY this JSON (no extra text):
{{
  "relationships": [
    {{"from_company": "CompanyA", "to_company": "CompanyB", "relationship_type": "supplies", "confidence": 0.8, "description": "short desc"}}
  ],
  "event_type": "event_name",
  "summary": "brief summary"
}}

If no relationships found, return: {{"relationships": [], "event_type": "news", "summary": "{article_title}"}}"""

                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,  # Lower for more consistent output
                        max_output_tokens=1500,  # Increased to avoid truncation
                        response_mime_type="application/json"  # Force JSON mode
                    )
                )
                
                # Track Gemini API call for budget management
                track_gemini_call()

                result = self._parse_json_response(response.text)

                if result and isinstance(result.get('relationships'), list):
                    logger.info(f"✓ Extracted {len(result.get('relationships', []))} relationships")
                    return result

                logger.warning(f"Attempt {attempt + 1}: Invalid response structure")

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

            if attempt < max_retries - 1:
                import time
                time.sleep(0.1)  # Brief delay before retry

        # All retries failed - return empty structure
        logger.info("No relationships extracted after retries")
        return {"relationships": [], "event_type": "news", "summary": article_title}

    def infer_cascade(self, event_summary: str, relationships: List[Dict], portfolio_companies: List[str]) -> Optional[Dict]:
        """
        Infer cascade effects on portfolio

        Args:
            event_summary: Summary of the triggering event
            relationships: List of extracted relationships
            portfolio_companies: List of portfolio company names

        Returns:
            Dictionary with cascade chain and affected companies
        """
        try:
            relationships_str = json.dumps(relationships, indent=2)
            portfolio_str = ", ".join(portfolio_companies)

            prompt = f"""
Analyze the CASCADE EFFECT of this supply chain event on the portfolio companies.

EVENT: {event_summary}

RELATIONSHIPS DETECTED:
{relationships_str}

PORTFOLIO COMPANIES: {portfolio_str}

Determine the cascade impact chain in this EXACT JSON format:
{{
  "cascade_chain": [
    {{
      "level": 1,
      "company": "Company name",
      "impact_type": "direct|indirect",
      "description": "What happens at this level"
    }},
    {{
      "level": 2,
      "company": "Company name",
      "impact_type": "indirect",
      "description": "How level 1 affects this company"
    }}
  ],
  "affected_portfolio_companies": ["Company1", "Company2"],
  "severity": "high|medium|low",
  "estimated_impact_percent": -5.5 (negative for losses, positive for gains),
  "reasoning": "Brief explanation of the cascade logic"
}}

IMPORTANT:
- Level 1 = directly affected company
- Level 2+ = downstream impacts
- Only include companies actually affected
- Impact percent should be realistic (-10% to +10%)
- Severity: high (>2%), medium (0.5-2%), low (<0.5%)

Return ONLY valid JSON, no other text.
"""

            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=GEMINI_TEMPERATURE,
                    max_output_tokens=1000
                )
            )

            result_text = response.text.strip()

            # Extract JSON from markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)
            logger.info(f"Inferred cascade affecting {len(result.get('affected_portfolio_companies', []))} companies")
            return result

        except Exception as e:
            logger.error(f"Error inferring cascade: {str(e)}")
            return None

    def generate_explanation(
        self,
        event_summary: str,
        cascade_chain: List[Dict],
        affected_holdings: List[Dict],
        impact_percent: float,
        sources: List[str]
    ) -> str:
        """
        Generate human-readable explanation

        Args:
            event_summary: Event summary
            cascade_chain: Cascade chain data
            affected_holdings: List of affected holdings
            impact_percent: Total portfolio impact percentage
            sources: Source URLs

        Returns:
            Human-readable explanation string
        """
        try:
            cascade_str = json.dumps(cascade_chain, indent=2)
            holdings_str = json.dumps(affected_holdings, indent=2)

            prompt = f"""
Generate a clear, concise explanation for a portfolio manager.

EVENT: {event_summary}

CASCADE CHAIN:
{cascade_str}

AFFECTED HOLDINGS:
{holdings_str}

TOTAL PORTFOLIO IMPACT: {impact_percent}%

Write a 2-3 sentence explanation that:
1. States what happened
2. Explains the supply chain impact
3. Quantifies the portfolio impact
4. Suggests an action

Be specific, professional, and actionable. Use actual company names and numbers.
"""

            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=GEMINI_TEMPERATURE + 0.1,  # Slightly higher for natural language
                    max_output_tokens=300
                )
            )

            explanation = response.text.strip()
            logger.info("Generated explanation successfully")
            return explanation

        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return f"Supply chain event detected with {impact_percent}% estimated portfolio impact. Review recommended."

    def detect_direct_impact(
        self,
        article_text: str,
        article_title: str,
        portfolio_companies: List[str]
    ) -> Optional[Dict]:
        """
        Detect direct impact on portfolio companies - OPTIMIZED FOR SHORT CONTENT
        """
        max_retries = 2

        for attempt in range(max_retries):
            try:
                companies_str = ", ".join(portfolio_companies)

                # ULTRA-SIMPLIFIED PROMPT for short summaries
                prompt = f"""News: "{article_title}"
Details: {article_text[:400]}

Does this impact {companies_str}?

Return ONLY this JSON:
{{
  "has_direct_impact": true,
  "affected_companies": ["Apple"],
  "impact_type": "positive",
  "event_category": "earnings",
  "estimated_impact_percent": 2.0,
  "reasoning": "Earnings beat estimates",
  "summary": "Good news"
}}

Rules:
- has_direct_impact: true if significant news about a portfolio company
- impact_type: positive/negative/neutral
- estimated_impact_percent: -5 to +5
- If no impact: {{"has_direct_impact": false, "affected_companies": [], "impact_type": "neutral", "event_category": "news", "estimated_impact_percent": 0, "reasoning": "No portfolio impact", "summary": "{article_title}"}}"""

                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=1500,
                        response_mime_type="application/json"
                    )
                )

                result = self._parse_json_response(response.text)

                if result and 'has_direct_impact' in result:
                    if result.get('has_direct_impact'):
                        logger.info(f"✓ Direct impact: {result.get('impact_type')} on {result.get('affected_companies')}")
                    else:
                        logger.info("No direct impact")
                    return result

                logger.warning(f"Attempt {attempt + 1}: Invalid response structure")

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

            if attempt < max_retries - 1:
                import time
                time.sleep(0.5)

        # Fallback: return no impact
        logger.info("Returning no impact after retries")
        return {
            "has_direct_impact": False,
            "affected_companies": [],
            "impact_type": "neutral",
            "event_category": "news",
            "estimated_impact_percent": 0.0,
            "reasoning": "Could not determine impact from summary",
            "summary": article_title
        }

    def answer_agent_question(
        self,
        context: str,
        question: str,
        tool_results: Dict = None
    ) -> str:
        """
        Answer agent question using context and tool results

        Args:
            context: Background context
            question: User's question
            tool_results: Results from agent tools

        Returns:
            Answer string
        """
        try:
            tools_str = json.dumps(tool_results, indent=2) if tool_results else "No tool data available"

            prompt = f"""
You are a financial analysis AI assistant for a portfolio manager.

CONTEXT: {context}

QUESTION: {question}

TOOL RESULTS:
{tools_str}

Provide a clear, data-driven answer that:
1. Directly answers the question
2. Uses specific numbers and facts from tool results
3. Cites evidence
4. Suggests next steps if applicable

Be concise (2-4 sentences) and professional.
"""

            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=GEMINI_TEMPERATURE + 0.2,
                    max_output_tokens=500
                )
            )

            answer = response.text.strip()
            logger.info("Generated agent answer successfully")
            return answer

        except Exception as e:
            logger.error(f"Error answering agent question: {str(e)}")
            return "I encountered an error processing your question. Please try rephrasing it."


# Create singleton instance
gemini_client = GeminiClient()
