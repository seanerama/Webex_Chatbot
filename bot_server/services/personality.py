"""Personality resolution service.

Loads personality definitions and user-to-personality mappings from JSON config,
then resolves which personality to use for a given user email.
"""

import json
import logging
from fnmatch import fnmatch
from pathlib import Path

logger = logging.getLogger(__name__)


class PersonalityService:
    """Resolves AI personalities for users based on email matching rules."""

    def __init__(self, config_dir: str) -> None:
        """Load personalities.json and user-mappings.json from config_dir."""
        self._config_dir = Path(config_dir)
        self._personalities: dict[str, dict] = {}
        self._mappings: list[dict] = []
        self._default_personality: str = "default"
        self._load()

    def _load(self) -> None:
        """Load personality and mapping files from disk."""
        personalities_path = self._config_dir / "personalities.json"
        mappings_path = self._config_dir / "user-mappings.json"

        with open(personalities_path) as f:
            self._personalities = json.load(f)

        with open(mappings_path) as f:
            mappings_data = json.load(f)
            self._default_personality = mappings_data.get("default_personality", "default")
            self._mappings = mappings_data.get("mappings", [])

        logger.info(
            "Loaded %d personalities and %d mappings",
            len(self._personalities),
            len(self._mappings),
        )

    def resolve(self, email: str) -> dict:
        """Resolve personality for a user.

        Order:
        1. Exact email match in user-mappings.json
        2. Pattern match (fnmatch glob, first match wins)
        3. Default personality

        Returns:
            dict with keys: name, system_prompt, temperature, max_tokens
        """
        email_lower = email.lower()

        # Pass 1: exact matches only
        for mapping in self._mappings:
            if mapping["type"] == "exact" and mapping["match"].lower() == email_lower:
                personality_key = mapping["personality"]
                if personality_key in self._personalities:
                    logger.debug("Exact match for %s → %s", email, personality_key)
                    return self._personalities[personality_key]

        # Pass 2: pattern matches in order
        for mapping in self._mappings:
            if mapping["type"] == "pattern" and fnmatch(email_lower, mapping["match"].lower()):
                personality_key = mapping["personality"]
                if personality_key in self._personalities:
                    logger.debug("Pattern match for %s → %s", email, personality_key)
                    return self._personalities[personality_key]

        # Fallback to default
        logger.debug("No match for %s, using default personality", email)
        return self._personalities[self._default_personality]

    def get_by_name(self, name: str) -> dict | None:
        """Look up personality by key name. For 'use prompt [name]' command."""
        return self._personalities.get(name)

    def list_personalities(self) -> list[dict]:
        """Return all personalities as [{"key": "...", "name": "..."}]."""
        return [
            {"key": key, "name": personality["name"]}
            for key, personality in self._personalities.items()
        ]

    def reload(self) -> None:
        """Reload personality and mapping files from disk."""
        self._load()
        logger.info("Personality configuration reloaded")
