"""Command handler for built-in bot commands.

Parses incoming messages for recognized commands and executes them,
sending responses directly to the Webex room.
"""

import logging

from webexteamssdk import WebexTeamsAPI

from bot_server.providers.base import BaseLLMProvider
from bot_server.services.personality import PersonalityService
from bot_server.services.user_manager import UserManager

logger = logging.getLogger(__name__)

# Command prefixes for matching (lowercase)
_COMMAND_PREFIXES = [
    "help",
    "ping",
    "health check",
    "list models",
    "use prompt",
    "add user",
    "remove user",
    "list users",
    "reload users",
    "reload prompts",
]

_ADMIN_PREFIXES = {"add user", "remove user", "list users", "reload users", "reload prompts"}


class CommandHandler:
    """Parses and executes built-in bot commands."""

    def __init__(
        self,
        webex_client: WebexTeamsAPI,
        user_manager: UserManager,
        personality_service: PersonalityService,
        provider: BaseLLMProvider,
    ) -> None:
        self._webex = webex_client
        self._user_manager = user_manager
        self._personality_service = personality_service
        self._provider = provider

    def is_command(self, text: str) -> bool:
        """Check if text starts with a recognized command prefix."""
        text_lower = text.lower().strip()
        for prefix in _COMMAND_PREFIXES:
            if text_lower == prefix or text_lower.startswith(prefix + " "):
                return True
        return False

    async def handle(self, text: str, sender_email: str, room_id: str) -> None:
        """Execute a command and send the response to the room."""
        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # Check admin permission for admin commands
        for prefix in _ADMIN_PREFIXES:
            if text_lower.startswith(prefix):
                if not self._user_manager.is_admin(sender_email):
                    self._send(room_id, "You don't have permission to use this command.")
                    return
                break

        if text_lower == "help":
            await self._handle_help(room_id, sender_email)
        elif text_lower == "ping":
            self._send(room_id, "pong")
        elif text_lower == "health check":
            await self._handle_health_check(room_id)
        elif text_lower == "list models":
            await self._handle_list_models(room_id)
        elif text_lower.startswith("use prompt"):
            await self._handle_use_prompt(text_stripped, room_id)
        elif text_lower.startswith("add user"):
            self._handle_add_user(text_stripped, sender_email, room_id)
        elif text_lower.startswith("remove user"):
            self._handle_remove_user(text_stripped, room_id)
        elif text_lower == "list users":
            self._handle_list_users(room_id)
        elif text_lower == "reload users":
            self._handle_reload_users(room_id)
        elif text_lower == "reload prompts":
            self._handle_reload_prompts(room_id)

    def _send(self, room_id: str, text: str) -> None:
        """Send a message to a Webex room."""
        self._webex.messages.create(roomId=room_id, text=text)

    async def _handle_help(self, room_id: str, sender_email: str) -> None:
        """Send the list of available commands."""
        lines = [
            "Available commands:",
            "  help — Show this help message",
            "  ping — Check if the bot is alive",
            "  health check — Check AI service status",
            "  list models — List available models (Ollama only)",
            "  use prompt [name] [question] — Ask with a specific personality",
        ]
        if self._user_manager.is_admin(sender_email):
            lines.extend(
                [
                    "",
                    "Admin commands:",
                    "  add user [email] — Approve a user",
                    "  remove user [email] — Remove a user",
                    "  list users — Show approved users",
                    "  reload users — Reload approved users from config",
                    "  reload prompts — Reload personalities from config",
                ]
            )
        self._send(room_id, "\n".join(lines))

    async def _handle_health_check(self, room_id: str) -> None:
        """Check provider health and report."""
        healthy = await self._provider.health_check()
        if healthy:
            self._send(room_id, "AI service is healthy and responding.")
        else:
            self._send(room_id, "AI service is not responding.")

    async def _handle_list_models(self, room_id: str) -> None:
        """List available models."""
        models = await self._provider.list_models()
        if models is None:
            self._send(
                room_id,
                "Model listing is only available for Ollama. "
                "Cloud providers use the model configured in settings.",
            )
        elif models:
            model_list = "\n".join(f"  - {m}" for m in models)
            self._send(room_id, f"Available models:\n{model_list}")
        else:
            self._send(room_id, "No models found.")

    async def _handle_use_prompt(self, text: str, room_id: str) -> None:
        """Generate a response using a specific personality."""
        # Parse: "use prompt [name] [question]"
        parts = text.split(maxsplit=3)
        # parts[0] = "use", parts[1] = "prompt", parts[2] = name, parts[3] = question
        if len(parts) < 4:
            self._send(room_id, "Usage: use prompt [name] [question]")
            return

        name = parts[2]
        question = parts[3]

        personality = self._personality_service.get_by_name(name)
        if personality is None:
            available = self._personality_service.list_personalities()
            names = ", ".join(p["key"] for p in available)
            self._send(room_id, f"Personality '{name}' not found. Available: {names}")
            return

        try:
            response = await self._provider.generate(
                messages=[{"role": "user", "content": question}],
                system_prompt=personality["system_prompt"],
                temperature=personality["temperature"],
                max_tokens=personality["max_tokens"],
            )
            self._send(room_id, response)
        except Exception:
            logger.exception("Error generating response with personality '%s'", name)
            self._send(
                room_id,
                "I'm having trouble connecting to the AI service. Please try again in a moment.",
            )

    def _handle_add_user(self, text: str, sender_email: str, room_id: str) -> None:
        """Add a user to the approved list."""
        # Parse: "add user [email]"
        parts = text.split()
        if len(parts) < 3:
            self._send(room_id, "Usage: add user [email]")
            return

        email = parts[2]
        added = self._user_manager.add_user(email, email, sender_email)
        if added:
            self._send(room_id, f"User {email} has been approved.")
        else:
            self._send(room_id, f"User {email} is already approved.")

    def _handle_remove_user(self, text: str, room_id: str) -> None:
        """Remove a user from the approved list."""
        # Parse: "remove user [email]"
        parts = text.split()
        if len(parts) < 3:
            self._send(room_id, "Usage: remove user [email]")
            return

        email = parts[2]
        removed = self._user_manager.remove_user(email)
        if removed:
            self._send(room_id, f"User {email} has been removed.")
        else:
            self._send(room_id, f"User {email} was not found in the approved list.")

    def _handle_list_users(self, room_id: str) -> None:
        """List all approved users."""
        users = self._user_manager.list_users()
        if not users:
            self._send(room_id, "No approved users.")
            return

        lines = ["Approved users:"]
        for user in users:
            lines.append(f"  - {user['email']} ({user.get('name', 'N/A')})")
        self._send(room_id, "\n".join(lines))

    def _handle_reload_users(self, room_id: str) -> None:
        """Reload approved users from config."""
        self._user_manager.reload()
        self._send(room_id, "Approved users reloaded from config.")

    def _handle_reload_prompts(self, room_id: str) -> None:
        """Reload personalities from config."""
        self._personality_service.reload()
        self._send(room_id, "Personalities reloaded from config.")
