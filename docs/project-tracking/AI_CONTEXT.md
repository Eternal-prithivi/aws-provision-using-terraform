# AI_CONTEXT.md — Project Architecture Reference

## Project Mission
**Smart, Cost-Aware, Self-Service AWS Infrastructure Provisioning System using Terraform**

Automate AWS infrastructure setup while reducing human error, preventing unnecessary costs, and simplifying cloud usage for beginners and small teams. Built as an internship-level project with production-grade thinking.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Infrastructure as Code | Terraform | Latest stable |
| Cloud Provider | AWS | Fresh account — 12-month free tier active |
| CLI Wizard | Python | 3.10+ |
| Policy Engine | Python + YAML | 3.10+ |
| Cost Estimation | Infracost CLI + API | Latest |
| Testing | pytest + unittest.mock | Latest |
| CI/CD | GitHub Actions | Free tier |
| Remote State | AWS S3 + DynamoDB | Free tier |
| Notifications | GitHub Actions summary + drift-report.txt | — |

---

## Architecture Summary

```
User
 │
 ├──► Web UI Dashboard (Next.js + FastAPI)
 │         ├── Deploy Wizard, Policy Dashboard, Audit Log
 │         ├── Drift Detection, Team Management
 │         ├── Web Terminal / CloudShell (Phase 16)
 │         └── BYOC Credential Management (Phase 17)
 │
 ├──► CLI Wizard (wizard.py)
 │
 ├──► Policy & Risk Engine (engine.py + rules.yaml)
 │         └── 8 rules: block or warn before deploy
 │
 ├──► OPA Engine (opa_engine.py + aws_security.rego)
 │         └── Combinatorial Rego policies (10 rules)
 │
 ├──► Infracost (infracost breakdown --path .)
 │         └── monthly cost estimate per resource
 │
 ├──► terraform init → terraform apply
 │         └── provisions AWS via modules (user's own credentials if BYOC)
 │
 └──► Outputs displayed (EC2 IP, S3 bucket name, etc.)

GitHub Actions (background)
 ├── On push/PR: pytest → terraform validate → plan → infracost diff
 └── Daily cron: terraform refresh → plan → drift-report.txt
```

---

## Module Map

### modules/vpc/
- Creates VPC with public and private subnets
- Configures internet gateway and route tables
- Variables: `vpc_cidr`, `enable_vpc` (bool)
- Outputs: `vpc_id`, `public_subnet_id`, `private_subnet_id`

### modules/ec2/
- Creates EC2 instance
- Default instance type: **t2.micro** (free tier)
- Variables: `instance_type`, `enable_ec2` (bool), `ami_id`
- Outputs: `public_ip`, `instance_id`

### modules/s3/
- Creates S3 bucket
- **Private ACL enforced** — public access blocked by default
- **Encryption enforced** — AES256 server-side encryption
- Variables: `bucket_name`, `enable_s3` (bool)
- Outputs: `bucket_name`, `bucket_arn`

### modules/iam/
- Creates IAM role with least privilege policy
- No wildcard `*` permissions allowed
- Variables: `role_name`, `enable_iam` (bool)
- Outputs: `role_arn`, `role_name`

### modules/cloudwatch/
- Creates basic CloudWatch alarms
- Variables: `enable_cloudwatch` (bool), `alarm_email`
- Outputs: `alarm_arn`

### modules/billing/
- Creates AWS Budget with email alert
- Default budget threshold: $1
- Variables: `budget_limit`, `budget_email`
- Outputs: `budget_name`

### modules/dynamodb/
- Creates DynamoDB NoSQL table
- Always Free tier eligible (25 GB storage, 25 WCU/RCU)
- Enforces encryption at rest
- Variables: `enable_dynamodb` (bool), `table_name`
- Outputs: `dynamodb_table_name`, `dynamodb_table_arn`

---

## Policy and Risk Engine

**Rules file**: `policy-engine/rules.yaml`
**Engine file**: `policy-engine/engine.py`

### Rule Schema
```yaml
rules:
  - name: string           # unique identifier
    description: string    # human-readable explanation
    severity: block|warning
    condition: string      # evaluated against config dict
```

### 8 Launch Rules
| # | Rule Name | Severity | What It Checks |
|---|---|---|---|
| 1 | public_s3_bucket | block | s3_bucket_public == True |
| 2 | open_ssh_port | block | port 22 open to 0.0.0.0/0 |
| 3 | open_rdp_port | block | port 3389 open to 0.0.0.0/0 |
| 4 | missing_s3_encryption | warning | s3_encryption == False |
| 5 | iam_wildcard_permissions | block | iam_policy contains "*" |
| 6 | expensive_ec2_instance | warning | instance_type not in free_tier_types |
| 7 | missing_resource_tags | warning | tags == {} or tags is None |
| 8 | cloudtrail_disabled | warning | cloudtrail_enabled == False |

---

## OPA Policy Engine (Phase 13)

**Policy file**: `opa-policies/aws_security.rego`
**Engine file**: `opa-policies/opa_engine.py`

Augments the YAML rules engine with richer, combinatorial Rego policies.
Running as **Step 6b** in the wizard — after YAML engine, before Infracost.

### Design Principle
OPA does NOT replace the YAML engine. It adds a second, more powerful layer:
- YAML engine: Simple key-value rules (fast, human-readable)
- OPA engine: Combinatorial cross-field logic (expressive, standards-based)

### OPA Rules
| # | Rule ID | Severity | What It Checks |
|---|---|---|---|
| 1 | opa_public_s3 | block | s3_bucket_public == true |
| 2 | opa_open_ssh | block | ssh_open_to_world == true |
| 3 | opa_open_rdp | block | rdp_open_to_world == true |
| 4 | opa_iam_wildcard | block | iam_wildcard == true |
| 5 | opa_public_unencrypted_s3 | block | **Combined**: public AND unencrypted S3 |
| 6 | opa_production_no_audit | block | **Combined**: production + no CloudTrail + no tags |
| 7 | opa_cloudtrail_disabled | warning | cloudtrail_enabled == false |
| 8 | opa_s3_no_encryption | warning | s3_encryption == false |
| 9 | opa_missing_tags | warning | count(tags) == 0 |
| 10 | opa_expensive_ec2 | warning | instance_type not in free-tier set |

### Graceful Degradation
If OPA CLI is not installed, the engine returns an empty result and the wizard continues without blocking.

---

## CLI Wizard Flow

```
python cli-wizard/wizard.py
  │
  ├── 0. GitHub token auth → role check (Phase 12.5)
  ├── 1. Display welcome + available templates
  ├── 2. Ask: select template or custom
  ├── 3. Ask: select services (VPC, EC2, S3, IAM, CloudWatch, DynamoDB)
  ├── 4. Ask: environment (free-tier or production)
  ├── 5. Ask: configuration options per service
  ├── 6. Generate terraform.tfvars
  ├── 6a. Run YAML Policy Engine → show violations/warnings
  │        ├── BLOCK → stop, explain, exit
  │        └── WARNINGS → show, ask confirmation
  ├── 6b. Run OPA Policy Engine → advanced combinatorial checks (Phase 13)
  │        ├── BLOCK → stop, explain, exit
  │        └── WARNINGS → show, ask confirmation
  ├── 7. Run Infracost → show monthly cost estimate
  ├── 8. Final confirmation: "Deploy? [y/N]"
  ├── 9. Run: terraform init
  └── 10. Run: terraform apply
```

---

## Drift Detection Flow

```
drift-detection/detect.sh (runs daily via GitHub Actions cron)
  │
  ├── terraform refresh       ← pull current real AWS state
  ├── terraform plan -detailed-exitcode
  │       ├── exit 0 → no drift, log "OK"
  │       └── exit 2 → drift detected
  │               └── write drift-report.txt
  │               └── GitHub Actions summary shows RED alert
```

---

## Remote State Configuration (backend.tf)

```hcl
terraform {
  backend "s3" {
    bucket         = "terraform-state-<your-account-id>"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

Both resources (S3 bucket and DynamoDB table) are created **manually once** before any Terraform runs. They stay within free tier permanently.

---

## Environment Variables

All sensitive values stored in environment variables. Never hardcoded.

```bash
# AWS (stored as GitHub Actions secrets)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1

# Infracost
INFRACOST_API_KEY=        # get free key at infracost.io

# State Backend
TF_STATE_BUCKET=          # S3 bucket name for state
TF_LOCK_TABLE=            # DynamoDB table name for locking
```

---

## Testing Architecture

```
tests/
├── unit/
│   ├── test_policy_engine.py     # all 8 rules + edge cases
│   ├── test_wizard.py            # input validation, config generation
│   └── test_cost_estimator.py    # infracost subprocess mocking
├── integration/
│   ├── test_terraform_commands.py    # subprocess mocking for tf commands
│   └── test_infracost_integration.py # infracost call + parse output
├── fixtures/
│   ├── sample_rules.yaml         # 8 rules for test use
│   ├── valid_config.tfvars       # passes all policy rules
│   └── insecure_config.tfvars    # triggers block-level violations
└── conftest.py                   # shared fixtures
```

Coverage target: **80% minimum**, enforced in CI/CD.

---

## Prebuilt Templates

### templates/static-site/
- Enables: S3 only
- Environment: free-tier
- Use case: static HTML/CSS/JS website hosting
- Expected monthly cost: $0.00 (under free tier)

### templates/backend-app/
- Enables: VPC + EC2 + IAM
- Instance type: t2.micro
- Environment: free-tier
- Expected monthly cost: $0.00 (under free tier)

---

## CI/CD Pipeline

### .github/workflows/terraform.yml (on push/PR)
```
Step 1: pip install + pytest tests/ --cov=. --cov-fail-under=80
Step 2: terraform init
Step 3: terraform validate
Step 4: terraform fmt -check
Step 5: terraform plan
```

### .github/workflows/infracost.yml (on PR only)
```
Step 1: infracost breakdown --path . --format json
Step 2: Post cost diff comment on PR
```

### .github/workflows/drift-detection.yml (daily cron)
```
Step 1: terraform init
Step 2: terraform refresh
Step 3: terraform plan -detailed-exitcode
Step 4: If exit 2 → upload drift-report.txt as artifact
```

---

## Key Design Decisions

See DECISIONS.md for full rationale. Summary:
- Python over Shell for wizard — testability and structure
- Infracost over custom cost calculator — accuracy and maintenance
- YAML rules file over hardcoded rules — extensibility
- 8 rules at launch — scope control, all expandable
- GitHub Actions summary for drift alerts — zero extra setup
- Remote state in S3 before any real deployment — required for drift detection

---

## Dual Purpose Context

This project is:
1. **Standalone internship project** — complete, self-contained, presented independently
2. **Future module** for existing Cloud Resource Optimizer project — integration happens AFTER internship, never before

When integrating later: this system becomes the "Infrastructure Provisioner" module feeding cost and drift data into the optimizer's dashboard.

## Web Terminal / CloudShell (Phase 16) ✅ COMPLETE

**WebSocket Endpoint**: `ws://localhost:8000/ws/terminal`
**Frontend Route**: `/terminal`
**Status**: Fully implemented and tested (31 tests)

Provides a browser-based terminal embedded in the dashboard, similar to AWS CloudShell.

### Architecture
```
Browser (xterm.js)  ←→  WebSocket  ←→  FastAPI  ←→  PTY subprocess (zsh)
```

### Security Model (Implemented)
- **RBAC-Gated**: Only Admin and DevOps roles can access
- **Command Blocklist**: 24 blocked patterns (rm -rf, shutdown, fork bomb, sudo su, etc.)
- **Credential Protection**: AWS keys, passwords, tokens auto-masked in output
- **Session Timeout**: Auto-disconnect after 30 minutes of inactivity
- **Session Limits**: Max 5 concurrent sessions per user, dead session auto-cleanup

### Implementation Files
- `web-ui/api/terminal.py` — WebSocket handler + PTY manager (370 lines)
- `web-ui/api/terminal_security.py` — Command blocklist + credential sanitizer (175 lines)
- `web-ui/frontend/src/components/Terminal.tsx` — xterm.js wrapper (315 lines)
- `web-ui/frontend/src/app/terminal/page.tsx` — Terminal page with RBAC gate
- `tests/unit/test_terminal.py` — 31 tests (blocklist, allowlist, credential masking)

### Pre-loaded Tools
- `terraform`, `aws`, `infracost`, `opa` available in PATH
- Working directory set to project root
- xterm-256color with JetBrains Mono font

---

## BYOC — Bring Your Own Credentials (Phase 17)

**API Endpoint**: `POST /api/credentials`
**Frontend Route**: `/settings/credentials`

Allows users to provide their own AWS Access Key and Secret Key for deployments.

### Credential Lifecycle
```
User submits credentials via UI
  │
  ├── Validate: aws sts get-caller-identity
  ├── Store: encrypted in-memory only (per-session)
  ├── Inject: set as env vars for Terraform subprocess
  └── Cleanup: credentials wiped on session end
```

### Security Model
- **Zero-Persistence**: Credentials exist only in memory, never written to disk
- **Session Isolation**: Each user's credentials scoped to their session
- **No Logging**: Credentials never appear in logs, audit trail, or API responses
- **Pre-Validation**: STS call verifies credentials before any Terraform operation
- **Fallback Mode**: Server-level credentials used when no BYOC provided

---

## Future Enhancements Roadmap

Phases 1-16 are complete. Phase 15 polish is ongoing.

The next planned phase is:
1. **Phase 17 — BYOC (Bring Your Own Credentials)** — Multi-tenant AWS credential management

Future considerations (unplanned):
- Multi-region deployment support
- Container orchestration (ECS/EKS modules)
- Cost anomaly ML detection
- SSO authentication (SAML/OIDC)
- Multi-cloud provider support (Azure/GCP)

---

*This file should be updated as architecture evolves. Last updated: 2026-05-15 — Phase 15 complete.*
