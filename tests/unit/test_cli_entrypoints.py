"""tests/unit/test_cli_entrypoints.py — Tests for CLI main() and build_parser() functions.

Covers the CLI entry points in:
- drift-detection/remediation.py (build_parser, main)
- team-management/audit.py (build_parser, main)
- team-management/team_engine.py (build_parser, main)
- opa-policies/opa_engine.py (_run_opa_query edge cases)
- policy-engine/engine.py (report)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Path setup ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "drift-detection"))
sys.path.insert(0, str(PROJECT_ROOT / "team-management"))
sys.path.insert(0, str(PROJECT_ROOT / "opa-policies"))
sys.path.insert(0, str(PROJECT_ROOT / "policy-engine"))

from remediation import build_parser as rem_build_parser, main as rem_main  # noqa: E402
from audit import build_parser as audit_build_parser, main as audit_main, AuditLogger  # noqa: E402
from team_engine import build_parser as team_build_parser, main as team_main, TeamEngine  # noqa: E402
from opa_engine import OPAEngine, OPAResult  # noqa: E402
from engine import PolicyEngine, EvaluationResult, Violation  # noqa: E402


# ═══════════════════════════════════════════════════
# Remediation CLI
# ═══════════════════════════════════════════════════

class TestRemediationCLI:
    def test_build_parser_returns_parser(self) -> None:
        parser = rem_build_parser()
        assert parser is not None

    def test_build_parser_defaults(self) -> None:
        parser = rem_build_parser()
        args = parser.parse_args([])
        assert args.apply is False
        assert args.auto_approve is False
        assert args.terraform_binary == "terraform"

    def test_build_parser_with_apply_flag(self) -> None:
        parser = rem_build_parser()
        args = parser.parse_args(["--apply", "--auto-approve"])
        assert args.apply is True
        assert args.auto_approve is True

    @patch("remediation.remediate_drift")
    def test_main_calls_remediate(self, mock_rem) -> None:
        mock_rem.return_value = MagicMock(success=True, message="OK", report_path="/tmp/r.txt")
        result = rem_main(["--apply", "--auto-approve"])
        assert result == 0
        mock_rem.assert_called_once()

    @patch("remediation.remediate_drift")
    def test_main_returns_1_on_failure(self, mock_rem) -> None:
        mock_rem.return_value = MagicMock(success=False, message="FAIL", report_path="/tmp/r.txt")
        result = rem_main([])
        assert result == 1

    @patch("remediation.run_command")
    def test_apply_failure_returns_failed_result(self, mock_cmd, tmp_path) -> None:
        """Test that terraform apply failure is properly handled."""
        from remediation import remediate_drift
        report = tmp_path / "drift-report.txt"
        # Must contain keywords the parser looks for
        report.write_text("Status: DRIFT DETECTED\n+1 to create, ~0 to update\nmodule.billing will be created")
        
        # First call (init) succeeds, second call (apply) fails
        mock_cmd.side_effect = [
            MagicMock(returncode=0, stdout="init ok", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="apply error"),
        ]
        
        result = remediate_drift(
            project_root=tmp_path,
            report_file=report,
            check_only=False,
            auto_approve=True,
        )
        assert result.success is False
        assert "failed" in result.message.lower()


# ═══════════════════════════════════════════════════
# Audit CLI
# ═══════════════════════════════════════════════════

class TestAuditCLI:
    def test_build_parser_returns_parser(self) -> None:
        parser = audit_build_parser()
        assert parser is not None

    def test_build_parser_with_actor(self) -> None:
        parser = audit_build_parser()
        args = parser.parse_args(["--actor", "admin"])
        assert args.actor == "admin"

    def test_build_parser_with_report_flag(self) -> None:
        parser = audit_build_parser()
        args = parser.parse_args(["--report"])
        assert args.report is True

    def test_main_default_shows_events(self, tmp_path) -> None:
        log = tmp_path / "audit.jsonl"
        result = audit_main(["--log-file", str(log)])
        assert result == 0

    def test_main_deployment_filter(self, tmp_path) -> None:
        log = tmp_path / "audit.jsonl"
        result = audit_main(["--deployment", "dep-123", "--log-file", str(log)])
        assert result == 0

    def test_main_user_filter(self, tmp_path) -> None:
        log = tmp_path / "audit.jsonl"
        result = audit_main(["--user", "admin", "--log-file", str(log)])
        assert result == 0

    def test_main_report(self, tmp_path) -> None:
        log = tmp_path / "audit.jsonl"
        result = audit_main(["--report", "--log-file", str(log)])
        assert result == 0

    def test_main_report_with_events(self, tmp_path) -> None:
        log = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log)
        logger.log_event("deploy", "admin", "prod", "d-1", "success")
        logger.log_event("approve", "mgr", "staging", "d-2", "pending")
        result = audit_main(["--report", "--log-file", str(log)])
        assert result == 0

    def test_main_deployment_with_events(self, tmp_path) -> None:
        log = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log)
        logger.log_event("deploy", "admin", "prod", "d-100", "success")
        result = audit_main(["--deployment", "d-100", "--log-file", str(log)])
        assert result == 0

    def test_main_user_with_events(self, tmp_path) -> None:
        log = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log)
        logger.log_event("deploy", "testuser", "prod", "d-1", "success")
        logger.log_event("deploy", "testuser", "staging", "d-2", "success")
        result = audit_main(["--user", "testuser", "--log-file", str(log)])
        assert result == 0

    def test_empty_lines_in_log_are_skipped(self, tmp_path) -> None:
        """Ensure blank lines in audit.jsonl are handled gracefully."""
        log = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log)
        logger.log_event("deploy", "admin", "prod", "d-1", "success")
        # Inject blank lines
        with open(log, "a") as f:
            f.write("\n\n")
        events = logger.read_events()
        assert len(events) == 1

    def test_generate_report_date_filtering(self, tmp_path) -> None:
        """Test that generate_report respects start_date and end_date."""
        from datetime import datetime, timezone, timedelta
        log = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file=log)
        logger.log_event("deploy", "admin", "prod", "d-1", "success")

        far_future = datetime.now(tz=timezone.utc) + timedelta(days=365)
        report = logger.generate_report(start_date=far_future)
        assert report["total_events"] == 0

        far_past = datetime.now(tz=timezone.utc) - timedelta(days=365)
        report2 = logger.generate_report(end_date=far_past)
        assert report2["total_events"] == 0


# ═══════════════════════════════════════════════════
# Team Engine CLI
# ═══════════════════════════════════════════════════

class TestTeamEngineCLI:
    def test_build_parser_returns_parser(self) -> None:
        parser = team_build_parser()
        assert parser is not None

    def test_build_parser_with_validate(self) -> None:
        parser = team_build_parser()
        args = parser.parse_args(["--validate"])
        assert args.validate is True

    def test_build_parser_with_user_and_permission(self) -> None:
        parser = team_build_parser()
        args = parser.parse_args(["--user", "admin", "--permission", "deploy"])
        assert args.user == "admin"
        assert args.permission == "deploy"

    def test_main_validate(self) -> None:
        result = team_main(["--validate"])
        assert result == 0

    def test_main_user_info(self) -> None:
        # Uses actual GitHub username from teams.yaml
        result = team_main(["--user", "Eternal-prithivi"])
        assert result == 0

    def test_main_user_not_found(self) -> None:
        result = team_main(["--user", "nonexistent_user_xyz"])
        assert result == 1

    def test_main_user_permission_check_granted(self) -> None:
        # Admin (Eternal-prithivi) has 'deploy:create' permission
        result = team_main(["--user", "Eternal-prithivi", "--permission", "deploy:create"])
        assert result == 0

    def test_main_user_permission_check_denied(self) -> None:
        result = team_main(["--user", "Eternal-prithivi", "--permission", "nonexistent_perm_xyz"])
        assert result == 1

    def test_main_no_args_shows_help(self) -> None:
        result = team_main([])
        assert result == 0

    def test_get_user_info_valid(self) -> None:
        engine = TeamEngine()
        info = engine.get_user_info("Eternal-prithivi")
        assert info is not None
        assert info["role_name"] == "Administrator"

    def test_get_user_info_invalid(self) -> None:
        engine = TeamEngine()
        info = engine.get_user_info("nonexistent_user_xyz")
        assert info is None


# ═══════════════════════════════════════════════════
# OPA Engine — _run_opa_query edge cases
# ═══════════════════════════════════════════════════

class TestOPAQueryEdgeCases:
    POLICIES_DIR = str(PROJECT_ROOT / "opa-policies")

    @patch("subprocess.run")
    @patch.object(OPAEngine, "is_opa_available", return_value=True)
    def test_run_opa_query_returns_empty_on_nonzero_exit(self, _avail, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        engine = OPAEngine(self.POLICIES_DIR)
        result = engine._run_opa_query("data.aws.security.deny", {})
        assert result == []

    @patch("subprocess.run")
    @patch.object(OPAEngine, "is_opa_available", return_value=True)
    def test_run_opa_query_returns_empty_on_no_results(self, _avail, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"result": []}))
        engine = OPAEngine(self.POLICIES_DIR)
        result = engine._run_opa_query("data.aws.security.deny", {})
        assert result == []

    @patch("subprocess.run")
    @patch.object(OPAEngine, "is_opa_available", return_value=True)
    def test_run_opa_query_returns_empty_on_no_expressions(self, _avail, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"result": [{"expressions": []}]})
        )
        engine = OPAEngine(self.POLICIES_DIR)
        result = engine._run_opa_query("data.aws.security.deny", {})
        assert result == []

    @patch("subprocess.run")
    @patch.object(OPAEngine, "is_opa_available", return_value=True)
    def test_run_opa_query_returns_values(self, _avail, mock_run) -> None:
        opa_output = {"result": [{"expressions": [{"value": ["block1", "block2"]}]}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(opa_output))
        engine = OPAEngine(self.POLICIES_DIR)
        result = engine._run_opa_query("data.aws.security.deny", {})
        assert result == ["block1", "block2"]

    @patch("subprocess.run")
    @patch.object(OPAEngine, "is_opa_available", return_value=True)
    def test_run_opa_query_handles_timeout(self, _avail, mock_run) -> None:
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="opa", timeout=30)
        engine = OPAEngine(self.POLICIES_DIR)
        result = engine._run_opa_query("data.aws.security.deny", {})
        assert result == []

    @patch("subprocess.run")
    @patch.object(OPAEngine, "is_opa_available", return_value=True)
    def test_run_opa_query_handles_json_error(self, _avail, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="not valid json")
        engine = OPAEngine(self.POLICIES_DIR)
        result = engine._run_opa_query("data.aws.security.deny", {})
        assert result == []

    def test_report_prints_error_message(self, capsys) -> None:
        engine = OPAEngine(self.POLICIES_DIR)
        result = OPAResult(opa_available=True, error="Policy file not found")
        engine.report(result)
        captured = capsys.readouterr()
        assert "Policy file not found" in captured.out

    def test_report_prints_blocks_and_warnings(self, capsys) -> None:
        engine = OPAEngine(self.POLICIES_DIR)
        result = OPAResult(blocks=["BLOCK: test"], warnings=["WARN: test"])
        engine.report(result)
        captured = capsys.readouterr()
        assert "BLOCK" in captured.out
        assert "WARN" in captured.out


# ═══════════════════════════════════════════════════
# Policy Engine — report() coverage
# ═══════════════════════════════════════════════════

class TestPolicyEngineReport:
    RULES_PATH = str(PROJECT_ROOT / "policy-engine" / "rules.yaml")

    def test_report_clean_result(self, capsys) -> None:
        engine = PolicyEngine(self.RULES_PATH)
        result = EvaluationResult()
        engine.report(result)
        captured = capsys.readouterr()
        assert "PASSED" in captured.out

    def test_report_with_blocks(self, capsys) -> None:
        engine = PolicyEngine(self.RULES_PATH)
        result = EvaluationResult(
            violations=[Violation("test_rule", "test desc", "block")]
        )
        engine.report(result)
        captured = capsys.readouterr()
        assert "BLOCK" in captured.out

    def test_report_with_warnings(self, capsys) -> None:
        engine = PolicyEngine(self.RULES_PATH)
        result = EvaluationResult(
            warnings=[Violation("test_warn", "test warn desc", "warning")]
        )
        engine.report(result)
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_report_with_blocks_and_warnings(self, capsys) -> None:
        engine = PolicyEngine(self.RULES_PATH)
        result = EvaluationResult(
            violations=[Violation("r1", "desc1", "block")],
            warnings=[Violation("r2", "desc2", "warning")],
        )
        engine.report(result)
        captured = capsys.readouterr()
        assert "BLOCK" in captured.out
        assert "WARNING" in captured.out
