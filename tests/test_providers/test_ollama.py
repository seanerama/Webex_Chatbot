"""Tests for OllamaProvider."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bot_server.config import Settings
from bot_server.providers.base import LLMProviderError
from bot_server.providers.ollama import OllamaProvider


@pytest.fixture
def settings() -> Settings:
    return Settings(
        webex_bot_token="test-token",
        webex_bot_id="test-bot-id",
        llm_provider="ollama",
        llm_model="llama3.1:8b",
        ollama_url="http://localhost:11434",
        llm_api_key="",
        admin_emails=[],
        log_level="INFO",
        ngrok_authtoken="",
        config_dir="/tmp/config",
    )


@pytest.fixture
def provider(settings) -> OllamaProvider:
    return OllamaProvider(settings)


@pytest.mark.asyncio
async def test_generate_success(provider):
    """generate() returns the LLM response text."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"message": {"content": "Hello, world!"}}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_server.providers.ollama.httpx.AsyncClient", return_value=mock_client):
        result = await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="You are helpful.",
        )

    assert result == "Hello, world!"
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["model"] == "llama3.1:8b"
    assert payload["messages"][0] == {"role": "system", "content": "You are helpful."}
    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0.2


@pytest.mark.asyncio
async def test_generate_connection_error(provider):
    """generate() wraps connection errors in LLMProviderError."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_server.providers.ollama.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(LLMProviderError, match="Ollama connection failed"):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="Test",
            )


@pytest.mark.asyncio
async def test_generate_timeout_error(provider):
    """generate() wraps timeout errors in LLMProviderError."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ReadTimeout("Read timed out")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_server.providers.ollama.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(LLMProviderError, match="Ollama connection failed"):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="Test",
            )


@pytest.mark.asyncio
async def test_generate_http_error(provider):
    """generate() wraps HTTP status errors in LLMProviderError."""
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    response = httpx.Response(500, request=request)

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error", request=request, response=response
    )
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_server.providers.ollama.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(LLMProviderError, match="Ollama API error"):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="Test",
            )


@pytest.mark.asyncio
async def test_health_check_success(provider):
    """health_check() returns True when Ollama is reachable."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_server.providers.ollama.httpx.AsyncClient", return_value=mock_client):
        result = await provider.health_check()

    assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(provider):
    """health_check() returns False when Ollama is unreachable."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_server.providers.ollama.httpx.AsyncClient", return_value=mock_client):
        result = await provider.health_check()

    assert result is False


@pytest.mark.asyncio
async def test_list_models_success(provider):
    """list_models() returns list of model names."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "llama3.1:8b", "size": 1000},
            {"name": "mistral:7b", "size": 2000},
        ]
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_server.providers.ollama.httpx.AsyncClient", return_value=mock_client):
        result = await provider.list_models()

    assert result == ["llama3.1:8b", "mistral:7b"]


@pytest.mark.asyncio
async def test_list_models_connection_error(provider):
    """list_models() wraps connection errors in LLMProviderError."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_server.providers.ollama.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(LLMProviderError, match="Ollama connection failed"):
            await provider.list_models()


@pytest.mark.asyncio
async def test_ollama_url_trailing_slash(settings):
    """OllamaProvider strips trailing slash from URL."""
    settings.ollama_url = "http://localhost:11434/"
    provider = OllamaProvider(settings)
    assert provider.base_url == "http://localhost:11434"
