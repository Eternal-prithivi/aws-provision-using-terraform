"""
tests/unit/test_policy_engine.py — Unit Tests for the Policy and Risk Engine

Tests all 8 rules × pass + fail + edge cases.
Uses tests/fixtures/sample_rules.yaml — never the production rules file.
"""

from __future__ import annotations

import pytest

from engine import EvaluationResult, PolicyEngine, Violation

RULES = "tests/fixtures/sample_rules.yaml"


# ============================================================
# Engine Initialization
# ============================================================


class TestPolicyEngineInit:
    def test_loads_rules_successfully(self) -> None:
        engine = PolicyEngine(RULES)
        assert len(engine.rules) == 8

    def test_raises_file_not_found_for_missing_rules(self) -> None:
        with pytest.raises(FileNotFoundError):
            PolicyEngine("nonexistent/path/rules.yaml")

    def test_raises_value_error_for_empty_rules_file(self, tmp_path) -> None:
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        with pytest.raises(ValueError):
            PolicyEngine(str(empty_file))

    def test_raises_value_error_for_rules_missing_key(self, tmp_path) -> None:
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("something: else\n")
        with pytest.raises(ValueError):
            PolicyEngine(str(bad_file))


# ============================================================
# BLOCK Rule: public_s3_bucket
# ============================================================


class TestPublicS3BucketRule:
    def test_blocks_when_s3_is_public(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"s3_bucket_public": True})
        assert result.has_blocks() is True
        assert any(v.rule_name == "public_s3_bucket" for v in result.violations)

    def test_passes_when_s3_is_private(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"s3_bucket_public": False})
        assert not any(v.rule_name == "public_s3_bucket" for v in result.violations)

    def test_passes_when_key_absent(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({})
        assert not any(v.rule_name == "public_s3_bucket" for v in result.violations)


# ============================================================
# BLOCK Rule: open_ssh_port
# ============================================================


class TestOpenSshPortRule:
    def test_blocks_when_ssh_open_to_world(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"ssh_open_to_world": True})
        assert any(v.rule_name == "open_ssh_port" for v in result.violations)

    def test_passes_when_ssh_not_open(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"ssh_open_to_world": False})
        assert not any(v.rule_name == "open_ssh_port" for v in result.violations)


# ============================================================
# BLOCK Rule: open_rdp_port
# ============================================================


class TestOpenRdpPortRule:
    def test_blocks_when_rdp_open_to_world(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"rdp_open_to_world": True})
        assert any(v.rule_name == "open_rdp_port" for v in result.violations)

    def test_passes_when_rdp_not_open(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"rdp_open_to_world": False})
        assert not any(v.rule_name == "open_rdp_port" for v in result.violations)


# ============================================================
# BLOCK Rule: iam_wildcard_permissions
# ============================================================


class TestIamWildcardRule:
    def test_blocks_when_iam_has_wildcard(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"iam_wildcard": True})
        assert any(v.rule_name == "iam_wildcard_permissions" for v in result.violations)

    def test_passes_when_iam_no_wildcard(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"iam_wildcard": False})
        assert not any(v.rule_name == "iam_wildcard_permissions" for v in result.violations)


# ============================================================
# WARNING Rule: expensive_ec2_instance
# ============================================================


class TestExpensiveEc2Rule:
    def test_warns_when_instance_not_free_tier(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"instance_type": "m5.4xlarge"})
        assert any(w.rule_name == "expensive_ec2_instance" for w in result.warnings)

    def test_passes_for_t2_micro(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"instance_type": "t2.micro"})
        assert not any(w.rule_name == "expensive_ec2_instance" for w in result.warnings)

    def test_passes_for_t3_micro(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"instance_type": "t3.micro"})
        assert not any(w.rule_name == "expensive_ec2_instance" for w in result.warnings)


# ============================================================
# WARNING Rule: missing_s3_encryption
# ============================================================


class TestS3EncryptionRule:
    def test_warns_when_encryption_disabled(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"s3_encryption": False})
        assert any(w.rule_name == "missing_s3_encryption" for w in result.warnings)

    def test_passes_when_encryption_enabled(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"s3_encryption": True})
        assert not any(w.rule_name == "missing_s3_encryption" for w in result.warnings)


# ============================================================
# WARNING Rule: missing_resource_tags
# ============================================================


class TestMissingTagsRule:
    def test_warns_when_tags_empty_dict(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"tags": {}})
        assert any(w.rule_name == "missing_resource_tags" for w in result.warnings)

    def test_warns_when_tags_is_none(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"tags": None})
        assert any(w.rule_name == "missing_resource_tags" for w in result.warnings)

    def test_passes_when_tags_present(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"tags": {"Owner": "dev", "Project": "test"}})
        assert not any(w.rule_name == "missing_resource_tags" for w in result.warnings)


# ============================================================
# WARNING Rule: cloudtrail_disabled
# ============================================================


class TestCloudtrailRule:
    def test_warns_when_cloudtrail_disabled(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"cloudtrail_enabled": False})
        assert any(w.rule_name == "cloudtrail_disabled" for w in result.warnings)

    def test_passes_when_cloudtrail_enabled(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({"cloudtrail_enabled": True})
        assert not any(w.rule_name == "cloudtrail_disabled" for w in result.warnings)


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    def test_evaluate_with_none_config_does_not_crash(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate(None)
        assert isinstance(result, EvaluationResult)

    def test_evaluate_with_empty_config_does_not_crash(self) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate({})
        assert isinstance(result, EvaluationResult)

    def test_clean_config_returns_is_clean_true(self, valid_config) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate(valid_config)
        assert result.is_clean() is True

    def test_insecure_config_returns_has_blocks_true(self, insecure_config) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate(insecure_config)
        assert result.has_blocks() is True
        assert len(result.violations) == 4  # 4 block-level rules

    def test_insecure_config_returns_has_warnings_true(self, insecure_config) -> None:
        engine = PolicyEngine(RULES)
        result = engine.evaluate(insecure_config)
        assert result.has_warnings() is True
