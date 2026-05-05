#!/usr/bin/env python3
"""
cli-wizard/wizard.py — Interactive CLI Wizard for AWS Infrastructure Provisioning

Flow:
  1. Display welcome + available templates
  2. Select template or custom configuration
  3. Select services (VPC, EC2, S3, IAM, CloudWatch)
  4. Select environment (free-tier or production)
  5. Configure each selected service
  6. Generate terraform.tfvars
  7. Run Policy Engine → show violations/warnings
  8. Run Infracost → show monthly cost estimate
  9. Final confirmation → terraform init + apply

Usage: python cli-wizard/wizard.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Add policy-engine to path so we can import the engine
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "policy-engine"))
from engine import EvaluationResult, PolicyEngine  # noqa: E402


# ============================================================
# Data Structures
# ============================================================

@dataclass
class WizardConfig:
    """Holds all configuration gathered from the wizard session."""

    aws_region: str = "ap-south-1"
    enable_vpc: bool = False
    enable_ec2: bool = False
    enable_s3: bool = False
    enable_iam: bool = False
    enable_cloudwatch: bool = False
    vpc_cidr: str = "10.0.0.0/16"
    instance_type: str = "t2.micro"
    ami_id: str = ""
    bucket_name: str = ""
    role_name: str = "app-role"
    alarm_email: str = ""
    budget_limit: str = "1"
    budget_email: str = ""
    tags: dict[str, str] = field(default_factory=dict)
    environment: str = "free-tier"

    def to_tfvars(self) -> str:
        """Convert config to terraform.tfvars format."""
        lines: list[str] = [
            f'aws_region = "{self.aws_region}"',
            "",
            f"enable_vpc        = {str(self.enable_vpc).lower()}",
            f"enable_ec2        = {str(self.enable_ec2).lower()}",
            f"enable_s3         = {str(self.enable_s3).lower()}",
            f"enable_iam        = {str(self.enable_iam).lower()}",
            f"enable_cloudwatch = {str(self.enable_cloudwatch).lower()}",
            "",
            f'vpc_cidr      = "{self.vpc_cidr}"',
            f'instance_type = "{self.instance_type}"',
            f'ami_id        = "{self.ami_id}"',
            f'bucket_name   = "{self.bucket_name}"',
            f'role_name     = "{self.role_name}"',
            f'alarm_email   = "{self.alarm_email}"',
            "",
            f'budget_limit = "{self.budget_limit}"',
            f'budget_email = "{self.budget_email}"',
            "",
            "tags = {",
        ]
        for key, value in self.tags.items():
            lines.append(f'  {key} = "{value}"')
        lines.append("}")
        lines.append("")
        return "\n".join(lines)

    def to_policy_dict(self) -> dict[str, Any]:
        """Convert config to dict format expected by the policy engine."""
        return {
            "s3_bucket_public": False,  # enforced by Terraform module
            "ssh_open_to_world": False,  # no SSH rule in security group
            "rdp_open_to_world": False,  # no RDP rule in security group
            "iam_wildcard": False,  # enforced by IAM module
            "instance_type": self.instance_type,
            "s3_encryption": True,  # enforced by S3 module
            "tags": self.tags if self.tags else {},
            "cloudtrail_enabled": self.environment == "production",
        }


# ============================================================
# Templates
# ============================================================

TEMPLATES: dict[str, dict[str, Any]] = {
    "static-site": {
        "name": "Static Website (S3 Only)",
        "description": "Host a static HTML/CSS/JS website on S3. Free tier eligible.",
        "services": {"enable_s3": True},
        "environment": "free-tier",
    },
    "backend-app": {
        "name": "Backend Application (VPC + EC2 + IAM)",
        "description": "EC2 instance with VPC networking and IAM role. Free tier eligible.",
        "services": {
            "enable_vpc": True,
            "enable_ec2": True,
            "enable_iam": True,
        },
        "environment": "free-tier",
    },
}


# ============================================================
# Input Helpers
# ============================================================

def prompt(message: str, default: str = "") -> str:
    """Prompt user for input with optional default value."""
    if default:
        raw = input(f"  {message} [{default}]: ").strip()
        return raw if raw else default
    return input(f"  {message}: ").strip()


def prompt_yes_no(message: str, default: bool = False) -> bool:
    """Prompt user for a yes/no answer."""
    suffix = "[Y/n]" if default else "[y/N]"
    raw = input(f"  {message} {suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def prompt_choice(message: str, choices: list[str]) -> str:
    """Prompt user to select from a list of choices."""
    print(f"\n  {message}")
    for i, choice in enumerate(choices, 1):
        print(f"    {i}. {choice}")
    while True:
        raw = input(f"  Enter choice (1-{len(choices)}): ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print(f"  ⚠️  Please enter a number between 1 and {len(choices)}")


# ============================================================
# Wizard Steps
# ============================================================

def display_welcome() -> None:
    """Display the wizard welcome banner."""
    print("\n" + "=" * 60)
    print("  🚀 Smart AWS Infrastructure Provisioning System")
    print("  ─────────────────────────────────────────────────")
    print("  Interactive CLI Wizard")
    print("=" * 60)
    print()
    print("  This wizard will help you:")
    print("    • Select and configure AWS services")
    print("    • Check security policies before deployment")
    print("    • Estimate monthly costs with Infracost")
    print("    • Deploy infrastructure with Terraform")
    print()


def step_select_template() -> Optional[str]:
    """Step 1-2: Ask user to select a template or go custom."""
    print("─" * 50)
    print("  📋 STEP 1: Select a Configuration")
    print("─" * 50)

    choices = []
    for key, tpl in TEMPLATES.items():
        choices.append(f"{tpl['name']} — {tpl['description']}")
    choices.append("Custom — Choose your own services")

    selected = prompt_choice("Choose a deployment option:", choices)

    if "Custom" in selected:
        return None

    # Find the template key
    for key, tpl in TEMPLATES.items():
        if tpl["name"] in selected:
            return key
    return None


def step_select_services(config: WizardConfig) -> None:
    """Step 3: Ask user which services to enable (custom mode only)."""
    print()
    print("─" * 50)
    print("  🔧 STEP 2: Select Services")
    print("─" * 50)
    print()

    config.enable_vpc = prompt_yes_no("Enable VPC (networking)?", default=True)
    config.enable_ec2 = prompt_yes_no("Enable EC2 (compute)?", default=True)
    config.enable_s3 = prompt_yes_no("Enable S3 (storage)?", default=False)
    config.enable_iam = prompt_yes_no("Enable IAM (roles & permissions)?", default=False)
    config.enable_cloudwatch = prompt_yes_no("Enable CloudWatch (monitoring)?", default=False)

    if not any([config.enable_vpc, config.enable_ec2, config.enable_s3,
                config.enable_iam, config.enable_cloudwatch]):
        print("\n  ⚠️  No services selected. At least one service is required.")
        step_select_services(config)


def step_select_environment(config: WizardConfig) -> None:
    """Step 4: Ask user for environment type."""
    print()
    print("─" * 50)
    print("  🌍 STEP 3: Select Environment")
    print("─" * 50)

    env = prompt_choice("Choose your environment:", ["free-tier", "production"])
    config.environment = env

    if env == "production":
        print("\n  ⚠️  Production environment selected.")
        print("     This may incur real AWS costs beyond the free tier.")
        if not prompt_yes_no("Continue with production?"):
            config.environment = "free-tier"
            print("  ✅  Switched to free-tier environment.")


def step_configure_services(config: WizardConfig) -> None:
    """Step 5: Configure each enabled service."""
    print()
    print("─" * 50)
    print("  ⚙️  STEP 4: Configure Services")
    print("─" * 50)
    print()

    # Region
    config.aws_region = prompt("AWS Region", default="ap-south-1")

    # VPC
    if config.enable_vpc:
        print("\n  [VPC Configuration]")
        config.vpc_cidr = prompt("VPC CIDR block", default="10.0.0.0/16")

    # EC2
    if config.enable_ec2:
        print("\n  [EC2 Configuration]")
        if config.environment == "free-tier":
            config.instance_type = "t2.micro"
            print("  ℹ️  Instance type locked to t2.micro (free tier)")
        else:
            config.instance_type = prompt("Instance type", default="t2.micro")

        config.ami_id = prompt(
            "AMI ID (Amazon Linux 2 for ap-south-1)",
            default="ami-0f58b397bc5c1f2e8"
        )

        # If EC2 is enabled but VPC is not, warn
        if not config.enable_vpc:
            print("  ⚠️  EC2 requires a VPC. Enabling VPC automatically.")
            config.enable_vpc = True
            config.vpc_cidr = prompt("VPC CIDR block", default="10.0.0.0/16")

    # S3
    if config.enable_s3:
        print("\n  [S3 Configuration]")
        config.bucket_name = prompt("S3 bucket name (must be globally unique)")
        while not config.bucket_name:
            print("  ⚠️  Bucket name is required.")
            config.bucket_name = prompt("S3 bucket name (must be globally unique)")
        print("  🔒  Public access: BLOCKED (enforced)")
        print("  🔒  Encryption: AES256 (enforced)")

    # IAM
    if config.enable_iam:
        print("\n  [IAM Configuration]")
        config.role_name = prompt("IAM role name", default="app-role")
        print("  🔒  Least privilege: enforced (no wildcard permissions)")

    # CloudWatch
    if config.enable_cloudwatch:
        print("\n  [CloudWatch Configuration]")
        config.alarm_email = prompt("Email for alarm notifications", default="")

    # Tags (always required by governance policy)
    print("\n  [Resource Tags — required by governance policy]")
    owner = prompt("Owner tag", default="developer")
    project = prompt("Project tag", default="aws-provisioner")
    config.tags = {
        "Owner": owner,
        "Project": project,
        "Env": config.environment,
    }

    # Budget
    print("\n  [Budget Configuration]")
    config.budget_limit = prompt("Monthly budget limit (USD)", default="1")
    config.budget_email = prompt("Email for billing alerts")
    while not config.budget_email:
        print("  ⚠️  Budget email is required for cost safety.")
        config.budget_email = prompt("Email for billing alerts")


def step_generate_tfvars(config: WizardConfig) -> str:
    """Step 6: Generate and write terraform.tfvars."""
    print()
    print("─" * 50)
    print("  📄 STEP 5: Generating terraform.tfvars")
    print("─" * 50)

    tfvars_content = config.to_tfvars()
    tfvars_path = Path(__file__).resolve().parent.parent / "terraform.tfvars"

    with open(tfvars_path, "w", encoding="utf-8") as f:
        f.write(tfvars_content)

    print(f"\n  ✅  Written to: {tfvars_path}")
    print("\n  Generated configuration:")
    print("  " + "-" * 40)
    for line in tfvars_content.strip().split("\n"):
        print(f"    {line}")
    print("  " + "-" * 40)

    return str(tfvars_path)


def step_run_policy_engine(config: WizardConfig) -> EvaluationResult:
    """Step 7: Run policy engine and display results."""
    print()
    print("─" * 50)
    print("  🛡️  STEP 6: Policy & Risk Check")
    print("─" * 50)
    print()

    rules_path = str(Path(__file__).resolve().parent.parent / "policy-engine" / "rules.yaml")

    try:
        engine = PolicyEngine(rules_path)
        policy_dict = config.to_policy_dict()
        result = engine.evaluate(policy_dict)
        engine.report(result)
        return result
    except FileNotFoundError:
        print("  ⚠️  Policy rules file not found. Skipping policy check.")
        return EvaluationResult()
    except Exception as e:
        print(f"  ⚠️  Policy engine error: {e}")
        return EvaluationResult()


def step_run_infracost() -> bool:
    """Step 8: Run Infracost to estimate monthly costs."""
    print()
    print("─" * 50)
    print("  💰 STEP 7: Cost Estimation (Infracost)")
    print("─" * 50)
    print()

    try:
        result = subprocess.run(
            ["infracost", "breakdown", "--path", ".", "--format", "table"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"  ⚠️  Infracost returned an error:")
            print(f"  {result.stderr.strip()}")
            return True  # Don't block deployment for infracost errors
    except FileNotFoundError:
        print("  ⚠️  Infracost is not installed. Skipping cost estimation.")
        print("     Install from: https://www.infracost.io/docs/")
        return True
    except subprocess.TimeoutExpired:
        print("  ⚠️  Infracost timed out. Skipping cost estimation.")
        return True


def _parse_plan_summary(plan_output: str) -> list[str]:
    """Extract only the resource names and summary line from terraform plan."""
    lines = []
    for line in plan_output.split("\n"):
        stripped = line.strip()
        # Capture resource-level summaries like "# module.s3.aws_s3_bucket.main[0] will be created"
        if stripped.startswith("#") and ("will be" in stripped or "must be" in stripped):
            # Clean up: "# module.s3.aws_s3_bucket.main[0] will be created" → readable
            resource_line = stripped.lstrip("# ").strip()
            if "will be created" in resource_line:
                name = resource_line.replace(" will be created", "")
                lines.append(f"    ＋ {name}")
            elif "will be updated" in resource_line:
                name = resource_line.replace(" will be updated in-place", "")
                lines.append(f"    ~ {name}")
            elif "will be destroyed" in resource_line:
                name = resource_line.replace(" will be destroyed", "")
                lines.append(f"    − {name}")
        # Capture the "Plan: X to add..." summary line
        elif stripped.startswith("Plan:"):
            lines.append(f"\n  {stripped}")
    return lines


def step_confirm_and_deploy() -> bool:
    """Step 9-11: Final confirmation and deployment."""
    print()
    print("─" * 50)
    print("  🚀 STEP 8: Deploy Infrastructure")
    print("─" * 50)
    print()

    if not prompt_yes_no("Ready to deploy? This will create real AWS resources.", default=False):
        print("\n  ❌  Deployment cancelled by user.")
        return False

    project_root = str(Path(__file__).resolve().parent.parent)

    # terraform init
    print("\n  ▶️  Running: terraform init...")
    init_result = subprocess.run(
        ["terraform", "init"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if init_result.returncode != 0:
        print(f"  ❌  terraform init failed:")
        print(f"  {init_result.stderr.strip()}")
        return False
    print("  ✅  terraform init complete.")

    # terraform plan
    print("\n  ▶️  Running: terraform plan...")
    plan_result = subprocess.run(
        ["terraform", "plan", "-input=false"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if plan_result.returncode != 0:
        print(f"  ❌  terraform plan failed:")
        print(f"  {plan_result.stderr.strip()}")
        return False

    # Show CLEAN summary instead of raw plan
    summary_lines = _parse_plan_summary(plan_result.stdout)
    if summary_lines:
        print("\n  📋 Resources to be created:")
        for line in summary_lines:
            print(line)
        print()
    else:
        print("  ✅  No changes needed.")

    # Final confirmation after seeing the plan
    if not prompt_yes_no("Apply this plan?", default=False):
        print("\n  ❌  Apply cancelled by user.")
        return False

    # terraform apply
    print("\n  ▶️  Deploying... (this may take 15-30 seconds)")
    apply_result = subprocess.run(
        ["terraform", "apply", "-auto-approve", "-input=false"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if apply_result.returncode != 0:
        print(f"  ❌  terraform apply failed:")
        print(f"  {apply_result.stderr.strip()}")
        return False

    # Show clean apply summary
    for line in apply_result.stdout.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Apply complete") or stripped.startswith("Outputs:"):
            print(f"  {stripped}")

    print("\n  ✅  Infrastructure deployed successfully!")

    # Show outputs
    print("\n  📋 Deployment Outputs:")
    output_result = subprocess.run(
        ["terraform", "output", "-json"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if output_result.returncode == 0 and output_result.stdout.strip():
        try:
            outputs = json.loads(output_result.stdout)
            for key, val in outputs.items():
                value = val.get("value", "N/A")
                if value is not None:
                    print(f"    {key}: {value}")
        except json.JSONDecodeError:
            print(output_result.stdout)

    return True


def step_destroy_prompt() -> None:
    """Prompt user to destroy resources after testing."""
    print()
    print("=" * 60)
    print("  ⚠️  COST SAFETY REMINDER")
    print("=" * 60)
    print()
    print("  AWS resources are now RUNNING and may incur charges.")
    print("  When you are done testing, run:")
    print()
    print("    terraform destroy")
    print()
    print("  Or run this wizard again with: python cli-wizard/wizard.py --destroy")
    print()


def handle_destroy() -> None:
    """Handle the --destroy flag to tear down infrastructure."""
    print("\n  🗑️  Destroying infrastructure...")
    project_root = str(Path(__file__).resolve().parent.parent)

    if not prompt_yes_no("Are you sure you want to destroy ALL resources?", default=False):
        print("  ❌  Destroy cancelled.")
        return

    print("\n  ▶️  Destroying... (this may take 15-30 seconds)")
    result = subprocess.run(
        ["terraform", "destroy", "-auto-approve"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if result.returncode == 0:
        # Show only the clean summary, not the full raw output
        for line in result.stdout.split("\n"):
            stripped = line.strip()
            if stripped.startswith("Destroy complete") or stripped.startswith("Plan:"):
                print(f"  {stripped}")
        print()
        print("  ✅  All resources destroyed successfully.")
        print("  💰  Your AWS bill: $0.00")
    else:
        print(f"  ❌  Destroy failed:")
        print(f"  {result.stderr.strip()}")


# ============================================================
# Main
# ============================================================

def main() -> None:
    """Entry point for the CLI wizard."""
    # Handle --destroy flag
    if len(sys.argv) > 1 and sys.argv[1] == "--destroy":
        handle_destroy()
        return

    # Step 1: Welcome
    display_welcome()

    # Step 2: Select template or custom
    template_key = step_select_template()

    config = WizardConfig()

    if template_key:
        # Apply template defaults
        tpl = TEMPLATES[template_key]
        print(f"\n  ✅  Selected template: {tpl['name']}")
        for key, value in tpl["services"].items():
            setattr(config, key, value)
        config.environment = tpl["environment"]
    else:
        # Custom: select services
        step_select_services(config)

    # Step 3: Environment (only for custom — templates have it preset)
    if not template_key:
        step_select_environment(config)

    # Step 4: Configure services
    step_configure_services(config)

    # Step 5: Generate terraform.tfvars
    step_generate_tfvars(config)

    # Step 6: Policy check
    policy_result = step_run_policy_engine(config)

    if policy_result.has_blocks():
        print("\n  🚫  DEPLOYMENT BLOCKED — Fix the violations above before proceeding.")
        print("  Exiting wizard.")
        sys.exit(1)

    if policy_result.has_warnings():
        if not prompt_yes_no("\n  Warnings found. Continue anyway?", default=True):
            print("  ❌  Deployment cancelled by user.")
            sys.exit(0)

    # Step 7: Cost estimate
    step_run_infracost()

    # Step 8: Deploy
    deployed = step_confirm_and_deploy()

    if deployed:
        step_destroy_prompt()

    print("\n  👋  Wizard complete. Goodbye!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  ⚠️  Wizard interrupted by user (Ctrl+C)")
        print("  👋  Goodbye!\n")
        sys.exit(0)
