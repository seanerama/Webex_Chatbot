"""Tests for the FastAPI application (bot_server/app.py)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bot_server.app import health, webhook


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_webhook_body(message_id: str = "msg-123", room_id: str = "room1") -> dict:
    """Create a valid webhook POST body."""
    return {"data": {"id": message_id, "roomId": room_id}}


def _make_message(
    person_id: str = "user-person-id",
    person_email: str = "user@example.com",
    text: str = "Hello bot",
    room_type: str = "direct",
):
    """Create a mock Webex message object."""
    msg = MagicMock()
    msg.personId = person_id
    msg.personEmail = person_email
    msg.text = text
    msg.roomType = room_type
    return msg


# ---------------------------------------------------------------------------
# Fixtures — test app with mocked dependencies
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_webhook_handler():
    return AsyncMock()


@pytest.fixture
def mock_provider():
    p = AsyncMock()
    p.health_check.return_value = True
    p.generate.return_value = "AI response"
    return p


@pytest.fixture
def test_app(mock_webhook_handler, mock_provider):
    """Create a FastAPI test app with mocked state (bypasses lifespan)."""
    test_application = FastAPI()

    # Re-register the route handlers from the real app
    test_application.add_api_route("/webhook", webhook, methods=["POST"])
    test_application.add_api_route("/health", health, methods=["GET"])

    # Inject mocked dependencies on state
    test_application.state.webhook_handler = mock_webhook_handler
    test_application.state.provider = mock_provider

    return test_application


@pytest_asyncio.fixture
async def client(test_app):
    """Async HTTP client for the test app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Unit tests — webhook endpoint
# ---------------------------------------------------------------------------


class TestWebhookEndpoint:
    @pytest.mark.asyncio
    async def test_webhook_returns_200(self, client):
        """POST /webhook returns 200."""
        resp = await client.post("/webhook", json=_make_webhook_body())
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_calls_handler(self, client, mock_webhook_handler):
        """Webhook handler's handle() is called with the request body."""
        body = _make_webhook_body("msg-456", "room-abc")
        await client.post("/webhook", json=body)
        mock_webhook_handler.handle.assert_called_once_with(body)

    @pytest.mark.asyncio
    async def test_webhook_returns_200_on_error(self, client, mock_webhook_handler):
        """Returns 200 even when handler raises an exception."""
        mock_webhook_handler.handle.side_effect = RuntimeError("boom")
        resp = await client.post("/webhook", json=_make_webhook_body())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Unit tests — health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_healthy(self, client, mock_provider):
        """Returns healthy when provider health check passes."""
        mock_provider.health_check.return_value = True
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy", "provider": True}

    @pytest.mark.asyncio
    async def test_health_degraded(self, client, mock_provider):
        """Returns degraded when provider health check fails."""
        mock_provider.health_check.return_value = False
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "degraded", "provider": False}

    @pytest.mark.asyncio
    async def test_health_degraded_on_exception(self, client, mock_provider):
        """Returns degraded when provider health check raises."""
        mock_provider.health_check.side_effect = Exception("connection refused")
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "degraded", "provider": False}


# ---------------------------------------------------------------------------
# Integration tests — full message flow through real handler stack
# ---------------------------------------------------------------------------


@pytest.fixture
def webex_client():
    """Mock Webex client for integration tests."""
    client = MagicMock()
    client.messages.create = MagicMock()
    return client


@pytest.fixture
def provider():
    """Mock LLM provider for integration tests."""
    p = AsyncMock()
    p.generate.return_value = "AI response"
    p.health_check.return_value = True
    return p


@pytest.fixture
def personality_service():
    """Mock PersonalityService."""
    svc = MagicMock()
    svc.resolve.return_value = {
        "name": "Default",
        "system_prompt": "You are helpful.",
        "temperature": 0.2,
        "max_tokens": 1000,
    }
    return svc


@pytest.fixture
def memory_service():
    """Mock MemoryService."""
    svc = MagicMock()
    svc.get_history.return_value = []
    return svc


@pytest.fixture
def user_manager():
    """Mock UserManager."""
    mgr = MagicMock()
    mgr.is_approved.return_value = True
    mgr.is_admin.return_value = False
    return mgr


@pytest.fixture
def integration_app(webex_client, provider, personality_service, memory_service, user_manager):
    """Full integration app with real handlers but mocked external dependencies."""
    from bot_server.handlers.command_handler import CommandHandler
    from bot_server.handlers.message_queue import MessageQueue
    from bot_server.handlers.webhook_handler import WebhookHandler

    command_handler = CommandHandler(webex_client, user_manager, personality_service, provider)
    message_queue = MessageQueue(webex_client, provider, personality_service, memory_service)
    wh = WebhookHandler(webex_client, "bot-id", user_manager, command_handler, message_queue)

    test_application = FastAPI()
    test_application.add_api_route("/webhook", webhook, methods=["POST"])
    test_application.add_api_route("/health", health, methods=["GET"])
    test_application.state.webhook_handler = wh
    test_application.state.provider = provider
    test_application.state.message_queue = message_queue

    return test_application


@pytest_asyncio.fixture
async def integration_client(integration_app):
    """Async HTTP client for the integration app."""
    # Start message queue worker
    mq = integration_app.state.message_queue
    await mq.start()

    transport = ASGITransport(app=integration_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await mq.stop()


class TestFullMessageFlow:
    @pytest.mark.asyncio
    async def test_full_message_flow(
        self, integration_client, integration_app, webex_client, provider
    ):
        """Webhook POST → handler processes → LLM generates → response sent."""
        msg = _make_message(text="What is Python?")
        webex_client.messages.get.return_value = msg

        resp = await integration_client.post("/webhook", json=_make_webhook_body())
        assert resp.status_code == 200

        # Give the queue worker time to process
        await asyncio.sleep(0.15)

        provider.generate.assert_called_once()
        webex_client.messages.create.assert_called_once_with(roomId="room1", text="AI response")


class TestCommandFlow:
    @pytest.mark.asyncio
    async def test_command_flow(self, integration_client, webex_client):
        """Webhook POST with command → command handler → response sent."""
        msg = _make_message(text="ping")
        webex_client.messages.get.return_value = msg

        resp = await integration_client.post("/webhook", json=_make_webhook_body())
        assert resp.status_code == 200

        webex_client.messages.create.assert_called_once_with(roomId="room1", text="pong")


class TestUnapprovedUserIgnored:
    @pytest.mark.asyncio
    async def test_unapproved_user_ignored(
        self, integration_client, webex_client, user_manager, provider
    ):
        """Webhook from unapproved user → no processing, no response."""
        msg = _make_message(person_email="stranger@evil.com", text="hack hack")
        webex_client.messages.get.return_value = msg
        user_manager.is_approved.return_value = False

        resp = await integration_client.post("/webhook", json=_make_webhook_body())
        assert resp.status_code == 200

        # Give the queue worker a chance (should have nothing to process)
        await asyncio.sleep(0.1)

        provider.generate.assert_not_called()
        webex_client.messages.create.assert_not_called()
