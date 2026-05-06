# Roles & Permissions Reference

## Overview

This document defines all available roles, their permissions, and usage guidelines for the multi-user collaboration system (Phase 12).

## Role Definitions

### 1. Administrator (Admin)

**Purpose**: Full infrastructure management and team oversight

**Permission Matrix**:

| Permission | Grant | Description |
|-----------|-------|-------------|
| `deploy:create` | ✅ | Create deployment requests |
| `deploy:approve` | ✅ | Approve pending deployments |
| `deploy:auto_approve` | ✅ | Auto-approve without waiting |
| `deploy:execute` | ✅ | Run terraform apply |
| `team:manage` | ✅ | Add/remove team members |
| `settings:modify` | ✅ | Change approval workflows |
| `audit:view_all` | ✅ | Read all audit logs |
| `audit:delete` | ✅ | (Reserved, not implemented) |

**Characteristics**:
- No waiting time for approval (auto_approve_threshold = 0)
- No approval required (requires_approval = false)
- Unlimited deployments per day
- Can deploy to all environments
- Can approve for any role
- Receives escalation alerts

**Deployment Limit**: Unlimited

**Use Cases**:
- Infrastructure leads
- Platform team managers
- DevOps directors
- System administrators

**Example**:
```yaml
roles:
  admin:
    name: "Administrator"
    permissions:
      - deploy:create
      - deploy:approve
      - deploy:auto_approve
      - team:manage
      - settings:modify
      - audit:view_all
    auto_approve_threshold: 0
    requires_approval: false
    max_per_day: null
```

---

### 2. DevOps Engineer (DevOps)

**Purpose**: Infrastructure deployment and approval authority

**Permission Matrix**:

| Permission | Grant | Description |
|-----------|-------|-------------|
| `deploy:create` | ✅ | Create deployment requests |
| `deploy:approve` | ✅ | Approve deployments |
| `deploy:auto_approve` | ✅ | Auto-approve with threshold met |
| `deploy:execute` | ✅ | Run terraform apply |
| `team:manage` | ❌ | Cannot manage teams |
| `settings:modify` | ❌ | Cannot modify settings |
| `audit:view_all` | ✅ | Read all audit logs |
| `audit:delete` | ❌ | Cannot delete logs |

**Characteristics**:
- Can auto-approve after threshold met (auto_approve_threshold = 0 for staging, 4+ for production)
- May require approval from Admin for production
- 10 deployments per day
- Can deploy to production and staging
- Can approve for Developers
- Primary approval authority

**Deployment Limit**: 10 per day

**Use Cases**:
- DevOps engineers
- Infrastructure engineers
- Release managers
- Platform engineers

**Example**:
```yaml
roles:
  devops:
    name: "DevOps Engineer"
    permissions:
      - deploy:create
      - deploy:approve
      - deploy:auto_approve
      - team:manage
      - audit:view_all
    auto_approve_threshold: 0
    requires_approval: false
    max_per_day: 10
```

---

### 3. Developer

**Purpose**: Create and deploy application infrastructure with oversight

**Permission Matrix**:

| Permission | Grant | Description |
|-----------|-------|-------------|
| `deploy:create` | ✅ | Create deployment requests |
| `deploy:approve` | ❌ | Cannot approve |
| `deploy:auto_approve` | ❌ | Cannot auto-approve |
| `deploy:execute` | ❌ | Cannot run apply directly |
| `team:manage` | ❌ | Cannot manage teams |
| `settings:modify` | ❌ | Cannot modify settings |
| `audit:view_all` | ❌ | Cannot view all logs |
| `audit:view_own` | ✅ | Read own deployment history |

**Characteristics**:
- Requires approval from DevOps/Admin (requires_approval = true)
- Can auto-approve after threshold met (auto_approve_threshold = 8 hours for production)
- 5 deployments per day
- Can deploy to staging only (or production with approval)
- Cannot approve other deployments
- Can only see their own audit logs

**Deployment Limit**: 5 per day

**Use Cases**:
- Application developers
- Backend engineers
- Junior infrastructure engineers
- Service owners

**Example**:
```yaml
roles:
  developer:
    name: "Developer"
    permissions:
      - deploy:create
      - audit:view_own
    auto_approve_threshold: 8
    requires_approval: true
    approval_required_from:
      - admin
      - devops
    max_per_day: 5
```

---

### 4. Viewer

**Purpose**: Read-only access for auditing and compliance

**Permission Matrix**:

| Permission | Grant | Description |
|-----------|-------|-------------|
| `deploy:create` | ❌ | Cannot create deployments |
| `deploy:approve` | ❌ | Cannot approve |
| `deploy:auto_approve` | ❌ | Cannot auto-approve |
| `deploy:execute` | ❌ | Cannot run apply |
| `team:manage` | ❌ | Cannot manage teams |
| `settings:modify` | ❌ | Cannot modify settings |
| `audit:view_all` | ✅ | Read all audit logs |
| `audit:delete` | ❌ | Cannot delete logs |

**Characteristics**:
- Read-only access
- Cannot deploy anything
- Cannot approve anything
- Can view all audit logs (compliance/security teams)
- Cannot create teams or settings

**Deployment Limit**: 0 (cannot deploy)

**Use Cases**:
- Security auditors
- Compliance officers
- Finance/billing team
- SREs (read-only)
- Consultants (read-only access)

**Example**:
```yaml
roles:
  viewer:
    name: "Viewer"
    permissions:
      - audit:view_all
    auto_approve_threshold: null
    requires_approval: false
    max_per_day: 0
```

---

## Permission Details

### Deploy Permissions

**`deploy:create`** — Create a deployment request
- Allows user to submit terraform changes
- Does not allow applying changes
- Workflow: Create request → Policy validation → Cost estimation → Approval queue

**`deploy:approve`** — Approve pending deployments
- Can approve deployment requests from others
- Must approve before `deploy:execute` can run
- Typically requires Admin or DevOps role

**`deploy:auto_approve`** — Approve automatically based on threshold
- Automatically approves after waiting time expires
- Threshold is hours (e.g., 8 hours for developers)
- Prevents waiting indefinitely for approvals

**`deploy:execute`** — Run terraform apply
- Actually applies infrastructure changes
- Only allowed after approval
- Creates immutable audit log entry

### Team Permissions

**`team:manage`** — Manage team membership and roles
- Add new team members
- Remove team members
- Assign roles to members
- Modify team structure

**`settings:modify`** — Modify approval workflows
- Change approval requirements
- Modify auto-approve thresholds
- Configure maintenance windows
- Update escalation policies

### Audit Permissions

**`audit:view_all`** — Read all deployment and approval logs
- Can query any user's actions
- Can view any deployment history
- Can generate full audit reports
- Typically for compliance/security teams

**`audit:view_own`** — Read only own deployment logs
- Can query own deployments
- Can see own approvals
- Cannot see other users' actions
- Limited audit access for developers

---

## Environment-Specific Permissions

Permissions can be restricted by environment:

```yaml
teams:
  application-team:
    members:
      - name: "Carol Wong"
        role: developer
    environment_access:
      staging:
        role: developer
        permissions:
          - deploy:create
          - deploy:execute
          - audit:view_own
      production:
        role: developer
        permissions:
          - deploy:create
          - audit:view_own
        # No deploy:execute for production (must wait for approval)
```

---

## Role Assignment Best Practices

### Team Composition

**Recommended team structure**:

```yaml
teams:
  devops-core:        # Production team
    members:
      - name: "Alice"
        role: admin        # 1 admin
      - name: "Bob"
        role: devops       # 1-2 devops engineers
  
  platform-team:      # Platform team
    members:
      - name: "Carol"
        role: devops       # Lead
      - name: "David"
        role: developer    # Support
  
  compliance:         # Audit team
    members:
      - name: "Eve"
        role: viewer       # Read-only access
```

### Avoid Anti-Patterns

❌ **Bad**: Give everyone admin role
```yaml
members:
  - role: admin
  - role: admin
  - role: admin
```

✅ **Good**: Distribute roles based on responsibility
```yaml
members:
  - role: admin         # Infrastructure lead
  - role: devops        # Engineers
  - role: developer     # Application team
```

❌ **Bad**: No developers with staging access
```yaml
developers:
  - role: viewer        # Cannot deploy anything
```

✅ **Good**: Let developers deploy to staging
```yaml
developers:
  - role: developer     # Can deploy to staging
```

---

## Permission Escalation Examples

### Example 1: Developer Deployment to Production

```
Developer Carol creates deployment request to production
  ↓
Policy engine validates (passes)
  ↓
Cost estimation runs (shows impact)
  ↓
Approval request sent to Bob (DevOps) + Alice (Admin)
  ↓
Bob approves after 30 minutes
  ↓
Alice approves after 1 hour
  ↓
Terraform apply proceeds (2 approvals met)
  ↓
Audit log: Carol (deploy:create) → Bob (deploy:approve) → Alice (deploy:approve) → Carol (deploy:execute)
```

### Example 2: DevOps Auto-Approval to Staging

```
Bob (DevOps) creates deployment request to staging
  ↓
Policy engine validates (passes)
  ↓
Cost estimation runs (shows impact)
  ↓
Waiting time starts (0 minutes for devops)
  ↓
4-hour auto-approval threshold passed immediately
  ↓
Terraform apply proceeds (auto-approved)
  ↓
Audit log: Bob (deploy:create) → Bob (deploy:auto_approve) → Bob (deploy:execute)
```

### Example 3: Viewer Audit Review

```
Eve (Viewer) queries audit trail for compliance report
  ↓
Eve can see all deployments, approvals, and results
  ↓
Eve generates report showing who deployed what, when, and why
  ↓
Report ready for compliance/security review
  ↓
Eve cannot create deployments or modify anything
```

---

## Migration Guide: Adding Roles

### Step 1: Define New Role in YAML

```yaml
roles:
  senior-devops:
    name: "Senior DevOps Engineer"
    permissions:
      - deploy:create
      - deploy:approve
      - team:manage  # New: manage team members
    auto_approve_threshold: 0
    requires_approval: false
    max_per_day: 20  # Increased from 10
```

### Step 2: Migrate Members to New Role

```yaml
teams:
  devops-core:
    members:
      - name: "Bob Martinez"
        role: senior-devops  # Changed from devops
```

### Step 3: Test New Permissions

```bash
python team-management/team_engine.py \
  --user bob-martinez \
  --permission team:manage \
  --verify
# ✅ bob-martinez has 'team:manage'
```

### Step 4: Validate No Regressions

```bash
pytest tests/unit/test_team_engine.py -v
# All tests passing
```

---

## Permission Matrix Reference

| Permission | Admin | DevOps | Developer | Viewer |
|-----------|-------|--------|-----------|--------|
| `deploy:create` | ✅ | ✅ | ✅ | ❌ |
| `deploy:approve` | ✅ | ✅ | ❌ | ❌ |
| `deploy:auto_approve` | ✅ | ✅ | ✅ | ❌ |
| `deploy:execute` | ✅ | ✅ | ❌ | ❌ |
| `team:manage` | ✅ | ❌ | ❌ | ❌ |
| `settings:modify` | ✅ | ❌ | ❌ | ❌ |
| `audit:view_all` | ✅ | ✅ | ❌ | ✅ |
| `audit:view_own` | ✅ | ✅ | ✅ | ❌ |

---

**Roles & Permissions Reference — complete guide to role-based access control in Phase 12.**
