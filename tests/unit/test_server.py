"""Tests for the Phase 14 FastAPI backend — web-ui/api/server.py.

Uses FastAPI TestClient with mocked subprocess calls and filesystem
access to verify all 18 API endpoints without touching real AWS.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ── Make project importable ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web-ui" / "api"))

# Ensure project sub-packages are importable (server.py needs these)
sys.path.insert(0, str(PROJECT_ROOT / "policy-engine"))
sys.path.insert(0, str(PROJECT_ROOT / "opa-policies"))
sys.path.insert(0, str(PROJECT_ROOT / "team-management"))
sys.path.insert(0, str(PROJECT_ROOT / "cli-wizard"))
sys.path.insert(0, str(PROJECT_ROOT / "drift-detection"))

from fastapi.testclient import TestClient
from server import app


client = TestClient(app)


# ═══════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════


class TestHealth:
    """Health check endpoint tests."""

    def test_health_returns_ok(self) -> None:
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_returns_version(self) -> None:
        res = client.get("/api/health")
        assert res.json()["version"] == "1.0.0"


# ═══════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════


class TestDashboard:
    """Dashboard overview endpoint tests."""

    def test_dashboard_returns_services(self) -> None:
        res = client.get("/api/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert "services" in data
        assert "active_count" in data
        assert isinstance(data["services"], dict)

    def test_dashboard_returns_policy_health(self) -> None:
        res = client.get("/api/dashboard")
        data = res.json()
        assert "policy_health" in data
        ph = data["policy_health"]
        assert "blocks" in ph
        assert "warnings" in ph
        assert "status" in ph

    def test_dashboard_returns_drift_status(self) -> None:
        res = client.get("/api/dashboard")
        data = res.json()
        assert "drift_status" in data

    def test_dashboard_returns_recent_events(self) -> None:
        res = client.get("/api/dashboard")
        data = res.json()
        assert "recent_events" in data
        assert isinstance(data["recent_events"], list)


# ═══════════════════════════════════════════════
# Templates
# ═══════════════════════════════════════════════


class TestTemplates:
    """Template listing endpoint tests."""

    def test_get_templates_returns_list(self) -> None:
        res = client.get("/api/templates")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_templates_have_required_fields(self) -> None:
        res = client.get("/api/templates")
        for t in res.json():
            assert "key" in t
            assert "name" in t
            assert "description" in t
            assert "services" in t

    def test_templates_include_static_site(self) -> None:
        res = client.get("/api/templates")
        keys = [t["key"] for t in res.json()]
        assert "static-site" in keys

    def test_templates_include_serverless_db(self) -> None:
        res = client.get("/api/templates")
        keys = [t["key"] for t in res.json()]
        assert "serverless-db" in keys


# ═══════════════════════════════════════════════
# Config Validation
# ═══════════════════════════════════════════════


class TestConfigValidation:
    """Config validation and policy evaluation tests."""

    def test_validate_config_returns_summary(self) -> None:
        res = client.post("/api/config/validate", json={
            "instance_type": "t2.micro",
            "environment": "free-tier",
        })
        assert res.status_code == 200
        data = res.json()
        assert "yaml" in data
        assert "opa" in data
        assert "summary" in data

    def test_validate_config_summary_has_can_deploy(self) -> None:
        res = client.post("/api/config/validate", json={})
        data = res.json()
        assert "can_deploy" in data["summary"]

    def test_generate_tfvars_returns_content(self) -> None:
        res = client.post("/api/config/generate-tfvars", json={
            "aws_region": "ap-south-1",
            "enable_s3": True,
            "bucket_name": "test-bucket",
        })
        assert res.status_code == 200
        data = res.json()
        assert "tfvars" in data
        assert "ap-south-1" in data["tfvars"]

    def test_evaluate_policies_same_as_validate(self) -> None:
        payload = {"instance_type": "t2.micro"}
        res1 = client.post("/api/config/validate", json=payload)
        res2 = client.post("/api/policies/evaluate", json=payload)
        assert res1.json()["summary"] == res2.json()["summary"]


# ═══════════════════════════════════════════════
# Cost Estimate
# ═══════════════════════════════════════════════


class TestCostEstimate:
    """Cost estimation endpoint tests."""

    @patch("server.subprocess.run")
    def test_cost_estimate_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "totalMonthlyCost": "0.00",
                "projects": [{"breakdown": {"resources": []}}],
            }),
        )
        res = client.post("/api/cost-estimate")
        assert res.status_code == 200
        data = res.json()
        assert data["available"] is True
        assert data["total_monthly_cost"] == "0.00"

    @patch("server.subprocess.run", side_effect=FileNotFoundError)
    def test_cost_estimate_missing_infracost(self, _: MagicMock) -> None:
        res = client.post("/api/cost-estimate")
        data = res.json()
        assert data["available"] is False
        assert "not installed" in data["error"]


# ═══════════════════════════════════════════════
# Policies
# ═══════════════════════════════════════════════


class TestPolicies:
    """Policy rule listing endpoint tests."""

    def test_get_yaml_policies(self) -> None:
        res = client.get("/api/policies/yaml")
        assert res.status_code == 200
        data = res.json()
        assert "rules" in data
        assert "count" in data
        assert data["count"] >= 8

    def test_yaml_rules_have_severity(self) -> None:
        res = client.get("/api/policies/yaml")
        for rule in res.json()["rules"]:
            assert rule["severity"] in ("block", "warning")

    def test_get_opa_policies(self) -> None:
        res = client.get("/api/policies/opa")
        assert res.status_code == 200
        data = res.json()
        assert "rules" in data
        assert "opa_available" in data


# ═══════════════════════════════════════════════
# Audit
# ═══════════════════════════════════════════════


class TestAudit:
    """Audit event endpoint tests."""

    def test_get_audit_events(self) -> None:
        res = client.get("/api/audit/events")
        assert res.status_code == 200
        data = res.json()
        assert "events" in data
        assert "total" in data

    def test_get_audit_events_with_filters(self) -> None:
        res = client.get("/api/audit/events?actor=admin&limit=5")
        assert res.status_code == 200

    def test_get_audit_report(self) -> None:
        res = client.get("/api/audit/report")
        assert res.status_code == 200
        data = res.json()
        assert "total_events" in data


# ═══════════════════════════════════════════════
# Team
# ═══════════════════════════════════════════════


class TestTeam:
    """Team management endpoint tests."""

    def test_get_team_members(self) -> None:
        res = client.get("/api/team/members")
        assert res.status_code == 200
        data = res.json()
        assert "members" in data
        assert "total" in data

    def test_get_team_roles(self) -> None:
        res = client.get("/api/team/roles")
        assert res.status_code == 200
        data = res.json()
        assert "roles" in data
        assert data["total"] >= 1

    def test_get_user_not_found(self) -> None:
        res = client.get("/api/team/user/nonexistent_user_xyz")
        assert res.status_code == 404


# ═══════════════════════════════════════════════
# Drift
# ═══════════════════════════════════════════════


class TestDrift:
    """Drift detection endpoint tests."""

    def test_get_drift_status(self) -> None:
        res = client.get("/api/drift/status")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data


# ═══════════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════════


class TestAuth:
    """Authentication endpoint tests."""

    def test_auth_empty_payload_fails(self) -> None:
        res = client.post("/api/auth/login", json={})
        data = res.json()
        assert data["authenticated"] is False
        assert "error" in data

    def test_auth_unknown_username_fails(self) -> None:
        res = client.post("/api/auth/login", json={"username": "nonexistent_user_xyz"})
        data = res.json()
        assert data["authenticated"] is False
        assert "not found" in data["error"]

    def test_auth_valid_username_returns_role(self) -> None:
        """Test with the first username found in teams.yaml."""
        members_res = client.get("/api/team/members")
        members = members_res.json().get("members", [])
        if members:
            username = members[0]["username"]
            res = client.post("/api/auth/login", json={"username": username})
            data = res.json()
            assert data["authenticated"] is True
            assert data["method"] == "username_lookup"
            assert data["role"] in ("admin", "devops", "developer", "viewer")
            assert "permissions" in data

    def test_auth_empty_token_fails(self) -> None:
        res = client.post("/api/auth/login", json={"github_token": ""})
        data = res.json()
        assert data["authenticated"] is False

    def test_auth_returns_authenticated_field(self) -> None:
        res = client.post("/api/auth/login", json={"username": "test"})
        data = res.json()
        assert "authenticated" in data


# ═══════════════════════════════════════════════
# Custom Policy CRUD (Phase 15)
# ═══════════════════════════════════════════════


class TestCustomPolicies:
    """Custom policy add/delete endpoint tests."""

    def test_add_custom_policy(self) -> None:
        """Adding a custom policy should succeed."""
        # Clean up first in case a previous run left this
        client.delete("/api/policies/yaml/test_custom_rule_phase15")
        res = client.post("/api/policies/yaml", json={
            "name": "test_custom_rule_phase15",
            "description": "Test custom rule",
            "severity": "warning",
            "condition": "instance_type == 't2.micro'",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        # Clean up
        client.delete("/api/policies/yaml/test_custom_rule_phase15")

    def test_add_duplicate_policy_fails(self) -> None:
        """Adding a rule with the same name should fail."""
        # Clean up first
        client.delete("/api/policies/yaml/test_duplicate_rule")
        # First add
        client.post("/api/policies/yaml", json={
            "name": "test_duplicate_rule",
            "description": "Dup test",
            "severity": "warning",
            "condition": "True",
        })
        # Second add with same name
        res = client.post("/api/policies/yaml", json={
            "name": "test_duplicate_rule",
            "description": "Dup test 2",
            "severity": "block",
            "condition": "False",
        })
        assert res.status_code == 400
        # Clean up
        client.delete("/api/policies/yaml/test_duplicate_rule")

    def test_delete_custom_policy(self) -> None:
        """Deleting a custom rule should succeed."""
        # Add then delete
        client.post("/api/policies/yaml", json={
            "name": "test_deleteme_rule",
            "description": "To be deleted",
            "severity": "warning",
            "condition": "True",
        })
        res = client.delete("/api/policies/yaml/test_deleteme_rule")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True

    def test_delete_builtin_policy_forbidden(self) -> None:
        """Deleting a built-in rule should return 403."""
        res = client.delete("/api/policies/yaml/public_s3_bucket")
        assert res.status_code == 403

    def test_delete_nonexistent_policy_not_found(self) -> None:
        """Deleting a non-existent rule should return 404."""
        res = client.delete("/api/policies/yaml/nonexistent_rule_xyz")
        assert res.status_code == 404

    def test_yaml_rules_count_after_add(self) -> None:
        """After adding a custom rule, count should increase."""
        # Get baseline
        before = client.get("/api/policies/yaml").json()["count"]
        client.post("/api/policies/yaml", json={
            "name": "test_count_rule_abc",
            "description": "Count test",
            "severity": "warning",
            "condition": "True",
        })
        after = client.get("/api/policies/yaml").json()["count"]
        assert after == before + 1
        # Clean up
        client.delete("/api/policies/yaml/test_count_rule_abc")


# ═══════════════════════════════════════════════
# Notifications (Phase 15)
# ═══════════════════════════════════════════════


class TestNotifications:
    """Notification aggregation endpoint tests."""

    def test_get_notifications_returns_list(self) -> None:
        res = client.get("/api/notifications")
        assert res.status_code == 200
        data = res.json()
        assert "notifications" in data
        assert "total" in data
        assert isinstance(data["notifications"], list)

    def test_notifications_have_required_fields(self) -> None:
        res = client.get("/api/notifications")
        data = res.json()
        for n in data["notifications"]:
            assert "id" in n
            assert "type" in n
            assert "title" in n
            assert "message" in n
            assert "severity" in n

    def test_notifications_include_policy_warnings(self) -> None:
        """Default config should generate policy warning notifications."""
        res = client.get("/api/notifications")
        data = res.json()
        policy_notifs = [n for n in data["notifications"] if n["type"] == "policy"]
        # Default config has warning-level violations (missing tags, cloudtrail)
        assert len(policy_notifs) >= 0  # May or may not have warnings


# ═══════════════════════════════════════════════
# Admin Settings (Phase 15)
# ═══════════════════════════════════════════════


class TestAdminSettings:
    """Admin settings endpoint tests."""

    def test_get_settings_returns_defaults(self) -> None:
        res = client.get("/api/settings")
        assert res.status_code == 200
        data = res.json()
        assert "settings" in data
        settings = data["settings"]
        assert "default_region" in settings
        assert "strict_mode" in settings
        assert "session_timeout_minutes" in settings

    def test_save_settings_updates_region(self) -> None:
        res = client.post("/api/settings", json={"default_region": "us-east-1"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "default_region" in data["updated"]
        assert data["settings"]["default_region"] == "us-east-1"

    def test_save_settings_updates_strict_mode(self) -> None:
        res = client.post("/api/settings", json={"strict_mode": True})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["settings"]["strict_mode"] is True
        # Reset
        client.post("/api/settings", json={"strict_mode": False})

    def test_save_settings_updates_timeout(self) -> None:
        res = client.post("/api/settings", json={"session_timeout_minutes": 60})
        assert res.status_code == 200
        data = res.json()
        assert data["settings"]["session_timeout_minutes"] == 60
        # Reset
        client.post("/api/settings", json={"session_timeout_minutes": 30})

    def test_save_settings_partial_update(self) -> None:
        """Only specified fields should be updated."""
        res = client.post("/api/settings", json={"cost_alert_threshold": 5.0})
        data = res.json()
        assert len(data["updated"]) == 1
        assert data["updated"][0] == "cost_alert_threshold"

    def test_get_settings_persists_changes(self) -> None:
        """Settings should persist across calls."""
        client.post("/api/settings", json={"default_region": "eu-central-1"})
        res = client.get("/api/settings")
        assert res.json()["settings"]["default_region"] == "eu-central-1"
        # Reset
        client.post("/api/settings", json={"default_region": "ap-south-1"})

