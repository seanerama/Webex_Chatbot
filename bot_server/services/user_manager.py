"""User access management service.

Manages approved user list and admin checks. Persists changes
to approved_users.json on add/remove operations.
"""

import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


class UserManager:
    """Approved user list management with admin checks."""

    def __init__(self, config_dir: str, admin_emails: list[str]) -> None:
        """Load approved_users.json from config_dir."""
        self._config_dir = Path(config_dir)
        self._admin_emails = [e.lower() for e in admin_emails]
        self._users_file = self._config_dir / "approved_users.json"
        self._users: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Load approved users from JSON file."""
        with open(self._users_file) as f:
            data = json.load(f)
            self._users = data.get("users", [])

        logger.info("Loaded %d approved users", len(self._users))

    def _save(self) -> None:
        """Persist current user list to JSON file."""
        data = {
            "description": "Approved users for Webex AI Bot",
            "users": self._users,
        }
        with open(self._users_file, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def is_approved(self, email: str) -> bool:
        """Check if email is in approved users list or is an admin."""
        if self.is_admin(email):
            return True
        email_lower = email.lower()
        return any(u["email"].lower() == email_lower for u in self._users)

    def is_admin(self, email: str) -> bool:
        """Check if email is in admin_emails list."""
        return email.lower() in self._admin_emails

    def add_user(self, email: str, name: str, added_by: str) -> bool:
        """Add user to approved list. Persist to JSON. Return False if exists."""
        email_lower = email.lower()
        if any(u["email"].lower() == email_lower for u in self._users):
            return False

        self._users.append(
            {
                "email": email,
                "name": name,
                "added_date": date.today().isoformat(),
                "added_by": added_by,
            }
        )
        self._save()
        logger.info("Added user %s (by %s)", email, added_by)
        return True

    def remove_user(self, email: str) -> bool:
        """Remove user from approved list. Persist to JSON. Return False if not found."""
        email_lower = email.lower()
        for i, user in enumerate(self._users):
            if user["email"].lower() == email_lower:
                self._users.pop(i)
                self._save()
                logger.info("Removed user %s", email)
                return True
        return False

    def list_users(self) -> list[dict]:
        """Return all approved users."""
        return list(self._users)

    def reload(self) -> None:
        """Reload approved users from JSON file."""
        self._load()
        logger.info("Approved users reloaded")
