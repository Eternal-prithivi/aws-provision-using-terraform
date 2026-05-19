# Architecture

## High-Level Flow

1. The user accesses the **Web UI Dashboard** (Next.js) or runs `python cli-wizard/wizard.py`.
2. Authentication via GitHub token verifies identity and loads RBAC permissions.
3. The wizard/dashboard collects configuration and writes `terraform.tfvars`.
4. The **YAML Policy Engine** evaluates the config against `policy-engine/rules.yaml` (8 rules).
5. The **OPA Policy Engine** runs combinatorial Rego checks for advanced violations.
6. **Infracost** estimates monthly cost before deployment.
7. Terraform provisions the selected AWS resources.
8. GitHub Actions runs validation, cost checks, and drift detection.

## Components

- `web-ui/frontend/` — Next.js 14 dashboard with Deploy Wizard, Policy Dashboard, Audit Log, Drift Detection, Team Management.
- `web-ui/api/server.py` — FastAPI backend with 19 REST endpoints, SSE streaming, and async tasks.
- `cli-wizard/wizard.py` — Interactive CLI for templates, prompts, validation, and deployment orchestration.
- `cli-wizard/auth_gate.py` — GitHub token authentication and role permission gate.
- `policy-engine/engine.py` — YAML-based rules engine (8 rules: block or warning).
- `opa-policies/opa_engine.py` — OPA/Rego policy engine (10 rules including combined-risk checks).
- `modules/` — 7 reusable Terraform modules (VPC, EC2, S3, IAM, CloudWatch, Billing, DynamoDB).
- `team-management/` — RBAC engine, approval workflows, and audit logging.
- `drift-detection/detect.sh` — Compares deployed state with Terraform plan and reports drift.
- `drift-detection/remediation.py` — Automated drift remediation with check-only safety mode.
- `web-ui/api/terminal.py` — WebSocket terminal handler + PTY subprocess manager (Phase 16).
- `web-ui/api/terminal_security.py` — Command blocklist engine + credential sanitizer (24 patterns, Phase 16).
- `web-ui/frontend/src/components/Terminal.tsx` — xterm.js terminal wrapper with auto-reconnect (Phase 16).
- `.github/workflows/` — CI/CD (terraform.yml), Infracost PR diffs (infracost.yml), daily drift (drift-detection.yml).

## Planned Components

### Phase 17 — BYOC (Bring Your Own Credentials)
- `web-ui/api/credentials.py` — In-memory credential vault with STS validation.
- `web-ui/frontend/src/app/settings/credentials/page.tsx` — Credential management UI.
- Zero-persistence model: credentials never written to disk.

## Current Scope

- The project is AWS-only.
- The policy engine uses both YAML rules and OPA/Rego policies.
- Both CLI and Web UI are supported as user interfaces.
- Authentication uses GitHub token verification with RBAC.