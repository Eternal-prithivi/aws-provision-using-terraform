# Approval Workflows Guide

## Overview

Approval workflows in Phase 12 provide environment-specific gates for infrastructure deployments. Different environments (staging vs production) have different approval requirements, auto-approval times, and scheduling restrictions.

## Core Concepts

### 1. Approval Requirements

Each environment has configurable approval rules:

```yaml
approval_workflows:
  staging:
    requires_approvals: 1      # How many approvals needed?
    approvers_must_include:    # Which roles must approve?
      - devops
    auto_approve_after_hours: 4  # Auto-approve after waiting
    allow_weekend_deploy: true   # Can deploy on weekends?
    allow_holiday_deploy: false  # Can deploy on holidays?
```

### 2. Approval Modes

**Standard Approval**:
- Developer creates request
- Waits for specified approvers
- Someone with approval permission approves manually

**Auto-Approval**:
- Developer creates request
- System waits X hours
- Automatically approves if not already approved
- Prevents indefinite waiting

### 3. Escalation

When approvals are pending too long:
- **Level 1** (30 min): Slack notification to team
- **Level 2** (60 min): Escalate to backup approver
- **Auto-Approve** (480 min = 8 hours): Auto-approve to unblock

## Environment Configurations

### Staging Deployments

**Standard Configuration**:
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

**Approval Flow**:
```
1. Developer creates request
   ↓
2. Policy engine validates
   ↓
3. Cost estimation runs
   ↓
4. Approval needed from: 1 DevOps engineer
   ↓
5a. (Manual approval) DevOps approves → proceed
5b. (Auto-approval) After 4 hours → auto-approve → proceed
   ↓
6. Terraform apply
```

**Approval Time**: 4 hours max (auto-approves)
**Deployable Days**: Mon-Fri, Sat, Sun (not holidays)
**Common Use Case**: Staging environment for testing

### Production Deployments

**Standard Configuration**:
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

**Approval Flow**:
```
1. Developer creates request
   ↓
2. Policy engine validates
   ↓
3. Cost estimation runs
   ↓
4. Approval needed from: 1 Admin + 1 DevOps (any order)
   ↓
5. Slack notifications sent to both approvers
   ↓
6a. (First approval) Admin approves → waiting for DevOps
   ↓
6b. (Second approval) DevOps approves → all approvals met
   ↓
7. (Wait time) After 8 hours → auto-approve if not yet approved
   ↓
8. Terraform apply
```

**Approval Time**: 8 hours max (auto-approves)
**Deployable Days**: Mon-Fri only (not weekends/holidays)
**Common Use Case**: Production environment

### Custom Environment

**Example: QA Environment**:
```yaml
approval_workflows:
  qa:
    name: "QA Approval Workflow"
    requires_approvals: 2
    approvers_must_include:
      - devops
      - devops
    auto_approve_after_hours: 2
    allow_weekend_deploy: true
    allow_holiday_deploy: false
```

## Approval Workflows by Role

### For Developers

**Staging Deployment**:
```
Developer submits request
  ↓
1 DevOps approval required (or 4 hours wait)
  ↓
Terraform apply
```

**Production Deployment**:
```
Developer submits request
  ↓
2 approvals required (Admin + DevOps) (or 8 hours wait)
  ↓
Terraform apply
```

### For DevOps Engineers

**Staging Deployment**:
```
DevOps submits request
  ↓
No approval required (self-approve immediately)
  ↓
Terraform apply
```

**Production Deployment**:
```
DevOps submits request
  ↓
Admin approval required (or 8 hours wait)
  ↓
Terraform apply
```

### For Admins

**Any Deployment**:
```
Admin submits request
  ↓
No approval required (auto-approve immediately)
  ↓
Terraform apply
```

## Scheduling & Maintenance Windows

### Business Hours Restriction

```yaml
maintenance_windows:
  - name: "Business Hours"
    timezone: "America/New_York"
    allow_on: [Monday, Tuesday, Wednesday, Thursday, Friday]
    start_hour: 9
    start_minute: 0
    end_hour: 18
    end_minute: 0
```

**Effect**: Production deployments outside business hours are queued until next business day

### Maintenance Windows

```yaml
maintenance_windows:
  - name: "Wednesday Maintenance Window"
    timezone: "UTC"
    allow_on: [Wednesday]
    start_hour: 2
    start_minute: 0
    end_hour: 4
    end_minute: 0
```

**Effect**: Infrastructure changes allowed only during this 2-hour window

### Holiday Restrictions

```yaml
holidays:
  - 2024-12-25  # Christmas
  - 2024-01-01  # New Year
  - 2024-07-04  # Independence Day
```

**Effect**: Deployments blocked on these dates regardless of approval

## Approval Scenarios

### Scenario 1: Standard Staging Deployment

**Timeline**:
- **10:00 AM** — Carol (Developer) creates staging deployment
- **10:05 AM** — Policy engine validates ✅, costs shown
- **10:10 AM** — Slack notifies Bob (DevOps): "Approval needed"
- **10:15 AM** — Bob approves
- **10:16 AM** — Terraform apply proceeds ✅
- **10:20 AM** — Audit log: Carol created, Bob approved, Carol executed

**Key**: Fast feedback loop, 1 approval, only 5 minutes

### Scenario 2: Urgent Production Deployment

**Timeline**:
- **2:00 PM** — Carol (Developer) creates prod deployment (urgent hotfix)
- **2:05 PM** — Policy engine validates ✅, costs shown ($50/month)
- **2:10 PM** — Slack notifies Alice (Admin) and Bob (DevOps)
- **2:15 PM** — Alice approves (1/2)
- **2:20 PM** — Bob approves (2/2) — all approvals met
- **2:21 PM** — Terraform apply proceeds ✅
- **2:30 PM** — Audit log: Full approval chain recorded

**Key**: 2 approvals needed, but fast (21 minutes total)

### Scenario 3: Auto-Approval After Waiting

**Timeline**:
- **9:00 AM** — Carol (Developer) creates prod deployment
- **9:05 AM** — Policy engine validates ✅, costs shown
- **9:10 AM** — Slack notifies Alice and Bob
- **9:15 AM** — Alice approves, but Bob doesn't respond (1/2)
- **5:00 PM** — Still waiting after 8 hours
- **5:01 PM** — Auto-approval triggers (threshold reached)
- **5:02 PM** — Terraform apply proceeds ✅
- **5:10 PM** — Audit log: Records auto-approval event

**Key**: Prevents indefinite waiting, auto-approves after 8 hours

### Scenario 4: Escalation Alert

**Timeline**:
- **10:00 AM** — Carol creates production deployment
- **10:05 AM** — Approval request sent
- **10:35 AM** — No approval after 30 minutes
- **10:36 AM** — Slack escalation alert: "Escalating to level 2"
- **10:37 AM** — Senior DevOps (backup) notified
- **10:45 AM** — Senior DevOps approves (1/2)
- **11:00 AM** — Bob approves (2/2)
- **11:01 AM** — Terraform apply proceeds ✅

**Key**: Escalation ensures response even if primary approver is away

### Scenario 5: Weekend Staging (No Prod)

**Timeline**:
- **Saturday 2:00 PM** — Carol (Developer) creates staging deployment
- **Saturday 2:05 PM** — Policy engine validates ✅
- **Saturday 2:10 PM** — Slack notifies Bob (staging allows weekends)
- **Saturday 2:15 PM** — Bob approves
- **Saturday 2:16 PM** — Terraform apply proceeds ✅

**vs Production on Saturday**:
- **Saturday 2:00 PM** — Carol creates production deployment
- **Saturday 2:05 PM** — ❌ **Error: Cannot deploy to production on weekend**
- **Solution**: Wait until Monday 9:00 AM during business hours

**Key**: Environment restrictions prevent risky weekend prod changes

### Scenario 6: Holiday Restriction

**Timeline**:
- **December 25 (Christmas) 10:00 AM** — Carol creates deployment
- **December 25 10:05 AM** — ❌ **Error: Cannot deploy on holiday**
- **Solution**: Deploy before or after holiday

**Effect**: Holiday blackout across all environments

## Handling Approvals

### Approving a Deployment

```bash
# Get list of pending approvals
python team-management/audit.py --action "approve_pending"

# Find deployment to approve
grep "status.*pending" audit.jsonl

# Approve in CI/CD
gh workflow run approve-deployment.yml \
  --ref development \
  --field deployment_id=deploy-12345 \
  --field approval_decision=approved \
  --field comments="Looks good. Security review passed."
```

### Rejecting a Deployment

```bash
# Reject with reason
gh workflow run approve-deployment.yml \
  --ref development \
  --field deployment_id=deploy-12345 \
  --field approval_decision=rejected \
  --field comments="Cost too high ($500/month), requires CFO approval"
```

### Requesting Extension

```bash
# If approval time is running out, request extension
gh workflow run request-approval-extension.yml \
  --ref development \
  --field deployment_id=deploy-12345 \
  --field hours=4 \
  --field reason="Waiting for compliance review"
```

## Best Practices

### 1. Staging = Fast, Production = Careful

```yaml
staging:
  requires_approvals: 1
  auto_approve_after_hours: 4
  allow_weekend_deploy: true

production:
  requires_approvals: 2
  auto_approve_after_hours: 8
  allow_weekend_deploy: false
```

### 2. Document Why Approvals Matter

Add comments to workflows explaining requirements:

```yaml
approval_workflows:
  production:
    # 2 approvals prevent single person from introducing bugs
    requires_approvals: 2
    
    # Must include both admin (business) and devops (technical)
    approvers_must_include:
      - admin    # Business context
      - devops   # Technical review
    
    # 8 hours max wait prevents blocking critical fixes
    auto_approve_after_hours: 8
```

### 3. Set Realistic Auto-Approve Times

- **Staging**: 4 hours (fast feedback)
- **Production**: 8 hours (more conservative)
- **Critical**: 2 hours (for hotfixes)

### 4. Team-Specific Approval Rules

Different teams may need different rules:

```yaml
approval_workflows:
  production:
    # Platform team (infrastructure): 2 approvals, 8 hours
    teams:
      - platform-team
    requires_approvals: 2
    auto_approve_after_hours: 8
    
    # Devops core (ops team): 1 approval, 4 hours
    teams:
      - devops-core
    requires_approvals: 1
    auto_approve_after_hours: 4
```

### 5. Alert on Pending Approvals

Configure Slack to ping approvers:

```yaml
escalation_policies:
  level_1:
    wait_minutes: 30
    notify: ["@devops-team"]
    message: "Deployment pending for 30 min, needs your review"
  
  level_2:
    wait_minutes: 60
    notify: ["@admin-channel"]
    message: "Escalating critical deployment approval"
```

## Troubleshooting

### Approval Always Fails

**Problem**: Deployment stuck in pending state

```bash
# Check approval requirements
python team-management/team_engine.py \
  --environment production \
  --approvers
```

**Solution**: Ensure at least 1 person has DevOps or Admin role

### Auto-Approve Not Working

**Problem**: After 8 hours, deployment still pending

**Cause**: Auto-approval disabled, or threshold misconfigured

```yaml
# Wrong (never auto-approves)
approval_workflows:
  production:
    auto_approve_after_hours: null

# Right (auto-approves after 8 hours)
approval_workflows:
  production:
    auto_approve_after_hours: 8
```

### Cannot Deploy on Weekend

**Problem**: Staging deployment blocked on Saturday

```bash
# Check scheduling rules
python team-management/team_engine.py --environment staging --can-deploy-now
# Result: allow_weekend_deploy = true (should work)
```

**Solution**: Check if scheduled maintenance window is active

---

**Approval Workflows — complete guide to environment-specific deployment gates and escalation policies.**
