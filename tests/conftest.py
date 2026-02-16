"""Shared test fixtures for Webex AI Chatbot tests."""

import json
import os
import shutil
import tempfile

import pytest

from bot_server.config import Settings, get_settings


@pytest.fixture
def mock_env(monkeypatch):
    """Set a complete valid environment for get_settings()."""
    env_vars = {
        "WEBEX_BOT_TOKEN": "test-token-abc123",
        "WEBEX_BOT_ID": "test-bot-id",
        "LLM_PROVIDER": "ollama",
        "LLM_MODEL": "llama3.1:8b",
        "OLLAMA_URL": "http://localhost:11434",
        "LLM_API_KEY": "",
        "ADMIN_EMAILS": "admin@example.com, admin2@example.com",
        "LOG_LEVEL": "INFO",
        "NGROK_AUTHTOKEN": "test-ngrok-token",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def settings(mock_env) -> Settings:
    """Return a valid Settings instance using mock environment."""
    return get_settings()


@pytest.fixture
def config_dir():
    """Provide a temp directory with JSON config files for testing."""
    tmpdir = tempfile.mkdtemp()

    personalities = {
        "default": {
            "name": "Test Assistant",
            "system_prompt": "You are a test assistant.",
            "temperature": 0.2,
            "max_tokens": 1000,
        }
    }
    user_mappings = {
        "default_personality": "default",
        "mappings": [],
    }
    approved_users = {
        "description": "Approved users for Webex AI Bot",
        "users": [],
    }

    for filename, data in [
        ("personalities.json", personalities),
        ("user-mappings.json", user_mappings),
        ("approved_users.json", approved_users),
    ]:
        with open(os.path.join(tmpdir, filename), "w") as f:
            json.dump(data, f, indent=2)

    yield tmpdir
    shutil.rmtree(tmpdir)
