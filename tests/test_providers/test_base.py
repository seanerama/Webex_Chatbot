"""Tests for BaseLLMProvider ABC and LLMProviderError."""

import pytest

from bot_server.providers.base import BaseLLMProvider, LLMProviderError


def test_cannot_instantiate_base_provider():
    """BaseLLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseLLMProvider()


def test_llm_provider_error_is_exception():
    """LLMProviderError is a proper Exception subclass."""
    error = LLMProviderError("test error")
    assert isinstance(error, Exception)
    assert str(error) == "test error"


def test_llm_provider_error_can_be_raised_and_caught():
    """LLMProviderError can be raised and caught."""
    with pytest.raises(LLMProviderError, match="something went wrong"):
        raise LLMProviderError("something went wrong")


def test_subclass_must_implement_all_methods():
    """A subclass that doesn't implement all abstract methods can't be instantiated."""

    class IncompleteProvider(BaseLLMProvider):
        async def generate(self, messages, system_prompt, temperature=0.2, max_tokens=1000):
            return ""

    with pytest.raises(TypeError):
        IncompleteProvider()
