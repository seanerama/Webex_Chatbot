"""Tests for the get_provider() factory function."""

import pytest

from bot_server.config import Settings
from bot_server.providers import get_provider
from bot_server.providers.ollama import OllamaProvider


def _make_settings(**overrides) -> Settings:
    """Create a Settings instance with defaults, applying overrides."""
    defaults = {
        "webex_bot_token": "test-token",
        "webex_bot_id": "test-bot-id",
        "llm_provider": "ollama",
        "llm_model": "llama3.1:8b",
        "ollama_url": "http://localhost:11434",
        "llm_api_key": "test-key",
        "admin_emails": [],
        "log_level": "INFO",
        "ngrok_authtoken": "",
        "config_dir": "/tmp/config",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_get_provider_ollama():
    """get_provider returns OllamaProvider for 'ollama'."""
    settings = _make_settings(llm_provider="ollama")
    provider = get_provider(settings)
    assert isinstance(provider, OllamaProvider)


def test_get_provider_anthropic():
    """get_provider returns AnthropicProvider for 'anthropic'."""
    settings = _make_settings(llm_provider="anthropic")
    provider = get_provider(settings)
    from bot_server.providers.anthropic import AnthropicProvider

    assert isinstance(provider, AnthropicProvider)


def test_get_provider_openai():
    """get_provider returns OpenAIProvider for 'openai'."""
    settings = _make_settings(llm_provider="openai")
    provider = get_provider(settings)
    from bot_server.providers.openai_provider import OpenAIProvider

    assert isinstance(provider, OpenAIProvider)


def test_get_provider_gemini():
    """get_provider returns GeminiProvider for 'gemini'."""
    settings = _make_settings(llm_provider="gemini")
    provider = get_provider(settings)
    from bot_server.providers.gemini import GeminiProvider

    assert isinstance(provider, GeminiProvider)


def test_get_provider_xai():
    """get_provider returns XAIProvider for 'xai'."""
    settings = _make_settings(llm_provider="xai")
    provider = get_provider(settings)
    from bot_server.providers.xai import XAIProvider

    assert isinstance(provider, XAIProvider)


def test_get_provider_case_insensitive():
    """get_provider handles case-insensitive provider names."""
    settings = _make_settings(llm_provider="Ollama")
    provider = get_provider(settings)
    assert isinstance(provider, OllamaProvider)


def test_get_provider_unknown_raises_value_error():
    """get_provider raises ValueError for unknown provider."""
    settings = _make_settings(llm_provider="unknown-provider")
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_provider(settings)
