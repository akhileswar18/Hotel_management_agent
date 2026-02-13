"""
LLM Client — Configurable client for Ollama (local) or OpenAI-compatible APIs.

Used only by InsightAgent. Timeout and graceful degradation are critical:
- Default timeout 5s so core flow is never blocked.
- Returns None on timeout/error for degradable behavior.
"""

import os
from typing import Optional


class LLMClient:
    """Configurable LLM client — Ollama (local) or OpenAI (cloud)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 5.0,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "ollama")).lower()
        self.model = model or os.environ.get("LLM_MODEL", "llama3.2")
        self.timeout = float(os.environ.get("LLM_TIMEOUT", timeout))
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434")).rstrip("/")

    def query(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Send prompt to LLM, return response text. Returns None on timeout/error."""
        try:
            if self.provider == "ollama":
                return self._query_ollama(prompt, system_prompt)
            if self.provider == "openai":
                return self._query_openai(prompt, system_prompt)
            return None
        except Exception:
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
        except Exception:
            return None
        return None

    def _query_openai(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Query OpenAI-compatible API (OpenAI or compatible endpoint)."""
        try:
            import httpx
            url = f"{self.base_url}/v1/chat/completions" if "/v1" not in self.base_url else f"{self.base_url}/chat/completions"
            if not url.startswith("http"):
                url = f"https://{self.base_url}/v1/chat/completions"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            response = httpx.post(
                url,
                json={"model": self.model, "messages": messages},
                headers=headers,
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return content.strip() or None
        except Exception:
            return None
        return None
