"""Tests for PersonalityService."""

import json

import pytest

from bot_server.services.personality import PersonalityService


@pytest.fixture
def personality_dir(tmp_path):
    """Create a temp config dir with personality and mapping files."""
    personalities = {
        "default": {
            "name": "Default Bot",
            "system_prompt": "You are a default assistant.",
            "temperature": 0.2,
            "max_tokens": 1000,
        },
        "cisco-expert": {
            "name": "Cisco Expert",
            "system_prompt": "You are a Cisco expert.",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
        "code-reviewer": {
            "name": "Code Reviewer",
            "system_prompt": "You review code.",
            "temperature": 0.1,
            "max_tokens": 2000,
        },
    }
    mappings = {
        "default_personality": "default",
        "mappings": [
            {"match": "admin@company.com", "type": "exact", "personality": "code-reviewer"},
            {"match": "*@cisco.com", "type": "pattern", "personality": "cisco-expert"},
            {
                "match": "*@engineering.company.com",
                "type": "pattern",
                "personality": "code-reviewer",
            },
        ],
    }

    (tmp_path / "personalities.json").write_text(json.dumps(personalities, indent=2))
    (tmp_path / "user-mappings.json").write_text(json.dumps(mappings, indent=2))
    return tmp_path


def test_resolve_exact_match(personality_dir):
    """Exact email match returns correct personality."""
    svc = PersonalityService(str(personality_dir))
    result = svc.resolve("admin@company.com")
    assert result["name"] == "Code Reviewer"
    assert result["temperature"] == 0.1


def test_resolve_pattern_match(personality_dir):
    """Glob pattern (*@cisco.com) resolves correctly."""
    svc = PersonalityService(str(personality_dir))
    result = svc.resolve("jane@cisco.com")
    assert result["name"] == "Cisco Expert"
    assert result["max_tokens"] == 1500


def test_resolve_default_fallback(personality_dir):
    """Unknown email falls back to default personality."""
    svc = PersonalityService(str(personality_dir))
    result = svc.resolve("nobody@unknown.org")
    assert result["name"] == "Default Bot"


def test_resolve_exact_before_pattern(personality_dir):
    """Exact match takes priority over pattern match.

    admin@company.com matches exact → code-reviewer,
    even though *@company.com would not match any pattern here.
    We add a pattern that would also match to verify priority.
    """
    # Add a pattern that would match admin@company.com
    mappings_file = personality_dir / "user-mappings.json"
    mappings = json.loads(mappings_file.read_text())
    mappings["mappings"].insert(
        0, {"match": "*@company.com", "type": "pattern", "personality": "cisco-expert"}
    )
    mappings_file.write_text(json.dumps(mappings, indent=2))

    svc = PersonalityService(str(personality_dir))
    result = svc.resolve("admin@company.com")
    # Exact match (code-reviewer) should win over pattern (cisco-expert)
    assert result["name"] == "Code Reviewer"


def test_get_by_name_exists(personality_dir):
    """Known personality name returns dict."""
    svc = PersonalityService(str(personality_dir))
    result = svc.get_by_name("cisco-expert")
    assert result is not None
    assert result["name"] == "Cisco Expert"


def test_get_by_name_not_found(personality_dir):
    """Unknown name returns None."""
    svc = PersonalityService(str(personality_dir))
    assert svc.get_by_name("nonexistent") is None


def test_list_personalities(personality_dir):
    """Returns all personalities with key and name."""
    svc = PersonalityService(str(personality_dir))
    result = svc.list_personalities()
    assert len(result) == 3
    keys = {p["key"] for p in result}
    assert keys == {"default", "cisco-expert", "code-reviewer"}
    for p in result:
        assert "key" in p
        assert "name" in p


def test_reload(personality_dir):
    """Modifying JSON and calling reload reflects changes."""
    svc = PersonalityService(str(personality_dir))
    assert svc.get_by_name("new-personality") is None

    # Add a new personality to the file
    personalities_file = personality_dir / "personalities.json"
    personalities = json.loads(personalities_file.read_text())
    personalities["new-personality"] = {
        "name": "New One",
        "system_prompt": "New personality.",
        "temperature": 0.5,
        "max_tokens": 500,
    }
    personalities_file.write_text(json.dumps(personalities, indent=2))

    svc.reload()
    result = svc.get_by_name("new-personality")
    assert result is not None
    assert result["name"] == "New One"
