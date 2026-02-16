"""Tests for GeminiProvider."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot_server.config import Settings
from bot_server.providers.base import LLMProviderError


@pytest.fixture
def settings() -> Settings:
    return Settings(
        webex_bot_token="test-token",
        webex_bot_id="test-bot-id",
        llm_provider="gemini",
        llm_model="gemini-2.0-flash",
        ollama_url="http://localhost:11434",
        llm_api_key="test-gemini-key",
        admin_emails=[],
        log_level="INFO",
        ngrok_authtoken="",
        config_dir="/tmp/config",
    )


@pytest.fixture
def provider(settings):
    """Create a GeminiProvider with a fully mocked genai module."""
    from bot_server.providers.gemini import GeminiProvider

    provider = GeminiProvider(settings)
    # Replace the real genai module with a MagicMock so tests don't hit the API
    provider._genai = MagicMock()
    return provider


@pytest.mark.asyncio
async def test_generate_success(provider):
    """generate() returns the response text from Gemini."""
    mock_response = MagicMock()
    mock_response.text = "Hello from Gemini!"

    mock_chat = MagicMock()
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)

    mock_model = MagicMock()
    mock_model.start_chat.return_value = mock_chat

    provider._genai.GenerativeModel.return_value = mock_model

    result = await provider.generate(
        messages=[{"role": "user", "content": "Hi"}],
        system_prompt="You are helpful.",
        temperature=0.3,
        max_tokens=500,
    )

    assert result == "Hello from Gemini!"
    provider._genai.GenerativeModel.assert_called_once()
    mock_chat.send_message_async.assert_called_once_with("Hi")


@pytest.mark.asyncio
async def test_generate_with_history(provider):
    """generate() passes conversation history correctly."""
    mock_response = MagicMock()
    mock_response.text = "Follow-up answer"

    mock_chat = MagicMock()
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)

    mock_model = MagicMock()
    mock_model.start_chat.return_value = mock_chat

    provider._genai.GenerativeModel.return_value = mock_model

    result = await provider.generate(
        messages=[
            {"role": "user", "content": "What is BGP?"},
            {"role": "assistant", "content": "BGP is..."},
            {"role": "user", "content": "Tell me more"},
        ],
        system_prompt="Expert",
    )

    assert result == "Follow-up answer"
    history = mock_model.start_chat.call_args.kwargs["history"]
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "model"
    mock_chat.send_message_async.assert_called_once_with("Tell me more")


@pytest.mark.asyncio
async def test_generate_api_error(provider):
    """generate() wraps Gemini errors in LLMProviderError."""
    provider._genai.GenerativeModel.side_effect = Exception("API quota exceeded")

    with pytest.raises(LLMProviderError, match="Gemini API error"):
        await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Test",
        )


@pytest.mark.asyncio
async def test_health_check_success(provider):
    """health_check() returns True when list_models succeeds."""
    provider._genai.list_models.return_value = [MagicMock()]

    result = await provider.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(provider):
    """health_check() returns False when list_models fails."""
    provider._genai.list_models.side_effect = Exception("Connection error")

    result = await provider.health_check()
    assert result is False


@pytest.mark.asyncio
async def test_list_models_returns_none(provider):
    """list_models() returns None (not supported)."""
    result = await provider.list_models()
    assert result is None
