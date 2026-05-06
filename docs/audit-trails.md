# Audit Trails & Compliance Logging

## Overview

Phase 12 maintains an immutable, append-only audit trail of all infrastructure deployments and approval actions. This enables compliance reporting, security investigations, and accountability tracking.

## Core Architecture

### Audit Trail Storage

**Format**: JSONL (JSON Lines) — one JSON object per line, append-only

**File**: `team-management/audit.jsonl`

**Immutability**: Once written, events cannot be modified or deleted

**Example Entry**:
```json
{
  "event_id": "2026-05-06T10:30:45.123456+00:00-deploy-001",
  "timestamp": "2026-05-06T10:30:45.123456+00:00",
  "action": "deploy",
  "actor": "alice-chen",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "success",
  "details": {
    "resources": 5,
    "duration_seconds": 125,
    "modules": ["vpc", "ec2"]
  },
  "reason": "Hotfix for database connection issue"
}
```

### Event Lifecycle

Every deployment creates multiple audit events:

```
1. Deploy Created
   {action: "deploy", status: "pending", ...}
   ↓
2. Policy Validation
   {action: "policy_check", status: "passed", ...}
   ↓
3. Cost Estimation
   {action: "cost_estimate", status: "success", details: {cost: 50}, ...}
   ↓
4. Approval Requested
   {action: "approval_requested", status: "pending", approvers: [...], ...}
   ↓
5. Approval Granted
   {action: "approved", actor: "bob-martinez", status: "approved", ...}
   ↓
6. Deployment Executed
   {action: "deploy", status: "success", details: {...}, ...}
   ↓
7. Audit Logged
   Event immutably recorded with full chain of custody
```

## Event Types

### Deployment Events

**Create Deployment**
```json
{
  "action": "deploy",
  "actor": "alice-chen",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "pending",
  "details": {
    "description": "Add VPC peering for disaster recovery",
    "terraform_modules": ["vpc"],
    "estimated_cost": 0
  }
}
```

**Execute Deployment**
```json
{
  "action": "deploy",
  "actor": "alice-chen",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "success",
  "details": {
    "resources_created": 3,
    "resources_modified": 1,
    "resources_destroyed": 0,
    "duration_seconds": 125,
    "terraform_output": {...}
  }
}
```

### Policy Validation Events

**Policy Check Passed**
```json
{
  "action": "policy_check",
  "actor": "system",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "passed",
  "details": {
    "rules_checked": 8,
    "rules_passed": 8,
    "rules_failed": 0
  }
}
```

**Policy Check Failed**
```json
{
  "action": "policy_check",
  "actor": "system",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "failed",
  "details": {
    "rules_checked": 8,
    "rules_passed": 6,
    "rules_failed": 2,
    "violations": [
      "MAX_EC2_INSTANCES_EXCEEDED",
      "COST_OVER_BUDGET"
    ]
  }
}
```

### Approval Events

**Approval Requested**
```json
{
  "action": "approval_requested",
  "actor": "alice-chen",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "pending",
  "details": {
    "approvers_needed": 2,
    "approvers": ["alice", "bob"],
    "approval_deadline": "2026-05-06T18:30:45Z"
  }
}
```

**Approval Granted**
```json
{
  "action": "approved",
  "actor": "bob-martinez",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "approved",
  "details": {
    "approval_reason": "Security review passed",
    "approvers_count": 2,
    "all_approvals_met": true
  },
  "reason": "Security review passed"
}
```

**Approval Rejected**
```json
{
  "action": "rejected",
  "actor": "bob-martinez",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "rejected",
  "reason": "Cost exceeds budget: $500/month > $200/month limit"
}
```

### Auto-Approval Events

**Auto-Approval Triggered**
```json
{
  "action": "auto_approved",
  "actor": "system",
  "environment": "production",
  "deployment_id": "deploy-001",
  "status": "approved",
  "details": {
    "wait_hours": 8,
    "approval_deadline": "2026-05-06T18:30:45Z",
    "auto_approved_at": "2026-05-06T18:30:45Z"
  },
  "reason": "Auto-approved after 8-hour waiting period"
}
```

## Querying Audit Logs

### Python API

```python
from team-management.audit import AuditLogger

logger = AuditLogger()

# Get all events
events = logger.read_events()

# Filter by actor
alice_events = logger.read_events(actor="alice-chen")

# Filter by action
deploy_events = logger.read_events(action="deploy")

# Filter by environment
prod_events = logger.read_events(environment="production")

# Get deployment history
history = logger.get_deployment_history("deploy-001")

# Get user actions
user_actions = logger.get_user_actions("alice-chen")

# Get environment history
prod_history = logger.get_environment_history("production")

# Generate report
report = logger.generate_report()
```

### Command Line

```bash
# View entire audit log
cat team-management/audit.jsonl | jq .

# Get events by actor
grep '"actor": "alice-chen"' team-management/audit.jsonl

# Get deployment events only
grep '"action": "deploy"' team-management/audit.jsonl

# Get production events
grep '"environment": "production"' team-management/audit.jsonl

# Find specific deployment
grep '"deployment_id": "deploy-001"' team-management/audit.jsonl | jq .

# Count deployments by user
grep '"action": "deploy"' team-management/audit.jsonl | \
  jq -r '.actor' | sort | uniq -c

# Find failed deployments
grep '"status": "failed"' team-management/audit.jsonl | jq .

# Export to CSV
jq -r '[.timestamp, .actor, .action, .environment, .status] | @csv' \
  team-management/audit.jsonl > audit_report.csv
```

## Compliance Reporting

### Generate Audit Report

```python
from team-management.audit import AuditLogger

logger = AuditLogger()
report = logger.generate_report()

print(f"Total Events: {report['total_events']}")
print(f"By Action: {report['by_action']}")
print(f"By Actor: {report['by_actor']}")
print(f"By Status: {report['by_status']}")
print(f"By Environment: {report['by_environment']}")
```

**Output**:
```json
{
  "total_events": 47,
  "by_action": {
    "deploy": 12,
    "approved": 10,
    "policy_check": 12,
    "approval_requested": 10,
    "auto_approved": 3
  },
  "by_actor": {
    "alice-chen": 15,
    "bob-martinez": 12,
    "carol-wong": 8,
    "system": 12
  },
  "by_status": {
    "success": 25,
    "approved": 10,
    "passed": 12
  },
  "by_environment": {
    "production": 30,
    "staging": 17
  }
}
```

### Deployment Audit Trail

Get complete audit trail for single deployment:

```bash
# Get all events for deployment
python team-management/audit.py --deployment deploy-001

# Output
Event 1: 2026-05-06T10:00:00Z — alice-chen — deploy (pending)
Event 2: 2026-05-06T10:05:00Z — system — policy_check (passed)
Event 3: 2026-05-06T10:10:00Z — system — cost_estimate (success: $50)
Event 4: 2026-05-06T10:15:00Z — alice-chen — approval_requested (pending)
Event 5: 2026-05-06T10:20:00Z — bob-martinez — approved
Event 6: 2026-05-06T10:25:00Z — alice-chen — deploy (success)
```

### User Activity Report

Track all actions by specific user:

```bash
# Get all actions by user
python team-management/audit.py --actor alice-chen

# Output showing deployment chain
2026-05-06T10:00:00Z — deploy-001 created (pending)
2026-05-06T10:25:00Z — deploy-001 executed (success)
2026-05-06T11:00:00Z — deploy-002 created (pending)
2026-05-06T11:30:00Z — deploy-002 executed (success: 2 resources modified)
```

### Environment History

Track all changes to environment:

```bash
# Get all production changes
python team-management/audit.py --environment production

# Output
Total events in production: 30
- Deployments: 12 (10 success, 2 failed)
- Approvals: 10
- Policy checks: 8
Last change: 2026-05-06T18:30:00Z by carol-wong
```

## Compliance Use Cases

### 1. SOC2 Audit Trail

**Requirement**: All infrastructure changes must be tracked with actor attribution

```python
from team-management.audit import AuditLogger

logger = AuditLogger()

# Get all deployment actions in date range
events = logger.read_events(action="deploy")

# Generate SOC2-compliant report
for event in events:
    print(f"Change ID: {event.deployment_id}")
    print(f"Changed by: {event.actor}")
    print(f"Timestamp: {event.timestamp}")
    print(f"Environment: {event.environment}")
    print(f"Status: {event.status}")
    print()
```

### 2. Change Advisory Board (CAB)

**Requirement**: Track all approvals for change management

```bash
# Get all approvals in production
grep '"action": "approved"' team-management/audit.jsonl | \
  grep '"environment": "production"'

# Output shows who approved what, when
alice-chen approved deploy-001 at 2026-05-06T10:20:00Z
bob-martinez approved deploy-001 at 2026-05-06T10:25:00Z
carol-wong approved deploy-002 at 2026-05-06T11:40:00Z
```

### 3. Failed Deployment Investigation

**Requirement**: Investigate why deployment failed

```bash
# Find failed deployment
grep '"status": "failed"' team-management/audit.jsonl | jq .

# Get full chain of events
python team-management/audit.py --deployment deploy-999

# Output shows failure point
Event 1: deploy created
Event 2: policy_check FAILED — MAX_EC2_INSTANCES_EXCEEDED
Event 3: deployment rejected (policy violation)
```

### 4. Quarterly Security Audit

**Requirement**: Report on all who deployed to production

```bash
# Get production deployments by user
grep '"environment": "production"' team-management/audit.jsonl | \
  grep '"action": "deploy"' | \
  jq -r '[.actor, .timestamp, .status] | @csv' | \
  sort | uniq > security_report.csv

# Output: alice-chen, 2026-05-06T10:25:00Z, success
```

### 5. Cost Tracking

**Requirement**: Link deployments to cost impact

```bash
# Find all deployments with cost data
grep '"details"' team-management/audit.jsonl | \
  jq 'select(.details.estimated_cost) | {actor, deployment_id, cost: .details.estimated_cost}'

# Output shows who deployed what and cost impact
alice-chen — deploy-001 — $50
bob-martinez — deploy-002 — $120
carol-wong — deploy-003 — $0 (within free tier)
```

## Audit Trail Backups

### Automated Backup

```bash
# Backup audit trail daily
0 0 * * * cp team-management/audit.jsonl \
  s3://backup-bucket/audit-$(date +\%Y\%m\%d).jsonl

# Keep 90 days of backups
```

### Restore from Backup

```bash
# Restore from backup
aws s3 cp s3://backup-bucket/audit-20260506.jsonl \
  team-management/audit.jsonl

# Verify integrity
wc -l team-management/audit.jsonl
```

## Privacy Considerations

### Sensitive Data in Logs

Audit logs may contain:
- Deployment descriptions (could contain sensitive info)
- Environment names
- User email addresses
- Actor names (GitHub usernames)

**Protection**:
- Restrict audit log access to authorized users (Viewer role)
- Redact sensitive details in reports
- Archive logs in encrypted S3 bucket
- Limit audit log retention per policy

### Example: Redacting Logs

```python
# Remove sensitive fields
def redact_audit_event(event):
    event_copy = event.copy()
    if 'details' in event_copy:
        # Remove potentially sensitive details
        del event_copy['details']['description']
    return event_copy
```

## Limitations & Considerations

### Log Retention

**Current**: Unlimited (all events kept indefinitely)

**Recommendation**: Archive old logs after 1 year

```bash
# Archive logs older than 1 year
python -c "
import json
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=365)

with open('audit.jsonl', 'r') as f:
    for line in f:
        event = json.loads(line)
        ts = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
        if ts < cutoff:
            # Archive old events
            pass
"
```

### Performance

**Concern**: Large audit logs (>100K events) slow down queries

**Solution**: Index by actor/environment/date

```bash
# Create index
python team-management/audit.py --create-index

# Now queries run faster
python team-management/audit.py --actor alice-chen --fast
```

## Best Practices

1. ✅ **Regular Backups** — Daily backup to S3
2. ✅ **Quarterly Reviews** — Audit logs for compliance
3. ✅ **Access Control** — Only Viewer role can read
4. ✅ **Archive Old Logs** — Move >1 year to cold storage
5. ✅ **Monitor Changes** — Alert on unusual deployment patterns
6. ✅ **Document Policies** — Keep audit policy in README
7. ✅ **Test Restores** — Monthly backup restore tests
8. ✅ **Redact Sensitive** — Remove sensitive details in reports

---

**Audit Trails & Compliance Logging — complete guide to immutable deployment tracking and compliance reporting.**
