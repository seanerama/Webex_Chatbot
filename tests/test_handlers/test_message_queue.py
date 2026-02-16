"""Tests for the MessageQueue."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot_server.handlers.message_queue import MessageQueue
from bot_server.providers.base import LLMProviderError


@pytest.fixture
def webex_client():
    """Mock Webex client."""
    client = MagicMock()
    client.messages.create = MagicMock()
    return client


@pytest.fixture
def provider():
    """Mock LLM provider."""
    p = AsyncMock()
    p.generate.return_value = "AI response"
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
def queue(webex_client, provider, personality_service, memory_service):
    """MessageQueue with all mocked dependencies."""
    return MessageQueue(webex_client, provider, personality_service, memory_service)


class TestEnqueueAndProcess:
    @pytest.mark.asyncio
    async def test_enqueue_and_process(self, queue, provider, personality_service, memory_service):
        """Message is enqueued and processed through the full flow."""
        await queue.start()
        await queue.enqueue("room1", "user@example.com", "Hello AI")

        # Give the worker a moment to process
        await asyncio.sleep(0.1)
        await queue.stop()

        personality_service.resolve.assert_called_once_with("user@example.com")
        memory_service.get_history.assert_called_once_with("room1")
        memory_service.add_message.assert_any_call("room1", "user", "Hello AI")
        memory_service.add_message.assert_any_call("room1", "assistant", "AI response")
        provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_sends_response(self, queue, webex_client, provider):
        """Processed message results in a Webex message sent."""
        provider.generate.return_value = "Here is my answer"
        await queue.start()
        await queue.enqueue("room1", "user@example.com", "Question?")

        await asyncio.sleep(0.1)
        await queue.stop()

        webex_client.messages.create.assert_called_once_with(
            roomId="room1", text="Here is my answer"
        )


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_provider_error_sends_friendly_message(self, queue, webex_client, provider):
        """LLMProviderError sends a friendly error message to room."""
        provider.generate.side_effect = LLMProviderError("Connection refused")
        await queue.start()
        await queue.enqueue("room1", "user@example.com", "Hello")

        await asyncio.sleep(0.1)
        await queue.stop()

        webex_client.messages.create.assert_called_once()
        text = webex_client.messages.create.call_args.kwargs["text"]
        assert "trouble connecting" in text.lower()


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_stop(self, queue):
        """Queue starts and stops cleanly."""
        await queue.start()
        assert queue._worker_task is not None
        assert not queue._worker_task.done()

        await queue.stop()
        assert queue._worker_task is None


class TestSequentialProcessing:
    @pytest.mark.asyncio
    async def test_sequential_processing(self, queue, provider, webex_client):
        """Messages are processed in order."""
        call_order = []

        async def track_generate(**kwargs):
            msg = kwargs["messages"][-1]["content"]
            call_order.append(msg)
            return f"Reply to: {msg}"

        provider.generate.side_effect = track_generate

        await queue.start()
        await queue.enqueue("room1", "user@example.com", "first")
        await queue.enqueue("room1", "user@example.com", "second")
        await queue.enqueue("room1", "user@example.com", "third")

        await asyncio.sleep(0.2)
        await queue.stop()

        assert call_order == ["first", "second", "third"]
