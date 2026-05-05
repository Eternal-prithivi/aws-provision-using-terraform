#!/usr/bin/env python3
"""
cli-wizard/wizard.py — Interactive CLI Wizard for AWS Infrastructure Provisioning

Flow:
  1. Display welcome + available templates
  2. Select template or custom
  3. Select services (VPC, EC2, S3, IAM, CloudWatch)
  4. Select environment (free-tier or production)
  5. Configure each selected service
  6. Generate terraform.tfvars
  7. Run Policy Engine → show violations/warnings
  8. Run Infracost → show monthly cost estimate
  9. Final confirmation → terraform init + apply

PLACEHOLDER — Full implementation in Phase 5.
"""

from __future__ import annotations

# Phase 5 implementation goes here.
# See AI_CONTEXT.md → CLI Wizard Flow for the full specification.


def main() -> None:
    """Entry point for the CLI wizard. Implement in Phase 5."""
    print("🚧  CLI Wizard — Coming in Phase 5")
    print("    Run: python cli-wizard/wizard.py")


if __name__ == "__main__":
    main()
