"""LLM provider factory and public interface."""

from bot_server.config import Settings
from bot_server.providers.base import BaseLLMProvider, LLMProviderError

__all__ = ["BaseLLMProvider", "LLMProviderError", "get_provider"]


def get_provider(settings: Settings) -> BaseLLMProvider:
    """Create and return the appropriate LLM provider based on settings.

    Args:
        settings: Application settings with provider config

    Returns:
        An initialized provider instance

    Raises:
        ValueError: If llm_provider is not recognized
    """
    provider = settings.llm_provider.lower()

    if provider == "ollama":
        from bot_server.providers.ollama import OllamaProvider

        return OllamaProvider(settings)
    elif provider == "anthropic":
        from bot_server.providers.anthropic import AnthropicProvider

        return AnthropicProvider(settings)
    elif provider == "openai":
        from bot_server.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(settings)
    elif provider == "gemini":
        from bot_server.providers.gemini import GeminiProvider

        return GeminiProvider(settings)
    elif provider == "xai":
        from bot_server.providers.xai import XAIProvider

        return XAIProvider(settings)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
