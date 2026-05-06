# Product Overview

The Smart AWS Infrastructure Provisioning System is a Terraform-based, policy-driven AWS deployment tool designed to help users provision infrastructure safely and with cost awareness. It combines a Python CLI wizard, a YAML-based policy engine, Infracost, and modular Terraform components to reduce misconfiguration and keep deployments within budget-conscious defaults.

The current implementation supports VPC, EC2, S3, IAM, CloudWatch, Billing alerts, and DynamoDB. All 12 core phases are complete:

- **Phases 1-10**: Core infrastructure provisioning and automation
- **Phase 11**: Drift Remediation (production-safe with check-only mode by default)
- **Phase 12**: Multi-User Collaboration (role-based RBAC with audit trails)

The roadmap now includes two planned enhancement phases: OPA integration and a web UI dashboard.

## Phase 11: Production-Safe Drift Detection & Remediation

Phase 11 operates in a **safe-by-default architecture**:

- **Automated detection**: Daily drift checks at 06:00 UTC via GitHub Actions
- **Check-only mode**: Shows what would change (runs `terraform plan`) without applying
- **Human approval required**: All changes are reported for review
- **Slack notifications**: Team alerted of detected drift immediately
- **Prevents accidents**: Intentional resource deletions won't be auto-reverted
- **Audit trail**: Full drift and remediation history in GitHub Actions artifacts

This design ensures infrastructure changes are intentional and traceable.

## Phase 12: Multi-User Collaboration

Phase 12 enables **enterprise-grade team collaboration**:

- **Role-Based Access Control**: 4 roles (Admin, DevOps, Developer, Viewer) with graduated permissions
- **Team Structure**: Multiple teams with distinct responsibilities and Slack channels
- **Approval Workflows**: Environment-specific approval requirements (2 for production, 1 for staging)
- **Immutable Audit Trail**: JSONL append-only log of all deployment actions for compliance
- **Escalation Policies**: Automatic escalation if approvals pending
- **Scheduled Deployments**: Maintenance windows, weekend/holiday restrictions
- **Auto-Approval**: Time-based auto-approval after waiting period

**Key Benefits:**
- ✅ Enforce least-privilege access
- ✅ Clear accountability for who deployed what
- ✅ Compliance-ready audit logs
- ✅ Slack integration for team notifications
- ✅ Flexible team management (YAML-configurable)
- ✅ Production-safe with approval gates

**Sample Configuration:**
- **DevOps Core Team**: Admins can auto-approve, deploy to production
- **Platform Team**: DevOps engineers can approve, developers create requests
- **Application Team**: Developers deploy to staging only, require approval

See [Phase 12 Documentation](phase-12-collaboration.md) for detailed configuration and usage.
