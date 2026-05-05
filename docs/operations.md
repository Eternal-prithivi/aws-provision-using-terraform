# Operations Guide

## Deployment Safety

- Always review the policy engine output before applying.
- Always run Infracost before deployment.
- Keep test deployments small and destroy them after validation.

## Billing Safety

- The project is configured with a `$1` monthly budget alert.
- DynamoDB is configured for conservative free-tier testing defaults.
- If a deployment is only for validation, prefer `terraform plan` before `terraform apply`.

## Common Checks

- Confirm AWS credentials are present in the environment.
- Confirm `terraform.tfvars` has the correct service flags enabled.
- Confirm the DynamoDB partition key uses a schema-style name such as `id`.

## Troubleshooting

- If the wizard reports a missing tool, install the tool and rerun the command.
- If Terraform validation fails, check the root module wiring and variable names.
- If costs look higher than expected, review the selected instance size and DynamoDB capacity settings.