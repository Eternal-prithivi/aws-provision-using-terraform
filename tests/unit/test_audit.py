"""tests/unit/test_audit.py — Unit tests for audit logging."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "team-management"))
from audit import AuditLogger  # noqa: E402


class TestAuditLogging:
    """Test audit event logging."""

    def test_creates_audit_log_file(self, tmp_path: Path) -> None:
        """Test audit logger creates log file."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        assert log_file.parent.exists()

    def test_logs_deployment_event(self, tmp_path: Path) -> None:
        """Test logging a deployment event."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        event = logger.log_event(
            action="deploy",
            actor="alice-chen",
            environment="production",
            deployment_id="deploy-001",
            status="success",
            details={"resources": 5},
        )
        
        assert event.event_id is not None
        assert event.action == "deploy"
        assert event.actor == "alice-chen"
        assert log_file.exists()

    def test_logs_approval_event(self, tmp_path: Path) -> None:
        """Test logging an approval event."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        event = logger.log_event(
            action="approve",
            actor="bob-martinez",
            environment="production",
            deployment_id="deploy-001",
            status="pending",
            reason="Security review passed",
        )
        
        assert event.action == "approve"
        assert event.reason == "Security review passed"


class TestAuditReading:
    """Test reading audit events."""

    def test_read_events_empty_log(self, tmp_path: Path) -> None:
        """Test reading from empty log."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        events = logger.read_events()
        assert events == []

    def test_read_events_with_filtering(self, tmp_path: Path) -> None:
        """Test reading with filters."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        # Log multiple events
        logger.log_event("deploy", "alice", "production", "deploy-001", "success")
        logger.log_event("deploy", "alice", "staging", "deploy-002", "success")
        logger.log_event("approve", "bob", "production", "deploy-001", "success")
        
        # Read only deployment events
        deploy_events = logger.read_events(action="deploy")
        assert len(deploy_events) == 2
        
        # Read only Alice's events
        alice_events = logger.read_events(actor="alice")
        assert len(alice_events) == 2

    def test_read_events_with_limit(self, tmp_path: Path) -> None:
        """Test reading with limit."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        # Log 5 events
        for i in range(5):
            logger.log_event("deploy", f"user{i}", "staging", f"deploy-{i:03d}", "success")
        
        # Read with limit
        events = logger.read_events(limit=2)
        assert len(events) == 2


class TestDeploymentHistory:
    """Test deployment-specific history tracking."""

    def test_get_deployment_history(self, tmp_path: Path) -> None:
        """Test retrieving history for specific deployment."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        # Log events for same deployment
        logger.log_event("deploy", "alice", "production", "deploy-001", "pending")
        logger.log_event("approve", "bob", "production", "deploy-001", "approved")
        logger.log_event("execute", "alice", "production", "deploy-001", "success")
        
        # Get history
        history = logger.get_deployment_history("deploy-001")
        assert len(history) == 3
        assert history[0].action == "deploy"

    def test_get_deployment_history_empty(self, tmp_path: Path) -> None:
        """Test deployment history when no events exist."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        history = logger.get_deployment_history("nonexistent-001")
        assert history == []


class TestUserActions:
    """Test user action tracking."""

    def test_get_user_actions(self, tmp_path: Path) -> None:
        """Test retrieving actions by specific user."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        # Log actions from different users
        logger.log_event("deploy", "alice", "production", "deploy-001", "success")
        logger.log_event("approve", "bob", "production", "deploy-001", "success")
        logger.log_event("deploy", "alice", "staging", "deploy-002", "success")
        
        # Get Alice's actions
        alice_actions = logger.get_user_actions("alice")
        assert len(alice_actions) == 2
        assert all(event.actor == "alice" for event in alice_actions)


class TestEnvironmentHistory:
    """Test environment-specific history tracking."""

    def test_get_environment_history(self, tmp_path: Path) -> None:
        """Test retrieving history for specific environment."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        # Log events from different environments
        logger.log_event("deploy", "alice", "production", "deploy-001", "success")
        logger.log_event("deploy", "alice", "staging", "deploy-002", "success")
        logger.log_event("deploy", "bob", "production", "deploy-003", "success")
        
        # Get production history
        prod_history = logger.get_environment_history("production")
        assert len(prod_history) == 2
        assert all(event.environment == "production" for event in prod_history)


class TestAuditReport:
    """Test audit reporting."""

    def test_generate_report_empty(self, tmp_path: Path) -> None:
        """Test report generation on empty log."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        report = logger.generate_report()
        assert report["total_events"] == 0
        assert report["by_action"] == {}

    def test_generate_report_with_events(self, tmp_path: Path) -> None:
        """Test report generation with events."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log_file)
        
        # Log various events
        logger.log_event("deploy", "alice", "production", "deploy-001", "success")
        logger.log_event("approve", "bob", "production", "deploy-001", "success")
        logger.log_event("deploy", "alice", "staging", "deploy-002", "pending")
        
        report = logger.generate_report()
        assert report["total_events"] == 3
        assert report["by_action"]["deploy"] == 2
        assert report["by_action"]["approve"] == 1
        assert report["by_actor"]["alice"] == 2
        assert report["by_status"]["success"] == 2
        assert report["by_environment"]["production"] == 2
