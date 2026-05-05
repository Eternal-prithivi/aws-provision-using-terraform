# DECISIONS.md — Settled Architecture Decisions

> These decisions are **FINAL**. Do not reopen without a critical reason.
> If you think a decision needs revisiting, add a note at the bottom with your reasoning — do not edit existing entries.

---

## Decision 001 — Python over Shell for CLI Wizard
**Date**: Project initialization
**Status**: FINAL

**Decision**: The CLI wizard is written in Python 3.10+, not Bash or Shell.

**Rationale**:
- Python is testable with pytest — shell scripts are not easily unit tested
- Python handles invalid user input, exceptions, and subprocess errors cleanly
- Python produces readable, maintainable code that an interviewer can review
- Python type hints make the intent of each function clear
- Shell scripts become brittle and hard to refactor at this complexity level

**Rejected Alternative**: Bash — rejected because untestable and fragile at this scope.

---

## Decision 002 — Infracost over Custom Cost Calculator
**Date**: Project initialization
**Status**: FINAL

**Decision**: Use Infracost CLI + free API for cost estimation. Do not build a custom pricing engine.

**Rationale**:
- AWS pricing has 40+ variables per service — manual estimation will be wrong within weeks
- Infracost is open-source, free for this use case, and actively maintained
- Integrating a real tool shows ecosystem awareness — a key senior engineer quality
- Wrong estimates destroy user trust; Infracost is accurate by design
- Infracost integrates directly with GitHub Actions for PR cost diffs

**Rejected Alternative**: Custom hardcoded pricing — rejected because inaccurate and unmaintainable.

---

## Decision 003 — YAML Rules File over Hardcoded Policy Logic
**Date**: Project initialization
**Status**: FINAL

**Decision**: All policy rules are defined in `policy-engine/rules.yaml`. The engine (`engine.py`) only reads and evaluates — it never contains rule logic.

**Rationale**:
- Adding a new rule requires zero code changes — only a YAML entry
- This is a real rules engine pattern used in production security tooling
- Interviewers can see architectural maturity in the separation of config from logic
- Rules file is version-controlled and reviewable independently of code
- This is how HashiCorp Sentinel works at enterprise scale

**Rejected Alternative**: Hardcoded if-else in engine.py — rejected because brittle and requires code changes for every new rule.

---

## Decision 004 — 8 Rules at Launch (Not More, Not Less)
**Date**: Project initialization
**Status**: FINAL

**Decision**: Launch with exactly 8 policy rules covering security, cost, and governance.

**Rationale**:
- 8 rules are enough to be genuinely useful and credible in an interview
- Scope control prevents project from becoming over-engineered before basics are solid
- The 8 rules cover all three categories: security (3 blocks), cost (1 warning), governance (4 warnings)
- More rules can be added by editing rules.yaml — no code change needed

**The 8 rules**: public_s3_bucket (block), open_ssh_port (block), open_rdp_port (block), missing_s3_encryption (warning), iam_wildcard_permissions (block), expensive_ec2_instance (warning), missing_resource_tags (warning), cloudtrail_disabled (warning).

---

## Decision 005 — GitHub Actions Summary + drift-report.txt for Drift Alerts
**Date**: Project initialization
**Status**: FINAL

**Decision**: Drift detection alerts go to GitHub Actions job summary and a local `drift-report.txt` file. No Slack webhook.

**Rationale**:
- Slack webhook requires external setup and a Slack workspace — unnecessary for internship scope
- GitHub Actions summary is visible immediately in the CI/CD interface with zero extra configuration
- drift-report.txt is downloadable as a GitHub Actions artifact for review
- Simpler is better for a student project — Slack can be added later as a future enhancement

**Rejected Alternative**: Slack webhook — rejected as unnecessary complexity for this scope.

---

## Decision 006 — Remote State in S3 + DynamoDB Before Any Real Deployment
**Date**: Project initialization
**Status**: FINAL

**Decision**: The S3 backend and DynamoDB lock table are set up in Phase 4 before Phase 6 (first real deployment). This is the only manual AWS step in the project.

**Rationale**:
- Drift detection requires remote state — local state cannot be read by GitHub Actions
- DynamoDB prevents state corruption from concurrent runs
- Both resources are within free tier permanently
- Setting this up early means no state migration issues later

---

## Decision 007 — Project Stays Standalone for Internship
**Date**: Project initialization
**Status**: FINAL

**Decision**: This project is NOT integrated with Cloud Resource Optimizer during the internship period. Integration happens after internship submission.

**Rationale**:
- Merging two projects mid-build creates confusion about authorship and scope
- Interviewers want to evaluate a standalone, complete system
- Integration architecture is planned (provisioner module → optimizer dashboard) but not executed yet
- Integration after completion means one fully working project, not two half-working ones

---

## Decision 008 — t2.micro as Default EC2 Instance Type
**Date**: Project initialization
**Status**: FINAL

**Decision**: t2.micro is the default EC2 instance type. The policy engine warns (not blocks) on non-free-tier instance types.

**Rationale**:
- t2.micro is free-tier eligible for 12 months on a new AWS account
- Warning (not block) for other types because production environments legitimately need larger instances
- The wizard should clearly show when a type is not free-tier eligible
- This protects student wallet while not being overly restrictive for real use cases

---

*Add new decisions below this line. Never edit existing decisions.*
