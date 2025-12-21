"""
Gemini Client Service
Wrapper around Google Generative AI for relationship extraction, cascade inference, and explanations
WITH ROBUST RATE LIMITING, QUEUING, AND EXPONENTIAL BACKOFF
"""

import google.generativeai as genai
import logging
import json
import time
import math
from typing import Dict, List, Optional, Any
import requests
from app.config import (
    GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE,
    OPENROUTER_API_KEYS
)

logger = logging.getLogger(__name__)

# Budget tracking
def track_gemini_call():
    """Track LLM API call for budget management"""
    try:
        pass 
    except Exception as e:
        logger.warning(f"Could not track LLM budget: {e}")

class GeminiClient:
    """Client for interacting with OpenRouter/Gemini with robust queuing and rate limits"""

    def __init__(self):
        """Initialize LLM client with automatic fallback"""
        self.openrouter_api_keys = OPENROUTER_API_KEYS
        self.current_key_index = 0
        self.use_openrouter = bool(self.openrouter_api_keys)
        self.has_gemini = bool(GEMINI_API_KEY)
        self.openrouter_available = self.use_openrouter
        
        # Priority list of models on OpenRouter (Optimized for Speed & Reliability)
        self.openrouter_models = [
            "google/gemini-2.0-flash-exp:free",      # Primary (Fastest)
            "mistralai/mistral-7b-instruct:free",    # Requested Robust Fallback
            "meta-llama/llama-3.2-3b-instruct:free", # Backup Speed
            "google/gemini-flash-1.5",               # Standard Flash
            "google/gemini-flash-1.5-8b",
        ]
        self.current_model_index = 0
        
        # Rate Limiting Configuration
        self.request_timestamps = []
        self.requests_per_minute = 30  # Conservative limit
        self.max_retries = 3
        self.retry_delay = 2.0  # Seconds
        self.backoff_multiplier = 2.0
        
        if self.use_openrouter:
            self.api_key = self.openrouter_api_keys[0]
            self.base_url = "https://openrouter.ai/api/v1"
            logger.info(f"OpenRouter client initialized with {len(self.openrouter_api_keys)} API key(s). Active model: {self.openrouter_models[0]}")
        
        if self.has_gemini:
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(GEMINI_MODEL) 
            logger.info(f"Gemini fallback initialized with model: {GEMINI_MODEL}")

    def _get_current_key(self):
        """Get current API key"""
        if not self.openrouter_api_keys:
            return None
        return self.openrouter_api_keys[self.current_key_index]

    def _rotate_api_key(self):
        """Rotate to next API key"""
        if len(self.openrouter_api_keys) <= 1:
            return
        prev_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.openrouter_api_keys)
        self.api_key = self.openrouter_api_keys[self.current_key_index]
        logger.warning(f"🔑 Rotating API key from #{prev_index + 1} to #{self.current_key_index + 1}")

    def _get_current_model(self):
        return self.openrouter_models[self.current_model_index]

    def _rotate_model(self):
        """Switch to next available model"""
        prev_model = self._get_current_model()
        self.current_model_index = (self.current_model_index + 1) % len(self.openrouter_models)
        new_model = self._get_current_model()
        logger.warning(f"🔄 Switching model from {prev_model} to {new_model}")

    def _enforce_rate_limit(self):
        """Enforce requests per minute limit"""
        now = time.time()
        # Clean old timestamps (older than 60s)
        self.request_timestamps = [t for t in self.request_timestamps if t > now - 60]
        
        if len(self.request_timestamps) >= self.requests_per_minute:
            oldest_request = self.request_timestamps[0]
            wait_time = (oldest_request + 60) - now
            if wait_time > 0:
                logger.warning(f"⏳ Rate limit approaching. Queueing request for {wait_time:.2f}s...")
                time.sleep(wait_time)
            # Recursive check/cleanup after sleep
            self._enforce_rate_limit()
        else:
            self.request_timestamps.append(now)

    def _send_openrouter_request_with_backoff(self, payload: Dict, retry_count=0) -> Optional[requests.Response]:
        """Send request with exponential backoff for 429s"""
        self._enforce_rate_limit()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://marketpulse.ai",
            "X-Title": "MarketPulse-X"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    # Exponential Backoff
                    wait_time = self.retry_delay * math.pow(self.backoff_multiplier, retry_count)
                    logger.warning(f"⚠️ 429 Rate Limited. Retrying in {wait_time:.1f}s (Attempt {retry_count + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    return self._send_openrouter_request_with_backoff(payload, retry_count + 1)
                else:
                    logger.error(f"❌ Rate limit exceeded after {self.max_retries} retries.")
                    # Try rotating to next API key if available
                    if len(self.openrouter_api_keys) > 1:
                        self._rotate_api_key()
                        # Retry with new key (reset retry count)
                        return self._send_openrouter_request_with_backoff(payload, retry_count=0)
                    return response # Return failing response to trigger model rotation

            if response.status_code in [404, 401, 500, 502, 503]:
                # Instant rotation for these errors
                return response
                
            return response
            
        except Exception as e:
            logger.error(f"Network error in OpenRouter request: {e}")
            if retry_count < self.max_retries:
                time.sleep(2)
                return self._send_openrouter_request_with_backoff(payload, retry_count + 1)
            return None

    def generate_content(self, prompt: str, generation_config=None, **kwargs) -> Any:
        """Content generation with intelligent fallback queue"""
        
        # 1. Try OpenRouter First (if enabled)
        if self.use_openrouter and self.openrouter_available:
            # Try rotating through models if one fails
            attempts_per_call = 3 
            for _ in range(attempts_per_call):
                current_model = self._get_current_model()
                
                # Align config
                temperature = kwargs.get("temperature", GEMINI_TEMPERATURE)
                max_tokens = 2000
                if generation_config:
                    if hasattr(generation_config, 'temperature'): temperature = generation_config.temperature
                    if hasattr(generation_config, 'max_output_tokens'): max_tokens = generation_config.max_output_tokens

                payload = {
                    "model": current_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                # Attempt with Backoff
                response = self._send_openrouter_request_with_backoff(payload)

                if response and response.status_code == 200:
                    try:
                        # Mock a response object compatible with genai
                        class MockResponse:
                            def __init__(self, text): self.text = text
                        
                        data = response.json()
                        content = data['choices'][0]['message']['content']
                        track_gemini_call()
                        return MockResponse(content)
                    except Exception as parse_error:
                        logger.error(f"Failed to parse OpenRouter response: {parse_error}")
                        # Fall through to rotate
                
                # If we get here, it failed. Log and Rotate.
                code = response.status_code if response else "Error"
                logger.warning(f"⚠️ OpenRouter error {code} on {current_model}. Rotating...")
                self._rotate_model()

            logger.warning("⚠️ All OpenRouter models failed for this request. Falling back to Gemini API...")
        
        # 2. Fallback to Direct Gemini API
        if self.has_gemini:
            try:
                logger.info("🔄 Using Gemini API Fallback")
                return self.gemini_model.generate_content(
                    prompt, 
                    generation_config=generation_config
                )
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                # Don't crash, just return None or raise
                return None
        
        return None

    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Clean and parse JSON from LLM response"""
        try:
            # Strip Markdown code blocks
            clean_text = text.replace("```json", "").replace("```", "").strip()
            # Find first { and last }
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1:
                clean_text = clean_text[start:end+1]
            return json.loads(clean_text)
        except Exception:
            return None

    def _heuristic_extraction(self, article_text: str, article_title: str) -> Dict:
        """Fallback: Extract relationships using simplistic keyword matching"""
        logger.info("⚠️ Using Heuristic Fallback for Extraction (AI Limit Reached)")
        
        tech_map = {
            "TSMC": ["Apple", "NVIDIA", "AMD"],
            "Apple": ["Foxconn", "TSMC"],
            "NVIDIA": ["TSMC", "Samsung"],
            "AMD": ["TSMC"],
            "Samsung": ["NVIDIA", "Apple"]
        }
        
        relationships = []
        text_lower = (article_title + " " + article_text).lower()
        
        for key_company, partners in tech_map.items():
            if key_company.lower() in text_lower:
                for partner in partners:
                    if partner.lower() in text_lower:
                        relationships.append({
                            "from_company": key_company,
                            "to_company": partner,
                            "relationship_type": "partnership/supply",
                            "confidence": 0.7,
                            "description": f"Heuristic detected mention of {key_company} and {partner}"
                        })
        
        if not relationships:
            if "apple" in text_lower:
                 relationships.append({"from_company": "Market", "to_company": "Apple", "relationship_type": "market_sentiment", "confidence": 0.6, "description": "Direct market impact"})
            elif "nvidia" in text_lower:
                 relationships.append({"from_company": "Market", "to_company": "NVIDIA", "relationship_type": "market_sentiment", "confidence": 0.6, "description": "Direct market impact"})

        return {
            "relationships": relationships,
            "event_type": "market_news_heuristic",
            "summary": article_title
        }

    def extract_relationships(self, article_text: str, article_title: str) -> Optional[Dict]:
        """Extract company relationships with robust retry logic"""
        
        prompt = f"""Analyze this news for Supply Chain Disruptions.
Title: "{article_title}"
Content: {article_text[:800]}

Identify relationships between: Apple, NVIDIA, AMD, Intel, Broadcom, TSMC, Samsung, MediaTek, ARM, ASML.

Return JSON format:
{{
  "relationships": [
    {{"from_company": "Name", "to_company": "Name", "relationship_type": "supply_chain", "confidence": 0.9, "description": "details"}}
  ],
  "event_type": "disruption_or_news",
  "summary": "brief summary"
}}

If no specific supply chain relationship is found, leave 'relationships' empty array [].
"""
        
        response = self.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1500,
                response_mime_type="application/json"
            )
        )
        
        if response and response.text:
            result = self._parse_json_response(response.text)
            if result and isinstance(result.get('relationships'), list):
                count = len(result.get('relationships', []))
                if count > 0:
                    logger.info(f"✓ Extracted {count} relationships")
                return result

        # FINAL FALLBACK
        return self._heuristic_extraction(article_text, article_title)

    def _dummy_cascade(self, portfolio_companies: List[str]) -> Dict:
        return {
          "cascade_chain": [],
          "affected_portfolio_companies": [portfolio_companies[0]] if portfolio_companies else [],
          "severity": "low",
          "estimated_impact_percent": 0.1,
          "reasoning": "Heuristic fallback: AI unavailable."
        }

    def infer_cascade(self, event_summary: str, relationships: List[Dict], portfolio_companies: List[str]) -> Optional[Dict]:
        """Infer cascade effects on portfolio"""
        try:
            relationships_str = json.dumps(relationships, indent=2)
            portfolio_str = ", ".join(portfolio_companies)

            prompt = f"""
Analyze CASCADE EFFECT.

EVENT: {event_summary}
RELATIONSHIPS: {relationships_str}
PORTFOLIO: {portfolio_str}

Return JSON:
{{
  "cascade_chain": [
    {{ "level": 1, "company": "Name", "impact_type": "direct", "description": "desc" }}
  ],
  "affected_portfolio_companies": ["Co1"],
  "severity": "medium",
  "estimated_impact_percent": -2.5,
  "reasoning": "reason"
}}
"""
            response = self.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=GEMINI_TEMPERATURE, max_output_tokens=1000)
            )
            
            if response and response.text:
                result = self._parse_json_response(response.text)
                if result:
                    logger.info(f"Inferred cascade affecting {len(result.get('affected_portfolio_companies', []))} companies")
                return result
            return self._dummy_cascade(portfolio_companies)
            
        except Exception as e:
            logger.error(f"Error inferring cascade: {str(e)}")
            return self._dummy_cascade(portfolio_companies)

    def generate_explanation(self, event_summary: str, cascade_chain: List[Dict], affected_holdings: List[Dict], impact_percent: float, sources: List[str]) -> str:
        """Generate human-readable explanation"""
        prompt = f"""Explain this supply chain impact to a user.
Event: {event_summary}
Impact: {impact_percent}%
Holdings: {[h['ticker'] for h in affected_holdings]}

Keep it brief (2 sentences)."""
        
        res = self.generate_content(prompt)
        return res.text if res else "Impact calculated based on supply chain dependencies."


    def detect_direct_impact(self, article_text: str, article_title: str, portfolio_holdings: List[str]) -> Optional[Dict]:
        """Detect direct impact on portfolio"""
        portfolio_str = ", ".join(portfolio_holdings)
        prompt = f"""Analyze DIRECT impact on: {portfolio_str}
Title: {article_title}
Content: {article_text[:500]}
Return JSON: {{"has_direct_impact": true/false, "affected_companies": ["TICKER"], "impact_type": "positive/negative/neutral", "severity": "low/medium/high", "reasoning": "brief"}}"""
        response = self.generate_content(prompt)
        if response and response.text:
            result = self._parse_json_response(response.text)
            if result and result.get('has_direct_impact'):
                logger.info(f"✓ Detected direct impact on {len(result.get('affected_companies', []))} companies")
            return result
        return {"has_direct_impact": False}

# Singleton instance
gemini_client = GeminiClient()

# Import usage tracker at the top
from app.services.usage_tracker import usage_tracker

# Override generate_content to add tracking
_original_generate = GeminiClient.generate_content

def _tracked_generate(self, prompt: str, generation_config=None, **kwargs):
    """Wrapped generate_content with usage tracking"""
    response = _original_generate(self, prompt, generation_config, **kwargs)
    
    # Log usage if successful
    if response and hasattr(response, 'text'):
        input_chars = len(prompt)
        output_chars = len(response.text) if response.text else 0
        usage_tracker.log_request("gemini-2.5-flash", input_chars, output_chars)
    
    return response

# Monkey patch
GeminiClient.generate_content = _tracked_generate
