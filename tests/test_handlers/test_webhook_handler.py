"""Tests for the WebhookHandler."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot_server.handlers.webhook_handler import WebhookHandler


def make_message(
    person_id="user-person-id",
    person_email="user@example.com",
    text="Hello bot",
    room_type="direct",
    room_id="room1",
):
    """Create a mock Webex message object."""
    msg = MagicMock()
    msg.personId = person_id
    msg.personEmail = person_email
    msg.text = text
    msg.roomType = room_type
    msg.roomId = room_id
    return msg


def make_webhook_data(message_id="msg-123", room_id="room1"):
    """Create a webhook payload dict."""
    return {
        "data": {
            "id": message_id,
            "roomId": room_id,
        }
    }


@pytest.fixture
def webex_client():
    """Mock Webex client."""
    client = MagicMock()
    return client


@pytest.fixture
def user_manager():
    """Mock UserManager."""
    mgr = MagicMock()
    mgr.is_approved.return_value = True
    return mgr


@pytest.fixture
def command_handler():
    """Mock CommandHandler."""
    handler = MagicMock()
    handler.is_command.return_value = False
    handler.handle = AsyncMock()
    return handler


@pytest.fixture
def message_queue():
    """Mock MessageQueue."""
    return AsyncMock()


@pytest.fixture
def webhook_handler(webex_client, user_manager, command_handler, message_queue):
    """WebhookHandler with all mocked dependencies."""
    return WebhookHandler(
        webex_client=webex_client,
        bot_id="bot-person-id",
        user_manager=user_manager,
        command_handler=command_handler,
        message_queue=message_queue,
    )


class TestNormalMessage:
    @pytest.mark.asyncio
    async def test_handle_normal_message(
        self, webhook_handler, webex_client, message_queue, command_handler
    ):
        """Message from approved user goes to message queue."""
        msg = make_message(text="What is Python?")
        webex_client.messages.get.return_value = msg

        await webhook_handler.handle(make_webhook_data())

        command_handler.is_command.assert_called_once_with("What is Python?")
        message_queue.enqueue.assert_called_once_with(
            "room1", "user@example.com", "What is Python?"
        )


class TestCommandRouting:
    @pytest.mark.asyncio
    async def test_handle_command(
        self, webhook_handler, webex_client, command_handler, message_queue
    ):
        """Command message goes to command handler."""
        msg = make_message(text="help")
        webex_client.messages.get.return_value = msg
        command_handler.is_command.return_value = True

        await webhook_handler.handle(make_webhook_data())

        command_handler.is_command.assert_called_once_with("help")
        command_handler.handle.assert_called_once_with("help", "user@example.com", "room1")
        message_queue.enqueue.assert_not_called()


class TestBotIgnore:
    @pytest.mark.asyncio
    async def test_ignore_bot_message(
        self, webhook_handler, webex_client, command_handler, message_queue
    ):
        """Messages from the bot itself are ignored."""
        msg = make_message(person_id="bot-person-id", text="I am the bot")
        webex_client.messages.get.return_value = msg

        await webhook_handler.handle(make_webhook_data())

        command_handler.is_command.assert_not_called()
        message_queue.enqueue.assert_not_called()


class TestAuthorization:
    @pytest.mark.asyncio
    async def test_ignore_unapproved_user(
        self, webhook_handler, webex_client, user_manager, command_handler, message_queue
    ):
        """Messages from unapproved users are ignored."""
        msg = make_message(person_email="stranger@example.com", text="Let me in")
        webex_client.messages.get.return_value = msg
        user_manager.is_approved.return_value = False

        await webhook_handler.handle(make_webhook_data())

        user_manager.is_approved.assert_called_once_with("stranger@example.com")
        command_handler.is_command.assert_not_called()
        message_queue.enqueue.assert_not_called()


class TestGroupSpace:
    @pytest.mark.asyncio
    async def test_group_space_strips_mention(
        self, webhook_handler, webex_client, message_queue, command_handler
    ):
        """@mention prefix is stripped in group spaces."""
        msg = make_message(
            text="BotName What is the weather?",
            room_type="group",
        )
        webex_client.messages.get.return_value = msg

        await webhook_handler.handle(make_webhook_data())

        command_handler.is_command.assert_called_once_with("What is the weather?")
        message_queue.enqueue.assert_called_once_with(
            "room1", "user@example.com", "What is the weather?"
        )

    @pytest.mark.asyncio
    async def test_direct_message_no_strip(
        self, webhook_handler, webex_client, message_queue, command_handler
    ):
        """Direct messages are not modified."""
        msg = make_message(
            text="BotName What is the weather?",
            room_type="direct",
        )
        webex_client.messages.get.return_value = msg

        await webhook_handler.handle(make_webhook_data())

        # In direct mode, the full text (including "BotName") is preserved
        command_handler.is_command.assert_called_once_with("BotName What is the weather?")
