"""Google Gemini LLM provider using the google-generativeai SDK."""

import logging

from bot_server.config import Settings
from bot_server.providers.base import BaseLLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

TIMEOUT = 30.0


class GeminiProvider(BaseLLMProvider):
    """LLM provider for Google Gemini API."""

    def __init__(self, settings: Settings) -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise LLMProviderError(
                "google-generativeai package not installed. "
                "Install with: uv pip install google-generativeai"
            ) from exc

        self.model_name = settings.llm_model
        self._genai = genai
        self._genai.configure(api_key=settings.llm_api_key)

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> str:
        try:
            model = self._genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt,
                generation_config=self._genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            # Convert messages to Gemini content format
            history = []
            for msg in messages[:-1]:
                role = "model" if msg["role"] == "assistant" else "user"
                history.append({"role": role, "parts": [msg["content"]]})

            chat = model.start_chat(history=history)
            last_message = messages[-1]["content"] if messages else ""
            response = await chat.send_message_async(last_message)
            return response.text
        except Exception as exc:
            if isinstance(exc, LLMProviderError):
                raise
            raise LLMProviderError(f"Gemini API error: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            list(self._genai.list_models())
            return True
        except Exception:
            return False

    async def list_models(self) -> list[str] | None:
        return None
