# AI_RULES.md — Operating Constraints

## ❌ NEVER DO THESE

### AWS & Cost Safety
- **NEVER** hardcode AWS credentials, account IDs, or region strings
- **NEVER** provision a NAT Gateway during development (costs $32/month)
- **NEVER** use instance types larger than t2.micro during testing
- **NEVER** leave AWS resources running after a test session ends
- **NEVER** make S3 buckets public — private ACL is enforced by both code and policy engine
- **NEVER** skip `terraform destroy` at the end of a test deployment

### Code Quality
- **NEVER** write Python functions without type hints
- **NEVER** hardcode policy rules in engine.py — all rules belong in rules.yaml
- **NEVER** write code without writing its tests in the same session
- **NEVER** commit terraform.tfvars to git (it is gitignored — keep it that way)
- **NEVER** commit .terraform/ directory or .tfstate files
- **NEVER** use `subprocess.run` in tests without mocking it with unittest.mock
- **NEVER** call real AWS APIs in unit tests

### Architecture
- **NEVER** rename "Policy and Risk Engine" to "Intelligence Layer" — this name is intentional and accurate
- **NEVER** reopen decisions in DECISIONS.md — they are final
- **NEVER** merge this project with Cloud Resource Optimizer before internship is complete
- **NEVER** add a feature that is not in the current phase without updating PROGRESS.md first
- **NEVER** skip the Infracost step before deployment — cost visibility is a core feature

### Terraform
- **NEVER** write a module without variables.tf and outputs.tf
- **NEVER** use `terraform apply` without `terraform plan` first
- **NEVER** use hardcoded string values in .tf files — use variables
- **NEVER** use `count` when `for_each` is more appropriate for resource sets

---

## ✅ ALWAYS DO THESE

### Code Standards
- **ALWAYS** use Python type hints on every function signature
- **ALWAYS** use `dataclasses` or `TypedDict` for structured data in Python
- **ALWAYS** follow PEP 8 — run `pylint` before considering a task done
- **ALWAYS** write at least one edge case test per function (null, empty, invalid)
- **ALWAYS** use `unittest.mock.patch` to mock subprocess calls in tests

### Terraform Standards
- **ALWAYS** run `terraform validate` after writing any .tf file
- **ALWAYS** run `terraform fmt` before committing any .tf file
- **ALWAYS** add an `enable_<module>` boolean variable to every module
- **ALWAYS** add `tags` variable to every module for resource tagging
- **ALWAYS** include a meaningful description on every Terraform variable

### Safety Standards
- **ALWAYS** check DECISIONS.md before proposing architectural changes
- **ALWAYS** update PROGRESS.md when completing a task
- **ALWAYS** add an AUDIT_LOG.md entry after each work session
- **ALWAYS** run `terraform destroy` after test deployments
- **ALWAYS** verify AWS console shows zero resources before ending a session

### Policy Engine Standards
- **ALWAYS** add new rules to rules.yaml, never to engine.py
- **ALWAYS** set severity to either "block" or "warning" — no other values
- **ALWAYS** test every new rule with both a passing and failing fixture

---

## 📐 CODE STYLE RULES

### Python
```python
# CORRECT — type hints, docstring, clean structure
def evaluate_config(config: dict[str, Any], rules_path: str) -> EvaluationResult:
    """Evaluate infrastructure config against policy rules."""
    ...

# WRONG — no type hints, no docstring
def evaluate_config(config, rules):
    ...
```

### Terraform
```hcl
# CORRECT — variable with description and default
variable "instance_type" {
  description = "EC2 instance type. Use t2.micro for free tier."
  type        = string
  default     = "t2.micro"
}

# WRONG — no description, no default
variable "instance_type" {
  type = string
}
```

### Test Structure
```python
# CORRECT — descriptive name, arrange-act-assert, edge case
def test_detects_public_s3_bucket_returns_block_severity():
    # Arrange
    engine = PolicyEngine("tests/fixtures/sample_rules.yaml")
    config = {"s3_bucket_public": True}
    # Act
    result = engine.evaluate(config)
    # Assert
    assert result.has_violations() is True
    assert result.severity == "block"

# WRONG — vague name, no structure
def test_s3():
    assert engine.check(config) == True
```

---

## 🔐 SECURITY RULES

- All S3 buckets must have `block_public_acls = true` and `block_public_policy = true`
- All S3 buckets must have server-side encryption enabled (AES256 minimum)
- All IAM policies must follow least privilege — no `"*"` in actions or resources
- Security groups must not have `0.0.0.0/0` inbound on port 22 or 3389
- All sensitive values must come from environment variables, not .tfvars
- CloudTrail should be enabled in production environments
- Resources must have `Owner` and `Project` tags for cost attribution

---

## 📦 DEPENDENCY RULES

### Python (requirements.txt)
```
pytest>=7.0.0
pytest-cov>=4.0.0
pyyaml>=6.0
pylint>=2.17.0
```

### Infracost
- Use Infracost CLI — do not build custom pricing logic
- API key stored as `INFRACOST_API_KEY` environment variable
- Never commit API keys to git

### Terraform Providers
```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

---

## 🚫 SCOPE RULES

These features are OUT OF SCOPE for the internship version:
- Multi-user or team collaboration
- Web UI dashboard (future enhancement)
- Multi-cloud support (AWS only)
- ML-based policy decisions (rule-based only)
- Automated drift remediation (detection only)
- OPA (Open Policy Agent) integration (future enhancement)
- Real-time AWS Cost Explorer API integration (Infracost is sufficient)

Do not implement these. Do not promise these. Reference them only under "Future Enhancements."

---

*These rules are final. Do not modify without updating DECISIONS.md with a rationale.*
