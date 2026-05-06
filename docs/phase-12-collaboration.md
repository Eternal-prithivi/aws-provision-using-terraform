# Phase 12: Multi-User Collaboration

## Overview

Phase 12 adds enterprise-grade multi-user infrastructure management with role-based access control (RBAC), approval workflows, and complete audit logging. This enables teams to safely collaborate on infrastructure deployments with clearly defined roles, approval requirements, and compliance tracking.

## Key Features

### 1. Role-Based Access Control (RBAC)

Four distinct roles with graduated permissions:

| Role | Description | Permissions | Auto-Approve | Max Deploys/Day |
|------|-------------|-------------|--------------|-----------------|
| **Admin** | Full infrastructure control | Deploy, approve, manage team, modify settings | ✅ Yes (immediate) | Unlimited |
| **DevOps** | Deploy and approve | Deploy, approve, schedule, view audit | ✅ Yes (immediate) | 10 |
| **Developer** | Create deployment requests | Deploy, view, read own audit | ❌ Requires approval | 5 |
| **Viewer** | Read-only access | View deployments, read own audit logs | ❌ No | 0 |

### 2. Team Structure

Organize multiple teams with different responsibilities:

```yaml
teams:
  devops-core:          # Production deployment team
  platform-team:        # Platform infrastructure
  application-team:     # Application deployments
```

Each team:
- Has multiple members with assigned roles
- Can deploy to specific environments (production, staging)
- Has a dedicated Slack channel for alerts
- Requires role-based approvals

### 3. Approval Workflows

Configurable approval rules per environment:

**Production Deployments:**
- ✅ Requires **2 approvals** (Admin + DevOps)
- ✅ Auto-approves after 8 hours if not approved
- ✅ Slack notifications on approval requests
- ❌ No weekend deployments (configurable)
- ❌ No holiday deployments (configurable)

**Staging Deployments:**
- ✅ Requires **1 approval** (DevOps)
- ✅ Auto-approves after 4 hours if not approved
- ✅ Slack notifications
- ✅ Weekend deployments allowed
- ❌ No holiday deployments

### 4. Immutable Audit Trail

All deployment actions are logged to an append-only JSONL file:

```json
{
  "event_id": "2026-05-06T10:30:45.123456+00:00-deploy-001",
  "timestamp": "2026-05-06T10:30:45.123456+00:00",
  "action": "deploy",
  "actor": "alice-chen",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "success",
  "details": {"resources": 5, "duration_seconds": 125}
}
```

Query audit logs:
```bash
python team-management/audit.py --actor alice-chen --environment production
python team-management/audit.py --deployment deploy-001
python team-management/audit.py --report
```

### 5. Approval Escalation

Automatic escalation when approvals are pending:

- **Level 1** (30 minutes): Notify DevOps team
- **Level 2** (60 minutes): Escalate to Admin
- **Level 3** (Auto-approve): Apply after 8 hours

### 6. Scheduled Maintenance Windows

Restrict or allow deployments based on schedule:

```yaml
maintenance_windows:
  - name: "Business Hours"
    timezone: "America/New_York"
    allowed_days: [Monday-Friday]
    start_time: "09:00"
    end_time: "18:00"
```

Deployments outside windows are queued and auto-approved after waiting period.

## Configuration

### teams.yaml Structure

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
    permissions:
      - deploy:production
    slack_channel: "#devops-alerts"

approval_workflows:
  production:
    requires_approvals: 2
    approvers_must_include:
      - admin
      - devops
    allow_weekend_deploy: false
```

## Usage Examples

### Check User Permissions

```bash
python team-management/team_engine.py --user alice-chen --permission deploy:approve
# Output: ✅ Yes — alice-chen has 'deploy:approve'
```

### Validate Configuration

```bash
python team-management/team_engine.py --validate
# Output: ✅ Configuration is valid
```

### View Audit Trail

```bash
# Get all events by a user
python team-management/audit.py --actor bob-martinez

# Get deployment history
python team-management/audit.py --deployment deploy-001

# Generate compliance report
python team-management/audit.py --report
```

## Integration with CI/CD

Phase 12 integrates with the approval workflows:

1. **Developer creates PR** → Triggers deployment request
2. **Policy engine validates** → Checks rules
3. **Cost estimation runs** → Shows impact
4. **Approval gate waits** → DevOps/Admin approves
5. **Terraform applies** → After approval
6. **Audit logged** → Immutable record created

## Slack Notifications

Each team's Slack channel receives notifications for:

- **Approval Requested**: "Deploy to production needs approval"
- **Approval Granted**: "Deployment approved and applied"
- **Escalation Alert**: "Approval escalated after 30 minutes"
- **Deployment Success/Failure**: Final outcome

## Compliance & Audit

Meet compliance requirements:

✅ **Immutable audit trail** - All changes logged append-only
✅ **Role-based access** - Enforce least privilege
✅ **Approval tracking** - Who approved what, when
✅ **Action attribution** - Every change tied to an actor
✅ **Timestamp accuracy** - UTC timestamps on all events
✅ **Deployment history** - Complete before/after tracking

## Test Coverage

Phase 12 includes **30 comprehensive tests**:

- **Team Engine Tests (18)**: Role loading, permissions, approvals, user info
- **Audit Tests (12)**: Event logging, filtering, history, reporting

All tests passing:
```bash
pytest tests/unit/test_team_engine.py tests/unit/test_audit.py -v
# 30 passed ✅
```

## Future Enhancements

Planned for Phase 13-14:

- **OPA Policy Engine**: Richer policy language for complex rules
- **Web UI Dashboard**: Visual approval queue and deployment history
- **Slack Approvals**: Interactive "Approve/Reject" buttons in Slack
- **Jira Integration**: Link deployments to ticket IDs
- **Cost governance**: Approval gates based on cost thresholds
- **Capacity planning**: Restrict deployments based on resource availability

## Configuration Best Practices

1. **Keep role permissions simple** - Start with 4 roles, extend carefully
2. **Use team channels** - One Slack channel per team for clarity
3. **Document approval rules** - Keep teams.yaml commented
4. **Regular audit reviews** - Weekly compliance checks
5. **Test approval flows** - Stage environment before production
6. **Backup audit logs** - Archive to S3 monthly for compliance

## Security Considerations

- ✅ **No plain-text secrets** - Use GitHub secrets for credentials
- ✅ **Immutable audit trail** - Append-only, no deletion
- ✅ **Role isolation** - Viewers cannot modify anything
- ✅ **Approval enforcement** - Developers cannot auto-approve
- ✅ **Slack integration** - Channel-based notifications (not DMs)
- ✅ **Timestamp integrity** - UTC times prevent spoofing

---

**Phase 12 enables safe, auditable, multi-user infrastructure deployments with clear accountability and compliance tracking.**
