"""Ollama LLM provider using httpx for HTTP calls."""

import logging

import httpx

from bot_server.config import Settings
from bot_server.providers.base import BaseLLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

TIMEOUT = 30.0


class OllamaProvider(BaseLLMProvider):
    """LLM provider for Ollama local inference."""

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.ollama_url.rstrip("/")
        self.model = settings.llm_model

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> str:
        full_messages = [{"role": "system", "content": system_prompt}, *messages]
        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise LLMProviderError(f"Ollama connection failed: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(f"Ollama API error: {exc.response.status_code}") from exc
        except (KeyError, TypeError) as exc:
            raise LLMProviderError(f"Unexpected Ollama response format: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str] | None:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise LLMProviderError(f"Ollama connection failed: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(f"Ollama API error: {exc.response.status_code}") from exc
