"""Tests for UserManager."""

import json

import pytest

from bot_server.services.user_manager import UserManager


@pytest.fixture
def users_dir(tmp_path):
    """Create a temp config dir with an approved_users.json file."""
    approved_users = {
        "description": "Approved users for Webex AI Bot",
        "users": [
            {
                "email": "alice@company.com",
                "name": "Alice",
                "added_date": "2025-01-01",
                "added_by": "setup",
            },
            {
                "email": "bob@company.com",
                "name": "Bob",
                "added_date": "2025-01-02",
                "added_by": "admin@company.com",
            },
        ],
    }
    (tmp_path / "approved_users.json").write_text(json.dumps(approved_users, indent=2))
    return tmp_path


@pytest.fixture
def admin_emails():
    return ["admin@company.com", "superadmin@company.com"]


def test_is_approved_true(users_dir, admin_emails):
    """Approved user returns True."""
    mgr = UserManager(str(users_dir), admin_emails)
    assert mgr.is_approved("alice@company.com") is True


def test_is_approved_false(users_dir, admin_emails):
    """Unknown user returns False."""
    mgr = UserManager(str(users_dir), admin_emails)
    assert mgr.is_approved("stranger@other.com") is False


def test_is_approved_case_insensitive(users_dir, admin_emails):
    """Email matching is case-insensitive."""
    mgr = UserManager(str(users_dir), admin_emails)
    assert mgr.is_approved("ALICE@COMPANY.COM") is True
    assert mgr.is_approved("Alice@Company.Com") is True


def test_is_admin(users_dir, admin_emails):
    """Admin email returns True."""
    mgr = UserManager(str(users_dir), admin_emails)
    assert mgr.is_admin("admin@company.com") is True
    assert mgr.is_admin("SUPERADMIN@COMPANY.COM") is True
    assert mgr.is_admin("alice@company.com") is False


def test_admin_implicitly_approved(users_dir, admin_emails):
    """Admin is approved even if not in approved_users.json."""
    mgr = UserManager(str(users_dir), admin_emails)
    # admin@company.com is not in the approved_users.json users list
    assert mgr.is_approved("admin@company.com") is True
    assert mgr.is_approved("superadmin@company.com") is True


def test_add_user(users_dir, admin_emails):
    """Add new user, persists to file, returns True."""
    mgr = UserManager(str(users_dir), admin_emails)
    result = mgr.add_user("newuser@company.com", "New User", "admin@company.com")
    assert result is True
    assert mgr.is_approved("newuser@company.com") is True

    # Verify persisted to file
    data = json.loads((users_dir / "approved_users.json").read_text())
    emails = [u["email"] for u in data["users"]]
    assert "newuser@company.com" in emails

    # Verify added_date and added_by are set
    new_user = next(u for u in data["users"] if u["email"] == "newuser@company.com")
    assert new_user["added_by"] == "admin@company.com"
    assert "added_date" in new_user


def test_add_user_duplicate(users_dir, admin_emails):
    """Adding existing user returns False."""
    mgr = UserManager(str(users_dir), admin_emails)
    result = mgr.add_user("alice@company.com", "Alice Again", "admin@company.com")
    assert result is False


def test_remove_user(users_dir, admin_emails):
    """Remove user, persists to file, returns True."""
    mgr = UserManager(str(users_dir), admin_emails)
    result = mgr.remove_user("alice@company.com")
    assert result is True
    assert mgr.is_approved("alice@company.com") is False

    # Verify persisted to file
    data = json.loads((users_dir / "approved_users.json").read_text())
    emails = [u["email"] for u in data["users"]]
    assert "alice@company.com" not in emails


def test_remove_user_not_found(users_dir, admin_emails):
    """Removing non-existent user returns False."""
    mgr = UserManager(str(users_dir), admin_emails)
    result = mgr.remove_user("ghost@nowhere.com")
    assert result is False


def test_list_users(users_dir, admin_emails):
    """Returns all users."""
    mgr = UserManager(str(users_dir), admin_emails)
    users = mgr.list_users()
    assert len(users) == 2
    emails = {u["email"] for u in users}
    assert emails == {"alice@company.com", "bob@company.com"}


def test_reload(users_dir, admin_emails):
    """Modifying JSON and calling reload reflects changes."""
    mgr = UserManager(str(users_dir), admin_emails)
    assert len(mgr.list_users()) == 2

    # Modify file directly
    data = json.loads((users_dir / "approved_users.json").read_text())
    data["users"].append(
        {
            "email": "charlie@company.com",
            "name": "Charlie",
            "added_date": "2025-06-01",
            "added_by": "test",
        }
    )
    (users_dir / "approved_users.json").write_text(json.dumps(data, indent=2))

    mgr.reload()
    assert len(mgr.list_users()) == 3
    assert mgr.is_approved("charlie@company.com") is True
