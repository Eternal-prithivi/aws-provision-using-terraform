"""tests/unit/test_drift_remediation.py — Unit tests for drift remediation."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "drift-detection"))
from remediation import remediate_drift, report_contains_drift  # noqa: E402


class TestReportParsing:
    def test_detects_drift_from_report_text(self) -> None:
        report_text = "Status: DRIFT DETECTED\nSummary: +1 to create"
        assert report_contains_drift(report_text) is True

    def test_ignores_non_drift_report_text(self) -> None:
        report_text = "Report: No drift detected at 2026-05-06 00:00:00 UTC"
        assert report_contains_drift(report_text) is False


class TestRemediateDrift:
    @patch("remediation.subprocess.run")
    def test_skips_when_report_missing(self, mock_run: MagicMock, tmp_path: Path) -> None:
        report_file = tmp_path / "drift-report.txt"
        result = remediate_drift(
            project_root=tmp_path,
            report_file=report_file,
            auto_approve=True,
        )
        assert result.success is True
        assert result.performed is False
        mock_run.assert_not_called()

    @patch("remediation.subprocess.run")
    def test_requires_auto_approve_to_apply(self, mock_run: MagicMock, tmp_path: Path) -> None:
        report_file = tmp_path / "drift-report.txt"
        report_file.write_text("Status: DRIFT DETECTED\n", encoding="utf-8")

        result = remediate_drift(
            project_root=tmp_path,
            report_file=report_file,
            auto_approve=False,
        )

        assert result.success is True
        assert result.performed is False
        mock_run.assert_not_called()

    @patch("remediation.subprocess.run")
    def test_applies_drift_when_auto_approved(self, mock_run: MagicMock, tmp_path: Path) -> None:
        report_file = tmp_path / "drift-report.txt"
        report_file.write_text("Status: DRIFT DETECTED\n", encoding="utf-8")
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="init ok", stderr=""),
            MagicMock(returncode=0, stdout="apply ok", stderr=""),
        ]

        result = remediate_drift(
            project_root=tmp_path,
            report_file=report_file,
            auto_approve=True,
        )

        assert result.success is True
        assert result.performed is True
        assert mock_run.call_args_list[0][0][0] == ["terraform", "init", "-input=false", "-no-color"]
        assert mock_run.call_args_list[1][0][0] == [
            "terraform",
            "apply",
            "-auto-approve",
            "-input=false",
            "-no-color",
        ]
        assert (tmp_path / "drift-remediation-report.txt").exists()

    @patch("remediation.subprocess.run")
    def test_init_failure_marks_remediation_failed(self, mock_run: MagicMock, tmp_path: Path) -> None:
        report_file = tmp_path / "drift-report.txt"
        report_file.write_text("Status: DRIFT DETECTED\n", encoding="utf-8")
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="init failed")

        result = remediate_drift(
            project_root=tmp_path,
            report_file=report_file,
            auto_approve=True,
        )

        assert result.success is False
        assert result.performed is True
        assert "FAILED" in (tmp_path / "drift-remediation-report.txt").read_text(encoding="utf-8")
