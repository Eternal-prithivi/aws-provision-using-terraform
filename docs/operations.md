# Operations Guide

## Deployment Safety

- Always review the policy engine output before applying.
- Always run Infracost before deployment.
- Keep test deployments small and destroy them after validation.

## Billing Safety

- The project is configured with a `$1` monthly budget alert.
- DynamoDB is configured for conservative free-tier testing defaults.
- If a deployment is only for validation, prefer `terraform plan` before `terraform apply`.

## Drift Detection & Remediation (Phase 11)

The automated drift remediation feature operates in **check-only mode by default** for safety:

### How It Works

1. **Daily at 06:00 UTC** (or via manual trigger), GitHub Actions runs drift detection
2. **Detects drift**: Compares AWS actual state to your Terraform desired state
3. **Analyzes changes** (check-only mode): Runs `terraform plan` to show what would change
4. **Generates reports**: Creates `drift-report.txt` and `drift-remediation-report.txt`
5. **Human review**: You review the reports and decide whether to apply changes

### Understanding the Reports

- **drift-report.txt**: Shows what AWS resources differ from Terraform code
- **drift-remediation-report.txt**: Shows what `terraform plan` would do (CHECK-ONLY status)

### Production-Safe Design

By default, **no automatic changes are applied**. This prevents accidental auto-remediation of intentional infrastructure changes:

- ✅ **You delete S3 bucket intentionally** → Drift detected but not automatically re-created
- ✅ **Manual AWS changes are detected** → Reports generated for review
- ✅ **Audit trail maintained** → All drift events logged in GitHub Actions artifacts

### Manual Approval Workflow (When Needed)

If you want to remediate drift automatically (not recommended for most production environments), you would need to:

1. Modify `.github/workflows/drift-detection.yml` to remove `--check-only` flag
2. Add `--auto-approve` flag (requires explicit opt-in)
3. Accept the risk that intentional resource deletions may be auto-reverted

This is a **conscious security decision** to prevent accidents.

## Common Checks

- Confirm AWS credentials are present in the environment.
- Confirm `terraform.tfvars` has the correct service flags enabled.
- Confirm the DynamoDB partition key uses a schema-style name such as `id`.

## Troubleshooting

- If the wizard reports a missing tool, install the tool and rerun the command.
- If Terraform validation fails, check the root module wiring and variable names.
- If costs look higher than expected, review the selected instance size and DynamoDB capacity settings.
- If drift is reported but you made intentional changes, verify your Terraform code matches your desired state.