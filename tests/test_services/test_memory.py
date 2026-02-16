"""Tests for MemoryService."""

from bot_server.services.memory import MemoryService


def test_add_and_get():
    """Add messages, get history returns them in order."""
    svc = MemoryService()
    svc.add_message("room1", "user", "Hello")
    svc.add_message("room1", "assistant", "Hi there")
    svc.add_message("room1", "user", "How are you?")

    history = svc.get_history("room1")
    assert len(history) == 3
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi there"}
    assert history[2] == {"role": "user", "content": "How are you?"}


def test_sliding_window():
    """Adding message 21 drops message 1."""
    svc = MemoryService(max_messages=20)
    for i in range(21):
        svc.add_message("room1", "user", f"Message {i}")

    history = svc.get_history("room1")
    assert len(history) == 20
    # First message should be "Message 1" (Message 0 was dropped)
    assert history[0]["content"] == "Message 1"
    assert history[-1]["content"] == "Message 20"


def test_get_empty_room():
    """Unknown room returns empty list."""
    svc = MemoryService()
    assert svc.get_history("nonexistent") == []


def test_clear():
    """Clear removes all history for a room."""
    svc = MemoryService()
    svc.add_message("room1", "user", "Hello")
    svc.add_message("room1", "assistant", "Hi")
    svc.clear("room1")
    assert svc.get_history("room1") == []


def test_get_returns_copy():
    """Modifying returned list doesn't affect internal state."""
    svc = MemoryService()
    svc.add_message("room1", "user", "Hello")

    history = svc.get_history("room1")
    history.append({"role": "user", "content": "Injected"})
    history[0]["content"] = "Modified"

    # Internal state should be unchanged
    actual = svc.get_history("room1")
    assert len(actual) == 1
    assert actual[0]["content"] == "Hello"


def test_multiple_rooms():
    """Rooms have independent history."""
    svc = MemoryService()
    svc.add_message("room1", "user", "Room 1 msg")
    svc.add_message("room2", "user", "Room 2 msg")

    assert len(svc.get_history("room1")) == 1
    assert len(svc.get_history("room2")) == 1
    assert svc.get_history("room1")[0]["content"] == "Room 1 msg"
    assert svc.get_history("room2")[0]["content"] == "Room 2 msg"

    svc.clear("room1")
    assert svc.get_history("room1") == []
    assert len(svc.get_history("room2")) == 1
