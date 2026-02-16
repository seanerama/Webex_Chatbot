"""Abstract base class for LLM providers and shared exception."""

from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    """Raised when an LLM provider call fails."""


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> str:
        """Send messages to the LLM and return the response text.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts
            system_prompt: The system message for the conversation
            temperature: Creativity dial (0.0-1.0)
            max_tokens: Maximum response length

        Returns:
            The LLM's response as a string

        Raises:
            LLMProviderError: On connection failure, timeout, or API error
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is reachable and responding.

        Returns:
            True if healthy, False otherwise
        """
        ...

    @abstractmethod
    async def list_models(self) -> list[str] | None:
        """List available models. Only meaningful for Ollama.

        Returns:
            List of model name strings, or None if not supported by this provider
        """
        ...
