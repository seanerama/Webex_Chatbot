"""Conversation memory service.

Manages sliding-window conversation history per Webex room.
All data is in-memory and lost on restart.
"""

import logging

logger = logging.getLogger(__name__)


class MemoryService:
    """Sliding-window conversation history per room."""

    def __init__(self, max_messages: int = 20) -> None:
        """Initialize with empty in-memory store."""
        self._max_messages = max_messages
        self._store: dict[str, list[dict]] = {}

    def get_history(self, room_id: str) -> list[dict]:
        """Return message history for room. Empty list if none."""
        return [msg.copy() for msg in self._store.get(room_id, [])]

    def add_message(self, room_id: str, role: str, content: str) -> None:
        """Add message. Drop oldest if exceeds max_messages."""
        if room_id not in self._store:
            self._store[room_id] = []

        self._store[room_id].append({"role": role, "content": content})

        if len(self._store[room_id]) > self._max_messages:
            self._store[room_id] = self._store[room_id][-self._max_messages :]

    def clear(self, room_id: str) -> None:
        """Clear history for a room."""
        self._store.pop(room_id, None)
