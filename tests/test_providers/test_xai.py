"""Tests for XAIProvider."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot_server.config import Settings
from bot_server.providers.base import LLMProviderError
from bot_server.providers.xai import XAI_BASE_URL


@pytest.fixture
def settings() -> Settings:
    return Settings(
        webex_bot_token="test-token",
        webex_bot_id="test-bot-id",
        llm_provider="xai",
        llm_model="grok-2",
        ollama_url="http://localhost:11434",
        llm_api_key="test-xai-key",
        admin_emails=[],
        log_level="INFO",
        ngrok_authtoken="",
        config_dir="/tmp/config",
    )


@pytest.fixture
def provider(settings):
    from bot_server.providers.xai import XAIProvider

    return XAIProvider(settings)


def test_xai_uses_custom_base_url(provider):
    """XAIProvider uses the xAI base URL."""
    assert str(provider.client.base_url).rstrip("/") == XAI_BASE_URL


@pytest.mark.asyncio
async def test_generate_success(provider):
    """generate() returns the response text from xAI."""
    mock_message = MagicMock()
    mock_message.content = "Hello from Grok!"

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.generate(
        messages=[{"role": "user", "content": "Hi"}],
        system_prompt="You are helpful.",
        temperature=0.3,
        max_tokens=500,
    )

    assert result == "Hello from Grok!"
    call_kwargs = provider.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "grok-2"
    assert call_kwargs["messages"][0] == {"role": "system", "content": "You are helpful."}


@pytest.mark.asyncio
async def test_generate_api_error(provider):
    """generate() wraps xAI API errors in LLMProviderError."""
    import openai

    provider.client.chat.completions.create = AsyncMock(
        side_effect=openai.APIError(
            message="Bad request",
            request=MagicMock(),
            body=None,
        )
    )

    with pytest.raises(LLMProviderError, match="xAI API error"):
        await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Test",
        )


@pytest.mark.asyncio
async def test_health_check_success(provider):
    """health_check() returns True when models.list() succeeds."""
    provider.client.models.list = AsyncMock(return_value=MagicMock())

    result = await provider.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(provider):
    """health_check() returns False when models.list() fails."""
    provider.client.models.list = AsyncMock(side_effect=Exception("Connection error"))

    result = await provider.health_check()
    assert result is False


@pytest.mark.asyncio
async def test_list_models_returns_none(provider):
    """list_models() returns None (not supported)."""
    result = await provider.list_models()
    assert result is None
