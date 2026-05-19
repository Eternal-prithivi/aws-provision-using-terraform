"""web-ui/api/server.py — FastAPI backend for the Web UI Dashboard.

Thin REST wrapper over existing Python modules:
- policy-engine/engine.py   → YAML policy evaluation
- opa-policies/opa_engine.py → OPA policy evaluation
- team-management/team_engine.py → RBAC + team management
- team-management/audit.py  → Audit logging
- cli-wizard/wizard.py      → WizardConfig + tfvars generation
- drift-detection/remediation.py → Drift status

Usage:
    cd web-ui/api && uvicorn server:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ─── Terminal Router (Phase 16) ───
from terminal import terminal_router

# ─── Add project paths so we can import existing modules ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "policy-engine"))
sys.path.insert(0, str(PROJECT_ROOT / "opa-policies"))
sys.path.insert(0, str(PROJECT_ROOT / "team-management"))
sys.path.insert(0, str(PROJECT_ROOT / "cli-wizard"))
sys.path.insert(0, str(PROJECT_ROOT / "drift-detection"))

from engine import EvaluationResult, PolicyEngine, Violation  # noqa: E402
from opa_engine import OPAEngine, OPAResult  # noqa: E402
from team_engine import TeamEngine  # noqa: E402
from audit import AuditLogger  # noqa: E402

# ─── Pydantic Models ───


class ConfigPayload(BaseModel):
    """Infrastructure configuration submitted from the wizard UI."""

    aws_region: str = "ap-south-1"
    enable_vpc: bool = False
    enable_ec2: bool = False
    enable_s3: bool = False
    enable_iam: bool = False
    enable_cloudwatch: bool = False
    enable_dynamodb: bool = False
    vpc_cidr: str = "10.0.0.0/16"
    instance_type: str = "t2.micro"
    instance_name: str = "main-instance"
    ami_id: str = ""
    bucket_name: str = ""
    role_name: str = "app-role"
    alarm_email: str = ""
    budget_limit: str = "1"
    budget_email: str = ""
    dynamodb_table_name: str = ""
    dynamodb_hash_key: str = "id"
    dynamodb_hash_key_type: str = "S"
    dynamodb_read_capacity: int = 5
    dynamodb_write_capacity: int = 5
    dynamodb_enable_pitr: bool = False
    tags: dict[str, str] = {}
    environment: str = "free-tier"


class AddUserPayload(BaseModel):
    """Payload for adding a new team member."""

    name: str
    email: str
    github_username: str
    role: str = "developer"
    team: str = "infrastructure"


# ─── App Setup ───

app = FastAPI(
    title="AWS Provisioning Dashboard API",
    version="1.0.0",
    description="REST API for the Smart AWS Infrastructure Provisioning Web UI",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Mount Terminal Router (Phase 16 — CloudShell) ───
app.include_router(terminal_router)


# ─── Auth Models ───


class LoginPayload(BaseModel):
    """GitHub token or username for authentication."""

    github_token: str = ""
    username: str = ""


# ─── Auth Endpoints ───


@app.post("/api/auth/login")
async def auth_login(payload: LoginPayload) -> dict[str, Any]:
    """Authenticate via GitHub token or fallback username lookup."""
    try:
        # Try GitHub token first
        if payload.github_token:
            try:
                import requests as req

                headers = {
                    "Authorization": f"token {payload.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                resp = req.get("https://api.github.com/user", headers=headers, timeout=10)
                if resp.status_code == 200:
                    gh_user = resp.json()
                    username = gh_user.get("login", "")
                    # Check if user exists in teams.yaml
                    engine = _get_team_engine()
                    info = engine.get_user_info(username)
                    if info:
                        return {
                            "authenticated": True,
                            "method": "github_token",
                            "username": username,
                            "name": info["name"],
                            "role": info["role"],
                            "role_name": info["role_name"],
                            "permissions": info["permissions"],
                            "teams": info["teams"],
                            "avatar_url": gh_user.get("avatar_url", ""),
                        }
                    else:
                        return {
                            "authenticated": True,
                            "method": "github_token",
                            "username": username,
                            "name": gh_user.get("name", username),
                            "role": "viewer",
                            "role_name": "Viewer",
                            "permissions": ["audit:read"],
                            "teams": [],
                            "avatar_url": gh_user.get("avatar_url", ""),
                            "warning": f"User '{username}' not in teams.yaml — assigned viewer role",
                        }
                else:
                    return {"authenticated": False, "error": "Invalid GitHub token"}
            except ImportError:
                return {"authenticated": False, "error": "requests library not installed"}
            except Exception as e:
                return {"authenticated": False, "error": f"GitHub API error: {str(e)}"}

        # Fallback: username lookup in teams.yaml
        if payload.username:
            engine = _get_team_engine()
            info = engine.get_user_info(payload.username)
            if info:
                return {
                    "authenticated": True,
                    "method": "username_lookup",
                    "username": payload.username,
                    "name": info["name"],
                    "role": info["role"],
                    "role_name": info["role_name"],
                    "permissions": info["permissions"],
                    "teams": info["teams"],
                    "avatar_url": "",
                }
            else:
                return {"authenticated": False, "error": f"User '{payload.username}' not found in teams.yaml"}

        return {"authenticated": False, "error": "Provide a GitHub token or username"}
    except Exception as e:
        return {"authenticated": False, "error": str(e)}


# ─── Helper Functions ───


def _get_policy_engine() -> PolicyEngine:
    """Create a PolicyEngine instance pointing at the project rules."""
    rules_path = str(PROJECT_ROOT / "policy-engine" / "rules.yaml")
    return PolicyEngine(rules_path)


def _get_opa_engine() -> OPAEngine:
    """Create an OPAEngine instance pointing at the project rego policies."""
    return OPAEngine(str(PROJECT_ROOT / "opa-policies"))


def _get_team_engine() -> TeamEngine:
    """Create a TeamEngine instance from the project teams.yaml."""
    return TeamEngine()


def _get_audit_logger() -> AuditLogger:
    """Create an AuditLogger instance."""
    return AuditLogger()


def _audit_log(action: str, status: str, details: dict[str, Any] | None = None, environment: str = "free-tier") -> None:
    """Convenience helper to log an audit event."""
    try:
        logger = _get_audit_logger()
        logger.log_event(
            action=action,
            actor="web-ui",
            environment=environment,
            deployment_id=f"web-{int(__import__('time').time())}",
            status=status,
            details=details or {},
        )
    except Exception:
        pass  # Never let audit logging break the main flow


def _config_to_policy_dict(config: ConfigPayload) -> dict[str, Any]:
    """Convert a ConfigPayload to the dict format expected by policy engines."""
    return {
        "s3_bucket_public": False,
        "ssh_open_to_world": False,
        "rdp_open_to_world": False,
        "iam_wildcard": False,
        "instance_type": config.instance_type,
        "s3_encryption": True,
        "tags": config.tags if config.tags else {},
        "cloudtrail_enabled": config.environment == "production",
        "environment": config.environment,
        "enable_s3": config.enable_s3,
        "bucket_name": config.bucket_name,
        "budget_limit": config.budget_limit,
        "enable_cloudwatch": config.enable_cloudwatch,
        "enable_ec2": config.enable_ec2,
        "vpc_cidr": config.vpc_cidr,
        "enable_vpc": config.enable_vpc,
    }


def _config_to_tfvars(config: ConfigPayload) -> str:
    """Convert a ConfigPayload to terraform.tfvars string format."""
    lines: list[str] = [
        f'aws_region = "{config.aws_region}"',
        "",
        f"enable_vpc        = {str(config.enable_vpc).lower()}",
        f"enable_ec2        = {str(config.enable_ec2).lower()}",
        f"enable_s3         = {str(config.enable_s3).lower()}",
        f"enable_iam        = {str(config.enable_iam).lower()}",
        f"enable_cloudwatch = {str(config.enable_cloudwatch).lower()}",
        f"enable_dynamodb   = {str(config.enable_dynamodb).lower()}",
        "",
        f'vpc_cidr      = "{config.vpc_cidr}"',
        f'instance_type = "{config.instance_type}"',
        f'instance_name = "{config.instance_name}"',
        f'ami_id        = "{config.ami_id}"',
        f'bucket_name   = "{config.bucket_name}"',
        f'dynamodb_table_name = "{config.dynamodb_table_name}"',
        f'role_name     = "{config.role_name}"',
        f'alarm_email   = "{config.alarm_email}"',
        "",
        f'budget_limit = "{config.budget_limit}"',
        f'budget_email = "{config.budget_email}"',
        "",
        "tags = {",
    ]
    for key, value in config.tags.items():
        lines.append(f'  {key} = "{value}"')
    lines.append("}")
    lines.append("")
    lines.append(f'dynamodb_hash_key = "{config.dynamodb_hash_key}"')
    lines.append(f'dynamodb_hash_key_type = "{config.dynamodb_hash_key_type}"')
    lines.append(f"dynamodb_read_capacity = {config.dynamodb_read_capacity}")
    lines.append(f"dynamodb_write_capacity = {config.dynamodb_write_capacity}")
    lines.append(f"dynamodb_enable_pitr = {str(config.dynamodb_enable_pitr).lower()}")
    lines.append("")
    return "\n".join(lines)


def _serialize_violation(v: Violation) -> dict[str, str]:
    """Serialize a policy Violation to a JSON-safe dict."""
    return {
        "rule_name": v.rule_name,
        "description": v.description,
        "severity": v.severity,
    }


async def _stream_terraform_command(command: list[str], audit_action: str = "") -> Any:
    """Stream terraform command output as Server-Sent Events."""
    if audit_action:
        _audit_log(audit_action, "started", {"command": " ".join(command)})

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
    )

    async def event_generator() -> Any:
        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            yield f"data: {json.dumps({'line': text})}\n\n"

        return_code = await process.wait()
        if audit_action:
            _audit_log(
                audit_action,
                "success" if return_code == 0 else "failed",
                {"command": " ".join(command), "exit_code": return_code},
            )
        yield f"data: {json.dumps({'done': True, 'exit_code': return_code})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ═══════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════


# ── Health ──


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


# ── Dashboard ──


@app.get("/api/dashboard")
async def dashboard() -> dict[str, Any]:
    """Return dashboard overview data."""
    # Read current terraform.tfvars to determine enabled services
    tfvars_path = PROJECT_ROOT / "terraform.tfvars"
    services: dict[str, bool] = {
        "vpc": False,
        "ec2": False,
        "s3": False,
        "iam": False,
        "cloudwatch": False,
        "dynamodb": False,
    }

    if tfvars_path.exists():
        content = tfvars_path.read_text(encoding="utf-8")
        for svc in services:
            if f"enable_{svc}" in content:
                services[svc] = f"enable_{svc} = true" in content.replace(" ", "").replace("=", " = ")
                # More robust check
                for line in content.split("\n"):
                    stripped = line.strip().replace(" ", "")
                    if stripped.startswith(f"enable_{svc}=true"):
                        services[svc] = True
                    elif stripped.startswith(f"enable_{svc}=false"):
                        services[svc] = False

    # Drift status
    drift_status = "unknown"
    drift_report_path = PROJECT_ROOT / "drift-report.txt"
    if drift_report_path.exists():
        drift_text = drift_report_path.read_text(encoding="utf-8")
        if "NO DRIFT" in drift_text.upper() or "NO DRIFT DETECTED" in drift_text.upper():
            drift_status = "clean"
        elif "DRIFT DETECTED" in drift_text.upper():
            drift_status = "drift_detected"

    # Policy health — run a quick check on current config
    policy_health = {"blocks": 0, "warnings": 0, "status": "unknown"}
    try:
        pe = _get_policy_engine()
        policy_dict = _config_to_policy_dict(ConfigPayload())
        result = pe.evaluate(policy_dict)
        policy_health = {
            "blocks": len(result.violations),
            "warnings": len(result.warnings),
            "status": "blocked" if result.has_blocks() else ("warnings" if result.has_warnings() else "clean"),
        }
    except Exception:
        pass

    # Recent audit events
    recent_events: list[dict[str, Any]] = []
    try:
        logger = _get_audit_logger()
        events = logger.read_events(limit=5)
        recent_events = [
            {
                "timestamp": e.timestamp,
                "action": e.action,
                "actor": e.actor,
                "environment": e.environment,
                "status": e.status,
            }
            for e in events
        ]
    except Exception:
        pass

    return {
        "services": services,
        "active_count": sum(1 for v in services.values() if v),
        "policy_health": policy_health,
        "drift_status": drift_status,
        "recent_events": recent_events,
    }


# ── Deploy Wizard ──


@app.get("/api/templates")
async def get_templates() -> list[dict[str, Any]]:
    """Return available deployment templates."""
    return [
        {
            "key": "static-site",
            "name": "Static Website (S3 Only)",
            "description": "Host a static HTML/CSS/JS website on S3. Free tier eligible.",
            "services": {"enable_s3": True},
            "environment": "free-tier",
            "icon": "globe",
        },
        {
            "key": "backend-app",
            "name": "Backend Application (VPC + EC2 + IAM)",
            "description": "EC2 instance with VPC networking and IAM role. Free tier eligible.",
            "services": {"enable_vpc": True, "enable_ec2": True, "enable_iam": True},
            "environment": "free-tier",
            "icon": "server",
        },
        {
            "key": "serverless-db",
            "name": "Serverless DB (DynamoDB)",
            "description": "Always-Free DynamoDB table (provisioned within free limits).",
            "services": {"enable_dynamodb": True},
            "environment": "free-tier",
            "icon": "database",
        },
    ]


@app.post("/api/config/validate")
async def validate_config(config: ConfigPayload) -> dict[str, Any]:
    """Validate config against policy engines."""
    policy_dict = _config_to_policy_dict(config)

    # YAML engine
    yaml_result: dict[str, Any] = {"blocks": [], "warnings": [], "error": None}
    try:
        pe = _get_policy_engine()
        result = pe.evaluate(policy_dict)
        yaml_result["blocks"] = [_serialize_violation(v) for v in result.violations]
        yaml_result["warnings"] = [_serialize_violation(v) for v in result.warnings]
    except Exception as e:
        yaml_result["error"] = str(e)

    # OPA engine
    opa_result_dict: dict[str, Any] = {"blocks": [], "warnings": [], "available": True, "error": None}
    try:
        opa = _get_opa_engine()
        if not opa.is_opa_available():
            opa_result_dict["available"] = False
            opa_result_dict["error"] = "OPA CLI not installed"
        else:
            opa_res = opa.evaluate(policy_dict)
            opa_result_dict["blocks"] = opa_res.blocks
            opa_result_dict["warnings"] = opa_res.warnings
    except Exception as e:
        opa_result_dict["error"] = str(e)

    total_blocks = len(yaml_result["blocks"]) + len(opa_result_dict["blocks"])
    total_warnings = len(yaml_result["warnings"]) + len(opa_result_dict["warnings"])

    can_deploy = total_blocks == 0
    _audit_log("policy_check", "success" if can_deploy else "blocked", {"blocks": total_blocks, "warnings": total_warnings})

    return {
        "yaml": yaml_result,
        "opa": opa_result_dict,
        "summary": {
            "total_blocks": total_blocks,
            "total_warnings": total_warnings,
            "can_deploy": can_deploy,
        },
    }


@app.post("/api/config/generate-tfvars")
async def generate_tfvars(config: ConfigPayload) -> dict[str, str]:
    """Generate terraform.tfvars content from config."""
    tfvars_content = _config_to_tfvars(config)

    # Also write to disk
    tfvars_path = PROJECT_ROOT / "terraform.tfvars"
    tfvars_path.write_text(tfvars_content, encoding="utf-8")

    services = [s for s in ["vpc","ec2","s3","iam","cloudwatch","dynamodb"] if getattr(config, f"enable_{s}", False)]
    _audit_log("generate_tfvars", "success", {"services": services, "region": config.aws_region}, config.environment)

    return {"tfvars": tfvars_content, "path": str(tfvars_path)}


@app.post("/api/cost-estimate")
async def cost_estimate() -> dict[str, Any]:
    """Run infracost on current terraform.tfvars."""
    try:
        result = subprocess.run(
            [
                "infracost", "breakdown",
                "--path", str(PROJECT_ROOT),
                "--terraform-var-file", "terraform.tfvars",
                "--exclude-path", "tests/",
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            return {"error": result.stderr.strip(), "available": False}

        data = json.loads(result.stdout)
        total = data.get("totalMonthlyCost", "0.00")
        projects = data.get("projects", [])

        resources: list[dict[str, Any]] = []
        if projects:
            for res in projects[0].get("breakdown", {}).get("resources", []):
                resources.append({
                    "name": res.get("name", ""),
                    "monthly_cost": res.get("monthlyCost", "0.00"),
                    "hourly_cost": res.get("hourlyCost", "0.00"),
                })

        return {
            "available": True,
            "total_monthly_cost": total,
            "currency": "USD",
            "resources": resources,
        }

    except FileNotFoundError:
        return {"available": False, "error": "Infracost CLI not installed"}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "Infracost timed out"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/api/deploy/status")
async def deploy_status() -> dict[str, Any]:
    """Check if any infrastructure is currently deployed by reading tfstate."""
    try:
        state_path = PROJECT_ROOT / "terraform.tfstate"
        if not state_path.exists():
            return {"deployed": False, "resources": [], "count": 0}

        state = json.loads(state_path.read_text(encoding="utf-8"))
        resources = []
        for res in state.get("resources", []):
            if res.get("mode") == "managed":
                name = f"{res.get('module', '')}.{res['type']}.{res['name']}".lstrip(".")
                resources.append(name)

        return {"deployed": len(resources) > 0, "resources": resources, "count": len(resources)}
    except Exception:
        return {"deployed": False, "resources": [], "count": 0}


@app.post("/api/deploy/plan")
async def deploy_plan() -> Any:
    """Run terraform plan and stream output via SSE."""
    return await _stream_terraform_command(["terraform", "plan", "-input=false", "-no-color"], audit_action="deploy_plan")


@app.post("/api/deploy/apply")
async def deploy_apply() -> Any:
    """Run terraform apply and stream output via SSE."""
    return await _stream_terraform_command(["terraform", "apply", "-auto-approve", "-input=false", "-no-color"], audit_action="deploy_apply")


@app.post("/api/deploy/destroy")
async def deploy_destroy() -> Any:
    """Run terraform destroy and stream output via SSE."""
    return await _stream_terraform_command(["terraform", "destroy", "-auto-approve", "-input=false", "-no-color"], audit_action="deploy_destroy")


# ── Policy Engine ──


@app.get("/api/policies/yaml")
async def get_yaml_policies() -> dict[str, Any]:
    """Return all 8 YAML policy rules."""
    try:
        pe = _get_policy_engine()
        rules = []
        for rule in pe.rules:
            rules.append({
                "name": rule.get("name", ""),
                "description": rule.get("description", ""),
                "severity": rule.get("severity", "warning"),
                "condition": rule.get("condition", ""),
            })
        return {"rules": rules, "count": len(rules)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CustomPolicyPayload(BaseModel):
    name: str
    description: str
    severity: str
    condition: str


@app.post("/api/policies/yaml")
async def add_yaml_policy(payload: CustomPolicyPayload) -> dict[str, Any]:
    """Add a new custom policy rule to rules.yaml."""
    try:
        rules_path = PROJECT_ROOT / "policy-engine" / "rules.yaml"
        if not rules_path.exists():
            raise HTTPException(status_code=404, detail="rules.yaml not found")
        
        import yaml
        
        with open(rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        if "rules" not in data:
            data["rules"] = []
            
        # Check if rule exists
        if any(r.get("name") == payload.name for r in data["rules"]):
            raise HTTPException(status_code=400, detail=f"Rule '{payload.name}' already exists")
            
        data["rules"].append({
            "name": payload.name,
            "description": payload.description,
            "severity": payload.severity,
            "condition": payload.condition
        })
        
        # Save back
        with open(rules_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
            
        # Clear engine cache
        global _policy_engine
        _policy_engine = None
        
        return {"success": True, "message": f"Rule '{payload.name}' added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/policies/yaml/{rule_name}")
async def delete_yaml_policy(rule_name: str) -> dict[str, Any]:
    """Delete a custom policy rule from rules.yaml."""
    import yaml

    # Protected built-in rules that cannot be deleted
    builtin_rules = {
        "public_s3_bucket", "open_ssh_port", "open_rdp_port",
        "iam_wildcard_permissions", "expensive_ec2_instance",
        "missing_s3_encryption", "missing_resource_tags", "cloudtrail_disabled",
    }
    if rule_name in builtin_rules:
        raise HTTPException(status_code=403, detail=f"Cannot delete built-in rule '{rule_name}'")

    try:
        rules_path = PROJECT_ROOT / "policy-engine" / "rules.yaml"
        if not rules_path.exists():
            raise HTTPException(status_code=404, detail="rules.yaml not found")

        with open(rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        rules_list = data.get("rules", [])
        new_rules = [r for r in rules_list if r.get("name") != rule_name]

        if len(new_rules) == len(rules_list):
            raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")

        data["rules"] = new_rules

        with open(rules_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        return {"success": True, "message": f"Rule '{rule_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/policies/opa")
async def get_opa_policies() -> dict[str, Any]:
    """Return OPA rule information parsed from the rego file."""
    rego_path = PROJECT_ROOT / "opa-policies" / "aws_security.rego"
    rules: list[dict[str, str]] = []

    if rego_path.exists():
        content = rego_path.read_text(encoding="utf-8")
        # Parse rule comments and identifiers
        current_comment = ""
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("# ─"):
                current_comment = stripped[2:]
            elif "deny contains msg if" in stripped:
                rules.append({"severity": "block", "description": current_comment, "type": "deny"})
                current_comment = ""
            elif "warn contains msg if" in stripped:
                rules.append({"severity": "warning", "description": current_comment, "type": "warn"})
                current_comment = ""

        # Extract rule IDs from the msg assignments
        for i, line in enumerate(content.split("\n")):
            if "opa_" in line and "msg :=" in line:
                # Find the rule ID like [opa_public_s3]
                start = line.find("[opa_")
                end = line.find("]", start)
                if start != -1 and end != -1:
                    rule_id = line[start + 1:end]
                    # Match to the appropriate rule entry
                    for rule in rules:
                        if "name" not in rule:
                            rule["name"] = rule_id
                            break

    # Ensure all rules have names
    for idx, rule in enumerate(rules):
        if "name" not in rule:
            rule["name"] = f"opa_rule_{idx}"

    opa = _get_opa_engine()
    return {
        "rules": rules,
        "count": len(rules),
        "opa_available": opa.is_opa_available(),
    }


@app.post("/api/policies/evaluate")
async def evaluate_policies(config: ConfigPayload) -> dict[str, Any]:
    """Evaluate a config against both YAML and OPA engines."""
    return await validate_config(config)


# ── Audit ──


@app.get("/api/audit/events")
async def get_audit_events(
    actor: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=50),
) -> dict[str, Any]:
    """Return audit events with optional filters."""
    try:
        logger = _get_audit_logger()
        events = logger.read_events(
            actor=actor,
            environment=environment,
            action=action,
            limit=limit,
        )
        return {
            "events": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp,
                    "action": e.action,
                    "actor": e.actor,
                    "environment": e.environment,
                    "deployment_id": e.deployment_id,
                    "status": e.status,
                    "details": e.details,
                    "reason": e.reason,
                }
                for e in events
            ],
            "total": len(events),
        }
    except Exception:
        return {"events": [], "total": 0}


@app.get("/api/audit/report")
async def get_audit_report() -> dict[str, Any]:
    """Generate aggregate audit report."""
    try:
        logger = _get_audit_logger()
        return logger.generate_report()
    except Exception:
        return {"total_events": 0, "by_action": {}, "by_actor": {}, "by_environment": {}, "by_status": {}}


# ── Team ──


@app.get("/api/team/members")
async def get_team_members() -> dict[str, Any]:
    """Return all team members with their roles."""
    try:
        engine = _get_team_engine()
        members = []
        for username, user in engine.users.items():
            info = engine.get_user_info(username)
            if info:
                members.append({
                    "username": username,
                    "name": info["name"],
                    "email": info["email"],
                    "role": info["role"],
                    "role_name": info["role_name"],
                    "teams": info["teams"],
                    "permissions": info["permissions"],
                })
        return {"members": members, "total": len(members)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/roles")
async def get_team_roles() -> dict[str, Any]:
    """Return all role definitions."""
    try:
        engine = _get_team_engine()
        roles = []
        for role_name, role_def in engine.roles.items():
            roles.append({
                "key": role_name,
                "name": role_def.name,
                "description": role_def.description,
                "permissions": role_def.permissions,
                "requires_approval": role_def.requires_approval,
                "max_per_day": role_def.max_per_day,
            })
        return {"roles": roles, "total": len(roles)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/user/{username}")
async def get_team_user(username: str) -> dict[str, Any]:
    """Get info for a specific user."""
    try:
        engine = _get_team_engine()
        info = engine.get_user_info(username)
        if not info:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        return {"user": {**info, "username": username}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/team/user")
async def add_team_user(payload: AddUserPayload) -> dict[str, Any]:
    """Add a new user to the team config."""
    try:
        engine = _get_team_engine()

        # Check if user already exists
        if payload.github_username in engine.users:
            raise HTTPException(status_code=409, detail=f"User '{payload.github_username}' already exists")

        # Add to config
        teams = engine.config.get("teams", {})
        if payload.team not in teams:
            raise HTTPException(status_code=400, detail=f"Team '{payload.team}' does not exist")

        member_entry = {
            "name": payload.name,
            "email": payload.email,
            "github_username": payload.github_username,
            "role": payload.role,
        }

        teams[payload.team].setdefault("members", []).append(member_entry)
        engine.save_config()
        engine._load_config()  # Reload to update in-memory state

        _audit_log("add_team_member", "success", {"username": payload.github_username, "role": payload.role, "team": payload.team})

        return {"success": True, "user": member_entry}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Drift Detection ──


@app.get("/api/drift/status")
async def get_drift_status() -> dict[str, Any]:
    """Read drift-report.txt and return parsed status."""
    report_path = PROJECT_ROOT / "drift-report.txt"

    if not report_path.exists():
        return {"status": "no_report", "message": "No drift report found. Run a scan first.", "report": None}

    report_text = report_path.read_text(encoding="utf-8")

    if "DRIFT DETECTED" in report_text.upper():
        status = "drift_detected"
    elif "NO DRIFT" in report_text.upper():
        status = "clean"
    elif "ERROR" in report_text.upper():
        status = "error"
    else:
        status = "unknown"

    # Extract timestamp if present
    timestamp = None
    for line in report_text.split("\n"):
        if line.startswith("Timestamp:"):
            timestamp = line.split(":", 1)[1].strip()
            break

    return {
        "status": status,
        "timestamp": timestamp,
        "report": report_text,
    }


@app.post("/api/drift/scan")
async def trigger_drift_scan() -> Any:
    """Trigger drift detection script and stream output via SSE."""
    detect_script = str(PROJECT_ROOT / "drift-detection" / "detect.sh")
    return await _stream_terraform_command(["bash", detect_script], audit_action="drift_scan")


@app.post("/api/drift/remediate")
async def trigger_drift_remediation(
    check_only: bool = True, auto_approve: bool = False,
) -> dict[str, Any]:
    """Run drift remediation — check-only by default for safety."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "drift-detection"))
        from remediation import remediate_drift

        report_file = PROJECT_ROOT / "drift-report.txt"
        result = remediate_drift(
            project_root=PROJECT_ROOT,
            report_file=report_file,
            check_only=check_only,
            auto_approve=auto_approve,
        )
        _audit_log("drift_remediation", "success" if result.success else "failed", {"check_only": check_only, "performed": result.performed})
        return {
            "success": result.success,
            "performed": result.performed,
            "message": result.message,
            "report_path": str(result.report_path),
        }
    except Exception as e:
        _audit_log("drift_remediation", "failed", {"error": str(e)})
        return {"success": False, "performed": False, "message": str(e), "report_path": ""}


# ═══════════════════════════════════════════════════════════
# Team Admin Operations
# ═══════════════════════════════════════════════════════════


class UserRolePayload(BaseModel):
    """Payload for modifying a user's role."""

    username: str
    new_role: str


@app.delete("/api/team/user/{username}")
async def delete_team_user(username: str) -> dict[str, Any]:
    """Remove a user from teams.yaml (admin only)."""
    try:
        engine = _get_team_engine()
        if username not in engine.users:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")

        # Remove user from all teams in the config
        found = False
        for team_name, team_data in engine.config.get("teams", {}).items():
            members = team_data.get("members", [])
            new_members = [m for m in members if m.get("github_username") != username]
            if len(new_members) < len(members):
                team_data["members"] = new_members
                found = True

        if not found:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found in any team")

        engine.save_config()
        engine._load_config()  # Reload to reflect changes

        _audit_log("remove_team_member", "success", {"username": username})

        return {"success": True, "message": f"User '{username}' removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.put("/api/team/user/role")
async def modify_user_role(payload: UserRolePayload) -> dict[str, Any]:
    """Change a user's role (admin only)."""
    try:
        engine = _get_team_engine()
        if payload.username not in engine.users:
            raise HTTPException(status_code=404, detail=f"User '{payload.username}' not found")

        valid_roles = list(engine.roles.keys())
        if payload.new_role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role '{payload.new_role}'. Valid: {valid_roles}")

        # Update role in config
        for team_name, team_data in engine.config.get("teams", {}).items():
            for member in team_data.get("members", []):
                if member.get("github_username") == payload.username:
                    member["role"] = payload.new_role

        engine.save_config()
        engine._load_config()

        user_info = engine.get_user_info(payload.username)
        return {
            "success": True,
            "message": f"Role updated to '{payload.new_role}' for '{payload.username}'",
            "user": user_info,
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════
# Approval Queue + Slack Webhook
# ═══════════════════════════════════════════════════════════

# In-memory approval queue (resets on server restart — fine for local-first tool)
_approval_queue: list[dict[str, Any]] = []


class ApprovalRequestPayload(BaseModel):
    """Payload to request deployment approval."""

    requester: str
    environment: str
    description: str = ""


class ApprovalActionPayload(BaseModel):
    """Payload for approving/rejecting a request."""

    request_id: str
    action: str  # "approve" or "reject"
    approver: str
    reason: str = ""


@app.post("/api/approvals/request")
async def create_approval_request(payload: ApprovalRequestPayload) -> dict[str, Any]:
    """Create a deployment approval request."""
    from datetime import datetime, timezone
    import uuid

    engine = _get_team_engine()
    req_id = str(uuid.uuid4())[:8]

    requirements = engine.get_approval_requirements(payload.environment)

    request_data: dict[str, Any] = {
        "request_id": req_id,
        "requester": payload.requester,
        "environment": payload.environment,
        "description": payload.description,
        "status": "pending",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "approvals_needed": requirements.get("requires_approvals", 1),
        "approvals_received": [],
        "rejections": [],
        "notify_slack": requirements.get("notify_slack", False),
    }

    _approval_queue.append(request_data)

    # Attempt Slack notification
    slack_msg = None
    if requirements.get("notify_slack", False):
        slack_msg = _send_slack_notification(
            f"🚀 *Approval Request #{req_id}*\n"
            f"Requester: {payload.requester}\n"
            f"Environment: {payload.environment}\n"
            f"Description: {payload.description or 'N/A'}\n"
            f"Approvals needed: {requirements.get('requires_approvals', 1)}\n"
            f"Approve at: http://localhost:3000/team",
        )

    return {
        "success": True,
        "request_id": req_id,
        "status": "pending",
        "slack_sent": slack_msg is not None,
    }


@app.get("/api/approvals")
async def list_approvals() -> dict[str, Any]:
    """List all approval requests."""
    return {
        "requests": _approval_queue,
        "total": len(_approval_queue),
        "pending": len([r for r in _approval_queue if r["status"] == "pending"]),
    }


@app.post("/api/approvals/action")
async def process_approval_action(payload: ApprovalActionPayload) -> dict[str, Any]:
    """Approve or reject a deployment request."""
    from datetime import datetime, timezone

    # Find the request
    request_data = None
    for r in _approval_queue:
        if r["request_id"] == payload.request_id:
            request_data = r
            break

    if not request_data:
        raise HTTPException(status_code=404, detail=f"Request '{payload.request_id}' not found")

    if request_data["status"] != "pending":
        return {"success": False, "message": f"Request already {request_data['status']}"}

    # Verify approver has permission
    engine = _get_team_engine()
    if not engine.has_permission(payload.approver, "deploy:approve"):
        return {"success": False, "message": f"User '{payload.approver}' lacks deploy:approve permission"}

    if payload.action == "approve":
        request_data["approvals_received"].append({
            "approver": payload.approver,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "reason": payload.reason,
        })
        if len(request_data["approvals_received"]) >= request_data["approvals_needed"]:
            request_data["status"] = "approved"
    elif payload.action == "reject":
        request_data["rejections"].append({
            "rejector": payload.approver,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "reason": payload.reason,
        })
        request_data["status"] = "rejected"
    else:
        return {"success": False, "message": f"Invalid action '{payload.action}'"}

    # Slack notification for resolution
    if request_data.get("notify_slack"):
        emoji = "✅" if payload.action == "approve" else "❌"
        _send_slack_notification(
            f"{emoji} *Request #{payload.request_id} {payload.action.upper()}D*\n"
            f"By: {payload.approver}\n"
            f"Reason: {payload.reason or 'N/A'}",
        )

    return {
        "success": True,
        "request_id": payload.request_id,
        "status": request_data["status"],
        "action": payload.action,
    }


def _send_slack_notification(message: str) -> str | None:
    """Send a Slack webhook notification. Returns webhook URL if successful."""
    import os

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return None

    try:
        import requests as req

        resp = req.post(webhook_url, json={"text": message}, timeout=10)
        return webhook_url if resp.status_code == 200 else None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
# Notifications (Live Feed)
# ═══════════════════════════════════════════════════════════


@app.get("/api/notifications")
async def get_notifications() -> dict[str, Any]:
    """Aggregate notifications from drift status, approvals, and recent audit events."""
    from datetime import datetime, timezone

    notifications: list[dict[str, Any]] = []

    # 1. Pending approval requests
    pending = [r for r in _approval_queue if r["status"] == "pending"]
    for req in pending:
        notifications.append({
            "id": f"approval-{req['request_id']}",
            "type": "approval",
            "title": "Approval Pending",
            "message": f"{req['requester']} requests {req['environment']} deployment",
            "severity": "info",
            "timestamp": req.get("created_at", ""),
            "action_url": "/team",
        })

    # 2. Drift status
    drift_report_path = PROJECT_ROOT / "drift-report.txt"
    if drift_report_path.exists():
        drift_text = drift_report_path.read_text(encoding="utf-8")
        if "DRIFT DETECTED" in drift_text.upper():
            notifications.append({
                "id": "drift-alert",
                "type": "drift",
                "title": "Drift Detected",
                "message": "Infrastructure state has diverged from Terraform config",
                "severity": "warning",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "action_url": "/drift",
            })

    # 3. Recent audit events (last 3)
    try:
        logger = _get_audit_logger()
        events = logger.read_events(limit=3)
        for e in events:
            notifications.append({
                "id": f"audit-{e.event_id}",
                "type": "audit",
                "title": f"{e.action.replace('_', ' ').title()}",
                "message": f"{e.actor} — {e.environment} ({e.status})",
                "severity": "error" if e.status == "failed" else "success",
                "timestamp": e.timestamp,
                "action_url": "/audit",
            })
    except Exception:
        pass

    # 4. Policy health warning
    try:
        pe = _get_policy_engine()
        policy_dict = _config_to_policy_dict(ConfigPayload())
        result = pe.evaluate(policy_dict)
        if result.has_warnings():
            notifications.append({
                "id": "policy-warnings",
                "type": "policy",
                "title": "Policy Warnings",
                "message": f"{len(result.warnings)} warning(s) on default config",
                "severity": "warning",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "action_url": "/policies",
            })
    except Exception:
        pass

    # Sort by timestamp descending
    notifications.sort(key=lambda n: n.get("timestamp", ""), reverse=True)

    return {
        "notifications": notifications,
        "total": len(notifications),
        "unread": len(notifications),  # All treated as unread for simplicity
    }


# ═══════════════════════════════════════════════════════════
# Admin Settings
# ═══════════════════════════════════════════════════════════

# In-memory settings (resets on server restart — fine for local-first tool)
_admin_settings: dict[str, Any] = {
    "slack_webhook_url": "",
    "default_region": "ap-south-1",
    "strict_mode": False,
    "cost_alert_threshold": 1.0,
    "session_timeout_minutes": 30,
}


class AdminSettingsPayload(BaseModel):
    """Payload for saving admin settings."""

    slack_webhook_url: str | None = None
    default_region: str | None = None
    strict_mode: bool | None = None
    cost_alert_threshold: float | None = None
    session_timeout_minutes: int | None = None


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    """Return current admin settings."""
    return {"settings": _admin_settings}


@app.post("/api/settings")
async def save_settings(payload: AdminSettingsPayload) -> dict[str, Any]:
    """Save admin settings (in-memory)."""
    updated_fields: list[str] = []
    if payload.slack_webhook_url is not None:
        _admin_settings["slack_webhook_url"] = payload.slack_webhook_url
        updated_fields.append("slack_webhook_url")
    if payload.default_region is not None:
        _admin_settings["default_region"] = payload.default_region
        updated_fields.append("default_region")
    if payload.strict_mode is not None:
        _admin_settings["strict_mode"] = payload.strict_mode
        updated_fields.append("strict_mode")
    if payload.cost_alert_threshold is not None:
        _admin_settings["cost_alert_threshold"] = payload.cost_alert_threshold
        updated_fields.append("cost_alert_threshold")
    if payload.session_timeout_minutes is not None:
        _admin_settings["session_timeout_minutes"] = payload.session_timeout_minutes
        updated_fields.append("session_timeout_minutes")

    return {"success": True, "updated": updated_fields, "settings": _admin_settings}


# ═══════════════════════════════════════════════════════════
# Entrypoint
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

