# Product Overview

The Smart AWS Infrastructure Provisioning System is a Terraform-based, policy-driven AWS deployment tool designed to help users provision infrastructure safely and with cost awareness. It combines a Python CLI wizard, a YAML-based policy engine, Infracost, and modular Terraform components to reduce misconfiguration and keep deployments within budget-conscious defaults.

The current implementation supports VPC, EC2, S3, IAM, CloudWatch, Billing alerts, and DynamoDB. The core 10 phases are complete, and the roadmap now includes four planned enhancement phases: drift remediation, multi-user collaboration, OPA integration, and a web UI dashboard.