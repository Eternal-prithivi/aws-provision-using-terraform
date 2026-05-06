"""opa-policies/opa_engine.py — OPA Policy Engine Wrapper

Runs OPA CLI to evaluate Rego policies against an infrastructure config dict.
Designed to AUGMENT the existing YAML-based Policy and Risk Engine, not replace it.

Key design decisions:
- Uses `opa eval` via subprocess (no OPA Go library required)
- Gracefully degrades when OPA is not installed (returns empty results)
- All block/warn messages include [opa_*] tags so they are distinguishable
  from the YAML engine's messages in the wizard output

Usage:
    engine = OPAEngine("opa-policies/")
    result = engine.evaluate(config_dict)
    engine.report(result)
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────

@dataclass
class OPAResult:
    """Holds OPA policy evaluation output."""

    blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    opa_available: bool = True
    error: str = ""

    def has_blocks(self) -> bool:
        """Return True if any block-level violations were found."""
        return len(self.blocks) > 0

    def has_warnings(self) -> bool:
        """Return True if any warnings were found."""
        return len(self.warnings) > 0

    def is_empty(self) -> bool:
        """Return True if OPA produced no output (clean result)."""
        return not self.blocks and not self.warnings


# ─────────────────────────────────────────────────────────
# OPA Engine
# ─────────────────────────────────────────────────────────

class OPAEngine:
    """Wraps the OPA CLI to evaluate Rego policies against a config dict."""

    def __init__(self, policies_dir: str) -> None:
        """Initialise the OPA engine with a path to the Rego policies directory.

        Args:
            policies_dir: Path to directory containing .rego policy files.
        """
        self.policies_dir = Path(policies_dir).resolve()
        self.policy_file = self.policies_dir / "aws_security.rego"

    def is_opa_available(self) -> bool:
        """Check whether the OPA CLI binary is installed and reachable.

        Returns:
            True if `opa version` exits with code 0, False otherwise.
        """
        try:
            result = subprocess.run(
                ["opa", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def evaluate(self, config: dict[str, Any]) -> OPAResult:
        """Evaluate an infrastructure config dict against the Rego policy file.

        Args:
            config: Dictionary of infrastructure configuration values.

        Returns:
            OPAResult with blocks and warnings extracted from OPA output.
        """
        if not self.is_opa_available():
            return OPAResult(
                opa_available=False,
                error="OPA CLI is not installed. Install from: https://www.openpolicyagent.org/docs/latest/#1-download-opa",
            )

        if not self.policy_file.exists():
            return OPAResult(
                opa_available=True,
                error=f"Policy file not found: {self.policy_file}",
            )

        result = OPAResult()

        # Evaluate deny rules (blocks)
        blocks = self._run_opa_query("data.aws.security.deny", config)
        result.blocks = blocks

        # Evaluate warn rules (warnings)
        warnings = self._run_opa_query("data.aws.security.warn", config)
        result.warnings = warnings

        return result

    def _run_opa_query(
        self,
        query: str,
        config: dict[str, Any],
    ) -> list[str]:
        """Run a single OPA query and return the string results.

        Args:
            query: Rego query string (e.g. "data.aws.security.deny").
            config: Input data to pass to OPA as JSON.

        Returns:
            List of result strings from OPA, or empty list on failure.
        """
        try:
            proc = subprocess.run(
                [
                    "opa", "eval",
                    "--format", "json",
                    "--data", str(self.policy_file),
                    "--input", "/dev/stdin",
                    query,
                ],
                input=json.dumps(config),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if proc.returncode != 0:
                return []

            data = json.loads(proc.stdout)
            # OPA eval returns: {"result": [{"expressions": [{"value": [...]}]}]}
            results = data.get("result", [])
            if not results:
                return []

            expressions = results[0].get("expressions", [])
            if not expressions:
                return []

            value = expressions[0].get("value", [])
            if isinstance(value, list):
                return [str(v) for v in value]
            return []

        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, IndexError):
            return []

    def report(self, result: OPAResult) -> None:
        """Print a formatted OPA evaluation report to stdout.

        Args:
            result: OPAResult from evaluate().
        """
        if not result.opa_available:
            print(f"  ⚠️  OPA not available: {result.error}")
            return

        if result.error:
            print(f"  ⚠️  OPA error: {result.error}")
            return

        if result.is_empty():
            print("  ✅  OPA: No additional violations found.")
            return

        if result.blocks:
            print()
            for msg in result.blocks:
                print(f"  🚫  {msg}")

        if result.warnings:
            print()
            for msg in result.warnings:
                print(f"  ⚠️  {msg}")
