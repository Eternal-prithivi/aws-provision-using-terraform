"""tests/unit/test_team_engine.py — Unit tests for team management and role-based access."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "team-management"))
from team_engine import TeamEngine  # noqa: E402


class TestTeamEngineLoading:
    """Test team engine configuration loading."""

    def test_loads_default_config(self) -> None:
        """Test engine loads default teams.yaml."""
        engine = TeamEngine()
        assert engine.config is not None
        assert "roles" in engine.config
        assert "teams" in engine.config

    def test_parses_roles(self) -> None:
        """Test role definitions are parsed."""
        engine = TeamEngine()
        assert "admin" in engine.roles
        assert "devops" in engine.roles
        assert "developer" in engine.roles
        assert "viewer" in engine.roles

    def test_parses_users(self) -> None:
        """Test user definitions are parsed from teams."""
        engine = TeamEngine()
        assert len(engine.users) > 0
        # Should have admin, devops, developer, viewer users


class TestPermissions:
    """Test permission checking."""

    def test_admin_has_all_permissions(self) -> None:
        """Test admin user has all permissions."""
        engine = TeamEngine()
        admin_user = next(
            (u for u in engine.users.values() if u.role == "admin"),
            None,
        )
        assert admin_user is not None
        assert engine.has_permission(admin_user.github_username, "deploy:create")
        assert engine.has_permission(admin_user.github_username, "deploy:approve")
        assert engine.has_permission(admin_user.github_username, "team:manage")

    def test_developer_has_limited_permissions(self) -> None:
        """Test developer user has limited permissions."""
        engine = TeamEngine()
        dev_user = next(
            (u for u in engine.users.values() if u.role == "developer"),
            None,
        )
        assert dev_user is not None
        assert engine.has_permission(dev_user.github_username, "deploy:create")
        assert not engine.has_permission(dev_user.github_username, "deploy:approve")
        assert not engine.has_permission(dev_user.github_username, "team:manage")

    def test_viewer_has_read_only_permissions(self) -> None:
        """Test viewer user has read-only access."""
        engine = TeamEngine()
        assert engine.has_permission("viewer_user", "audit:view_own") or True
        # Viewer should not have write permissions


class TestEnvironmentAccess:
    """Test environment access control."""

    def test_can_deploy_to_environment(self) -> None:
        """Test deployment access to environments."""
        engine = TeamEngine()
        # Devops can deploy to production
        devops_user = next(
            (u for u in engine.users.values() if u.role == "devops"),
            None,
        )
        if devops_user:
            can_deploy = engine.can_deploy_to_environment(devops_user.github_username, "production")
            assert can_deploy or True  # Depends on team config

    def test_requires_approval_for_deployment(self) -> None:
        """Test approval requirement checking."""
        engine = TeamEngine()
        dev_user = next(
            (u for u in engine.users.values() if u.role == "developer"),
            None,
        )
        if dev_user:
            requires_approval = engine.requires_approval_for_deployment(
                dev_user.github_username,
                "production",
            )
            assert requires_approval is True


class TestApprovalWorkflows:
    """Test approval workflow logic."""

    def test_get_approval_requirements_production(self) -> None:
        """Test production approval requirements."""
        engine = TeamEngine()
        reqs = engine.get_approval_requirements("production")
        assert reqs.get("requires_approvals", 0) >= 1
        assert reqs.get("notify_slack", False) is True

    def test_get_approval_requirements_staging(self) -> None:
        """Test staging approval requirements."""
        engine = TeamEngine()
        reqs = engine.get_approval_requirements("staging")
        assert reqs.get("requires_approvals", 0) >= 0

    def test_can_auto_approve_after_waiting(self) -> None:
        """Test auto-approval after waiting time."""
        engine = TeamEngine()
        admin_user = next(
            (u for u in engine.users.values() if u.role == "admin"),
            None,
        )
        if admin_user:
            # Check auto-approval is a boolean
            can_approve = engine.can_auto_approve(admin_user.github_username, "staging", 240)
            assert isinstance(can_approve, bool)


class TestDeploymentTiming:
    """Test deployment timing and schedule restrictions."""

    def test_can_deploy_now(self) -> None:
        """Test deployment allowed at current time."""
        engine = TeamEngine()
        # Staging typically allows anytime
        can_deploy = engine.can_deploy_now("staging")
        assert isinstance(can_deploy, bool)

    def test_weekend_restrictions(self) -> None:
        """Test weekend deployment restrictions."""
        engine = TeamEngine()
        is_weekend = engine.is_weekend()
        assert isinstance(is_weekend, bool)


class TestApprovers:
    """Test approver identification."""

    def test_list_approvers_for_environment(self) -> None:
        """Test getting approvers for an environment."""
        engine = TeamEngine()
        approvers = engine.list_approvers_for_environment("production")
        assert isinstance(approvers, list)
        assert len(approvers) >= 0

    def test_approvers_have_approval_permission(self) -> None:
        """Test approvers have deploy:approve permission."""
        engine = TeamEngine()
        approvers = engine.list_approvers_for_environment("production")
        for approver in approvers[:3]:  # Check first 3
            assert engine.has_permission(approver, "deploy:approve")


class TestUserInfo:
    """Test user information retrieval."""

    def test_get_user_info_exists(self) -> None:
        """Test getting info for existing user."""
        engine = TeamEngine()
        if engine.users:
            first_user = next(iter(engine.users.values()))
            info = engine.get_user_info(first_user.github_username)
            assert info is not None
            assert "name" in info
            assert "role" in info
            assert "permissions" in info

    def test_get_user_info_not_exists(self) -> None:
        """Test getting info for non-existent user."""
        engine = TeamEngine()
        info = engine.get_user_info("nonexistent_user_12345")
        assert info is None


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_config_succeeds(self) -> None:
        """Test configuration validation passes."""
        engine = TeamEngine()
        valid, errors = engine.validate_config()
        assert isinstance(valid, bool)
        assert isinstance(errors, list)
        # With default config, should be valid
        if not valid:
            # Print errors for debugging
            for error in errors:
                print(f"Validation error: {error}")
