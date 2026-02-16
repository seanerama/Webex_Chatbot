"""Tests for the CommandHandler."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot_server.handlers.command_handler import CommandHandler


@pytest.fixture
def webex_client():
    """Mock Webex client."""
    client = MagicMock()
    client.messages.create = MagicMock()
    return client


@pytest.fixture
def user_manager():
    """Mock UserManager."""
    mgr = MagicMock()
    mgr.is_admin.return_value = True
    mgr.add_user.return_value = True
    mgr.remove_user.return_value = True
    mgr.list_users.return_value = [
        {"email": "user1@example.com", "name": "User One"},
        {"email": "user2@example.com", "name": "User Two"},
    ]
    return mgr


@pytest.fixture
def personality_service():
    """Mock PersonalityService."""
    svc = MagicMock()
    svc.get_by_name.return_value = {
        "name": "Test Personality",
        "system_prompt": "You are a test bot.",
        "temperature": 0.5,
        "max_tokens": 500,
    }
    svc.list_personalities.return_value = [
        {"key": "default", "name": "Helpful Assistant"},
        {"key": "cisco-expert", "name": "Cisco Expert"},
    ]
    return svc


@pytest.fixture
def provider():
    """Mock LLM provider."""
    p = AsyncMock()
    p.health_check.return_value = True
    p.list_models.return_value = ["llama3.1:8b", "mistral:7b"]
    p.generate.return_value = "Generated response"
    return p


@pytest.fixture
def handler(webex_client, user_manager, personality_service, provider):
    """CommandHandler with all mocked dependencies."""
    return CommandHandler(webex_client, user_manager, personality_service, provider)


class TestIsCommand:
    def test_is_command_recognized(self, handler):
        """All known commands return True."""
        commands = [
            "help",
            "ping",
            "health check",
            "list models",
            "use prompt default What is Python?",
            "add user test@example.com",
            "remove user test@example.com",
            "list users",
            "reload users",
            "reload prompts",
        ]
        for cmd in commands:
            assert handler.is_command(cmd), f"Expected '{cmd}' to be recognized as a command"

    def test_is_command_not_command(self, handler):
        """Regular messages return False."""
        not_commands = [
            "Hello, how are you?",
            "What is the weather?",
            "Tell me about Python",
            "pinging the server",
            "helpful tips",
            "",
        ]
        for text in not_commands:
            assert not handler.is_command(text), f"Expected '{text}' to NOT be a command"

    def test_is_command_case_insensitive(self, handler):
        """Commands are recognized regardless of case."""
        assert handler.is_command("HELP")
        assert handler.is_command("Help")
        assert handler.is_command("help")
        assert handler.is_command("PING")
        assert handler.is_command("Health Check")
        assert handler.is_command("LIST MODELS")


class TestHelpCommand:
    @pytest.mark.asyncio
    async def test_help_command(self, handler, webex_client):
        """Help command sends help text to room."""
        await handler.handle("help", "user@example.com", "room1")
        webex_client.messages.create.assert_called_once()
        call_kwargs = webex_client.messages.create.call_args
        assert call_kwargs.kwargs["roomId"] == "room1"
        assert "Available commands" in call_kwargs.kwargs["text"]
        assert "help" in call_kwargs.kwargs["text"]
        assert "ping" in call_kwargs.kwargs["text"]


class TestPingCommand:
    @pytest.mark.asyncio
    async def test_ping_command(self, handler, webex_client):
        """Ping command sends pong response."""
        await handler.handle("ping", "user@example.com", "room1")
        webex_client.messages.create.assert_called_once_with(roomId="room1", text="pong")


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, handler, webex_client, provider):
        """Reports healthy when provider returns True."""
        provider.health_check.return_value = True
        await handler.handle("health check", "user@example.com", "room1")
        webex_client.messages.create.assert_called_once()
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "healthy" in text.lower()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, handler, webex_client, provider):
        """Reports unhealthy when provider returns False."""
        provider.health_check.return_value = False
        await handler.handle("health check", "user@example.com", "room1")
        webex_client.messages.create.assert_called_once()
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "not responding" in text.lower()


class TestListModels:
    @pytest.mark.asyncio
    async def test_list_models_ollama(self, handler, webex_client, provider):
        """Sends model list when models are available."""
        provider.list_models.return_value = ["llama3.1:8b", "mistral:7b"]
        await handler.handle("list models", "user@example.com", "room1")
        webex_client.messages.create.assert_called_once()
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "llama3.1:8b" in text
        assert "mistral:7b" in text

    @pytest.mark.asyncio
    async def test_list_models_cloud(self, handler, webex_client, provider):
        """Sends appropriate message when list_models returns None (cloud provider)."""
        provider.list_models.return_value = None
        await handler.handle("list models", "user@example.com", "room1")
        webex_client.messages.create.assert_called_once()
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "only available for Ollama" in text


class TestUsePrompt:
    @pytest.mark.asyncio
    async def test_use_prompt_valid(self, handler, webex_client, personality_service, provider):
        """Generates response with specified personality."""
        await handler.handle("use prompt default What is Python?", "user@example.com", "room1")
        personality_service.get_by_name.assert_called_once_with("default")
        provider.generate.assert_called_once()
        call_kwargs = provider.generate.call_args.kwargs
        assert call_kwargs["system_prompt"] == "You are a test bot."
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 500
        webex_client.messages.create.assert_called_once_with(
            roomId="room1", text="Generated response"
        )

    @pytest.mark.asyncio
    async def test_use_prompt_not_found(self, handler, webex_client, personality_service):
        """Sends 'personality not found' when name doesn't exist."""
        personality_service.get_by_name.return_value = None
        await handler.handle("use prompt nonexistent What is Python?", "user@example.com", "room1")
        webex_client.messages.create.assert_called_once()
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "not found" in text.lower()
        assert "nonexistent" in text


class TestAdminCommands:
    @pytest.mark.asyncio
    async def test_admin_add_user(self, handler, webex_client, user_manager):
        """Admin can add a user."""
        await handler.handle("add user new@example.com", "admin@example.com", "room1")
        user_manager.add_user.assert_called_once_with(
            "new@example.com", "new@example.com", "admin@example.com"
        )
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "approved" in text.lower()

    @pytest.mark.asyncio
    async def test_admin_remove_user(self, handler, webex_client, user_manager):
        """Admin can remove a user."""
        await handler.handle("remove user old@example.com", "admin@example.com", "room1")
        user_manager.remove_user.assert_called_once_with("old@example.com")
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "removed" in text.lower()

    @pytest.mark.asyncio
    async def test_admin_list_users(self, handler, webex_client, user_manager):
        """Admin can list users."""
        await handler.handle("list users", "admin@example.com", "room1")
        user_manager.list_users.assert_called_once()
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "user1@example.com" in text
        assert "user2@example.com" in text

    @pytest.mark.asyncio
    async def test_admin_command_non_admin(self, handler, webex_client, user_manager):
        """Non-admin gets permission denied for admin commands."""
        user_manager.is_admin.return_value = False
        await handler.handle("add user test@example.com", "nonadmin@example.com", "room1")
        user_manager.add_user.assert_not_called()
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "permission" in text.lower()
