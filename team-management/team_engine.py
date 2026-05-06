#!/usr/bin/env python3
"""team-management/team_engine.py — Role-based access control and team management.

This module manages teams, roles, permissions, and approval workflows for multi-user
infrastructure deployments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class Permission(Enum):
    """Enumeration of available permissions."""

    DEPLOY_CREATE = "deploy:create"
    DEPLOY_APPROVE = "deploy:approve"
    DEPLOY_AUTO_APPROVE = "deploy:auto_approve"
    DEPLOY_SCHEDULE = "deploy:schedule"
    DEPLOY_VIEW = "deploy:view"
    TEAM_MANAGE = "team:manage"
    AUDIT_VIEW_OWN = "audit:view_own"
    AUDIT_VIEW_ALL = "audit:view_all"
    SETTINGS_MODIFY = "settings:modify"


@dataclass(slots=True)
class User:
    """Represents a team member with role and permissions."""

    name: str
    email: str
    role: str
    github_username: str
    teams: list[str]


@dataclass(slots=True)
class RoleDefinition:
    """Defines a role and its permissions."""

    name: str
    description: str
    permissions: list[str]
    auto_approve_threshold: int | None
    requires_approval: bool | None
    max_per_day: int | None


@dataclass(slots=True)
class ApprovalRequest:
    """Represents a deployment approval request."""

    deployment_id: str
    requester: str
    environment: str
    timestamp: datetime
    status: str  # pending, approved, rejected, auto_approved
    approvers: list[str]
    auto_approve_eligible: bool
    auto_approve_after: datetime | None


class TeamEngine:
    """Manages teams, roles, and permissions for infrastructure deployments."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize team engine with configuration."""
        if config_path is None:
            config_path = Path(__file__).resolve().parent / "teams.yaml"
        
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.roles: dict[str, RoleDefinition] = {}
        self.users: dict[str, User] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load team configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}
        
        self._parse_roles()
        self._parse_users()

    def _parse_roles(self) -> None:
        """Parse role definitions from configuration."""
        for role_name, role_def in self.config.get("roles", {}).items():
            self.roles[role_name] = RoleDefinition(
                name=role_def.get("name", role_name),
                description=role_def.get("description", ""),
                permissions=role_def.get("permissions", []),
                auto_approve_threshold=role_def.get("auto_approve_threshold"),
                requires_approval=role_def.get("requires_approval"),
                max_per_day=role_def.get("max_per_day"),
            )

    def _parse_users(self) -> None:
        """Parse user definitions from teams configuration."""
        for team_name, team_data in self.config.get("teams", {}).items():
            for member in team_data.get("members", []):
                username = member.get("github_username", member.get("name"))
                self.users[username] = User(
                    name=member.get("name", ""),
                    email=member.get("email", ""),
                    role=member.get("role", "viewer"),
                    github_username=username,
                    teams=[team_name],
                )

    def has_permission(self, user: str, permission: str) -> bool:
        """Check if user has a specific permission."""
        if user not in self.users:
            return False
        
        user_obj = self.users[user]
        role = self.roles.get(user_obj.role)
        
        if not role:
            return False
        
        return permission in role.permissions

    def can_deploy_to_environment(self, user: str, environment: str) -> bool:
        """Check if user can deploy to a specific environment."""
        if user not in self.users:
            return False
        
        user_obj = self.users[user]
        
        # Check if user's team has permission for environment
        for team_name in user_obj.teams:
            team_data = self.config.get("teams", {}).get(team_name, {})
            permissions = team_data.get("permissions", [])
            
            if f"deploy:{environment}" in permissions:
                return True
        
        return False

    def requires_approval_for_deployment(self, user: str, environment: str) -> bool:
        """Check if deployment requires approval."""
        if user not in self.users:
            return True  # Default to requiring approval
        
        user_obj = self.users[user]
        role = self.roles.get(user_obj.role)
        
        if not role:
            return True
        
        return role.requires_approval or False

    def get_approval_requirements(self, environment: str) -> dict[str, Any]:
        """Get approval workflow requirements for an environment."""
        workflow_key = environment if environment in ["production", "staging"] else "staging"
        workflows = self.config.get("approval_workflows", {})
        
        return workflows.get(workflow_key, {
            "requires_approvals": 1,
            "approvers_must_include": ["devops"],
            "notify_slack": True,
        })

    def can_auto_approve(self, user: str, environment: str, wait_time_minutes: int) -> bool:
        """Check if deployment can be auto-approved after waiting time."""
        requirements = self.get_approval_requirements(environment)
        auto_approve_hours = requirements.get("auto_approve_after_hours", 480)
        
        return wait_time_minutes >= auto_approve_hours

    def is_weekend(self) -> bool:
        """Check if current time is weekend."""
        today = datetime.now(tz=timezone.utc).weekday()
        return today >= 5  # Saturday = 5, Sunday = 6

    def is_holiday(self) -> bool:
        """Check if current date is a holiday (simplified check)."""
        # This is a placeholder - extend with actual holiday calendar
        return False

    def can_deploy_now(self, environment: str) -> bool:
        """Check if deployments are allowed at current time."""
        requirements = self.get_approval_requirements(environment)
        
        if self.is_weekend() and not requirements.get("allow_weekend_deploy", True):
            return False
        
        if self.is_holiday() and not requirements.get("allow_holiday_deploy", True):
            return False
        
        return True

    def get_user_info(self, username: str) -> dict[str, Any] | None:
        """Get information about a user."""
        if username not in self.users:
            return None
        
        user = self.users[username]
        role = self.roles.get(user.role)
        
        return {
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "role_name": role.name if role else "Unknown",
            "teams": user.teams,
            "permissions": role.permissions if role else [],
        }

    def save_config(self) -> None:
        """Persist current `self.config` to the config file path.

        This will make a timestamped backup of the existing file before
        writing, then rewrite the YAML from the in-memory `self.config`.
        """
        bak = self.config_path.with_suffix(self.config_path.suffix + f".bak.{int(datetime.now(tz=timezone.utc).timestamp())}")
        # Backup existing file
        try:
            if self.config_path.exists():
                with open(self.config_path, "rb") as src, open(bak, "wb") as dst:
                    dst.write(src.read())
        except Exception:
            # If backup fails, continue but log is omitted here to keep simple
            pass

        # Write the YAML file
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f, sort_keys=False)

    def list_approvers_for_environment(self, environment: str) -> list[str]:
        """Get list of users who can approve deployments for an environment."""
        approvers = []
        requirements = self.get_approval_requirements(environment)
        required_roles = requirements.get("approvers_must_include", ["devops"])
        
        for username, user in self.users.items():
            if user.role in required_roles:
                approvers.append(username)
        
        return approvers

    def get_slack_channel_for_team(self, team_name: str) -> str | None:
        """Get Slack channel for a team."""
        team_data = self.config.get("teams", {}).get(team_name)
        return team_data.get("slack_channel") if team_data else None

    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate configuration for consistency."""
        errors = []
        
        # Check all referenced roles exist
        for team_name, team_data in self.config.get("teams", {}).items():
            for member in team_data.get("members", []):
                role = member.get("role")
                if role not in self.roles:
                    errors.append(f"Team '{team_name}': Unknown role '{role}'")
        
        # Check approval workflow roles exist
        for env, workflow in self.config.get("approval_workflows", {}).items():
            for role in workflow.get("approvers_must_include", []):
                if role not in self.roles:
                    errors.append(f"Workflow '{env}': Unknown role '{role}'")
        
        return len(errors) == 0, errors


class RoleGate:
    """Enforces role-based access to wizard functions."""

    def __init__(self, engine: TeamEngine) -> None:
        """Initialize with team engine instance."""
        self.engine = engine

    def check_can_deploy(self, username: str, environment: str) -> tuple[bool, str]:
        """Check if user can deploy to environment.
        
        Args:
            username: GitHub username
            environment: Target environment (staging/production)
            
        Returns:
            (can_deploy, message)
        """
        user_info = self.engine.get_user_info(username)
        
        if not user_info:
            return False, f"❌ User '{username}' not found in team configuration"

        role = user_info.get("role")
        permissions = user_info.get("permissions", [])

        if "deploy:create" not in permissions:
            return False, f"❌ Role '{role}' cannot create deployments"

        if environment == "production":
            can_deploy = self.engine.can_deploy_to_environment(username, "production")
            if not can_deploy:
                return False, f"❌ Role '{role}' cannot deploy to production"

        return True, f"✅ User '{username}' ({role}) allowed"

    def get_allowed_environments(self, username: str) -> list[str]:
        """Get list of environments user can deploy to.
        
        Args:
            username: GitHub username
            
        Returns:
            List of allowed environments
        """
        environments = []
        for env in ["staging", "production"]:
            if self.engine.can_deploy_to_environment(username, env):
                environments.append(env)
        return environments or ["staging"]

    def show_role_summary(self, username: str) -> None:
        """Display user's role and permissions.
        
        Args:
            username: GitHub username
        """
        user_info = self.engine.get_user_info(username)
        
        if not user_info:
            print(f"  ⚠️  User '{username}' not found in team configuration")
            return

        print("\n" + "=" * 60)
        print(f"  👤 Authenticated: {user_info['name']}")
        print("=" * 60)
        print(f"  Role: {user_info['role_name']}")
        print(f"  Teams: {', '.join(user_info['teams'])}")
        print(f"  Environments: {', '.join(self.get_allowed_environments(username))}")
        print("=" * 60)
        print()


def build_parser() -> Any:
    """Build argument parser for CLI."""
    import argparse
    parser = argparse.ArgumentParser(description="Team management and access control.")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to teams.yaml configuration file.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate team configuration.",
    )
    parser.add_argument(
        "--user",
        help="Check permissions for a specific user.",
    )
    parser.add_argument(
        "--permission",
        help="Permission to check.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for team management."""
    parser = build_parser()
    args = parser.parse_args(argv)
    
    engine = TeamEngine(config_path=args.config)
    
    if args.validate:
        valid, errors = engine.validate_config()
        if valid:
            print("✅ Configuration is valid")
            return 0
        else:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return 1
    
    if args.user and args.permission:
        has_perm = engine.has_permission(args.user, args.permission)
        status = "✅ Yes" if has_perm else "❌ No"
        print(f"{status} — {args.user} has '{args.permission}'")
        return 0 if has_perm else 1
    
    if args.user:
        info = engine.get_user_info(args.user)
        if info:
            print(f"User: {info['name']}")
            print(f"Email: {info['email']}")
            print(f"Role: {info['role_name']}")
            print(f"Teams: {', '.join(info['teams'])}")
            print(f"Permissions: {', '.join(info['permissions'])}")
            return 0
        else:
            print(f"❌ User '{args.user}' not found")
            return 1
    
    print(parser.format_help())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
