# Product Overview

The Smart AWS Infrastructure Provisioning System is a Terraform-based, policy-driven AWS deployment tool designed to help users provision infrastructure safely and with cost awareness. It combines a Python CLI wizard, a YAML-based policy engine, Infracost, and modular Terraform components to reduce misconfiguration and keep deployments within budget-conscious defaults.

The current implementation supports VPC, EC2, S3, IAM, CloudWatch, Billing alerts, and DynamoDB. All 11 core phases are complete:

- **Phases 1-10**: Core infrastructure provisioning and automation
- **Phase 11**: Drift Remediation (production-safe with check-only mode by default)

The roadmap now includes three planned enhancement phases: multi-user collaboration, OPA integration, and a web UI dashboard.

## Phase 11: Production-Safe Drift Detection & Remediation

Phase 11 operates in a **safe-by-default architecture**:

- **Automated detection**: Daily drift checks at 06:00 UTC via GitHub Actions
- **Check-only mode**: Shows what would change (runs `terraform plan`) without applying
- **Human approval required**: All changes are reported for review
- **Prevents accidents**: Intentional resource deletions won't be auto-reverted
- **Audit trail**: Full drift and remediation history in GitHub Actions artifacts

This design ensures infrastructure changes are intentional and traceable.