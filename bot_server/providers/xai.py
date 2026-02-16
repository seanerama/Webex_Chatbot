"""xAI LLM provider using the openai SDK with custom base URL."""

import logging

from bot_server.config import Settings
from bot_server.providers.base import BaseLLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

TIMEOUT = 30.0
XAI_BASE_URL = "https://api.x.ai/v1"


class XAIProvider(BaseLLMProvider):
    """LLM provider for xAI (OpenAI-compatible API)."""

    def __init__(self, settings: Settings) -> None:
        try:
            import openai
        except ImportError as exc:
            raise LLMProviderError(
                "openai package not installed. Install with: uv pip install openai"
            ) from exc

        self.model = settings.llm_model
        self.client = openai.AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=XAI_BASE_URL,
            timeout=TIMEOUT,
        )
        self._openai = openai

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> str:
        full_messages = [{"role": "system", "content": system_prompt}, *messages]
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except self._openai.APIError as exc:
            raise LLMProviderError(f"xAI API error: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    async def list_models(self) -> list[str] | None:
        return None
