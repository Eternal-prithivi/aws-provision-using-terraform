# PROGRESS.md — Smart AWS Infrastructure Provisioning System

## Current Status
**Active Phase**: 🔵 PHASE 17 — BYOC (Bring Your Own Credentials)
**Overall Progress**: 16 / 17 Phases (Phase 15 complete, 17 next)
**Last Updated**: 2026-05-15 — Phase 15 (UI/UX Polish) completed. 308/308 tests passing.

---

## Phase Overview

| Phase | Name | Status | Notes |
|---|---|---|---|
| 1 | Foundation Setup | ✅ Complete | Folder structure, tools, all 6 modules written |
| 2 | Policy and Risk Engine | ✅ Complete | 8 rules, 32 tests passing, engine.py fully tested |
| 3 | Terraform Modules | ✅ Complete | All 6 modules validated + formatted, CI pipeline green |
| 4 | Remote State Backend | ✅ Complete | S3 + use_lockfile, terraform plan verified from remote state |
| 5 | CLI Wizard | ✅ Complete | wizard.py + 106 tests passing, 98% coverage |
| 6 | First Real Deployment | ✅ Complete | S3 bucket deployed + destroyed in same session, $0 |
| 7 | Drift Detection | ✅ Complete | detect.sh + daily cron workflow + drift-report.txt |
| 8 | CI/CD Pipeline | ✅ Complete | 3 workflows: terraform, infracost, drift-detection |
| 9 | Templates and Documentation | ✅ Complete | README.md, templates, final test suite green |
| 10 | Serverless Database Expansion (DynamoDB) | ✅ Complete | DynamoDB module, wizard support, and tests added |
| 11 | Drift Remediation | ✅ Complete | Check-only mode, Slack notifications, safe by default |
| 12 | Multi-User Collaboration | ✅ Complete | Role-based RBAC, approval workflows, audit trail |
| 12.5 | Role-Based CLI Authentication | ✅ Complete | GitHub token verification, role gates, permission checks |
| 13 | OPA Integration | ✅ Complete | Rego policies, Python wrapper, 31 tests, wizard integrated |
| 14 | Web UI Dashboard | ✅ Complete | FastAPI backend + Next.js frontend, 6 pages, 26 API tests |
| 15 | UI/UX Polish & Extended Functionality | ✅ Complete | Custom policies, live notifications, admin settings |
| 16 | Web Terminal (CloudShell) | ✅ Complete | WebSocket + xterm.js terminal, 31 tests, RBAC-gated |
| 17 | BYOC (Bring Your Own Credentials) | 🔵 Planned | Users provide their own AWS credentials for deployments |

---

## Phase 1 — Foundation Setup ✅ COMPLETE
**Goal**: Repository exists, tools installed, AWS account secured, folder structure created.

### Tasks
- [x] Create AWS account
- [x] Set $1 billing alert in AWS console immediately
- [x] Install Terraform v1.15.1
- [x] Install Python 3.9.6
- [x] Install AWS CLI and run `aws configure`
- [x] Install Infracost v0.10.44
- [x] Install Git 2.54.0
- [x] Create GitHub repository (development branch pushed)
- [x] Create complete folder structure with all module files
- [x] Write .gitignore (covers .terraform/, terraform.tfvars, .tfstate, __pycache__, .env)
- [x] Write requirements.txt (pytest, pytest-cov, pyyaml, pylint)
- [x] Write pytest.ini
- [x] Commit and push structure to GitHub development branch
- [x] Verify all tools work: `terraform version`, `python --version`, `aws --version`, `infracost --version`

### Definition of Done for Phase 1 ✅
- [x] GitHub repo exists with correct folder structure
- [x] All tools installed and version-verified
- [x] AWS account has $1 billing alert active (user confirmed)
- [x] .gitignore correctly excludes sensitive files
- [x] First commit pushed to development branch

---

## Phase 2 — Policy and Risk Engine
**Goal**: Engine reads rules.yaml and correctly evaluates config against all 8 rules.

### Tasks
- [x] Write policy-engine/rules.yaml with all 8 rules
- [x] Write policy-engine/engine.py (PolicyEngine class with load, evaluate, report methods)
- [x] Write tests/fixtures/sample_rules.yaml (test copy of rules)
- [x] Write tests/fixtures/valid_config.tfvars (passes all rules)
- [x] Write tests/fixtures/insecure_config.tfvars (triggers block violations)
- [x] Write tests/unit/test_policy_engine.py (all 8 rules × pass + fail + edge case)
- [x] Run pytest tests/unit/ — 29 tests PASSED
- [ ] Run pylint policy-engine/engine.py — no errors (pending)

### Definition of Done for Phase 2
- [x] All 8 rules defined in rules.yaml
- [x] engine.py reads rules at runtime (not hardcoded)
- [x] Unit tests pass for all 8 rules
- [x] Edge cases tested: empty config, None config, invalid YAML, missing rules file
- [x] Zero AWS touched in this phase

---

## Phase 3 — Terraform Modules ✅ COMPLETE
**Goal**: All 6 AWS modules written, validated, and formatted.

### Tasks
- [x] Write modules/vpc/main.tf, variables.tf, outputs.tf
- [x] Write modules/ec2/main.tf, variables.tf, outputs.tf (default: t2.micro)
- [x] Write modules/s3/main.tf, variables.tf, outputs.tf (private + encrypted enforced)
- [x] Write modules/iam/main.tf, variables.tf, outputs.tf (least privilege)
- [x] Write modules/cloudwatch/main.tf, variables.tf, outputs.tf
- [x] Write modules/billing/main.tf, variables.tf, outputs.tf ($1 budget alert)
- [x] Write root main.tf connecting all modules with enable/disable flags
- [x] Write root variables.tf and outputs.tf
- [x] Run `terraform init` on root — ✅ hashicorp/aws v5.100.0 installed
- [x] Run `terraform validate` — ✅ Success! The configuration is valid.
- [x] Run `terraform fmt` — ✅ FMT CLEAN

### Definition of Done for Phase 3 ✅
- [x] All 6 modules complete with variables.tf + outputs.tf
- [x] terraform validate passes on root and all modules
- [x] terraform fmt passes (no formatting errors)
- [x] Zero AWS resources created in this phase

---

## Phase 4 — Remote State Backend ✅ COMPLETE
**Goal**: Terraform state stored safely in S3 with locking.

### Tasks
- [x] Manually create S3 bucket in AWS console (ap-south-1): terraform-state-412628362844
- [x] Versioning enabled on S3 bucket (required for use_lockfile)
- [x] Write backend.tf pointing to S3 bucket with use_lockfile = true
- [x] Run `terraform init -reconfigure` — ✅ backend "s3" configured successfully
- [x] Fixed deprecated `dynamodb_table` → `use_lockfile = true` (Terraform v1.15+)
- [x] Run `terraform plan` from remote state — ✅ Plan: 1 to add (billing budget)
- [x] Verified S3 bucket accessible via AWS CLI

### Definition of Done for Phase 4 ✅
- [x] backend.tf written with S3 + use_lockfile
- [x] Remote state working (terraform init connected to S3)
- [x] State locking via S3 native locking (use_lockfile = true)
- [x] Both resources within free tier (S3 versioning enabled as required)

---

## Phase 5 — CLI Wizard
**Goal**: Users can run wizard, answer questions, get terraform.tfvars, policy check, and cost estimate.

### Tasks
- [ ] Write cli-wizard/wizard.py (interactive prompts)
- [ ] Connect wizard to policy engine (call engine.evaluate() on generated config)
- [ ] Integrate Infracost (run subprocess: infracost breakdown --path .)
- [ ] Add confirmation prompt before running terraform commands
- [ ] Handle error cases: missing tools, invalid input, user cancels
- [ ] Write tests/unit/test_wizard.py
- [ ] Write tests/integration/test_terraform_commands.py (mock subprocess)
- [ ] Write tests/integration/test_infracost_integration.py (mock subprocess)
- [ ] Run full pytest suite — all tests pass

### Definition of Done for Phase 5
- [ ] wizard.py interactive and produces valid terraform.tfvars
- [ ] Policy engine called and respected (block stops deploy)
- [ ] Infracost runs and displays cost estimate
- [ ] All error cases handled gracefully
- [ ] Unit and integration tests pass

---

## Phase 6 — First Real Deployment ✅ COMPLETE
**Goal**: Deploy real AWS infrastructure, verify outputs, destroy immediately.

### Tasks
- [x] Generated terraform.tfvars using static-site template (S3 only, free-tier)
- [x] Ran `terraform plan` — Plan: 5 to add (S3 bucket + encryption + versioning + public block + budget)
- [x] Ran `terraform apply -auto-approve` — Apply complete! 5 added, 0 changed, 0 destroyed
- [x] Verified outputs: s3_bucket_name = "prithivi-static-site-412628362844"
- [x] Verified S3 bucket exists via `aws s3api head-bucket` — ✅ BUCKET EXISTS
- [x] Ran `terraform destroy -auto-approve` — Destroy complete! 5 destroyed
- [x] Verified S3 bucket gone via `aws s3api head-bucket` — ✅ BUCKET GONE - ALL CLEAN
- [x] Total cost: $0.00 (bucket existed for ~30 seconds)

### Definition of Done for Phase 6 ✅
- [x] Successful deployment confirmed (5 resources created)
- [x] Outputs displayed correctly (S3 ARN + name)
- [x] Resources destroyed same session (5 resources destroyed)
- [x] Billing shows $0

---

## Phase 7 — Drift Detection ✅ COMPLETE
**Goal**: Daily job detects and reports infrastructure drift.

### Tasks
- [x] Write drift-detection/detect.sh (exit 0=clean, exit 2=drift, exit 1=error)
- [x] Update .github/workflows/drift-detection.yml (daily cron at 06:00 UTC, Terraform ~1.15)
- [x] Test locally: detect.sh correctly identifies drift (budget resource expected but destroyed)
- [x] Verified drift-report.txt generated with correct resource details
- [x] Exit code 2 on drift, exit code 0 on clean state

### Definition of Done for Phase 7 ✅
- [x] detect.sh correctly identifies drift
- [x] GitHub Actions cron workflow created
- [x] drift-report.txt generated on drift detection
- [x] Local test confirmed working

---

## Phase 8 — CI/CD Pipeline ✅ COMPLETE
**Goal**: Every code change automatically tested and validated.

### Tasks
- [x] .github/workflows/terraform.yml: pytest → fmt → init → validate → plan
- [x] .github/workflows/infracost.yml: cost diff on PRs
- [x] .github/workflows/drift-detection.yml: daily cron drift check
- [x] AWS credentials stored as GitHub Actions secrets
- [x] CI pipeline verified green on push
- [x] Coverage check (--cov-fail-under=80) passing at 98%

### Definition of Done for Phase 8 ✅
- [x] All three workflows created
- [x] Pipeline blocks on test failure (verified)
- [x] Infracost PR workflow ready
- [x] AWS secrets correctly configured

---

## Phase 9 — Templates and Documentation ✅ COMPLETE
**Goal**: Prebuilt templates work, README complete, project presentable.

### Tasks
- [x] templates/static-site/terraform.tfvars.tpl written (S3 only, $0/month)
- [x] templates/backend-app/terraform.tfvars.tpl written (VPC + EC2 + IAM, $0/month)
- [x] README.md: installation, usage, architecture, policy rules, CI/CD, testing, security
- [x] Full pytest suite: 106 tests, 98% coverage
- [x] Final end-to-end deployment and destroy verified (Phase 6)
- [x] Project structure matches defined layout
- [x] AUDIT_LOG.md updated with project completion

### Definition of Done for Phase 9 ✅
- [x] Both templates produce valid configurations
- [x] README covers all setup steps clearly
- [x] Full test suite passes (106/106)
- [x] Final deployment + destroy confirmed
- [x] Project ready for submission

---

## Phase 10 — Serverless Database Expansion (DynamoDB) ✅ COMPLETE
**Goal**: Add an "Always Free" DynamoDB module to allow users to deploy a NoSQL database without incurring costs.

### Tasks
- [x] Update documentation (`AI_MASTER.md`, `AI_CONTEXT.md`, `PROGRESS.md`)
- [x] Create `modules/dynamodb/main.tf`, `variables.tf`, `outputs.tf` (module exists)
- [x] Update root `main.tf`, `variables.tf`, `outputs.tf` to support DynamoDB
- [x] Add DynamoDB prompt to `cli-wizard/wizard.py`
- [x] Create a new `serverless-db` template in the wizard
- [x] Write unit tests for wizard changes
- [x] Test deployment and ensure Infracost reports $0.00 (Infracost step preserved in wizard)

### Definition of Done for Phase 10
- [x] DynamoDB module present with encryption and governance tags
- [x] Wizard can enable and configure a DynamoDB table and writes terraform.tfvars
- [x] Unit tests updated and all tests passing (107/107)
- [x] Terraform configuration validated locally

---

## Phase 11 — Drift Remediation ✅ COMPLETE
**Goal**: Detect and safely analyze infrastructure drift, with manual approval required before any changes.

### Tasks
- [x] Write remediation.py helper with check-only mode (safe by default)
- [x] Add --check-only flag (default True) to show terraform plan without applying
- [x] Add --auto-approve flag (requires check_only=False to actually apply)
- [x] Update drift-detection.yml workflow to run in check-only mode
- [x] Update tests to verify safe-by-default behavior
- [x] Document production-safe design in operations.md
- [x] Verify all 114 tests pass with new safer implementation

### Key Safety Features
- ✅ Runs terraform plan only (check-only mode by default)
- ✅ No automatic changes applied without explicit approval
- ✅ Prevents accidental auto-revert of intentional resource deletions
- ✅ All drift events logged and available for review
- ✅ Human approval required for any actual remediation

### Definition of Done for Phase 11 ✅
- [x] Drift remediation helper created with check-only mode (safe by default)
- [x] Drift workflow runs in check-only mode and generates analysis reports
- [x] Remediation report clearly shows status (CHECK-ONLY vs manual approval needed)
- [x] No production risk: intentional changes won't be auto-reverted
- [x] 114 unit and integration tests passing
- [x] Documentation updated explaining safe-by-default design

---

---

## Phase 12.5 — Role-Based CLI Authentication ✅ COMPLETE
**Goal**: Add GitHub token-based user authentication before wizard starts, enforcing role-based permissions.

### Tasks
- [x] Create authentication gate module (GitHub token verification)
- [x] Add RoleGate class for permission enforcement
- [x] Integrate auth into CLI wizard startup
- [x] Add permission checks before terraform apply
- [x] Support token from environment variable or interactive prompt
- [x] Fallback to teams.yaml username verification
- [x] Write 13 comprehensive unit tests for auth
- [x] Full documentation for authentication flow

### Key Features
- ✅ **GitHub Token Verification**: Validates user identity against GitHub API
- ✅ **Role-Based Access**: Only users with deploy:create permission can proceed
- ✅ **Environment-Specific Gates**: Production deployments require extra permission checks
- ✅ **Fallback Authentication**: Works without token via teams.yaml username verification
- ✅ **Role Summary Display**: Shows user's permissions and allowed environments
- ✅ **Permission Enforcement**: Blocks unauthorized deployments before terraform apply
- ✅ **Reusable Auth Pattern**: Same code works for CLI, dashboard, and API later

### Implementation Files
- `team-management/team_engine.py` — RoleGate class (70 lines added)
- `cli-wizard/auth_gate.py` — GitHub token verification (150+ lines)
- `cli-wizard/wizard.py` — Authentication gate integration (35 lines added)
- `tests/unit/test_auth.py` — 13 authentication tests
- `requirements.txt` — Added requests library for GitHub API

### Test Results
✅ **157/157 tests passing** (144 existing + 13 new auth tests)
- RoleGate tests: 6 passed
- Authentication flow tests: 4 passed
- Permission enforcement tests: 3 passed
- No regressions in existing tests

### User Experience
1. User runs: `python cli-wizard/wizard.py`
2. Authentication step prompts for GitHub token (or reads GITHUB_TOKEN env var)
3. Token verified against GitHub API to confirm user identity
4. User role and permissions loaded from teams.yaml
5. Role summary displayed showing allowed environments
6. Permission check before terraform apply prevents unauthorized deployments
7. All actions logged with username for audit trail

### Definition of Done for Phase 12.5 ✅
- [x] GitHub token authentication fully implemented
- [x] Role-based permission gates enforced
- [x] Integration with wizard wizard complete
- [x] 13 unit tests with 100% coverage
- [x] Fallback authentication when token unavailable
- [x] Authentication pattern reusable for web dashboard
- [x] No breaking changes to existing Phases 1-12

---
**Goal**: Enable team-based infrastructure management with role-based access control and audit logging.

### Tasks
- [x] Create team-management module with role definitions
- [x] Implement role-based access control (Admin/DevOps/Developer/Viewer)
- [x] Build approval workflow engine with environment-based restrictions
- [x] Create audit logging for all deployment actions
- [x] Add scheduling/maintenance window support
- [x] Implement escalation policies
- [x] Write 30 comprehensive unit tests (team_engine + audit)
- [x] Full documentation for team configuration

### Key Features
- ✅ **4 Role Types**: Admin (full access), DevOps (can approve), Developer (needs approval), Viewer (read-only)
- ✅ **Environment-Based Approvals**: Different rules for production vs staging
- ✅ **Audit Trail**: Immutable JSONL log of all deployment actions
- ✅ **Approval Workflows**: Configurable approval counts, escalation policies
- ✅ **Team Structure**: Multi-team support with Slack channel integration
- ✅ **Scheduled Deployments**: Maintenance windows, weekend/holiday restrictions
- ✅ **Auto-Approval**: Time-based auto-approval with configurable thresholds

### Implementation Files
- `team-management/teams.yaml` — Team structure, roles, approval workflows (95 lines)
- `team-management/team_engine.py` — Role-based access control engine (400+ lines)
- `team-management/audit.py` — Deployment audit logging (250+ lines)
- `tests/unit/test_team_engine.py` — 18 unit tests for team engine
- `tests/unit/test_audit.py` — 12 unit tests for audit logging

### Definition of Done for Phase 12 ✅
- [x] Role-based access control fully implemented
- [x] Approval workflows for production and staging configured
- [x] Audit logging tracks all deployment actions
- [x] 30 unit tests passing with 100% coverage
- [x] Team configuration is extensible (YAML-based)
- [x] Slack channel integration configured per team
- [x] Escalation policies support multi-level approvals
- [x] All documentation updated

---

## Phase 13 — OPA Integration ✅ COMPLETE
**Goal**: Extend policy enforcement using Open Policy Agent for richer, combinatorial rule management that the YAML engine cannot express.

### Tasks
- [x] Install OPA CLI (`brew install opa` — v1.16.1)
- [x] Write `opa-policies/aws_security.rego` (Rego policy file with 4 block rules + 2 combined-risk rules + 4 warning rules)
- [x] Write `opa-policies/opa_engine.py` (Python wrapper with OPAResult, OPAEngine, graceful degradation)
- [x] Integrate OPA check into `cli-wizard/wizard.py` as Step 6b (after YAML engine, before Infracost)
- [x] Write `tests/unit/test_opa_engine.py` — 31 comprehensive tests
- [x] Fix 3 existing wizard tests to mock `step_run_opa_engine`
- [x] Full test suite: 190/190 passing, 83.26% coverage
- [x] `opa check` validates Rego file (no syntax errors)
- [x] Update AI_MASTER.md, AI_CONTEXT.md, PROGRESS.md

### Key Features
- ✅ **Rego Policies**: 4 block rules + 4 warning rules in `aws_security.rego`
- ✅ **Combined-Risk Rules**: OPA detects compound violations the YAML engine cannot (e.g. public+unencrypted S3, production with no audit trail AND no tags)
- ✅ **Graceful Degradation**: Returns clean empty result if OPA CLI is not installed
- ✅ **Additive Design**: OPA augments the YAML engine — does not replace it (preserves Decision 003)
- ✅ **Tagged Messages**: All OPA messages include `[opa_*]` prefix so they are distinguishable in wizard output
- ✅ **31 Unit Tests**: Covering data structures, availability, all block/warning rules, combined-risk rules, degradation, and report formatting

### Implementation Files
- `opa-policies/aws_security.rego` — Rego policy file (10 rules)
- `opa-policies/opa_engine.py` — Python wrapper (156 lines)
- `cli-wizard/wizard.py` — Step 6b integration (35 lines added)
- `tests/unit/test_opa_engine.py` — 31 unit tests

### Definition of Done for Phase 13 ✅
- [x] OPA Rego policy file written and validated (`opa check` passes)
- [x] Python OPA engine wrapper implemented with full type hints
- [x] Combined-risk rules that go beyond YAML engine capabilities
- [x] Wizard Step 6b integrated cleanly
- [x] 31 new OPA tests passing with 100% coverage
- [x] No regressions in existing 159 tests (190 total all green)
- [x] Coverage above 80% threshold (83.26%)
- [x] All documentation updated

---

## Phase 14 — Web UI Dashboard ✅ COMPLETE
**Goal**: Provide a visual web dashboard replacing CLI-only interaction for demos and team usage.

### Tasks
- [x] **14a**: FastAPI backend (server.py — 18 REST endpoints, 736 lines)
- [x] **14b**: Next.js scaffold + layout (Sidebar, TopBar, Dashboard page)
- [x] **14c**: Deploy Wizard (7-step form: template → services → env → config → policy → cost → deploy)
- [x] **14d**: Policy Dashboard (YAML + OPA rules tables, config test runner) + Audit Log (filterable table, export)
- [x] **14e**: Team Management (roles overview, member cards, add user) + Drift Detection (status banner, scan trigger, live output)
- [x] **14f**: Build verification — Next.js compiles all 6 routes
- [x] **14g**: 26 FastAPI endpoint tests, full suite 216/216 passing, documentation updated

### Implementation Files
- `web-ui/api/server.py` — FastAPI backend (18 endpoints)
- `web-ui/api/requirements.txt` — Python dependencies
- `web-ui/frontend/src/app/page.tsx` — Dashboard
- `web-ui/frontend/src/app/deploy/page.tsx` — Deploy Wizard
- `web-ui/frontend/src/app/policies/page.tsx` — Policy Dashboard
- `web-ui/frontend/src/app/audit/page.tsx` — Audit Log
- `web-ui/frontend/src/app/team/page.tsx` — Team Management
- `web-ui/frontend/src/app/drift/page.tsx` — Drift Detection
- `web-ui/frontend/src/lib/api.ts` — API client
- `web-ui/frontend/src/components/layout/Sidebar.tsx` — Navigation
- `web-ui/frontend/src/components/layout/TopBar.tsx` — Header
- `web-ui/frontend/src/components/layout/AuthGuard.tsx` — Auth protection
- `web-ui/frontend/src/app/login/page.tsx` — Login page (GitHub token + username)
- `tests/unit/test_server.py` — 31 API endpoint tests (incl. auth)

### Test Results
✅ **221/221 tests passing** (190 existing + 31 new API/auth tests)
- Zero regressions across Phases 1-13
- Next.js build compiles successfully (7 routes incl. login)

### Definition of Done for Phase 14 ✅
- [x] FastAPI backend with 19 endpoints implemented and tested (incl. auth)
- [x] Next.js frontend with all 7 pages building successfully (incl. login)
- [x] GitHub token + username authentication with RBAC
- [x] Premium design system (glassmorphism, gradient borders, spring animations)
- [x] Dashboard: service status, policy health, cost, drift, recent activity
- [x] Deploy Wizard: 7-step flow matching CLI wizard capabilities
- [x] Policy Dashboard: YAML + OPA rules with live test runner
- [x] Audit Log: filterable table with JSON export
- [x] Team Management: roles, members, add user form
- [x] Drift Detection: status, report viewer, live scan
- [x] 31 new API tests passing
- [x] 221 total tests passing (zero regressions)
- [x] Documentation updated

---

## ✅ Phase 15 — UI/UX Polish & Extended Functionality ✅ COMPLETE

### Phase 15 Goal
Implement final user-requested features: Drift remediation automation fixes, Admin settings panel, interactive TopBar, and custom policy creation.

### Tasks
- [x] **Drift Remediation Automation**: Fixed `remediation.py` CLI args to support complete automation (`--apply`), and added "Dry Run Fix" & "Apply Fix" buttons to the Web UI.
- [x] **Team Admin Operations**: Admins can now delete users and change roles directly from the Team page UI.
- [x] **Approval Workflow & Slack**: Added an Approvals section in the Team page for admins to approve/reject deployments. Integrated Slack webhook notification logic.
- [x] **Custom Policies**: Full CRUD for custom YAML policy rules from the Web UI — add new rules with name, description, severity, and condition; delete custom rules; built-in rules protected from deletion. Visual distinction (Core vs Custom badges).
- [x] **TopBar Polish**: Live notifications polling from `/api/notifications` (aggregates drift, approvals, audit, policy warnings). Count badge with relative timestamps. Global search navigates to pages and audit logs. ⌘K keyboard shortcut hint.
- [x] **Admin Settings**: Multi-section settings page with sidebar navigation (Profile, Notifications, Infrastructure, Security, Cost Controls, Session). Live save with visual feedback. Toggle switches for strict mode. Logout button moved to Settings and user dropdown.

### New API Endpoints (Phase 15)
- `DELETE /api/policies/yaml/{rule_name}` — Delete custom policy (built-in rules protected)
- `GET /api/notifications` — Aggregated notification feed from drift, approvals, audit, policy health
- `GET /api/settings` — Get admin settings
- `POST /api/settings` — Save admin settings (partial update support)

### Implementation Files (Phase 15 additions)
- `web-ui/api/server.py` — 4 new endpoints (delete policy, notifications, get/save settings)
- `web-ui/frontend/src/app/policies/page.tsx` — Custom policy CRUD with add/delete, visual badges
- `web-ui/frontend/src/components/layout/TopBar.tsx` — Live notifications, enhanced search, user dropdown
- `web-ui/frontend/src/app/settings/page.tsx` — Full admin settings with 6 sections
- `web-ui/frontend/src/components/layout/Sidebar.tsx` — Settings nav item added
- `web-ui/frontend/src/lib/api.ts` — 6 new typed API functions
- `tests/unit/test_server.py` — 15 new tests (custom policies, notifications, settings)

### Test Results
✅ **308/308 tests passing** (293 existing + 15 new Phase 15 tests)
- Zero regressions across Phases 1-16
- Next.js build compiles all 10 routes

### Definition of Done for Phase 15 ✅
- [x] Custom policy CRUD (add/delete) with built-in rule protection
- [x] Live notification feed aggregating drift, approvals, audit, policy events
- [x] Global search navigating to pages and audit logs
- [x] Admin settings page with 6 configuration sections
- [x] Logout button in user dropdown and settings page
- [x] 15 new tests written and passing
- [x] 308 total tests passing (zero regressions)
- [x] Next.js build compiles successfully (10 routes)
- [x] Documentation updated

---

## ✅ Phase 16 — Web Terminal (CloudShell) ✅ COMPLETE
**Goal**: Provide a browser-based terminal embedded in the Web UI Dashboard, similar to AWS CloudShell, allowing users to execute Terraform commands, AWS CLI commands, and system diagnostics without leaving the dashboard.

### Tasks
- [x] **16a**: Backend WebSocket endpoint (`/ws/terminal`) for bidirectional terminal communication
- [x] **16b**: PTY subprocess management — spawn a shell session per authenticated user
- [x] **16c**: Frontend terminal component using xterm.js (full ANSI color, resize, scrollback)
- [x] **16d**: Terminal page in Next.js with sidebar integration (`/terminal` route)
- [x] **16e**: Session management — auto-timeout after inactivity, max concurrent sessions per user
- [x] **16f**: Security hardening — command allowlist/blocklist, prevent credential leaks in output
- [x] **16g**: Pre-loaded environment — `terraform`, `aws`, `infracost`, `opa` available in PATH
- [x] **16h**: Terminal history persistence — store last 100 commands per user session
- [x] **16i**: Unit tests for WebSocket endpoint, session lifecycle, and security filters (31 tests)
- [x] **16j**: Documentation update — usage guide, security model, configuration

### Key Features (Implemented)
- ✅ **xterm.js Frontend**: Full terminal emulation with ANSI colors, copy/paste, resize (JetBrains Mono font, xterm-256color)
- ✅ **RBAC-Gated**: Only Admin and DevOps roles can access the terminal
- ✅ **Working Directory**: Terminal opens in the project root with Terraform state access
- ✅ **Session Timeout**: Auto-disconnect after 30 minutes of inactivity
- ✅ **Command Guardrails**: 24 blocked patterns (rm -rf, shutdown, fork bomb, etc.)
- ✅ **Credential Protection**: AWS keys, passwords, and tokens masked in terminal output
- ✅ **Session Management**: Max 2 concurrent sessions per user, REST API for session listing/kill

### Implementation Files
- `web-ui/api/terminal.py` — WebSocket handler + PTY manager (280 lines)
- `web-ui/api/terminal_security.py` — Command allowlist/blocklist engine (175 lines)
- `web-ui/frontend/src/app/terminal/page.tsx` — Terminal UI page with RBAC gate
- `web-ui/frontend/src/components/Terminal.tsx` — xterm.js wrapper component
- `tests/unit/test_terminal.py` — 31 security tests (blocklist, allowlist, credential sanitization)

### Test Results
✅ **293/293 tests passing** (221 existing + 31 new terminal + 41 previously added)
- Next.js build compiles all 10 routes including `/terminal`

### Definition of Done for Phase 16 ✅
- [x] WebSocket terminal endpoint functional with PTY subprocess
- [x] xterm.js frontend renders a fully interactive shell
- [x] RBAC enforced — Viewer and Developer roles see "Access Denied"
- [x] Command blocklist prevents destructive operations (24 patterns)
- [x] Session timeout and cleanup implemented
- [x] Credential sanitization masks AWS keys in output
- [x] Terraform, AWS CLI, Infracost, and OPA available in terminal PATH
- [x] 31 unit tests written and passing
- [x] Documentation updated

---

## 🔵 Phase 17 — BYOC (Bring Your Own Credentials)
**Goal**: Allow users to provide their own AWS Access Key and Secret Key for deployments, replacing the current single-credential model. This enables multi-tenant usage where each user deploys to their own AWS account.

### Tasks
- [ ] **17a**: Backend credential vault — encrypted in-memory credential store (per-session, never persisted to disk)
- [ ] **17b**: API endpoint `POST /api/credentials` to accept and validate AWS credentials
- [ ] **17c**: Credential validation — call `aws sts get-caller-identity` to verify credentials before use
- [ ] **17d**: Credential injection — set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as environment variables for Terraform subprocess calls
- [ ] **17e**: Frontend "Cloud Credentials" settings page with secure input form
- [ ] **17f**: Credential status indicator in TopBar (connected/disconnected badge)
- [ ] **17g**: Credential rotation support — users can update credentials without restarting
- [ ] **17h**: Session isolation — ensure one user's credentials never leak to another user's session
- [ ] **17i**: Fallback mode — if no BYOC credentials provided, fall back to server-configured credentials (current behavior)
- [ ] **17j**: Security audit — credentials never logged, never written to disk, never returned in API responses
- [ ] **17k**: Unit tests for credential validation, injection, isolation, and cleanup
- [ ] **17l**: Documentation update — BYOC setup guide, security model, FAQ

### Key Features (Planned)
- 🔐 **Zero-Persistence**: Credentials exist only in memory for the duration of the session
- ✅ **Pre-Validation**: `sts:GetCallerIdentity` verifies credentials before any Terraform operation
- 🔄 **Hot Swap**: Users can change credentials mid-session without restarting the server
- 🛡️ **Session Isolation**: Each user's credentials are scoped to their authenticated session only
- 📊 **Account Info Display**: Shows AWS Account ID, IAM user/role, and region after connection
- ⚡ **Fallback Mode**: Server-level credentials used when no BYOC credentials are provided
- 🚫 **No Logging**: Credentials are never written to logs, audit trail, or disk

### Implementation Files (Planned)
- `web-ui/api/credentials.py` — Credential vault, validation, and injection logic
- `web-ui/api/credential_security.py` — Encryption helpers, session-scoped storage
- `web-ui/frontend/src/app/settings/credentials/page.tsx` — BYOC credentials UI
- `web-ui/frontend/src/components/CredentialStatus.tsx` — TopBar credential badge
- `tests/unit/test_credentials.py` — Credential lifecycle tests
- `tests/unit/test_credential_security.py` — Isolation and cleanup tests

### Definition of Done for Phase 17
- [ ] Users can input AWS credentials via the Web UI
- [ ] Credentials validated against AWS STS before use
- [ ] Terraform commands use BYOC credentials when provided
- [ ] Credentials never persisted to disk or logged
- [ ] Session isolation prevents credential leaks between users
- [ ] Fallback to server credentials when no BYOC provided
- [ ] Credential status visible in TopBar
- [ ] Unit tests written and passing
- [ ] Documentation updated with BYOC setup guide

---

## Completed Tasks Archive

### ✅ Phase 1 — Foundation Setup (Completed: 2026-05-05)
- All tools installed and verified (Terraform 1.15.1, Python 3.9.6, AWS CLI 2.34.42, Infracost 0.10.44, Git 2.54.0)
- AWS configured with access key + secret key
- GitHub repo created, development branch pushed
- Complete folder structure created: 6 modules, policy-engine, cli-wizard, drift-detection, tests, templates, .github/workflows
- .gitignore, requirements.txt, pytest.ini written
- All root Terraform files written (main.tf, variables.tf, outputs.tf, backend.tf)
- Policy engine (engine.py + rules.yaml) written and tested
- 32 tests collected, 32 passed

---

## Notes / Blockers
*(Add any current blockers or important notes here)*
