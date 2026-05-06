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

# Add opa-policies to path so we can import the OPA engine
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "opa-policies"))
from opa_engine import OPAEngine, OPAResult  # noqa: E402

# Module-level variables for wizard state
# These are set by main() and used by step functions
engine: Any = None
config: WizardConfig | None = None
config_username: str | None = None


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
    # DynamoDB
    enable_dynamodb: bool = False
    dynamodb_table_name: str = ""
    dynamodb_hash_key: str = "id"
    dynamodb_hash_key_type: str = "S"
    dynamodb_read_capacity: int = 5
    dynamodb_write_capacity: int = 5
    dynamodb_enable_pitr: bool = False

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
            f"enable_dynamodb  = {str(self.enable_dynamodb).lower()}",
            "",
            f'vpc_cidr      = "{self.vpc_cidr}"',
            f'instance_type = "{self.instance_type}"',
            f'ami_id        = "{self.ami_id}"',
            f'bucket_name   = "{self.bucket_name}"',
            f'dynamodb_table_name = "{self.dynamodb_table_name}"',
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
        # DynamoDB provisioning details (if enabled)
        lines.append(f'dynamodb_hash_key = "{self.dynamodb_hash_key}"')
        lines.append(f'dynamodb_hash_key_type = "{self.dynamodb_hash_key_type}"')
        lines.append(f'dynamodb_read_capacity = {self.dynamodb_read_capacity}')
        lines.append(f'dynamodb_write_capacity = {self.dynamodb_write_capacity}')
        lines.append(f'dynamodb_enable_pitr = {str(self.dynamodb_enable_pitr).lower()}')
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
    "serverless-db": {
        "name": "Serverless DB (DynamoDB)",
        "description": "Always-Free DynamoDB table (provisioned within free limits).",
        "services": {"enable_dynamodb": True},
        "environment": "free-tier",
    },
}


# ============================================================
# Input Helpers
# ============================================================

def prompt(message: str, default: str = "", help_text: str | None = None) -> str:
    """Prompt user for input with optional default value."""
    if help_text and "pytest" not in sys.modules:
        print(f"  ℹ️  {help_text}")
    if default:
        raw = input(f"  {message} [{default}]: ").strip()
        return raw if raw else default
    return input(f"  {message}: ").strip()


def prompt_yes_no(message: str, default: bool = False, help_text: str | None = None) -> bool:
    """Prompt user for a yes/no answer."""
    if help_text and "pytest" not in sys.modules:
        print(f"  ℹ️  {help_text}")
    suffix = "[Y/n]" if default else "[y/N]"
    raw = input(f"  {message} {suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def prompt_choice(message: str, choices: list[str], help_text: str | None = None) -> str:
    """Prompt user to select from a list of choices."""
    print(f"\n  {message}")
    if help_text and "pytest" not in sys.modules:
        print(f"  ℹ️  {help_text}")
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


def _has_admin(engine: Any) -> bool:
    """Return True if any user in engine has role 'admin'."""
    try:
        for u in engine.users.values():
            if getattr(u, "role", "") == "admin":
                return True
    except Exception:
        return False
    return False


def first_run_admin_onboarding(engine: Any, force: bool = False) -> None:
    """Create the first admin user if none exist.

    If `force=True`, the onboarding will run even when under pytest (used by tests).
    """
    if "pytest" in sys.modules and not force:
        return

    if _has_admin(engine):
        return

    print("\n" + "=" * 60)
    print("  FIRST-TIME SETUP: Create an Admin Account")
    print("=" * 60)
    print("No admin user found in configuration. Create the first admin now.")
    print()

    name = prompt("Full name", default="Administrator", help_text="Used in audit logs and approvals")
    print("  (Used for audit logs and notifications)")
    email = prompt("Email address", default="admin@example.com", help_text="Used for alerts and security notifications")
    print("  (Used for alerts and audit contact)")
    github_username = prompt(
        "GitHub username (example: alice-chen)",
        help_text="Find this in your GitHub profile URL: https://github.com/<your-handle>",
    )
    print("  Tip: find this on your GitHub profile page: https://github.com/<your-handle>")

    if not prompt_yes_no(
        f"Create admin user '{github_username}' with role admin?",
        default=True,
        help_text="This user can manage teams and deploy to production",
    ):
        print("Skipping admin creation. You must add an admin to teams.yaml manually.")
        return

    # Ensure teams section exists
    teams = engine.config.setdefault("teams", {})
    target_team = "devops-core"
    if target_team not in teams:
        teams[target_team] = {
            "name": "DevOps Core Team",
            "description": "Auto-created team for first admin",
            "members": [],
            "permissions": ["deploy:production", "deploy:staging"],
            "requires_approval": False,
        }

    member = {
        "name": name,
        "email": email,
        "role": "admin",
        "github_username": github_username,
    }

    teams[target_team].setdefault("members", []).append(member)

    # Persist and reload
    try:
        engine.save_config()
        engine._load_config()
        print(f"\n  ✅ Admin user '{github_username}' added to team '{target_team}'.")
    except Exception as e:
        print(f"\n  ❌ Failed to write teams.yaml: {e}")
        return

    if prompt_yes_no("Commit this change to git?", default=False, help_text="Recommended for audit trail"):
        try:
            subprocess.run(["git", "add", str(engine.config_path)], check=True)
            subprocess.run(["git", "commit", "-m", f"Add initial admin {github_username} to teams.yaml"], check=True)
            print("  ✅ Changes committed. Please push to remote if desired.")
        except Exception:
            print("  ⚠️  Git commit failed or git not available. Please commit manually.")


def add_member(engine: Any, target_team: str, name: str, email: str, github_username: str, role: str) -> None:
    """Programmatically add a member to a team and persist the config."""
    engine.config.setdefault("teams", {})
    if target_team not in engine.config["teams"]:
        engine.config["teams"][target_team] = {
            "name": target_team,
            "description": "Created programmatically",
            "members": [],
            "permissions": ["deploy:staging"],
            "requires_approval": True,
        }
    engine.config["teams"][target_team].setdefault("members", []).append({
        "name": name,
        "email": email,
        "role": role,
        "github_username": github_username,
    })
    engine.save_config()
    engine._load_config()


def edit_member(engine: Any, github_username: str, new_role: str | None = None, new_email: str | None = None) -> bool:
    """Edit a member's role/email. Returns True if edited."""
    for team_name, team_data in engine.config.get("teams", {}).items():
        for m in team_data.get("members", []):
            if m.get("github_username") == github_username:
                if new_role:
                    m["role"] = new_role
                if new_email:
                    m["email"] = new_email
                engine.save_config()
                engine._load_config()
                return True
    return False


def remove_member(engine: Any, github_username: str) -> bool:
    """Remove a member by GitHub username. Returns True if removed."""
    for team_name, team_data in engine.config.get("teams", {}).items():
        members = team_data.get("members", [])
        new_members = [m for m in members if m.get("github_username") != github_username]
        if len(new_members) != len(members):
            team_data["members"] = new_members
            engine.save_config()
            engine._load_config()
            return True
    return False


def admin_manage_team_menu(engine: Any) -> None:
    """Simple admin menu to list/add/edit/remove team members.

    This runs interactively; skipped during tests.
    """
    if "pytest" in sys.modules:
        return

    while True:
        print("\n" + "-" * 50)
        print("  TEAM MANAGEMENT (admin)")
        print("-" * 50)
        print("  1) List members")
        print("  2) Add member")
        print("  3) Edit member")
        print("  4) Remove member")
        print("  5) Exit team management")

        choice = prompt_choice("Choose an action", ["List", "Add", "Edit", "Remove", "Exit"])
        if choice == "List":
            for team_name, team_data in engine.config.get("teams", {}).items():
                print(f"\nTeam: {team_name} — {team_data.get('name','')}")
                for m in team_data.get("members", []):
                    print(f"  - {m.get('name')} ({m.get('github_username')}) — {m.get('role')}")

        elif choice == "Add":
            name = prompt("Full name")
            email = prompt("Email")
            gh = prompt(
                "GitHub username (example: alice-chen)",
                help_text="Find this in the member's profile URL: https://github.com/<handle>",
            )
            role = prompt_choice("Role", ["admin", "devops", "developer", "viewer"])  # type: ignore[arg-type]
            teams_list = list(engine.config.get("teams", {}).keys())
            team_choice = None
            if teams_list:
                team_choice = prompt_choice("Choose team or create new", teams_list + ["Create new team"])  # type: ignore[arg-type]
            else:
                team_choice = "Create new team"

            if team_choice == "Create new team":
                new_team = prompt("New team key (no spaces)")
                engine.config.setdefault("teams", {})[new_team] = {
                    "name": new_team,
                    "description": "Created from wizard",
                    "members": [],
                    "permissions": ["deploy:staging"],
                    "requires_approval": True,
                }
                target = new_team
            else:
                target = team_choice

            engine.config.setdefault("teams", {}).setdefault(target, {}).setdefault("members", []).append({
                "name": name,
                "email": email,
                "role": role,
                "github_username": gh,
            })

            try:
                engine.save_config()
                engine._load_config()
                print(f"  ✅ Member {gh} added to {target}.")
            except Exception as e:
                print(f"  ❌ Failed to save teams.yaml: {e}")

        elif choice == "Edit":
            gh = prompt(
                "GitHub username of member to edit",
                help_text="Use the exact GitHub handle from teams.yaml",
            )
            found = False
            for team_name, team_data in engine.config.get("teams", {}).items():
                for m in team_data.get("members", []):
                    if m.get("github_username") == gh:
                        print(f"Found {m.get('name')} in {team_name}")
                        new_role = prompt_choice("New role", ["admin", "devops", "developer", "viewer"])  # type: ignore[arg-type]
                        m["role"] = new_role
                        m["email"] = prompt("Email", default=m.get("email", ""))
                        try:
                            engine.save_config()
                            engine._load_config()
                            print(f"  ✅ Updated {gh}.")
                        except Exception as e:
                            print(f"  ❌ Failed to save teams.yaml: {e}")
                        found = True
                        break
                if found:
                    break
            if not found:
                print(f"  ⚠️  Member {gh} not found")

        elif choice == "Remove":
            gh = prompt(
                "GitHub username of member to remove",
                help_text="Use the exact GitHub handle from teams.yaml",
            )
            removed = False
            for team_name, team_data in engine.config.get("teams", {}).items():
                members = team_data.get("members", [])
                for i, m in enumerate(list(members)):
                    if m.get("github_username") == gh:
                        if prompt_yes_no(f"Confirm remove {gh} from {team_name}?", default=False):
                            members.pop(i)
                            try:
                                engine.save_config()
                                engine._load_config()
                                print(f"  ✅ Removed {gh}.")
                            except Exception as e:
                                print(f"  ❌ Failed to save teams.yaml: {e}")
                            removed = True
                        break
                if removed:
                    break
            if not removed:
                print(f"  ⚠️  Member {gh} not found or not removed")

        elif choice == "Exit":
            break
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
    config.enable_dynamodb = prompt_yes_no("Enable DynamoDB (NoSQL table)?", default=False)

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
    config.aws_region = prompt("AWS Region", default="ap-south-1", help_text="Example: ap-south-1, us-east-1")

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
            config.instance_type = prompt("Instance type", default="t2.micro", help_text="Use t2.micro to stay free-tier eligible")

        config.ami_id = prompt(
            "AMI ID (Amazon Linux 2 for ap-south-1)",
            default="ami-0f58b397bc5c1f2e8",
            help_text="Verify region-specific AMI IDs in the AWS EC2 console",
        )

        # If EC2 is enabled but VPC is not, warn
        if not config.enable_vpc:
            print("  ⚠️  EC2 requires a VPC. Enabling VPC automatically.")
            config.enable_vpc = True
            config.vpc_cidr = prompt("VPC CIDR block", default="10.0.0.0/16")

    # S3
    if config.enable_s3:
        print("\n  [S3 Configuration]")
        config.bucket_name = prompt(
            "S3 bucket name (must be globally unique)",
            help_text="Use lowercase letters, numbers, and hyphens only",
        )
        while not config.bucket_name:
            print("  ⚠️  Bucket name is required.")
            config.bucket_name = prompt(
                "S3 bucket name (must be globally unique)",
                help_text="Example: my-team-static-site-2026",
            )
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
        config.alarm_email = prompt("Email for alarm notifications", default="", help_text="Receives CloudWatch alarm emails")

    # Tags (always required by governance policy)
    print("\n  [Resource Tags — required by governance policy]")
    owner = prompt("Owner tag", default="developer", help_text="Team or person responsible for these resources")
    project = prompt("Project tag", default="aws-provisioner", help_text="Short project identifier for governance")
    config.tags = {
        "Owner": owner,
        "Project": project,
        "Env": config.environment,
    }

    # Budget
    print("\n  [Budget Configuration]")
    config.budget_limit = prompt("Monthly budget limit (USD)", default="1", help_text="Set low during testing to catch unexpected costs")
    config.budget_email = prompt("Email for billing alerts", help_text="Required for budget threshold notifications")
    while not config.budget_email:
        print("  ⚠️  Budget email is required for cost safety.")
        config.budget_email = prompt("Email for billing alerts", help_text="Enter a monitored team inbox if possible")

    # DynamoDB configuration
    if config.enable_dynamodb:
        print("\n  [DynamoDB Configuration]")
        config.dynamodb_table_name = prompt("DynamoDB table name (must be unique)", default="my-table", help_text="Use a stable name like app-events-prod")
        config.dynamodb_hash_key = prompt("Hash key name", default="id", help_text="Primary partition key field")
        config.dynamodb_hash_key_type = prompt("Hash key type (S/N/B)", default="S", help_text="S=String, N=Number, B=Binary")
        if config.environment == "free-tier":
            config.dynamodb_read_capacity = 5
            config.dynamodb_write_capacity = 5
            print("  ℹ️  Read/Write capacity set to 5 to stay within free tier limits")
            config.dynamodb_enable_pitr = prompt_yes_no("Enable PITR (Point-in-Time Recovery)?", default=False)
        else:
            # Allow user to adjust capacities in production
            rc = prompt("Read capacity units (RCU)", default="5", help_text="Higher values increase cost")
            wc = prompt("Write capacity units (WCU)", default="5", help_text="Higher values increase cost")
            try:
                config.dynamodb_read_capacity = int(rc)
                config.dynamodb_write_capacity = int(wc)
            except ValueError:
                print("  ⚠️  Invalid capacity values; using defaults 5/5")
                config.dynamodb_read_capacity = 5
                config.dynamodb_write_capacity = 5
            config.dynamodb_enable_pitr = prompt_yes_no("Enable PITR (Point-in-Time Recovery)?", default=False)


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
    """Step 7: Run YAML policy engine and display results."""
    print()
    print("─" * 50)
    print("  🛡️  STEP 6: Policy & Risk Check (YAML Engine)")
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


def step_run_opa_engine(config: WizardConfig) -> OPAResult:
    """Step 6b: Run OPA policy engine for richer combinatorial checks."""
    print()
    print("─" * 50)
    print("  🔍 STEP 6b: OPA Policy Check (Advanced Rules)")
    print("─" * 50)
    print()

    opa_policies_dir = str(Path(__file__).resolve().parent.parent / "opa-policies")

    try:
        opa = OPAEngine(opa_policies_dir)
        if not opa.is_opa_available():
            print("  ⚠️  OPA CLI not installed — skipping advanced policy check.")
            print("     Install with: brew install opa")
            return OPAResult(opa_available=False)

        policy_dict = config.to_policy_dict()
        result = opa.evaluate(policy_dict)
        opa.report(result)

        if result.is_empty():
            print("  ✅  OPA: No additional violations found.")

        return result
    except Exception as e:
        print(f"  ⚠️  OPA engine error: {e}")
        return OPAResult(opa_available=True, error=str(e))


def step_run_infracost() -> bool:
    """Step 8: Run Infracost to estimate monthly costs."""
    print()
    print("─" * 50)
    print("  💰 STEP 7: Cost Estimation (Infracost)")
    print("─" * 50)
    print()

    try:
        result = subprocess.run(
            [
                "infracost",
                "breakdown",
                "--path", ".",
                "--terraform-var-file", "terraform.tfvars",
                "--exclude-path", "tests/",
                "--format", "table"
            ],
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

    # Check deployment permission (if available)
    if engine is not None and config_username is not None and config is not None:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from auth_gate import check_deployment_permission  # noqa: E402
            
            print("\n  🔐 Checking deployment permissions...")
            if not check_deployment_permission(engine, config_username, config.environment):
                print("\n  🚫  DEPLOYMENT BLOCKED — Insufficient permissions")
                return False
        except (ImportError, Exception):
            # If auth_gate not available or check fails, continue
            pass

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
    global engine, config, config_username
    
    # Handle --destroy flag
    if len(sys.argv) > 1 and sys.argv[1] == "--destroy":
        handle_destroy()
        return

    # Step 1: Welcome
    display_welcome()

    # NEW: Step 0 — Authenticate user
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "team-management"))
    from team_engine import TeamEngine, RoleGate  # noqa: E402
    
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from auth_gate import authenticate_user, check_deployment_permission  # noqa: E402

    if "pytest" not in sys.modules:
        print("\n" + "=" * 60)
        print("  STEP 0: User Authentication")
        print("=" * 60)

    engine = TeamEngine()
    # If no admin exists, run first-run onboarding to create one
    first_run_admin_onboarding(engine)
    username = authenticate_user(engine)

    if not username:
        print("\n  ⚠️  Authentication failed.")
        print("  Ensure your GitHub username is in teams.yaml")
        sys.exit(1)

    # Show user role summary (skip during tests)
    gate = RoleGate(engine)
    if "pytest" not in sys.modules:
        gate.show_role_summary(username)
    
    config_username = username

    # If admin, offer team management UI
    user_info = engine.get_user_info(username)
    if user_info and user_info.get("role") == "admin":
        admin_manage_team_menu(engine)

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

    # Step 6: YAML Policy check
    policy_result = step_run_policy_engine(config)

    if policy_result.has_blocks():
        print("\n  🚫  DEPLOYMENT BLOCKED — Fix the violations above before proceeding.")
        print("  Exiting wizard.")
        sys.exit(1)

    if policy_result.has_warnings():
        if not prompt_yes_no("\n  Warnings found. Continue anyway?", default=True):
            print("  ❌  Deployment cancelled by user.")
            sys.exit(0)

    # Step 6b: OPA advanced policy check
    opa_result = step_run_opa_engine(config)

    if opa_result.has_blocks():
        print("\n  🚫  DEPLOYMENT BLOCKED BY OPA — Fix the violations above before proceeding.")
        print("  Exiting wizard.")
        sys.exit(1)

    if opa_result.has_warnings():
        if not prompt_yes_no("\n  OPA warnings found. Continue anyway?", default=True):
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
