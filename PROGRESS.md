# PROGRESS.md — Smart AWS Infrastructure Provisioning System

## Current Status
**Active Phase**: Phase 1 — Foundation Setup
**Overall Progress**: 0 / 9 Phases Complete
**Last Updated**: Project initialization

---

## Phase Overview

| Phase | Name | Status | Notes |
|---|---|---|---|
| 1 | Foundation Setup | 🔄 In Progress | Starting point |
| 2 | Policy and Risk Engine | ⏳ Not Started | — |
| 3 | Terraform Modules | ⏳ Not Started | — |
| 4 | Remote State Backend | ⏳ Not Started | — |
| 5 | CLI Wizard | ⏳ Not Started | — |
| 6 | First Real Deployment | ⏳ Not Started | — |
| 7 | Drift Detection | ⏳ Not Started | — |
| 8 | CI/CD Pipeline | ⏳ Not Started | — |
| 9 | Templates and Documentation | ⏳ Not Started | — |

---

## Phase 1 — Foundation Setup
**Goal**: Repository exists, tools installed, AWS account secured, folder structure created.

### Tasks
- [ ] Create AWS account
- [ ] Set $1 billing alert in AWS console immediately
- [ ] Install Terraform (latest stable)
- [ ] Install Python 3.10+
- [ ] Install AWS CLI and run `aws configure`
- [ ] Install Infracost CLI and get free API key from infracost.io
- [ ] Install Git
- [ ] Create GitHub repository
- [ ] Create complete folder structure with empty placeholder files
- [ ] Write .gitignore (covers .terraform/, terraform.tfvars, .tfstate, __pycache__, .env)
- [ ] Write requirements.txt (pytest, pytest-cov, pyyaml, pylint)
- [ ] Write pytest.ini
- [ ] Commit and push empty structure to GitHub
- [ ] Verify all tools work: `terraform version`, `python --version`, `aws --version`, `infracost --version`

### Definition of Done for Phase 1
- [ ] GitHub repo exists with correct folder structure
- [ ] All tools installed and version-verified
- [ ] AWS account has $1 billing alert active
- [ ] .gitignore correctly excludes sensitive files
- [ ] First commit pushed

---

## Phase 2 — Policy and Risk Engine
**Goal**: Engine reads rules.yaml and correctly evaluates config against all 8 rules.

### Tasks
- [ ] Write policy-engine/rules.yaml with all 8 rules
- [ ] Write policy-engine/engine.py (PolicyEngine class with load, evaluate, report methods)
- [ ] Write tests/fixtures/sample_rules.yaml (test copy of rules)
- [ ] Write tests/fixtures/valid_config.tfvars (passes all rules)
- [ ] Write tests/fixtures/insecure_config.tfvars (triggers block violations)
- [ ] Write tests/unit/test_policy_engine.py (all 8 rules × pass + fail + edge case)
- [ ] Run pytest tests/unit/ — all tests must pass
- [ ] Run pylint policy-engine/engine.py — no errors

### Definition of Done for Phase 2
- [ ] All 8 rules defined in rules.yaml
- [ ] engine.py reads rules at runtime (not hardcoded)
- [ ] Unit tests pass for all 8 rules
- [ ] Edge cases tested: empty config, None config, invalid YAML, missing rules file
- [ ] Zero AWS touched in this phase

---

## Phase 3 — Terraform Modules
**Goal**: All 6 AWS modules written, validated, and formatted.

### Tasks
- [ ] Write modules/vpc/main.tf, variables.tf, outputs.tf
- [ ] Write modules/ec2/main.tf, variables.tf, outputs.tf (default: t2.micro)
- [ ] Write modules/s3/main.tf, variables.tf, outputs.tf (private + encrypted enforced)
- [ ] Write modules/iam/main.tf, variables.tf, outputs.tf (least privilege)
- [ ] Write modules/cloudwatch/main.tf, variables.tf, outputs.tf
- [ ] Write modules/billing/main.tf, variables.tf, outputs.tf ($1 budget alert)
- [ ] Write root main.tf connecting all modules with enable/disable flags
- [ ] Write root variables.tf and outputs.tf
- [ ] Run `terraform init` on root
- [ ] Run `terraform validate` — must pass
- [ ] Run `terraform fmt` — must pass

### Definition of Done for Phase 3
- [ ] All 6 modules complete with variables.tf + outputs.tf
- [ ] terraform validate passes on root and all modules
- [ ] terraform fmt passes (no formatting errors)
- [ ] Zero AWS resources created in this phase

---

## Phase 4 — Remote State Backend
**Goal**: Terraform state stored safely in S3 with DynamoDB locking.

### Tasks
- [ ] Manually create S3 bucket for state in AWS console (one-time manual step)
- [ ] Manually create DynamoDB table for state locking in AWS console (one-time manual step)
- [ ] Write backend.tf pointing to S3 bucket and DynamoDB table
- [ ] Run `terraform init` to migrate state to remote backend
- [ ] Verify .tfstate file appears in S3 bucket
- [ ] Verify DynamoDB table has a lock entry during init

### Definition of Done for Phase 4
- [ ] backend.tf written
- [ ] Remote state working (verified in S3 console)
- [ ] State locking working (verified in DynamoDB console)
- [ ] Both resources confirmed within free tier

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

## Phase 6 — First Real Deployment
**Goal**: Deploy real AWS infrastructure, verify outputs, destroy immediately.

### Tasks
- [ ] Run wizard with static-site template, free-tier environment
- [ ] Verify policy engine passes all 8 rules
- [ ] Verify Infracost shows near-zero cost
- [ ] Confirm and deploy
- [ ] Verify outputs: S3 bucket name displayed correctly
- [ ] Verify AWS console shows expected resources
- [ ] **Run `terraform destroy` immediately**
- [ ] Verify AWS console shows zero resources
- [ ] Verify AWS billing dashboard shows $0

### Definition of Done for Phase 6
- [ ] Successful deployment confirmed
- [ ] Outputs displayed correctly
- [ ] Resources destroyed same session
- [ ] Billing shows $0

---

## Phase 7 — Drift Detection
**Goal**: Daily job detects and reports infrastructure drift.

### Tasks
- [ ] Write drift-detection/detect.sh
- [ ] Write .github/workflows/drift-detection.yml (daily cron schedule)
- [ ] Test locally: manually change a resource in AWS console, run detect.sh
- [ ] Verify drift-report.txt is generated with correct resource details
- [ ] Restore correct state with terraform apply
- [ ] Verify detect.sh exits 0 after restore

### Definition of Done for Phase 7
- [ ] detect.sh correctly identifies drift
- [ ] GitHub Actions cron workflow created
- [ ] drift-report.txt generated on drift detection
- [ ] Manual test confirmed working

---

## Phase 8 — CI/CD Pipeline
**Goal**: Every code change automatically tested and validated.

### Tasks
- [ ] Write .github/workflows/terraform.yml (pytest → init → validate → fmt → plan)
- [ ] Write .github/workflows/infracost.yml (cost diff on PRs)
- [ ] Store AWS credentials as GitHub Actions secrets
- [ ] Push test commit and verify pipeline runs
- [ ] Introduce deliberate test failure and verify pipeline blocks
- [ ] Verify Infracost comments appear on PRs

### Definition of Done for Phase 8
- [ ] All three workflows created
- [ ] Pipeline blocks on test failure (verified)
- [ ] Infracost PR comments working
- [ ] AWS secrets correctly configured

---

## Phase 9 — Templates and Documentation
**Goal**: Prebuilt templates work, README complete, project presentable.

### Tasks
- [ ] Write templates/static-site/terraform.tfvars.tpl
- [ ] Write templates/backend-app/terraform.tfvars.tpl
- [ ] Write complete README.md (installation, usage, configuration, examples)
- [ ] Run full pytest suite one final time
- [ ] Do final end-to-end deployment and destroy
- [ ] Review project structure matches defined layout exactly
- [ ] Final AUDIT_LOG.md entry for project completion

### Definition of Done for Phase 9
- [ ] Both templates produce valid deployments
- [ ] README covers all setup steps clearly
- [ ] Full test suite passes
- [ ] Final deployment + destroy confirmed
- [ ] Project ready for internship submission

---

## Completed Tasks Archive
*(Move completed phase entries here)*

---

## Notes / Blockers
*(Add any current blockers or important notes here)*
