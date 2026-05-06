# Team Management Guide

## Overview

The team management module enables multi-user infrastructure deployments with role-based access control, approval workflows, and complete audit logging. It's designed for teams ranging from 2-person startups to large enterprise organizations.

## Quick Start

### 1. Define Your Teams

Edit `team-management/teams.yaml` to define roles, teams, and approval workflows:

```yaml
roles:
  admin:
    name: "Administrator"
    permissions:
      - deploy:create
      - deploy:approve
      - deploy:auto_approve
      - team:manage
    auto_approve_threshold: 0
    requires_approval: false

teams:
  devops-core:
    name: "DevOps Core Team"
    members:
      - name: "Alice Chen"
        role: admin
        github_username: alice-chen
```

### 2. Load Team Configuration

```python
from team_engine import TeamEngine

engine = TeamEngine()
engine.validate_config()  # Verify configuration is correct
```

### 3. Check Permissions

```python
# Can alice-chen deploy to production?
user = engine.get_user_info("alice-chen")
can_deploy = engine.can_deploy_to_environment(user, "production")

# Does deployment require approval?
requires_approval = engine.requires_approval_for_deployment(user, "staging")
```

### 4. Get Approval Requirements

```python
# What approvals are needed for production deployment?
requirements = engine.get_approval_requirements("production")
print(f"Requires {requirements['required_approvals']} approvals")
print(f"Approvers needed: {requirements['approvers_must_include']}")
```

### 5. Find Approvers

```python
# Who can approve deployments to production?
approvers = engine.list_approvers_for_environment("production")
for approver in approvers:
    print(f"- {approver.name} ({approver.role})")
```

### 6. Log Actions

```python
from audit import AuditLogger

logger = AuditLogger()

# Log a deployment
logger.log_event(
    action="deploy",
    actor="alice-chen",
    environment="production",
    deployment_id="deploy-12345",
    status="success",
    details={"resources": 5, "duration_seconds": 120}
)
```

### 7. Query Audit Trail

```python
# Get all events by a user
alice_events = logger.read_events(actor="alice-chen")

# Get deployment history
history = logger.get_deployment_history("deploy-12345")

# Generate audit report
report = logger.generate_report()
print(f"Total deployments: {report['total_events']}")
print(f"By status: {report['by_status']}")
```

## Team Structure

### Roles

Define roles once, assign to multiple team members:

```yaml
roles:
  admin:
    name: "Administrator"
    permissions: [ALL]
    auto_approve_threshold: 0
  
  devops:
    name: "DevOps Engineer"
    permissions: [deploy:create, deploy:approve, ...]
    auto_approve_threshold: 0
  
  developer:
    name: "Developer"
    permissions: [deploy:create, audit:view_own]
    auto_approve_threshold: 8  # Hours
  
  viewer:
    name: "Viewer"
    permissions: [audit:view_all]
    auto_approve_threshold: null
```

### Teams

Organize members into teams:

```yaml
teams:
  devops-core:
    name: "DevOps Core Team"
    description: "Manages production infrastructure"
    members:
      - name: "Alice Chen"
        email: alice@company.com
        github_username: alice-chen
        role: admin
      
      - name: "Bob Martinez"
        email: bob@company.com
        github_username: bob-martinez
        role: devops
    
    slack_channel: "#devops-alerts"
    environments: [production, staging]
```

### Environment Access

Control which teams can deploy to which environments:

```yaml
teams:
  application-team:
    environments:
      staging:   # Can deploy to staging
        role: developer
        approval_required: false
      production:  # Can deploy to production but needs approval
        role: developer
        approval_required: true
```

## Approval Workflows

### Production Deployments

Production deployments require multiple approvals:

```yaml
approval_workflows:
  production:
    name: "Production Approval Workflow"
    requires_approvals: 2
    approvers_must_include:
      - admin
      - devops
    auto_approve_after_hours: 8
    allow_weekend_deploy: false
    allow_holiday_deploy: false
```

Steps:
1. Developer submits deployment request
2. Policy engine validates rules
3. Approval request sent to DevOps + Admin
4. Both must approve (in any order)
5. After 8 hours, auto-approves if not yet approved
6. Deployment proceeds

### Staging Deployments

Staging is faster with single approval:

```yaml
approval_workflows:
  staging:
    name: "Staging Approval Workflow"
    requires_approvals: 1
    approvers_must_include:
      - devops
    auto_approve_after_hours: 4
    allow_weekend_deploy: true
    allow_holiday_deploy: false
```

## Maintenance Windows

Restrict deployments outside business hours:

```yaml
maintenance_windows:
  - name: "Business Hours"
    timezone: "America/New_York"
    allow_on: [Monday, Tuesday, Wednesday, Thursday, Friday]
    start_hour: 9
    start_minute: 0
    end_hour: 18
    end_minute: 0
  
  - name: "Wednesday Maintenance"
    timezone: "UTC"
    allow_on: [Wednesday]
    start_hour: 2
    start_minute: 0
    end_hour: 4
    end_minute: 0
```

## Escalation Policies

Automatically escalate approvals if they're pending:

```yaml
escalation_policies:
  level_1:
    wait_minutes: 30
    notify: ["devops-team"]
    message: "Approval pending for 30 minutes"
  
  level_2:
    wait_minutes: 60
    notify: ["admin", "devops-team"]
    message: "Escalating approval to Admin"
  
  auto_approve:
    wait_minutes: 480  # 8 hours
    message: "Auto-approving after 8 hours"
```

## Best Practices

### 1. Keep Role Count Small

Start with 4 roles (Admin, DevOps, Developer, Viewer) and extend carefully.

```yaml
roles:
  admin:      # Full access
  devops:     # Deploy + approve
  developer:  # Deploy only
  viewer:     # Read-only
```

### 2. Use Team Channels

Create one Slack channel per team:

```yaml
teams:
  platform-team:
    slack_channel: "#platform-alerts"  # Dedicated channel
```

### 3. Document Approval Rules

Add comments explaining why rules exist:

```yaml
approval_workflows:
  production:
    # 2 approvals: prevents single person from deploying to prod
    requires_approvals: 2
    
    # Must include both perspectives
    approvers_must_include:
      - admin  # Business decision
      - devops  # Technical decision
```

### 4. Regular Audit Reviews

Review audit logs weekly:

```bash
python team-management/audit.py --report > audit_report.txt
```

### 5. Backup Audit Logs

Archive audit trail monthly:

```bash
cp team-management/audit.jsonl s3://backup-bucket/audit-$(date +%Y%m%d).jsonl
```

### 6. Test Approval Flows

Always test approval workflows in staging first:

```bash
# Simulate approval flow
python team-management/team_engine.py --test-approval staging alice-chen
```

## Integration with CI/CD

Phase 12 integrates with GitHub Actions:

```yaml
# .github/workflows/deploy.yml
jobs:
  check-approval:
    runs-on: ubuntu-latest
    steps:
      - name: Check deployment permissions
        run: |
          python team-management/team_engine.py \
            --user ${{ github.actor }} \
            --environment ${{ env.DEPLOY_ENV }} \
            --verify-approval
```

## Troubleshooting

### User Not Found

```bash
# Check if user exists
python team-management/team_engine.py --user alice-chen --info
# Error: User 'alice-chen' not found in teams.yaml
```

**Solution**: Add user to teams.yaml

### Permission Denied

```bash
# Check user permissions
python team-management/team_engine.py --user alice-chen --permission deploy:create
# ❌ alice-chen does not have 'deploy:create'
```

**Solution**: Verify role has permission in roles definition

### Approval Not Required

```bash
# Check if approval is required
python team-management/team_engine.py --user bob-martinez --environment staging --check-approval
# No approval required for staging (1 approver, threshold met)
```

**Solution**: This is expected for staging deployments. Production requires approval.

## Command Reference

```bash
# Validate configuration
python team-management/team_engine.py --validate

# Get user info
python team-management/team_engine.py --user alice-chen --info

# Check permission
python team-management/team_engine.py --user alice-chen --permission deploy:approve

# List approvers
python team-management/team_engine.py --environment production --approvers

# View audit trail
python team-management/audit.py --read

# Filter audit events
python team-management/audit.py --read --actor alice-chen

# Generate report
python team-management/audit.py --report
```

## Next Steps

- **Phase 13**: OPA integration for richer policy enforcement
- **Phase 14**: Web UI dashboard for visual deployment tracking
- **Slack Approvals**: Interactive approval buttons in Slack channels
- **Cost Governance**: Approval gates based on cost thresholds

---

**Team Management enables safe, auditable, multi-user infrastructure deployments with clear roles and compliance tracking.**
