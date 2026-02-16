"""Anthropic LLM provider using the anthropic SDK."""

import logging

from bot_server.config import Settings
from bot_server.providers.base import BaseLLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

TIMEOUT = 30.0


class AnthropicProvider(BaseLLMProvider):
    """LLM provider for Anthropic Claude API."""

    def __init__(self, settings: Settings) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise LLMProviderError(
                "anthropic package not installed. Install with: uv pip install anthropic"
            ) from exc

        self.model = settings.llm_model
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.llm_api_key,
            timeout=TIMEOUT,
        )
        self._anthropic = anthropic

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> str:
        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.content[0].text
        except self._anthropic.APIError as exc:
            raise LLMProviderError(f"Anthropic API error: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False

    async def list_models(self) -> list[str] | None:
        return None
