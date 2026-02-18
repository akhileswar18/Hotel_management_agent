"""
LLM Client — Configurable client for Ollama, Groq, or OpenAI-compatible APIs.

Used by InsightAgent and IntentParser (LLM mode). Timeout and graceful
degradation are critical:
- Default timeout 8s so core flow is never blocked.
- Returns None on timeout/error for degradable behavior.

Supported providers:
- ollama: Local Ollama (default, no API key needed)
- groq: Groq cloud (fast, needs GROQ_API_KEY)
- openai: OpenAI or any compatible endpoint (needs LLM_API_KEY)
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("hms.llm")


class LLMClient:
    """Configurable LLM client — Ollama (local), Groq, or OpenAI (cloud)."""

    # Default models per provider
    DEFAULT_MODELS = {
        "ollama": "llama3.2",
        "groq": "llama-3.3-70b-versatile",
        "openai": "gpt-4o-mini",
    }

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 8.0,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "ollama")).lower()
        default_model = self.DEFAULT_MODELS.get(self.provider, "llama3.2")
        self.model = model or os.environ.get("LLM_MODEL", default_model)
        self.timeout = float(os.environ.get("LLM_TIMEOUT", timeout))

        # API key: check provider-specific env vars first, then generic
        if api_key:
            self.api_key = api_key
        elif self.provider == "groq":
            self.api_key = os.environ.get("GROQ_API_KEY", os.environ.get("LLM_API_KEY", ""))
        else:
            self.api_key = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))

        # Base URL defaults per provider
        if base_url:
            self.base_url = base_url.rstrip("/")
        elif self.provider == "groq":
            self.base_url = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai").rstrip("/")
        elif self.provider == "openai":
            self.base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com").rstrip("/")
        else:
            self.base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434").rstrip("/")

    @property
    def is_available(self) -> bool:
        """Quick check if the LLM is likely reachable (has API key for cloud providers)."""
        if self.provider in ("groq", "openai"):
            return bool(self.api_key)
        return True  # Ollama doesn't need a key

    def query(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Send prompt to LLM, return response text. Returns None on timeout/error."""
        try:
            if self.provider == "ollama":
                return self._query_ollama(prompt, system_prompt)
            if self.provider in ("openai", "groq"):
                return self._query_openai_compatible(prompt, system_prompt)
            logger.warning(f"Unknown LLM provider: {self.provider}")
            return None
        except Exception as e:
            logger.debug(f"LLM query failed ({self.provider}): {e}")
            return None  # Graceful degradation

    def _query_ollama(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Query local Ollama instance."""
        try:
            import httpx
            body = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            if system_prompt:
                body["system"] = system_prompt
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=body,
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip() or None
            logger.debug(f"Ollama returned {response.status_code}")
        except Exception as e:
            logger.debug(f"Ollama query error: {e}")
            return None
        return None

    def _query_openai_compatible(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Query OpenAI-compatible API (OpenAI, Groq, or compatible endpoint)."""
        try:
            import httpx

            # Build the URL — handle various base_url formats
            base = self.base_url
            if "/v1" in base:
                url = f"{base}/chat/completions"
            else:
                url = f"{base}/v1/chat/completions"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            body = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,  # Low temperature for deterministic parsing
                "max_tokens": 1024,
            }

            response = httpx.post(url, json=body, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return content.strip() or None
            else:
                logger.debug(f"{self.provider} returned {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.debug(f"{self.provider} query error: {e}")
            return None
        return None
