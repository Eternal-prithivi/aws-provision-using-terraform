"""
tests/unit/test_wizard.py — Unit Tests for CLI Wizard

Tests input validation, config generation, tfvars output, policy integration,
interactive steps (with mocked input), and the main wizard flow.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Add cli-wizard to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "cli-wizard"))
from wizard import (  # noqa: E402
    WizardConfig, TEMPLATES,
    prompt, prompt_yes_no, prompt_choice,
    display_welcome,
    step_select_template, step_select_services,
    step_select_environment, step_configure_services,
    step_generate_tfvars, step_run_policy_engine,
    step_run_infracost, step_destroy_prompt,
    handle_destroy, main,
)


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
# Input Helpers (mocked input)
# ============================================================


class TestPrompt:
    @patch("builtins.input", return_value="hello")
    def test_prompt_returns_user_input(self, mock_input: MagicMock) -> None:
        result = prompt("Enter value")
        assert result == "hello"

    @patch("builtins.input", return_value="")
    def test_prompt_returns_default_when_empty(self, mock_input: MagicMock) -> None:
        result = prompt("Enter value", default="fallback")
        assert result == "fallback"

    @patch("builtins.input", return_value="custom")
    def test_prompt_returns_custom_over_default(self, mock_input: MagicMock) -> None:
        result = prompt("Enter value", default="fallback")
        assert result == "custom"


class TestPromptYesNo:
    @patch("builtins.input", return_value="y")
    def test_yes_returns_true(self, mock_input: MagicMock) -> None:
        assert prompt_yes_no("Continue?") is True

    @patch("builtins.input", return_value="yes")
    def test_yes_full_word_returns_true(self, mock_input: MagicMock) -> None:
        assert prompt_yes_no("Continue?") is True

    @patch("builtins.input", return_value="n")
    def test_no_returns_false(self, mock_input: MagicMock) -> None:
        assert prompt_yes_no("Continue?") is False

    @patch("builtins.input", return_value="")
    def test_empty_returns_default_false(self, mock_input: MagicMock) -> None:
        assert prompt_yes_no("Continue?", default=False) is False

    @patch("builtins.input", return_value="")
    def test_empty_returns_default_true(self, mock_input: MagicMock) -> None:
        assert prompt_yes_no("Continue?", default=True) is True


class TestPromptChoice:
    @patch("builtins.input", return_value="1")
    def test_select_first_choice(self, mock_input: MagicMock) -> None:
        result = prompt_choice("Pick:", ["alpha", "beta", "gamma"])
        assert result == "alpha"

    @patch("builtins.input", return_value="3")
    def test_select_last_choice(self, mock_input: MagicMock) -> None:
        result = prompt_choice("Pick:", ["alpha", "beta", "gamma"])
        assert result == "gamma"

    @patch("builtins.input", side_effect=["invalid", "0", "2"])
    def test_retries_on_invalid_input(self, mock_input: MagicMock) -> None:
        result = prompt_choice("Pick:", ["alpha", "beta"])
        assert result == "beta"
        assert mock_input.call_count == 3


# ============================================================
# Interactive Steps (mocked input)
# ============================================================


class TestDisplayWelcome:
    def test_welcome_prints_without_error(self, capsys: pytest.CaptureFixture) -> None:
        display_welcome()
        captured = capsys.readouterr()
        assert "Smart AWS Infrastructure" in captured.out
        assert "Interactive CLI Wizard" in captured.out


class TestStepSelectTemplate:
    @patch("builtins.input", return_value="3")  # Custom option (last)
    def test_custom_returns_none(self, mock_input: MagicMock) -> None:
        result = step_select_template()
        assert result is None

    @patch("builtins.input", return_value="1")  # First template: static-site
    def test_static_site_returns_key(self, mock_input: MagicMock) -> None:
        result = step_select_template()
        assert result == "static-site"

    @patch("builtins.input", return_value="2")  # Second template: backend-app
    def test_backend_app_returns_key(self, mock_input: MagicMock) -> None:
        result = step_select_template()
        assert result == "backend-app"


class TestStepSelectServices:
    @patch("builtins.input", side_effect=["y", "y", "n", "n", "n"])
    def test_enables_vpc_and_ec2(self, mock_input: MagicMock) -> None:
        config = WizardConfig()
        step_select_services(config)
        assert config.enable_vpc is True
        assert config.enable_ec2 is True
        assert config.enable_s3 is False

    @patch("builtins.input", side_effect=[
        "n", "n", "n", "n", "n",  # All no → retry
        "n", "y", "n", "n", "n",  # Second round: enable EC2
    ])
    def test_retries_when_no_services_selected(self, mock_input: MagicMock) -> None:
        config = WizardConfig()
        step_select_services(config)
        assert config.enable_ec2 is True


class TestStepSelectEnvironment:
    @patch("builtins.input", return_value="1")  # free-tier
    def test_free_tier_selected(self, mock_input: MagicMock) -> None:
        config = WizardConfig()
        step_select_environment(config)
        assert config.environment == "free-tier"

    @patch("builtins.input", side_effect=["2", "y"])  # production + confirm
    def test_production_confirmed(self, mock_input: MagicMock) -> None:
        config = WizardConfig()
        step_select_environment(config)
        assert config.environment == "production"

    @patch("builtins.input", side_effect=["2", "n"])  # production + decline
    def test_production_declined_falls_back(self, mock_input: MagicMock) -> None:
        config = WizardConfig()
        step_select_environment(config)
        assert config.environment == "free-tier"


class TestStepConfigureServices:
    @patch("builtins.input", side_effect=[
        "",           # region (default)
        "dev",        # owner tag
        "myproject",  # project tag
        "1",          # budget
        "a@b.com",    # budget email
    ])
    def test_minimal_config_with_defaults(self, mock_input: MagicMock) -> None:
        config = WizardConfig()
        step_configure_services(config)
        assert config.aws_region == "ap-south-1"
        assert config.tags["Owner"] == "dev"
        assert config.budget_email == "a@b.com"

    @patch("builtins.input", side_effect=[
        "",                      # region
        "",                      # vpc cidr (default)
        "ami-0f58b397bc5c1f2e8", # ami
        "dev",                   # owner
        "test",                  # project
        "1",                     # budget
        "a@b.com",               # budget email
    ])
    def test_ec2_free_tier_locks_instance_type(self, mock_input: MagicMock) -> None:
        config = WizardConfig(enable_vpc=True, enable_ec2=True, environment="free-tier")
        step_configure_services(config)
        assert config.instance_type == "t2.micro"

    @patch("builtins.input", side_effect=[
        "",            # region
        "",            # vpc cidr
        "t3.medium",   # instance type (production allows choice)
        "ami-123",     # ami
        "dev",         # owner
        "test",        # project
        "10",          # budget
        "a@b.com",     # budget email
    ])
    def test_ec2_production_allows_custom_instance(self, mock_input: MagicMock) -> None:
        config = WizardConfig(enable_vpc=True, enable_ec2=True, environment="production")
        step_configure_services(config)
        assert config.instance_type == "t3.medium"

    @patch("builtins.input", side_effect=[
        "",                # region
        "my-bucket-123",   # s3 bucket name
        "dev",             # owner
        "test",            # project
        "1",               # budget
        "a@b.com",         # budget email
    ])
    def test_s3_requires_bucket_name(self, mock_input: MagicMock) -> None:
        config = WizardConfig(enable_s3=True)
        step_configure_services(config)
        assert config.bucket_name == "my-bucket-123"

    @patch("builtins.input", side_effect=[
        "",            # region
        "",            # s3 bucket (empty → retry)
        "my-bucket",   # s3 bucket (second try)
        "dev",         # owner
        "test",        # project
        "1",           # budget
        "a@b.com",     # budget email
    ])
    def test_s3_retries_on_empty_bucket(self, mock_input: MagicMock) -> None:
        config = WizardConfig(enable_s3=True)
        step_configure_services(config)
        assert config.bucket_name == "my-bucket"

    @patch("builtins.input", side_effect=[
        "",           # region
        "my-role",    # iam role
        "dev",        # owner
        "test",       # project
        "1",          # budget
        "a@b.com",    # budget email
    ])
    def test_iam_config(self, mock_input: MagicMock) -> None:
        config = WizardConfig(enable_iam=True)
        step_configure_services(config)
        assert config.role_name == "my-role"

    @patch("builtins.input", side_effect=[
        "",           # region
        "x@y.com",    # cloudwatch alarm email
        "dev",        # owner
        "test",       # project
        "1",          # budget
        "a@b.com",    # budget email
    ])
    def test_cloudwatch_config(self, mock_input: MagicMock) -> None:
        config = WizardConfig(enable_cloudwatch=True)
        step_configure_services(config)
        assert config.alarm_email == "x@y.com"

    @patch("builtins.input", side_effect=[
        "",          # region
        "",          # vpc cidr
        "ami-123",   # ami
        "dev",       # owner
        "test",      # project
        "1",         # budget
        "a@b.com",   # budget email
    ])
    def test_ec2_without_vpc_auto_enables_vpc(self, mock_input: MagicMock) -> None:
        config = WizardConfig(enable_ec2=True, enable_vpc=False)
        step_configure_services(config)
        assert config.enable_vpc is True

    @patch("builtins.input", side_effect=[
        "",        # region
        "dev",     # owner
        "test",    # project
        "1",       # budget
        "",        # budget email (empty → retry)
        "a@b.com", # budget email (second try)
    ])
    def test_budget_email_retries_on_empty(self, mock_input: MagicMock) -> None:
        config = WizardConfig()
        step_configure_services(config)
        assert config.budget_email == "a@b.com"


class TestStepGenerateTfvars:
    @patch("builtins.open", mock_open())
    def test_generates_and_writes_file(self) -> None:
        config = WizardConfig(
            enable_s3=True,
            bucket_name="test",
            tags={"Owner": "dev"},
            budget_email="a@b.com",
        )
        result = step_generate_tfvars(config)
        assert "terraform.tfvars" in result


class TestStepRunPolicyEngine:
    def test_runs_policy_check_on_valid_config(self) -> None:
        config = WizardConfig(
            instance_type="t2.micro",
            tags={"Owner": "dev"},
            environment="free-tier",
        )
        result = step_run_policy_engine(config)
        assert result.has_blocks() is False

    def test_warns_on_expensive_instance(self) -> None:
        config = WizardConfig(
            instance_type="m5.4xlarge",
            tags={"Owner": "dev"},
            environment="free-tier",
        )
        result = step_run_policy_engine(config)
        assert result.has_warnings() is True

    def test_warns_on_missing_tags(self) -> None:
        config = WizardConfig(
            instance_type="t2.micro",
            tags={},
            environment="free-tier",
        )
        result = step_run_policy_engine(config)
        assert result.has_warnings() is True


class TestStepDestroyPrompt:
    def test_prints_cost_safety_reminder(self, capsys: pytest.CaptureFixture) -> None:
        step_destroy_prompt()
        captured = capsys.readouterr()
        assert "COST SAFETY REMINDER" in captured.out
        assert "terraform destroy" in captured.out


# ============================================================
# Main Flow
# ============================================================


class TestMainFlow:
    @patch("wizard.step_confirm_and_deploy", return_value=False)
    @patch("wizard.step_run_infracost", return_value=True)
    @patch("wizard.step_run_policy_engine")
    @patch("wizard.step_generate_tfvars", return_value="/tmp/terraform.tfvars")
    @patch("wizard.step_configure_services")
    @patch("wizard.step_select_template", return_value="static-site")
    @patch("wizard.display_welcome")
    def test_main_template_flow(self, mock_welcome, mock_template, mock_config,
                                 mock_tfvars, mock_policy, mock_infra, mock_deploy) -> None:
        mock_policy.return_value = MagicMock(has_blocks=lambda: False, has_warnings=lambda: False)
        main()
        mock_welcome.assert_called_once()
        mock_template.assert_called_once()
        mock_config.assert_called_once()

    @patch("wizard.step_confirm_and_deploy", return_value=False)
    @patch("wizard.step_run_infracost", return_value=True)
    @patch("wizard.step_run_policy_engine")
    @patch("wizard.step_generate_tfvars", return_value="/tmp/terraform.tfvars")
    @patch("wizard.step_configure_services")
    @patch("wizard.step_select_environment")
    @patch("wizard.step_select_services")
    @patch("wizard.step_select_template", return_value=None)  # Custom
    @patch("wizard.display_welcome")
    def test_main_custom_flow(self, mock_welcome, mock_template, mock_services,
                               mock_env, mock_config, mock_tfvars, mock_policy,
                               mock_infra, mock_deploy) -> None:
        mock_policy.return_value = MagicMock(has_blocks=lambda: False, has_warnings=lambda: False)
        main()
        mock_services.assert_called_once()
        mock_env.assert_called_once()

    @patch("wizard.step_run_policy_engine")
    @patch("wizard.step_generate_tfvars", return_value="/tmp/terraform.tfvars")
    @patch("wizard.step_configure_services")
    @patch("wizard.step_select_template", return_value="static-site")
    @patch("wizard.display_welcome")
    def test_main_blocks_on_policy_violation(self, mock_welcome, mock_template,
                                              mock_config, mock_tfvars, mock_policy) -> None:
        mock_policy.return_value = MagicMock(has_blocks=lambda: True)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch("wizard.prompt_yes_no", return_value=False)  # Don't continue after warning
    @patch("wizard.step_run_policy_engine")
    @patch("wizard.step_generate_tfvars", return_value="/tmp/terraform.tfvars")
    @patch("wizard.step_configure_services")
    @patch("wizard.step_select_template", return_value="static-site")
    @patch("wizard.display_welcome")
    def test_main_user_cancels_on_warnings(self, mock_welcome, mock_template,
                                            mock_config, mock_tfvars, mock_policy,
                                            mock_prompt) -> None:
        mock_policy.return_value = MagicMock(has_blocks=lambda: False, has_warnings=lambda: True)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @patch("wizard.handle_destroy")
    def test_main_destroy_flag(self, mock_destroy: MagicMock) -> None:
        with patch.object(sys, "argv", ["wizard.py", "--destroy"]):
            main()
            mock_destroy.assert_called_once()

    @patch("wizard.step_destroy_prompt")
    @patch("wizard.step_confirm_and_deploy", return_value=True)
    @patch("wizard.step_run_infracost", return_value=True)
    @patch("wizard.step_run_policy_engine")
    @patch("wizard.step_generate_tfvars", return_value="/tmp/terraform.tfvars")
    @patch("wizard.step_configure_services")
    @patch("wizard.step_select_template", return_value="static-site")
    @patch("wizard.display_welcome")
    def test_main_successful_deploy_shows_destroy_prompt(
        self, mock_welcome, mock_template, mock_config, mock_tfvars,
        mock_policy, mock_infra, mock_deploy, mock_destroy_prompt
    ) -> None:
        mock_policy.return_value = MagicMock(has_blocks=lambda: False, has_warnings=lambda: False)
        main()
        mock_destroy_prompt.assert_called_once()


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
