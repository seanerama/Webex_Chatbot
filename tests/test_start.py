"""Tests for the bot launcher (start.py)."""

from unittest.mock import MagicMock, patch

import pytest

from start import check_env_file, load_settings, register_webhook, start_ngrok


# ---------------------------------------------------------------------------
# .env file checks
# ---------------------------------------------------------------------------


class TestCheckEnvFile:
    def test_start_no_env_file(self, tmp_path, monkeypatch):
        """Missing .env gives helpful error pointing to setup.py."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            check_env_file()

        assert exc_info.value.code == 1

    def test_start_env_file_exists(self, tmp_path, monkeypatch):
        """Existing .env passes the check."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("WEBEX_BOT_TOKEN=tok\n")

        # Should not raise
        check_env_file()


# ---------------------------------------------------------------------------
# Settings loading
# ---------------------------------------------------------------------------


class TestLoadSettings:
    def test_start_loads_settings(self, monkeypatch):
        """Settings loaded from .env."""
        monkeypatch.setenv("WEBEX_BOT_TOKEN", "test-tok")
        monkeypatch.setenv("WEBEX_BOT_ID", "test-bid")
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
        monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
        monkeypatch.setenv("ADMIN_EMAILS", "admin@co.com")

        settings = load_settings()

        assert settings.webex_bot_token == "test-tok"
        assert settings.llm_provider == "ollama"
        assert settings.llm_model == "llama3.1:8b"


# ---------------------------------------------------------------------------
# Webhook registration
# ---------------------------------------------------------------------------


class TestStartWebhookRegistration:
    @patch("start.WebexTeamsAPI")
    def test_start_registers_webhook(self, mock_api_cls):
        """New webhook registered with new ngrok URL."""
        mock_api = MagicMock()
        mock_api.webhooks.list.return_value = []
        mock_api_cls.return_value = mock_api

        register_webhook("tok-123", "https://new-url.ngrok.io")

        mock_api.webhooks.create.assert_called_once_with(
            name="Webex AI Chatbot",
            targetUrl="https://new-url.ngrok.io/webhook",
            resource="messages",
            event="created",
        )

    @patch("start.WebexTeamsAPI")
    def test_start_cleans_old_webhooks(self, mock_api_cls):
        """Old webhooks removed before new registration."""
        mock_api = MagicMock()
        old_wh = MagicMock()
        old_wh.id = "old-wh-1"
        mock_api.webhooks.list.return_value = [old_wh]
        mock_api_cls.return_value = mock_api

        register_webhook("tok-123", "https://new-url.ngrok.io")

        mock_api.webhooks.delete.assert_called_once_with("old-wh-1")
        mock_api.webhooks.create.assert_called_once()


# ---------------------------------------------------------------------------
# ngrok startup
# ---------------------------------------------------------------------------


class TestStartNgrok:
    @patch("start.ngrok")
    @patch("start.conf")
    def test_start_ngrok_returns_url(self, mock_conf, mock_ngrok):
        """ngrok tunnel started and URL returned."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://xyz.ngrok.io"
        mock_ngrok.connect.return_value = mock_tunnel

        url = start_ngrok("auth-tok", 8080)

        assert url == "https://xyz.ngrok.io"
        mock_ngrok.connect.assert_called_once_with(8080, "http")

    @patch("start.ngrok")
    @patch("start.conf")
    def test_start_ngrok_failure_exits(self, mock_conf, mock_ngrok):
        """ngrok failure calls sys.exit."""
        mock_ngrok.connect.side_effect = Exception("ngrok error")

        with pytest.raises(SystemExit) as exc_info:
            start_ngrok("auth-tok", 8080)

        assert exc_info.value.code == 1
