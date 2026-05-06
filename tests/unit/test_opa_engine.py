"""tests/unit/test_opa_engine.py — Unit tests for the OPA Policy Engine.

Tests cover:
- OPAResult data structure
- OPA availability detection (mocked)
- clean config produces no blocks/warnings
- dangerous config triggers all blocks and warnings
- combined-risk rules (OPA-only logic)
- graceful degradation when OPA is not installed
- report() output formatting
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "opa-policies"))
from opa_engine import OPAEngine, OPAResult  # noqa: E402


POLICIES_DIR = str(Path(__file__).resolve().parent.parent.parent / "opa-policies")

# ─────────────────────────────────────────────────────────
# Clean infrastructure config (should produce zero issues)
# ─────────────────────────────────────────────────────────
CLEAN_CONFIG = {
    "s3_bucket_public": False,
    "s3_encryption": True,
    "ssh_open_to_world": False,
    "rdp_open_to_world": False,
    "iam_wildcard": False,
    "cloudtrail_enabled": True,
    "tags": {"Owner": "dev", "Project": "test"},
    "instance_type": "t2.micro",
    "environment": "free-tier",
}

# ─────────────────────────────────────────────────────────
# Dangerous config (should trigger blocks and warnings)
# ─────────────────────────────────────────────────────────
DANGEROUS_CONFIG = {
    "s3_bucket_public": True,
    "s3_encryption": False,
    "ssh_open_to_world": True,
    "rdp_open_to_world": True,
    "iam_wildcard": True,
    "cloudtrail_enabled": False,
    "tags": {},
    "instance_type": "m5.4xlarge",
    "environment": "production",
}


# ─────────────────────────────────────────────────────────
# OPAResult Data Structure Tests
# ─────────────────────────────────────────────────────────

class TestOPAResult:
    def test_default_result_has_no_blocks(self) -> None:
        result = OPAResult()
        assert result.has_blocks() is False

    def test_default_result_has_no_warnings(self) -> None:
        result = OPAResult()
        assert result.has_warnings() is False

    def test_default_result_is_empty(self) -> None:
        result = OPAResult()
        assert result.is_empty() is True

    def test_result_with_blocks_is_not_empty(self) -> None:
        result = OPAResult(blocks=["BLOCK: something"])
        assert result.is_empty() is False
        assert result.has_blocks() is True

    def test_result_with_warnings_is_not_empty(self) -> None:
        result = OPAResult(warnings=["WARN: something"])
        assert result.is_empty() is False
        assert result.has_warnings() is True

    def test_opa_unavailable_result(self) -> None:
        result = OPAResult(opa_available=False, error="not installed")
        assert result.opa_available is False
        assert result.error == "not installed"
        assert result.is_empty() is True  # no blocks or warnings


# ─────────────────────────────────────────────────────────
# OPA Availability
# ─────────────────────────────────────────────────────────

class TestOPAAvailability:
    def test_opa_reports_available_when_installed(self) -> None:
        """Real OPA is installed in the environment — should return True."""
        engine = OPAEngine(POLICIES_DIR)
        assert engine.is_opa_available() is True

    @patch("subprocess.run")
    def test_opa_reports_unavailable_when_not_found(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.side_effect = FileNotFoundError
        engine = OPAEngine(POLICIES_DIR)
        assert engine.is_opa_available() is False

    @patch("subprocess.run")
    def test_opa_reports_unavailable_on_timeout(
        self, mock_run: MagicMock
    ) -> None:
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="opa", timeout=10)
        engine = OPAEngine(POLICIES_DIR)
        assert engine.is_opa_available() is False


# ─────────────────────────────────────────────────────────
# Clean Config Tests
# ─────────────────────────────────────────────────────────

class TestCleanConfig:
    def test_clean_config_has_no_blocks(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        result = engine.evaluate(CLEAN_CONFIG)
        assert result.has_blocks() is False

    def test_clean_config_has_no_warnings(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        result = engine.evaluate(CLEAN_CONFIG)
        assert result.has_warnings() is False

    def test_clean_config_result_is_empty(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        result = engine.evaluate(CLEAN_CONFIG)
        assert result.is_empty() is True


# ─────────────────────────────────────────────────────────
# Individual Block Rules
# ─────────────────────────────────────────────────────────

class TestBlockRules:
    def test_public_s3_triggers_block(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "s3_bucket_public": True}
        result = engine.evaluate(config)
        assert result.has_blocks() is True
        assert any("opa_public_s3" in b for b in result.blocks)

    def test_open_ssh_triggers_block(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "ssh_open_to_world": True}
        result = engine.evaluate(config)
        assert result.has_blocks() is True
        assert any("opa_open_ssh" in b for b in result.blocks)

    def test_open_rdp_triggers_block(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "rdp_open_to_world": True}
        result = engine.evaluate(config)
        assert result.has_blocks() is True
        assert any("opa_open_rdp" in b for b in result.blocks)

    def test_iam_wildcard_triggers_block(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "iam_wildcard": True}
        result = engine.evaluate(config)
        assert result.has_blocks() is True
        assert any("opa_iam_wildcard" in b for b in result.blocks)


# ─────────────────────────────────────────────────────────
# Combined-Risk Rules (OPA-only logic)
# ─────────────────────────────────────────────────────────

class TestCombinedRiskRules:
    def test_public_plus_unencrypted_s3_triggers_combined_block(self) -> None:
        """Public + unencrypted S3 is a special combined-risk block."""
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "s3_bucket_public": True, "s3_encryption": False}
        result = engine.evaluate(config)
        assert any("opa_public_unencrypted_s3" in b for b in result.blocks)

    def test_public_but_encrypted_s3_no_combined_block(self) -> None:
        """Public S3 but encrypted — should NOT trigger the combined rule."""
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "s3_bucket_public": True, "s3_encryption": True}
        result = engine.evaluate(config)
        # Should trigger individual public_s3 block, but NOT the combined one
        assert not any("opa_public_unencrypted_s3" in b for b in result.blocks)

    def test_production_no_cloudtrail_no_tags_triggers_block(self) -> None:
        """Production with no CloudTrail AND no tags is a combined-risk block."""
        engine = OPAEngine(POLICIES_DIR)
        config = {
            **CLEAN_CONFIG,
            "cloudtrail_enabled": False,
            "tags": {},
            "environment": "production",
        }
        result = engine.evaluate(config)
        assert any("opa_production_no_audit" in b for b in result.blocks)

    def test_free_tier_no_cloudtrail_no_tags_no_combined_block(self) -> None:
        """Free-tier with no CloudTrail + no tags should NOT trigger the production block."""
        engine = OPAEngine(POLICIES_DIR)
        config = {
            **CLEAN_CONFIG,
            "cloudtrail_enabled": False,
            "tags": {},
            "environment": "free-tier",
        }
        result = engine.evaluate(config)
        assert not any("opa_production_no_audit" in b for b in result.blocks)


# ─────────────────────────────────────────────────────────
# Warning Rules
# ─────────────────────────────────────────────────────────

class TestWarningRules:
    def test_cloudtrail_disabled_triggers_warning(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "cloudtrail_enabled": False}
        result = engine.evaluate(config)
        assert result.has_warnings() is True
        assert any("opa_cloudtrail_disabled" in w for w in result.warnings)

    def test_s3_no_encryption_triggers_warning(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "s3_encryption": False}
        result = engine.evaluate(config)
        assert result.has_warnings() is True
        assert any("opa_s3_no_encryption" in w for w in result.warnings)

    def test_missing_tags_triggers_warning(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "tags": {}}
        result = engine.evaluate(config)
        assert result.has_warnings() is True
        assert any("opa_missing_tags" in w for w in result.warnings)

    def test_expensive_ec2_triggers_warning(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "instance_type": "m5.4xlarge"}
        result = engine.evaluate(config)
        assert result.has_warnings() is True
        assert any("opa_expensive_ec2" in w for w in result.warnings)

    def test_t2_micro_does_not_trigger_ec2_warning(self) -> None:
        engine = OPAEngine(POLICIES_DIR)
        config = {**CLEAN_CONFIG, "instance_type": "t2.micro"}
        result = engine.evaluate(config)
        assert not any("opa_expensive_ec2" in w for w in result.warnings)


# ─────────────────────────────────────────────────────────
# Graceful Degradation
# ─────────────────────────────────────────────────────────

class TestGracefulDegradation:
    @patch("subprocess.run")
    def test_returns_unavailable_result_when_opa_missing(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.side_effect = FileNotFoundError
        engine = OPAEngine(POLICIES_DIR)
        result = engine.evaluate(CLEAN_CONFIG)
        assert result.opa_available is False
        assert result.is_empty() is True

    def test_returns_error_result_when_policy_file_missing(self) -> None:
        engine = OPAEngine("/nonexistent/path/to/policies")
        result = engine.evaluate(CLEAN_CONFIG)
        assert result.error != ""
        assert result.is_empty() is True


# ─────────────────────────────────────────────────────────
# Report Formatting
# ─────────────────────────────────────────────────────────

class TestReport:
    def test_report_prints_unavailable_message(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        engine = OPAEngine(POLICIES_DIR)
        result = OPAResult(opa_available=False, error="not installed")
        engine.report(result)
        captured = capsys.readouterr()
        assert "not installed" in captured.out

    def test_report_prints_blocks(self, capsys: pytest.CaptureFixture) -> None:
        engine = OPAEngine(POLICIES_DIR)
        result = OPAResult(blocks=["BLOCK [opa_test]: Something bad"])
        engine.report(result)
        captured = capsys.readouterr()
        assert "BLOCK" in captured.out

    def test_report_prints_warnings(self, capsys: pytest.CaptureFixture) -> None:
        engine = OPAEngine(POLICIES_DIR)
        result = OPAResult(warnings=["WARN [opa_test]: Something to note"])
        engine.report(result)
        captured = capsys.readouterr()
        assert "WARN" in captured.out

    def test_report_on_clean_result(self, capsys: pytest.CaptureFixture) -> None:
        engine = OPAEngine(POLICIES_DIR)
        result = OPAResult()
        engine.report(result)
        captured = capsys.readouterr()
        assert "No additional" in captured.out
