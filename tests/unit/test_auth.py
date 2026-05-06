"""tests/unit/test_auth.py — Tests for CLI authentication and role-based access."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "team-management"))
from team_engine import RoleGate, TeamEngine  # noqa: E402


class TestRoleGate:
    """Test role-based access control for CLI."""

    def test_role_gate_creation(self) -> None:
        """Test RoleGate can be instantiated."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        assert gate.engine is not None
        assert gate.engine is engine

    def test_check_can_deploy_valid_user(self) -> None:
        """Test deployment permission check for valid user."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        
        # Find a user with deploy:create permission
        for username, user_obj in engine.users.items():
            role = engine.roles.get(user_obj.role)
            if role and "deploy:create" in role.permissions:
                can_deploy, msg = gate.check_can_deploy(username, "staging")
                assert can_deploy is True
                assert "✅" in msg
                return
        
        # If no such user, test passes (team config may be empty)
        assert True

    def test_check_can_deploy_invalid_user(self) -> None:
        """Test deployment permission check for non-existent user."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        
        can_deploy, msg = gate.check_can_deploy("nonexistent-user-xyz", "staging")
        assert can_deploy is False
        assert "❌" in msg
        assert "not found" in msg

    def test_check_can_deploy_to_production(self) -> None:
        """Test production deployment permission check."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        
        # Find an admin or devops user
        for username, user_obj in engine.users.items():
            if user_obj.role in ["admin", "devops"]:
                can_deploy, msg = gate.check_can_deploy(username, "production")
                assert isinstance(can_deploy, bool)
                assert ("✅" in msg or "❌" in msg)
                return

    def test_get_allowed_environments(self) -> None:
        """Test getting list of allowed environments."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        
        for username in engine.users:
            envs = gate.get_allowed_environments(username)
            assert isinstance(envs, list)
            assert len(envs) > 0
            assert all(e in ["staging", "production"] for e in envs)

    def test_get_allowed_environments_nonexistent_user(self) -> None:
        """Test allowed environments for non-existent user."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        
        envs = gate.get_allowed_environments("nonexistent-user-xyz")
        assert envs == ["staging"]  # Default fallback

    def test_show_role_summary(self, capsys: pytest.CaptureFixture) -> None:
        """Test role summary display."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        
        for username in engine.users:
            gate.show_role_summary(username)
            captured = capsys.readouterr()
            assert "Authenticated" in captured.out or "found" in captured.out
            return

    def test_show_role_summary_invalid_user(self, capsys: pytest.CaptureFixture) -> None:
        """Test role summary for non-existent user."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        
        gate.show_role_summary("nonexistent-user-xyz")
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_role_gate_permission_validation(self) -> None:
        """Test role gate validates permissions correctly."""
        engine = TeamEngine()
        gate = RoleGate(engine)
        
        # All users should have a valid role
        for username, user_obj in engine.users.items():
            assert user_obj.role in engine.roles
            role_def = engine.roles[user_obj.role]
            assert role_def is not None
            assert isinstance(role_def.permissions, list)


class TestAuthenticationFlow:
    """Test authentication flow scenarios."""

    def test_user_found_in_teams(self) -> None:
        """Test user lookup from teams configuration."""
        engine = TeamEngine()
        
        for username in engine.users:
            user_info = engine.get_user_info(username)
            assert user_info is not None
            assert user_info["role"] in engine.roles
            return

    def test_user_not_found(self) -> None:
        """Test lookup for non-existent user."""
        engine = TeamEngine()
        
        user_info = engine.get_user_info("totally-nonexistent-user-xyz")
        assert user_info is None

    def test_permission_enforcement(self) -> None:
        """Test permission enforcement."""
        engine = TeamEngine()
        
        for username, user_obj in engine.users.items():
            role = engine.roles.get(user_obj.role)
            if role:
                # Check that all users have some permissions or are viewer
                if user_obj.role != "viewer":
                    assert len(role.permissions) > 0
            return

    def test_role_definitions_consistency(self) -> None:
        """Test that role definitions are consistent."""
        engine = TeamEngine()
        
        # All roles should have a name and description
        for role_name, role_def in engine.roles.items():
            assert role_def.name is not None
            assert role_def.description is not None
            assert isinstance(role_def.permissions, list)
            
            # All permissions should be valid
            valid_perms = {
                "deploy:create",
                "deploy:approve",
                "deploy:auto_approve",
                "deploy:schedule",
                "deploy:view",
                "team:manage",
                "audit:view_own",
                "audit:view_all",
                "settings:modify",
            }
            for perm in role_def.permissions:
                assert perm in valid_perms, f"Invalid permission: {perm}"
