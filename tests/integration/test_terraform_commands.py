"""
tests/integration/test_terraform_commands.py — Integration Tests for Terraform Commands

All subprocess calls MUST be mocked — never call real Terraform in tests.
Tests verify the wizard correctly calls terraform init, plan, and apply.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "cli-wizard"))
from wizard import step_confirm_and_deploy, handle_destroy  # noqa: E402


class TestTerraformInit:
    @patch("wizard.subprocess.run")
    @patch("wizard.prompt_yes_no", side_effect=[True, True])  # deploy yes, apply yes
    def test_init_is_called_before_plan(self, mock_prompt: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        step_confirm_and_deploy()
        calls = mock_run.call_args_list
        # First call should be terraform init
        assert calls[0][0][0] == ["terraform", "init"]

    @patch("wizard.subprocess.run")
    @patch("wizard.prompt_yes_no", return_value=True)
    def test_init_failure_stops_deployment(self, mock_prompt: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="init error")
        result = step_confirm_and_deploy()
        assert result is False


class TestTerraformPlan:
    @patch("wizard.subprocess.run")
    @patch("wizard.prompt_yes_no", side_effect=[True, True])
    def test_plan_is_called_after_init(self, mock_prompt: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="Plan output", stderr="")
        step_confirm_and_deploy()
        calls = mock_run.call_args_list
        assert calls[1][0][0] == ["terraform", "plan", "-input=false"]

    @patch("wizard.subprocess.run")
    @patch("wizard.prompt_yes_no", return_value=True)
    def test_plan_failure_stops_deployment(self, mock_prompt: MagicMock, mock_run: MagicMock) -> None:
        # init succeeds, plan fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # init
            MagicMock(returncode=1, stdout="", stderr="plan error"),  # plan
        ]
        result = step_confirm_and_deploy()
        assert result is False


class TestTerraformApply:
    @patch("wizard.subprocess.run")
    @patch("wizard.prompt_yes_no", side_effect=[True, True])
    def test_apply_is_called_with_auto_approve(self, mock_prompt: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        step_confirm_and_deploy()
        calls = mock_run.call_args_list
        assert calls[2][0][0] == ["terraform", "apply", "-auto-approve", "-input=false"]

    @patch("wizard.subprocess.run")
    @patch("wizard.prompt_yes_no", side_effect=[True, False])  # deploy yes, apply no
    def test_user_can_cancel_after_plan(self, mock_prompt: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="Plan output", stderr="")
        result = step_confirm_and_deploy()
        assert result is False


class TestTerraformDestroy:
    @patch("wizard.subprocess.run")
    @patch("wizard.prompt_yes_no", return_value=True)
    def test_destroy_calls_terraform_destroy(self, mock_prompt: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="Destroyed", stderr="")
        handle_destroy()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["terraform", "destroy", "-auto-approve"]

    @patch("wizard.subprocess.run")
    @patch("wizard.prompt_yes_no", return_value=False)
    def test_destroy_cancelled_by_user(self, mock_prompt: MagicMock, mock_run: MagicMock) -> None:
        handle_destroy()
        mock_run.assert_not_called()


class TestUserCancellation:
    @patch("wizard.prompt_yes_no", return_value=False)
    def test_deploy_cancelled_returns_false(self, mock_prompt: MagicMock) -> None:
        result = step_confirm_and_deploy()
        assert result is False
