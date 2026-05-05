"""
tests/unit/test_wizard.py — Unit Tests for CLI Wizard

Tests input validation, config generation, tfvars output, and policy integration.
All subprocess calls are mocked — never calls real Terraform or Infracost.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add cli-wizard to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "cli-wizard"))
from wizard import WizardConfig, TEMPLATES, prompt, prompt_yes_no  # noqa: E402


# ============================================================
# WizardConfig — Data Structure Tests
# ============================================================


class TestWizardConfig:
    def test_default_config_has_correct_region(self) -> None:
        config = WizardConfig()
        assert config.aws_region == "ap-south-1"

    def test_default_config_has_all_services_disabled(self) -> None:
        config = WizardConfig()
        assert config.enable_vpc is False
        assert config.enable_ec2 is False
        assert config.enable_s3 is False
        assert config.enable_iam is False
        assert config.enable_cloudwatch is False

    def test_default_instance_type_is_t2_micro(self) -> None:
        config = WizardConfig()
        assert config.instance_type == "t2.micro"

    def test_default_budget_is_one_dollar(self) -> None:
        config = WizardConfig()
        assert config.budget_limit == "1"


# ============================================================
# WizardConfig.to_tfvars — Output Generation
# ============================================================


class TestToTfvars:
    def test_generates_valid_tfvars_string(self) -> None:
        config = WizardConfig(
            aws_region="ap-south-1",
            enable_s3=True,
            bucket_name="test-bucket-123",
            budget_email="test@example.com",
            tags={"Owner": "dev", "Project": "test"},
        )
        output = config.to_tfvars()
        assert 'aws_region = "ap-south-1"' in output
        assert "enable_s3         = true" in output
        assert "enable_vpc        = false" in output
        assert 'bucket_name   = "test-bucket-123"' in output
        assert 'Owner = "dev"' in output

    def test_tfvars_contains_all_enable_flags(self) -> None:
        config = WizardConfig()
        output = config.to_tfvars()
        assert "enable_vpc" in output
        assert "enable_ec2" in output
        assert "enable_s3" in output
        assert "enable_iam" in output
        assert "enable_cloudwatch" in output

    def test_tfvars_contains_tags_block(self) -> None:
        config = WizardConfig(tags={"Owner": "test"})
        output = config.to_tfvars()
        assert "tags = {" in output
        assert 'Owner = "test"' in output
        assert "}" in output

    def test_empty_tags_produces_empty_block(self) -> None:
        config = WizardConfig(tags={})
        output = config.to_tfvars()
        assert "tags = {\n}" in output


# ============================================================
# WizardConfig.to_policy_dict — Policy Engine Integration
# ============================================================


class TestToPolicyDict:
    def test_policy_dict_has_all_required_keys(self) -> None:
        config = WizardConfig()
        pd = config.to_policy_dict()
        required_keys = [
            "s3_bucket_public", "ssh_open_to_world", "rdp_open_to_world",
            "iam_wildcard", "instance_type", "s3_encryption",
            "tags", "cloudtrail_enabled",
        ]
        for key in required_keys:
            assert key in pd, f"Missing key: {key}"

    def test_free_tier_has_cloudtrail_disabled(self) -> None:
        config = WizardConfig(environment="free-tier")
        pd = config.to_policy_dict()
        assert pd["cloudtrail_enabled"] is False

    def test_production_has_cloudtrail_enabled(self) -> None:
        config = WizardConfig(environment="production")
        pd = config.to_policy_dict()
        assert pd["cloudtrail_enabled"] is True

    def test_enforced_security_defaults(self) -> None:
        """S3 public access, SSH, RDP, and IAM wildcard are always blocked."""
        config = WizardConfig()
        pd = config.to_policy_dict()
        assert pd["s3_bucket_public"] is False
        assert pd["ssh_open_to_world"] is False
        assert pd["rdp_open_to_world"] is False
        assert pd["iam_wildcard"] is False
        assert pd["s3_encryption"] is True

    def test_empty_tags_in_policy_dict(self) -> None:
        config = WizardConfig(tags={})
        pd = config.to_policy_dict()
        assert pd["tags"] == {}

    def test_tags_passed_through_correctly(self) -> None:
        config = WizardConfig(tags={"Owner": "dev", "Project": "test"})
        pd = config.to_policy_dict()
        assert pd["tags"] == {"Owner": "dev", "Project": "test"}


# ============================================================
# Templates
# ============================================================


class TestTemplates:
    def test_static_site_template_exists(self) -> None:
        assert "static-site" in TEMPLATES

    def test_backend_app_template_exists(self) -> None:
        assert "backend-app" in TEMPLATES

    def test_static_site_enables_only_s3(self) -> None:
        tpl = TEMPLATES["static-site"]
        assert tpl["services"] == {"enable_s3": True}

    def test_backend_app_enables_vpc_ec2_iam(self) -> None:
        tpl = TEMPLATES["backend-app"]
        assert tpl["services"]["enable_vpc"] is True
        assert tpl["services"]["enable_ec2"] is True
        assert tpl["services"]["enable_iam"] is True

    def test_all_templates_have_required_fields(self) -> None:
        for key, tpl in TEMPLATES.items():
            assert "name" in tpl, f"Template {key} missing 'name'"
            assert "description" in tpl, f"Template {key} missing 'description'"
            assert "services" in tpl, f"Template {key} missing 'services'"
            assert "environment" in tpl, f"Template {key} missing 'environment'"

    def test_all_templates_are_free_tier(self) -> None:
        for key, tpl in TEMPLATES.items():
            assert tpl["environment"] == "free-tier", f"Template {key} is not free-tier"


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    def test_config_with_all_services_enabled(self) -> None:
        config = WizardConfig(
            enable_vpc=True, enable_ec2=True, enable_s3=True,
            enable_iam=True, enable_cloudwatch=True,
        )
        output = config.to_tfvars()
        assert "enable_vpc        = true" in output
        assert "enable_ec2        = true" in output
        assert "enable_s3         = true" in output
        assert "enable_iam        = true" in output
        assert "enable_cloudwatch = true" in output

    def test_config_to_tfvars_never_contains_credentials(self) -> None:
        """terraform.tfvars must never contain AWS credentials."""
        config = WizardConfig(
            enable_s3=True, bucket_name="test",
            budget_email="test@test.com",
        )
        output = config.to_tfvars()
        assert "AWS_ACCESS_KEY" not in output
        assert "AWS_SECRET" not in output
        assert "password" not in output.lower()

    def test_wizard_config_is_dataclass(self) -> None:
        """Verify WizardConfig follows the dataclass pattern (AI_RULES.md requirement)."""
        from dataclasses import fields
        field_names = [f.name for f in fields(WizardConfig)]
        assert "aws_region" in field_names
        assert "enable_vpc" in field_names
        assert "tags" in field_names
