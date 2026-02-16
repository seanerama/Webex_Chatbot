"""Tests for AnthropicProvider."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot_server.config import Settings
from bot_server.providers.base import LLMProviderError


@pytest.fixture
def settings() -> Settings:
    return Settings(
        webex_bot_token="test-token",
        webex_bot_id="test-bot-id",
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-5-20250929",
        ollama_url="http://localhost:11434",
        llm_api_key="test-anthropic-key",
        admin_emails=[],
        log_level="INFO",
        ngrok_authtoken="",
        config_dir="/tmp/config",
    )


@pytest.fixture
def provider(settings):
    from bot_server.providers.anthropic import AnthropicProvider

    return AnthropicProvider(settings)


@pytest.mark.asyncio
async def test_generate_success(provider):
    """generate() returns the response text from Anthropic."""
    mock_text_block = MagicMock()
    mock_text_block.text = "Hello from Claude!"

    mock_response = MagicMock()
    mock_response.content = [mock_text_block]

    provider.client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.generate(
        messages=[{"role": "user", "content": "Hi"}],
        system_prompt="You are helpful.",
        temperature=0.3,
        max_tokens=500,
    )

    assert result == "Hello from Claude!"
    provider.client.messages.create.assert_called_once_with(
        model="claude-sonnet-4-5-20250929",
        system="You are helpful.",
        messages=[{"role": "user", "content": "Hi"}],
        temperature=0.3,
        max_tokens=500,
    )


@pytest.mark.asyncio
async def test_generate_api_error(provider):
    """generate() wraps Anthropic API errors in LLMProviderError."""
    import anthropic

    provider.client.messages.create = AsyncMock(
        side_effect=anthropic.APIError(
            message="Bad request",
            request=MagicMock(),
            body=None,
        )
    )

    with pytest.raises(LLMProviderError, match="Anthropic API error"):
        await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Test",
        )


@pytest.mark.asyncio
async def test_health_check_success(provider):
    """health_check() returns True on successful API call."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="ok")]
    provider.client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(provider):
    """health_check() returns False when API call fails."""
    provider.client.messages.create = AsyncMock(side_effect=Exception("Connection error"))

    result = await provider.health_check()
    assert result is False


def test_list_models_returns_none(provider):
    """list_models() returns None (not supported)."""
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(provider.list_models())
    assert result is None
