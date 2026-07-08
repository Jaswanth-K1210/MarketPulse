"""
LLMRouter — 4-tier LLM fallback chain
Priority: Groq (free, fast) → OpenRouter free models → Gemini Flash → Ollama (local dev)

Never call any LLM API directly from an agent. Always go through this router.
It handles rate limits, fallbacks, and logging automatically.
"""
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODE = os.getenv("LLM_MODE", "auto")  # auto | groq | openrouter | gemini | ollama


class LLMRouter:
    """
    Routes LLM calls through a priority fallback chain.

    Tiers:
        fast     → Groq llama-3.1-8b-instant   (classify, match — high volume, low complexity)
        strong   → Groq llama-3.3-70b-versatile (monitor, validate, synthesize — complex reasoning)
        discovery→ OpenRouter deepseek-v3-free   (supplier inference, relationship discovery)
        synthesis→ OpenRouter gemini-2.0-flash   (narrative generation, alert writing)
    """

    def __init__(self):
        self._groq_fast = None
        self._groq_strong = None
        self._openrouter_deepseek = None
        self._openrouter_gemini = None
        self._gemini = None
        self._ollama = None
        self._init_clients()

    def _init_clients(self):
        """Lazy-initialise only the clients whose keys are present."""
        if GROQ_API_KEY:
            try:
                from langchain_groq import ChatGroq
                self._groq_fast = ChatGroq(
                    model="llama-3.1-8b-instant",
                    temperature=0,
                    api_key=GROQ_API_KEY,
                )
                self._groq_strong = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.1,
                    api_key=GROQ_API_KEY,
                )
                logger.info("LLMRouter: Groq clients ready")
            except ImportError:
                logger.warning("langchain-groq not installed — Groq tier unavailable")

        if OPENROUTER_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                self._openrouter_deepseek = ChatOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_API_KEY,
                    model="deepseek/deepseek-chat-v3-0324:free",
                    temperature=0.1,
                )
                self._openrouter_gemini = ChatOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_API_KEY,
                    model="google/gemini-2.0-flash-exp:free",
                    temperature=0.1,
                )
                logger.info("LLMRouter: OpenRouter clients ready")
            except ImportError:
                logger.warning("langchain-openai not installed — OpenRouter tier unavailable")

        if GEMINI_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._gemini = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=GEMINI_API_KEY,
                    temperature=0.1,
                )
                logger.info("LLMRouter: Gemini fallback ready")
            except ImportError:
                logger.warning("langchain-google-genai not installed — Gemini tier unavailable")

        try:
            from langchain_ollama import OllamaLLM
            self._ollama = OllamaLLM(
                model=os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
                base_url=OLLAMA_BASE_URL,
            )
            logger.info("LLMRouter: Ollama local dev client ready")
        except ImportError:
            logger.debug("langchain-ollama not installed — Ollama offline dev unavailable")

    def _invoke(self, client, prompt: str) -> str:
        """Invoke a langchain client and return string content."""
        response = client.invoke(prompt)
        if hasattr(response, "content"):
            return response.content
        return str(response)

    def call(self, tier: str, prompt: str, retries: int = 1) -> str:
        """
        Call the LLM for the given tier with automatic fallback.

        Args:
            tier: 'fast' | 'strong' | 'discovery' | 'synthesis'
            prompt: The full prompt string.
            retries: Number of retry attempts before falling back to next tier.

        Returns:
            LLM response as a string.

        Raises:
            RuntimeError if all tiers fail.
        """
        if LLM_MODE != "auto":
            return self._call_forced_mode(prompt)

        chain = self._build_chain(tier)
        last_error = None

        for client_name, client in chain:
            if client is None:
                continue
            for attempt in range(retries + 1):
                try:
                    result = self._invoke(client, prompt)
                    if attempt > 0 or client_name != chain[0][0]:
                        logger.info("LLMRouter: Used %s for tier '%s'", client_name, tier)
                    return result
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    if "rate_limit" in err_str or "429" in err_str:
                        wait = 2 ** attempt
                        logger.warning("Rate limit on %s, waiting %ds: %s", client_name, wait, e)
                        time.sleep(wait)
                    else:
                        logger.warning("LLMRouter: %s failed for tier '%s': %s", client_name, tier, e)
                        break  # Non-rate-limit error — skip to next tier immediately

        raise RuntimeError(f"All LLM tiers failed for tier='{tier}'. Last error: {last_error}")

    def _build_chain(self, tier: str) -> list:
        """Return ordered list of (name, client) for the given tier."""
        if tier == "fast":
            return [
                ("groq-fast", self._groq_fast),
                ("groq-strong", self._groq_strong),
                ("openrouter-gemini", self._openrouter_gemini),
                ("gemini", self._gemini),
                ("ollama", self._ollama),
            ]
        if tier == "strong":
            return [
                ("groq-strong", self._groq_strong),
                ("openrouter-deepseek", self._openrouter_deepseek),
                ("gemini", self._gemini),
                ("ollama", self._ollama),
            ]
        if tier == "discovery":
            return [
                ("openrouter-deepseek", self._openrouter_deepseek),
                ("groq-strong", self._groq_strong),
                ("gemini", self._gemini),
                ("ollama", self._ollama),
            ]
        if tier == "synthesis":
            return [
                ("openrouter-gemini", self._openrouter_gemini),
                ("groq-strong", self._groq_strong),
                ("gemini", self._gemini),
                ("ollama", self._ollama),
            ]
        # Default fallback
        return [
            ("groq-fast", self._groq_fast),
            ("gemini", self._gemini),
            ("ollama", self._ollama),
        ]

    def _call_forced_mode(self, prompt: str) -> str:
        """When LLM_MODE is set, bypass tier logic and use specified provider."""
        client_map = {
            "groq": self._groq_strong,
            "openrouter": self._openrouter_deepseek,
            "gemini": self._gemini,
            "ollama": self._ollama,
        }
        client = client_map.get(LLM_MODE)
        if client is None:
            raise RuntimeError(f"LLM_MODE='{LLM_MODE}' but that client is not available")
        return self._invoke(client, prompt)

    def health(self) -> dict:
        """Return which tiers are available — used by /api/health endpoint."""
        return {
            "groq_fast": self._groq_fast is not None,
            "groq_strong": self._groq_strong is not None,
            "openrouter_deepseek": self._openrouter_deepseek is not None,
            "openrouter_gemini": self._openrouter_gemini is not None,
            "gemini": self._gemini is not None,
            "ollama": self._ollama is not None,
            "mode": LLM_MODE,
        }


# Singleton — imported by all agents
llm_router = LLMRouter()
