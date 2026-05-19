"""web-ui/api/terminal_security.py — Command blocklist engine for Web Terminal.

Provides security filtering for terminal commands:
- Blocks destructive system commands (rm -rf /, shutdown, reboot, etc.)
- Masks AWS credentials in terminal output
- Validates commands before execution

Usage:
    guard = TerminalSecurityGuard()
    result = guard.check_command("terraform plan")
    clean_output = guard.sanitize_output(raw_output)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandCheckResult:
    """Result of a command security check."""

    allowed: bool
    command: str
    reason: str = ""


# ─── Blocked command patterns (regex) ───
BLOCKED_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?/\s*$", "Recursive delete on root filesystem"),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f", "Recursive force delete"),
    (r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r", "Recursive force delete"),
    (r"\bshutdown\b", "System shutdown not allowed"),
    (r"\breboot\b", "System reboot not allowed"),
    (r"\bhalt\b", "System halt not allowed"),
    (r"\bpoweroff\b", "System poweroff not allowed"),
    (r"\binit\s+[06]", "System runlevel change not allowed"),
    (r"\bmkfs\b", "Filesystem creation not allowed"),
    (r"\bdd\s+.*of=/dev/", "Direct disk write not allowed"),
    (r"\bformat\b.*[cCdD]:", "Disk format not allowed"),
    (r">\s*/dev/sd[a-z]", "Direct device write not allowed"),
    (r"\bchmod\s+(-[a-zA-Z]*\s+)?777\s+/", "Recursive 777 on root not allowed"),
    (r"\bchown\s+(-[a-zA-Z]*R)", "Recursive chown not allowed on system dirs"),
    (r":\(\)\s*\{", "Fork bomb detected"),
    (r"\bcurl\b.*\|\s*(ba)?sh", "Pipe-to-shell not allowed"),
    (r"\bwget\b.*\|\s*(ba)?sh", "Pipe-to-shell not allowed"),
    (r"\bsudo\s+su\b", "Root escalation not allowed"),
    (r"\bpasswd\b", "Password change not allowed"),
    (r"\buseradd\b", "User creation not allowed"),
    (r"\buserdel\b", "User deletion not allowed"),
    (r"\bvisudo\b", "Sudoers edit not allowed"),
    (r"\biptables\s+-F", "Firewall flush not allowed"),
    (r"\bsystemctl\s+(stop|disable|mask)\s+(sshd|firewalld|ufw)", "Critical service disable not allowed"),
]

# ─── Credential patterns to mask in output ───
CREDENTIAL_PATTERNS: list[tuple[str, str]] = [
    (r"(AKIA[0-9A-Z]{16})", "***AWS_ACCESS_KEY***"),
    (r"(?i)(aws_secret_access_key\s*=\s*)[^\s]+", r"\1***REDACTED***"),
    (r"(?i)(aws_access_key_id\s*=\s*)[^\s]+", r"\1***REDACTED***"),
    (r"(?i)(AWS_SECRET_ACCESS_KEY=)[^\s]+", r"\1***REDACTED***"),
    (r"(?i)(AWS_ACCESS_KEY_ID=)[^\s]+", r"\1***REDACTED***"),
    (r"(?i)(aws_session_token\s*=\s*)[^\s]+", r"\1***REDACTED***"),
    (r"(?i)(password\s*[:=]\s*)[^\s]+", r"\1***REDACTED***"),
    (r"(?i)(token\s*[:=]\s*)[^\s]+", r"\1***REDACTED***"),
    (r"(?i)(secret\s*[:=]\s*)[^\s]+", r"\1***REDACTED***"),
]

# ─── Allowed base commands (whitelist for extra safety) ───
ALLOWED_COMMANDS: set[str] = {
    "terraform", "aws", "infracost", "opa",
    "ls", "cat", "echo", "pwd", "cd", "mkdir", "touch",
    "head", "tail", "grep", "find", "wc", "sort", "uniq",
    "diff", "less", "more", "file", "which", "whereis",
    "env", "export", "printenv", "date", "whoami", "hostname",
    "python", "python3", "pip", "pip3",
    "git", "curl", "wget", "jq", "yq",
    "clear", "history", "man", "help",
    "tree", "du", "df",
}


class TerminalSecurityGuard:
    """Security guard for terminal command execution."""

    def __init__(
        self,
        blocked_patterns: list[tuple[str, str]] | None = None,
        credential_patterns: list[tuple[str, str]] | None = None,
        use_allowlist: bool = False,
    ) -> None:
        """Initialize the security guard.

        Args:
            blocked_patterns: Custom blocked patterns (defaults to BLOCKED_PATTERNS).
            credential_patterns: Custom credential patterns (defaults to CREDENTIAL_PATTERNS).
            use_allowlist: If True, only commands in ALLOWED_COMMANDS are permitted.
        """
        self.blocked_patterns = blocked_patterns or BLOCKED_PATTERNS
        self.credential_patterns = credential_patterns or CREDENTIAL_PATTERNS
        self.use_allowlist = use_allowlist
        self._compiled_blocked = [
            (re.compile(pattern, re.IGNORECASE), reason)
            for pattern, reason in self.blocked_patterns
        ]
        self._compiled_creds = [
            (re.compile(pattern), replacement)
            for pattern, replacement in self.credential_patterns
        ]

    def check_command(self, command: str) -> CommandCheckResult:
        """Check if a command is safe to execute.

        Args:
            command: The shell command string to check.

        Returns:
            CommandCheckResult with allowed=True if safe.
        """
        if not command or not command.strip():
            return CommandCheckResult(allowed=True, command=command, reason="Empty command")

        stripped = command.strip()

        # Check against blocked patterns
        for pattern, reason in self._compiled_blocked:
            if pattern.search(stripped):
                return CommandCheckResult(
                    allowed=False,
                    command=command,
                    reason=f"🚫 Blocked: {reason}",
                )

        # Optional allowlist check
        if self.use_allowlist:
            base_cmd = stripped.split()[0].split("/")[-1]  # Get basename
            if base_cmd not in ALLOWED_COMMANDS:
                return CommandCheckResult(
                    allowed=False,
                    command=command,
                    reason=f"🚫 Command '{base_cmd}' not in allowed list",
                )

        return CommandCheckResult(allowed=True, command=command)

    def sanitize_output(self, output: str) -> str:
        """Remove or mask sensitive data from terminal output.

        Args:
            output: Raw terminal output string.

        Returns:
            Sanitized output with credentials masked.
        """
        sanitized = output
        for pattern, replacement in self._compiled_creds:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    def get_blocked_patterns_info(self) -> list[dict[str, str]]:
        """Return human-readable list of blocked patterns.

        Returns:
            List of dicts with 'pattern' and 'reason' keys.
        """
        return [
            {"pattern": pattern, "reason": reason}
            for pattern, reason in self.blocked_patterns
        ]
