"""
tests/integration/test_infracost_integration.py — Integration Tests for Infracost

All subprocess calls MUST be mocked — never call real Infracost in tests.
Tests verify the wizard correctly calls infracost and handles its output.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "cli-wizard"))
from wizard import step_run_infracost  # noqa: E402


class TestInfracostExecution:
    @patch("wizard.subprocess.run")
    def test_infracost_breakdown_is_called(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="Monthly cost: $0.00", stderr="")
        step_run_infracost()
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "infracost"
        assert "breakdown" in args
        assert "--path" in args

    @patch("wizard.subprocess.run")
    def test_infracost_success_returns_true(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="Cost: $0.00", stderr="")
        result = step_run_infracost()
        assert result is True

    @patch("wizard.subprocess.run")
    def test_infracost_error_returns_true_does_not_block(self, mock_run: MagicMock) -> None:
        """Infracost errors should not block deployment."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="API error")
        result = step_run_infracost()
        assert result is True  # Does NOT block


class TestInfracostErrorHandling:
    @patch("wizard.subprocess.run", side_effect=FileNotFoundError)
    def test_missing_infracost_returns_true(self, mock_run: MagicMock) -> None:
        """Missing infracost binary should not crash the wizard."""
        result = step_run_infracost()
        assert result is True

    @patch("wizard.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="infracost", timeout=120))
    def test_infracost_timeout_returns_true(self, mock_run: MagicMock) -> None:
        """Timeout should not crash the wizard."""
        result = step_run_infracost()
        assert result is True
