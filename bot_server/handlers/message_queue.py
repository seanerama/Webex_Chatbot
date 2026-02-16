"""Async message queue for sequential LLM processing.

Enqueues incoming messages and processes them one at a time,
calling the LLM provider and sending responses back to Webex.
"""

import asyncio
import logging

from webexteamssdk import WebexTeamsAPI

from bot_server.providers.base import BaseLLMProvider, LLMProviderError
from bot_server.services.memory import MemoryService
from bot_server.services.personality import PersonalityService

logger = logging.getLogger(__name__)


class MessageQueue:
    """Async queue that processes messages sequentially through the LLM."""

    def __init__(
        self,
        webex_client: WebexTeamsAPI,
        provider: BaseLLMProvider,
        personality_service: PersonalityService,
        memory_service: MemoryService,
    ) -> None:
        self._webex = webex_client
        self._provider = provider
        self._personality_service = personality_service
        self._memory_service = memory_service
        self._queue: asyncio.Queue[tuple[str, str, str]] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._running = False

    async def enqueue(self, room_id: str, sender_email: str, text: str) -> None:
        """Add a message to the processing queue."""
        await self._queue.put((room_id, sender_email, text))
        logger.debug("Enqueued message from %s in room %s", sender_email, room_id)

    async def start(self) -> None:
        """Start the queue worker task."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Message queue worker started")

    async def stop(self) -> None:
        """Stop the queue worker gracefully."""
        self._running = False
        if self._worker_task is not None:
            # Put a sentinel to unblock the worker if it's waiting on queue.get()
            await self._queue.put(None)  # type: ignore[arg-type]
            await self._worker_task
            self._worker_task = None
        logger.info("Message queue worker stopped")

    async def _worker(self) -> None:
        """Background worker that consumes messages from the queue."""
        while self._running:
            item = await self._queue.get()
            if item is None:
                # Sentinel received — stop signal
                break
            room_id, sender_email, text = item
            try:
                await self._process_message(room_id, sender_email, text)
            except Exception:
                logger.exception("Unexpected error processing message in room %s", room_id)
            finally:
                self._queue.task_done()

    async def _process_message(self, room_id: str, sender_email: str, text: str) -> None:
        """Process a single message through the LLM pipeline."""
        personality = self._personality_service.resolve(sender_email)
        history = self._memory_service.get_history(room_id)
        self._memory_service.add_message(room_id, "user", text)

        try:
            response = await self._provider.generate(
                messages=history + [{"role": "user", "content": text}],
                system_prompt=personality["system_prompt"],
                temperature=personality["temperature"],
                max_tokens=personality["max_tokens"],
            )
        except LLMProviderError as e:
            logger.error("LLM provider error in room %s: %s", room_id, e)
            self._webex.messages.create(
                roomId=room_id,
                text=(
                    "I'm having trouble connecting to the AI service. Please try again in a moment."
                ),
            )
            return

        self._memory_service.add_message(room_id, "assistant", response)
        self._webex.messages.create(roomId=room_id, text=response)
        logger.debug("Sent response in room %s", room_id)
