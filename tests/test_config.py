"""Tests for bot_server.config module."""

import json
import os
from pathlib import Path

import pytest

from bot_server.config import get_settings, setup_logging


def test_get_settings_valid(mock_env):
    """All required env vars set, settings loads correctly."""
    settings = get_settings()
    assert settings.webex_bot_token == "test-token-abc123"
    assert settings.webex_bot_id == "test-bot-id"
    assert settings.llm_provider == "ollama"
    assert settings.llm_model == "llama3.1:8b"
    assert settings.ollama_url == "http://localhost:11434"
    assert settings.ngrok_authtoken == "test-ngrok-token"


def test_get_settings_missing_token(mock_env, monkeypatch):
    """Missing WEBEX_BOT_TOKEN raises ValueError."""
    monkeypatch.delenv("WEBEX_BOT_TOKEN")
    with pytest.raises(ValueError, match="WEBEX_BOT_TOKEN"):
        get_settings()


def test_get_settings_missing_provider(mock_env, monkeypatch):
    """Missing LLM_PROVIDER raises ValueError."""
    monkeypatch.delenv("LLM_PROVIDER")
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        get_settings()


def test_get_settings_missing_model(mock_env, monkeypatch):
    """Missing LLM_MODEL raises ValueError."""
    monkeypatch.delenv("LLM_MODEL")
    with pytest.raises(ValueError, match="LLM_MODEL"):
        get_settings()


def test_get_settings_defaults(monkeypatch):
    """Optional fields get correct defaults when not set."""
    monkeypatch.setenv("WEBEX_BOT_TOKEN", "tok")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    # Clear optional vars to test defaults
    for key in [
        "WEBEX_BOT_ID",
        "OLLAMA_URL",
        "LLM_API_KEY",
        "ADMIN_EMAILS",
        "LOG_LEVEL",
        "NGROK_AUTHTOKEN",
    ]:
        monkeypatch.delenv(key, raising=False)

    settings = get_settings()
    assert settings.webex_bot_id == ""
    assert settings.ollama_url == "http://localhost:11434"
    assert settings.llm_api_key == ""
    assert settings.admin_emails == []
    assert settings.log_level == "INFO"
    assert settings.ngrok_authtoken == ""


def test_admin_emails_parsing(mock_env):
    """Comma-separated ADMIN_EMAILS string parses to list correctly."""
    settings = get_settings()
    assert settings.admin_emails == ["admin@example.com", "admin2@example.com"]


def test_admin_emails_single(monkeypatch):
    """Single admin email parses correctly."""
    monkeypatch.setenv("WEBEX_BOT_TOKEN", "tok")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.setenv("ADMIN_EMAILS", "solo@example.com")
    settings = get_settings()
    assert settings.admin_emails == ["solo@example.com"]


def test_setup_logging_creates_log_dir(settings, tmp_path, monkeypatch):
    """Logging setup creates logs/ directory."""
    monkeypatch.chdir(tmp_path)
    setup_logging(settings)
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "logs" / "bot_server.log").exists()


def test_json_config_files_valid():
    """All JSON files in bot_server/config/ parse without errors."""
    config_path = Path(__file__).parent.parent / "bot_server" / "config"
    json_files = list(config_path.glob("*.json"))
    assert len(json_files) >= 3, f"Expected at least 3 JSON files, found {len(json_files)}"

    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
        assert isinstance(data, dict), f"{json_file.name} should contain a JSON object"


def test_config_dir_is_absolute(settings):
    """config_dir should be an absolute path."""
    assert os.path.isabs(settings.config_dir)


def test_config_dir_points_to_config(settings):
    """config_dir should point to the bot_server/config/ directory."""
    assert settings.config_dir.endswith(os.path.join("bot_server", "config"))
