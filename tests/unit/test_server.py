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
        assert data["count"] == 8

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

