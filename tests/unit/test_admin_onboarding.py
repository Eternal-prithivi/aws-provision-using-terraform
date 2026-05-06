"""tests/unit/test_admin_onboarding.py — Tests for onboarding and team management helpers."""

from __future__ import annotations

import sys
import yaml
from pathlib import Path
from unittest.mock import patch

import pytest

# Make sure team-management module is importable
import sys
from pathlib import Path as P
sys.path.insert(0, str(P(__file__).resolve().parent.parent.parent / "team-management"))
from team_engine import TeamEngine  # noqa: E402

# Import helpers from wizard
sys.path.insert(0, str(P(__file__).resolve().parent.parent.parent / "cli-wizard"))
from wizard import (
    first_run_admin_onboarding,
    add_member,
    edit_member,
    remove_member,
)  # noqa: E402


SAMPLE_CONFIG = {
    "roles": {
        "admin": {"name": "Administrator", "permissions": ["deploy:create"]},
        "developer": {"name": "Developer", "permissions": ["deploy:create"]},
    },
    "teams": {},
}


def write_config(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def test_first_run_onboarding_creates_admin(tmp_path, monkeypatch):
    cfg = tmp_path / "teams.yaml"
    write_config(cfg, SAMPLE_CONFIG)

    engine = TeamEngine(config_path=cfg)

    # Mock prompts: name, email, github_username, confirm yes, commit no
    inputs = iter(["Test Admin", "admin@test.com", "test-admin", "y", "n"])

    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr("cli-wizard.wizard.prompt_yes_no", lambda *a, **k: True if next(inputs, "y") in ("y", "Y") else False)

    # Force onboarding to run in pytest
    first_run_admin_onboarding(engine, force=True)

    # Reload engine and verify user exists
    engine._load_config()
    assert engine.get_user_info("test-admin") is not None
    assert engine.get_user_info("test-admin")["role"] == "admin"


def test_add_edit_remove_member(tmp_path):
    cfg = tmp_path / "teams.yaml"
    write_config(cfg, SAMPLE_CONFIG)
    engine = TeamEngine(config_path=cfg)

    add_member(engine, "devops-core", "Alice", "a@x.com", "alice", "devops")
    assert engine.get_user_info("alice") is not None

    edited = edit_member(engine, "alice", new_role="admin", new_email="alice2@x.com")
    assert edited
    info = engine.get_user_info("alice")
    assert info["role"] == "admin"
    assert info["email"] == "alice2@x.com"

    removed = remove_member(engine, "alice")
    assert removed
    assert engine.get_user_info("alice") is None
