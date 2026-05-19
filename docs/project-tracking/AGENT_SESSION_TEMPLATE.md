# AGENT_SESSION_TEMPLATE.md — Audit Log Entry Format

> Copy this template into AUDIT_LOG.md at the start of every session.
> Fill in all sections. Add entry at the TOP of AUDIT_LOG.md (newest first).

---

## Template

```markdown
## [SESSION-XXX] [Short description of what was done]
**Date**: [Today's date]
**Agent/Human**: [Claude / Human / Claude + Human]
**Phase**: [Phase N — Phase Name]

### Actions Taken
- [Specific action 1]
- [Specific action 2]
- [Files created or modified]

### Tests Run
- [ ] pytest tests/unit/ — [PASS / FAIL / NOT RUN]
- [ ] pytest tests/integration/ — [PASS / FAIL / NOT RUN]
- [ ] terraform validate — [PASS / FAIL / NOT RUN]
- [ ] terraform fmt — [PASS / FAIL / NOT RUN]

### AWS Resources
- Provisioned: [list resources or "none"]
- Destroyed: [list resources or "none"]
- Billing check: [$0 confirmed / NOT CHECKED — must check before session end]

### Decisions Made
- [Any new decisions → also add to DECISIONS.md]
- [Or: "No new decisions"]

### PROGRESS.md Updated
- [ ] Tasks moved from In Progress → Completed
- [ ] Phase status updated if phase completed

### Next Session Should
- [Exact next task]
- [Any context needed for next session]

### Issues / Blockers
- [Any problems encountered]
- [Or: "None"]
```

---

## Example Filled Entry

```markdown
## [SESSION-004] Policy engine complete — all 8 rules passing
**Date**: 2025-06-15
**Agent/Human**: Claude + Human
**Phase**: Phase 2 — Policy and Risk Engine

### Actions Taken
- Created policy-engine/rules.yaml with all 8 rules
- Created policy-engine/engine.py (PolicyEngine class)
- Created tests/fixtures/sample_rules.yaml
- Created tests/fixtures/valid_config.tfvars
- Created tests/fixtures/insecure_config.tfvars
- Created tests/unit/test_policy_engine.py (24 tests)
- Created tests/conftest.py with shared fixtures

### Tests Run
- [x] pytest tests/unit/ — PASS (24 tests, 0 failures)
- [ ] pytest tests/integration/ — NOT RUN (not yet written)
- [ ] terraform validate — NOT RUN (Phase 3)
- [ ] terraform fmt — NOT RUN (Phase 3)

### AWS Resources
- Provisioned: none
- Destroyed: none
- Billing check: $0 confirmed

### Decisions Made
- No new decisions

### PROGRESS.md Updated
- [x] Phase 2 tasks marked complete
- [x] Phase 2 status → Complete
- [x] Phase 3 status → In Progress

### Next Session Should
- Start Phase 3: Write Terraform modules
- Begin with modules/vpc/

### Issues / Blockers
- None
```
