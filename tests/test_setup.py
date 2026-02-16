"""Tests for the setup wizard (setup.py)."""

import json
from unittest.mock import MagicMock, patch

from setup import (
    add_approved_user,
    generate_env_file,
    prompt_bot_token,
    prompt_ollama_model,
    prompt_provider,
    register_webhook,
    start_ngrok,
    verify_llm_connectivity,
)


# ---------------------------------------------------------------------------
# Bot token validation
# ---------------------------------------------------------------------------


class TestValidateBotToken:
    @patch("setup.WebexTeamsAPI")
    @patch("builtins.input", return_value="valid-token-123")
    def test_validate_bot_token_valid(self, mock_input, mock_api_cls):
        """Valid token returns bot info."""
        mock_api = MagicMock()
        mock_me = MagicMock()
        mock_me.id = "bot-id-abc"
        mock_me.displayName = "Test Bot"
        mock_api.people.me.return_value = mock_me
        mock_api_cls.return_value = mock_api

        token, bot_id = prompt_bot_token()

        assert token == "valid-token-123"
        assert bot_id == "bot-id-abc"
        mock_api_cls.assert_called_once_with(access_token="valid-token-123")

    @patch("setup.WebexTeamsAPI")
    @patch("builtins.input", side_effect=["bad-token", "good-token"])
    def test_validate_bot_token_invalid_then_valid(self, mock_input, mock_api_cls):
        """Invalid token re-prompts, then accepts valid token."""
        mock_api_bad = MagicMock()
        mock_api_bad.people.me.side_effect = Exception("401 Unauthorized")

        mock_api_good = MagicMock()
        mock_me = MagicMock()
        mock_me.id = "bot-id-ok"
        mock_me.displayName = "Good Bot"
        mock_api_good.people.me.return_value = mock_me

        mock_api_cls.side_effect = [mock_api_bad, mock_api_good]

        token, bot_id = prompt_bot_token()

        assert token == "good-token"
        assert bot_id == "bot-id-ok"


# ---------------------------------------------------------------------------
# LLM connectivity
# ---------------------------------------------------------------------------


class TestLlmConnectivity:
    @patch("setup.get_provider")
    def test_ollama_connectivity_success(self, mock_get_provider):
        """Ollama health check passes."""
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        with patch("setup.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = True
            result = verify_llm_connectivity("ollama", "http://localhost:11434", "", "llama3.1:8b")

        assert result is True

    @patch("setup.get_provider")
    def test_ollama_connectivity_failure(self, mock_get_provider):
        """Ollama unreachable gives clear error."""
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        with patch("setup.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = False
            result = verify_llm_connectivity("ollama", "http://localhost:11434", "", "llama3.1:8b")

        assert result is False


# ---------------------------------------------------------------------------
# Ollama model listing
# ---------------------------------------------------------------------------


class TestOllamaListModels:
    @patch("builtins.input", return_value="1")
    @patch("setup.httpx")
    def test_ollama_list_models(self, mock_httpx, mock_input):
        """Models retrieved and presented correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.1:8b"},
                {"name": "mistral:7b"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        model = prompt_ollama_model("http://localhost:11434")

        assert model == "llama3.1:8b"
        mock_httpx.get.assert_called_once_with("http://localhost:11434/api/tags", timeout=10.0)


# ---------------------------------------------------------------------------
# Cloud provider selection
# ---------------------------------------------------------------------------


class TestCloudProviderSelection:
    @patch("builtins.input", return_value="2")
    def test_anthropic_selection(self, mock_input):
        """Anthropic selection sets correct provider."""
        provider = prompt_provider()
        assert provider == "anthropic"

    @patch("builtins.input", return_value="3")
    def test_openai_selection(self, mock_input):
        """OpenAI selection sets correct provider."""
        provider = prompt_provider()
        assert provider == "openai"

    @patch("builtins.input", return_value="4")
    def test_gemini_selection(self, mock_input):
        """Gemini selection sets correct provider."""
        provider = prompt_provider()
        assert provider == "gemini"

    @patch("builtins.input", return_value="5")
    def test_xai_selection(self, mock_input):
        """xAI selection sets correct provider."""
        provider = prompt_provider()
        assert provider == "xai"

    @patch("builtins.input", return_value="1")
    def test_ollama_selection(self, mock_input):
        """Ollama (default) selection sets correct provider."""
        provider = prompt_provider()
        assert provider == "ollama"

    @patch("builtins.input", return_value="")
    def test_default_selection(self, mock_input):
        """Empty input defaults to ollama."""
        provider = prompt_provider()
        assert provider == "ollama"


# ---------------------------------------------------------------------------
# .env file generation
# ---------------------------------------------------------------------------


class TestEnvFileGeneration:
    def test_env_file_generation(self, tmp_path, monkeypatch):
        """.env file written with correct values."""
        monkeypatch.chdir(tmp_path)

        generate_env_file(
            token="tok-123",
            bot_id="bid-456",
            provider="ollama",
            model="llama3.1:8b",
            ollama_url="http://localhost:11434",
            api_key="",
            admin_emails="admin@co.com",
            ngrok_authtoken="ngrok-tok",
        )

        env_path = tmp_path / ".env"
        assert env_path.exists()
        content = env_path.read_text()
        assert "WEBEX_BOT_TOKEN=tok-123" in content
        assert "WEBEX_BOT_ID=bid-456" in content
        assert "LLM_PROVIDER=ollama" in content
        assert "LLM_MODEL=llama3.1:8b" in content
        assert "OLLAMA_URL=http://localhost:11434" in content
        assert "ADMIN_EMAILS=admin@co.com" in content
        assert "NGROK_AUTHTOKEN=ngrok-tok" in content

    @patch("builtins.input", return_value="y")
    def test_env_file_overwrite_warning(self, mock_input, tmp_path, monkeypatch):
        """Existing .env triggers warning and overwrite confirmation."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("OLD=value\n")

        generate_env_file(
            token="new-tok",
            bot_id="new-bid",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            ollama_url="http://localhost:11434",
            api_key="sk-key",
            admin_emails="admin@co.com",
            ngrok_authtoken="",
        )

        content = (tmp_path / ".env").read_text()
        assert "WEBEX_BOT_TOKEN=new-tok" in content
        assert "OLD=value" not in content


# ---------------------------------------------------------------------------
# Webhook registration
# ---------------------------------------------------------------------------


class TestWebhookRegistration:
    @patch("setup.WebexTeamsAPI")
    def test_webhook_registration(self, mock_api_cls):
        """Webhook registered with correct URL and settings."""
        mock_api = MagicMock()
        mock_api.webhooks.list.return_value = []
        mock_api_cls.return_value = mock_api

        register_webhook("tok-123", "https://abc.ngrok.io")

        mock_api.webhooks.create.assert_called_once_with(
            name="Webex AI Chatbot",
            targetUrl="https://abc.ngrok.io/webhook",
            resource="messages",
            event="created",
        )

    @patch("setup.WebexTeamsAPI")
    def test_webhook_cleanup(self, mock_api_cls):
        """Old webhooks are cleaned up before registration."""
        mock_api = MagicMock()
        old_wh1 = MagicMock()
        old_wh1.id = "old-1"
        old_wh2 = MagicMock()
        old_wh2.id = "old-2"
        mock_api.webhooks.list.return_value = [old_wh1, old_wh2]
        mock_api_cls.return_value = mock_api

        register_webhook("tok-123", "https://abc.ngrok.io")

        assert mock_api.webhooks.delete.call_count == 2
        mock_api.webhooks.delete.assert_any_call("old-1")
        mock_api.webhooks.delete.assert_any_call("old-2")
        mock_api.webhooks.create.assert_called_once()


# ---------------------------------------------------------------------------
# Approved user management
# ---------------------------------------------------------------------------


class TestApprovedUser:
    def test_approved_user_added(self, tmp_path):
        """User added to approved_users.json when requested."""
        users_file = tmp_path / "approved_users.json"
        users_file.write_text(
            json.dumps(
                {
                    "description": "Approved users for Webex AI Bot",
                    "users": [],
                }
            )
        )

        with patch("setup.APPROVED_USERS_FILE", users_file):
            add_approved_user("user@example.com", "Test User")

        data = json.loads(users_file.read_text())
        assert len(data["users"]) == 1
        assert data["users"][0]["email"] == "user@example.com"
        assert data["users"][0]["name"] == "Test User"
        assert data["users"][0]["added_by"] == "setup"

    def test_approved_user_no_duplicate(self, tmp_path):
        """Adding an existing user does not create a duplicate."""
        users_file = tmp_path / "approved_users.json"
        users_file.write_text(
            json.dumps(
                {
                    "description": "Approved users for Webex AI Bot",
                    "users": [
                        {
                            "email": "user@example.com",
                            "name": "Test User",
                            "added_date": "2025-01-01",
                            "added_by": "setup",
                        }
                    ],
                }
            )
        )

        with patch("setup.APPROVED_USERS_FILE", users_file):
            add_approved_user("user@example.com", "Test User")

        data = json.loads(users_file.read_text())
        assert len(data["users"]) == 1


# ---------------------------------------------------------------------------
# ngrok startup
# ---------------------------------------------------------------------------


class TestNgrokStartup:
    @patch("setup.ngrok")
    @patch("setup.conf")
    def test_start_ngrok_with_token(self, mock_conf, mock_ngrok):
        """ngrok starts and returns HTTPS URL."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://abc123.ngrok.io"
        mock_ngrok.connect.return_value = mock_tunnel

        url = start_ngrok("my-token", 8080)

        assert url == "https://abc123.ngrok.io"
        mock_ngrok.connect.assert_called_once_with(8080, "http")

    @patch("setup.ngrok")
    @patch("setup.conf")
    def test_start_ngrok_converts_http_to_https(self, mock_conf, mock_ngrok):
        """HTTP URLs from ngrok are converted to HTTPS."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "http://abc123.ngrok.io"
        mock_ngrok.connect.return_value = mock_tunnel

        url = start_ngrok("", 8080)

        assert url == "https://abc123.ngrok.io"
