# Architecture

## High-Level Flow

1. The user runs `python cli-wizard/wizard.py`.
2. The wizard collects configuration and writes `terraform.tfvars`.
3. The policy engine evaluates the config against `policy-engine/rules.yaml`.
4. Infracost estimates monthly cost before deployment.
5. Terraform provisions the selected AWS resources.
6. GitHub Actions runs validation, cost checks, and drift detection.

## Components

- `cli-wizard/wizard.py` handles templates, prompts, validation, and deployment orchestration.
- `policy-engine/engine.py` reads rules from YAML and reports block or warning outcomes.
- `modules/` contains the reusable Terraform modules for each AWS service.
- `drift-detection/detect.sh` compares deployed state with the Terraform plan and reports drift.
- `.github/workflows/` contains CI/CD, Infracost, and drift-detection automation.

## Current Scope

- The project is AWS-only.
- The policy engine remains rule-based.
- The CLI is the primary user interface for the internship version.