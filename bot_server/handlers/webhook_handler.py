"""Webhook handler for incoming Webex events.

Receives webhook POST data, fetches the full message from the Webex API,
performs authorization checks, and routes to the command handler or message queue.
"""

import logging

from webexteamssdk import WebexTeamsAPI

from bot_server.handlers.command_handler import CommandHandler
from bot_server.handlers.message_queue import MessageQueue
from bot_server.services.user_manager import UserManager

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Receives webhook events, validates, authorizes, and routes messages."""

    def __init__(
        self,
        webex_client: WebexTeamsAPI,
        bot_id: str,
        user_manager: UserManager,
        command_handler: CommandHandler,
        message_queue: MessageQueue,
    ) -> None:
        self._webex = webex_client
        self._bot_id = bot_id
        self._user_manager = user_manager
        self._command_handler = command_handler
        self._message_queue = message_queue

    async def handle(self, webhook_data: dict) -> None:
        """Process an incoming webhook event.

        Flow:
        1. Extract message ID and room ID from webhook data
        2. Fetch full message from Webex API
        3. Ignore messages from the bot itself
        4. Check sender authorization
        5. Strip @mention prefix in group spaces
        6. Route to command handler or message queue
        """
        data = webhook_data.get("data", {})
        message_id = data.get("id")
        room_id = data.get("roomId")

        if not message_id or not room_id:
            logger.warning("Webhook missing message ID or room ID")
            return

        # Fetch full message from Webex API
        try:
            message = self._webex.messages.get(message_id)
        except Exception:
            logger.exception("Failed to fetch message %s from Webex API", message_id)
            return

        # Ignore messages from the bot itself
        if message.personId == self._bot_id:
            return

        # Check authorization
        if not self._user_manager.is_approved(message.personEmail):
            logger.info("Ignoring message from unapproved user: %s", message.personEmail)
            return

        text = message.text or ""

        # Strip @mention prefix in group spaces
        if message.roomType == "group" and text:
            # Webex prepends the bot's display name in group spaces
            # The text typically looks like "BotName some message"
            # We strip the first word (the bot mention)
            parts = text.split(maxsplit=1)
            text = parts[1] if len(parts) > 1 else ""

        text = text.strip()

        if not text:
            return

        # Route to command handler or message queue
        if self._command_handler.is_command(text):
            await self._command_handler.handle(text, message.personEmail, room_id)
        else:
            await self._message_queue.enqueue(room_id, message.personEmail, text)
