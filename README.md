# Smart AWS Infrastructure Provisioning System

> An intelligent, policy-driven infrastructure-as-code system for deploying AWS resources safely and cost-effectively.

[![Terraform CI/CD](https://github.com/Eternal-prithivi/aws-provision-using-terraform/actions/workflows/terraform.yml/badge.svg)](https://github.com/Eternal-prithivi/aws-provision-using-terraform/actions/workflows/terraform.yml)

---

## Features

- **Interactive CLI Wizard** — Deploy infrastructure by answering simple questions
- **Policy Engine** — 8 security & governance rules automatically checked before deployment
- **Cost Estimation** — Infracost integration shows monthly costs before you deploy
- **Drift Detection** — Daily GitHub Actions job detects unauthorized infrastructure changes
- **Drift Remediation** — Check-only analysis of drift with safe-by-default mode
- **Multi-User Collaboration** — Role-based access control with approval workflows and audit trails
- **Free-Tier Safe** — Default configuration stays within AWS Free Tier ($0/month)
- **Modular Architecture** — 7 independent Terraform modules (VPC, EC2, S3, IAM, CloudWatch, Billing, DynamoDB)
- **144 Tests** — covering policy engine, wizard, drift remediation, team collaboration, and deployment flow

## Documentation

Project-facing documentation lives in the [`docs/`](docs) folder:

- [Documentation Hub](docs/README.md)
- [Product Overview](docs/product-overview.md)
- [Architecture](docs/architecture.md)
- [Getting Started](docs/getting-started.md)
- [Operations Guide](docs/operations.md)
- [Roadmap](docs/roadmap.md)

## Roadmap

Completed: Phases 1-12 (all core features + multi-user collaboration).

The next planned enhancements, in order, are:
1. OPA integration — extend policy control with Open Policy Agent.
2. Web UI dashboard — add a visual interface for easier interaction.

---

## Quick Start

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Terraform | >= 1.10.0 | [terraform.io](https://www.terraform.io/downloads) |
| Python | >= 3.9 | [python.org](https://www.python.org/downloads/) |
| AWS CLI | >= 2.x | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| Infracost | >= 0.10 | [infracost.io](https://www.infracost.io/docs/) |
| Git | >= 2.x | [git-scm.com](https://git-scm.com/) |

### 1. Clone and Install

```bash
git clone https://github.com/Eternal-prithivi/aws-provision-using-terraform.git
cd aws-provision-using-terraform
pip install -r requirements.txt
```

### 2. Configure AWS

```bash
aws configure
# Enter your AWS Access Key ID, Secret Key, and default region (ap-south-1)
```

### 3. Initialize Terraform

```bash
terraform init
```

### 4. Run the Wizard

```bash
python cli-wizard/wizard.py
```

The wizard will:
1. Ask you to select a template or custom configuration
2. Configure your selected AWS services
3. Run the **Policy Engine** — blocks insecure configurations
4. Run **Infracost** — shows estimated monthly cost
5. Deploy with `terraform apply` (after your confirmation)

### 5. Destroy Resources

```bash
python cli-wizard/wizard.py --destroy
# or
terraform destroy
```

---

## Project Structure

```
├── main.tf                     # Root Terraform configuration
├── variables.tf                # Input variables with defaults
├── outputs.tf                  # Deployment outputs
├── backend.tf                  # S3 remote state backend
│
├── modules/
│   ├── vpc/                    # VPC with public/private subnets
│   ├── ec2/                    # EC2 instance (default: t2.micro)
│   ├── s3/                     # S3 bucket (private + AES256 encryption)
│   ├── iam/                    # IAM role (least privilege)
│   ├── cloudwatch/             # CloudWatch alarms + SNS
│   ├── billing/                # AWS Budget ($1 alert)
│   └── dynamodb/               # DynamoDB table (Always Free-ready)
│
├── docs/                      # Project-facing documentation hub
├── policy-engine/
│   ├── engine.py               # PolicyEngine class (load, evaluate, report)
│   └── rules.yaml              # 8 security & governance rules
│
├── cli-wizard/
│   └── wizard.py               # Interactive CLI wizard
│
├── drift-detection/
│   └── detect.sh               # Infrastructure drift detector
│
├── templates/
│   ├── static-site/            # S3-only static website template
│   └── backend-app/            # VPC + EC2 + IAM backend template
│
├── tests/
│   ├── unit/                   # Unit tests (policy engine, wizard)
│   ├── integration/            # Integration tests (terraform, infracost)
│   └── fixtures/               # Test data files
│
└── .github/workflows/
    ├── terraform.yml           # CI: test → fmt → init → validate → plan
    ├── infracost.yml           # PR cost diff comments
    └── drift-detection.yml     # Daily drift check (cron)
```

---

## Policy Engine

The policy engine enforces 8 rules before any deployment:

| Rule | Type | Description |
|---|---|---|
| `no_public_s3` | 🚫 Block | S3 buckets must not be public |
| `no_open_ssh` | 🚫 Block | SSH (port 22) must not be open to 0.0.0.0/0 |
| `no_open_rdp` | 🚫 Block | RDP (port 3389) must not be open to 0.0.0.0/0 |
| `no_iam_wildcard` | 🚫 Block | IAM policies must not use `*` permissions |
| `expensive_ec2` | ⚠️ Warn | Non-free-tier instance types trigger warnings |
| `s3_encryption` | ⚠️ Warn | S3 encryption must be enabled |
| `missing_tags` | ⚠️ Warn | All resources must have tags |
| `cloudtrail` | ⚠️ Warn | CloudTrail should be enabled in production |

**Block** rules prevent deployment. **Warn** rules allow deployment with acknowledgment.

---

## Available Templates

### Static Site (S3 Only)
```bash
# Deploys: S3 bucket (private, encrypted) + Budget alert
# Cost: $0.00/month
```

### Backend Application (VPC + EC2 + IAM)
```bash
# Deploys: VPC + EC2 (t2.micro) + IAM role + Budget alert
# Cost: $0.00/month (within free tier)
```

---

## CI/CD Pipeline

| Workflow | Trigger | Actions |
|---|---|---|
| `terraform.yml` | Push to `main`/`development` | pytest → fmt → init → validate → plan |
| `infracost.yml` | PR to `main` | Cost estimate + PR comment |
| `drift-detection.yml` | Daily at 06:00 UTC | terraform plan drift check |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=80

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

**Current: 106 tests, 98% coverage**

---

## Configuration

All configuration is done through `terraform.tfvars` (generated by the wizard or manually):

```hcl
aws_region = "ap-south-1"

# Feature flags
enable_vpc        = true
enable_ec2        = true
enable_s3         = false
enable_iam        = true
enable_cloudwatch = false

# Service configuration
vpc_cidr      = "10.0.0.0/16"
instance_type = "t2.micro"          # Free tier
ami_id        = "ami-0f58b397bc5c1f2e8"  # Amazon Linux 2 (ap-south-1)
bucket_name   = "my-unique-bucket-name"
role_name     = "app-role"
alarm_email   = "alerts@example.com"

# Budget
budget_limit = "1"
budget_email = "billing@example.com"

# Tags (required by policy)
tags = {
  Owner   = "developer"
  Project = "my-project"
  Env     = "free-tier"
}
```

---

## Security

- **No credentials in code** — AWS credentials via environment variables or `aws configure`
- **S3 buckets** — Always private, AES256 encrypted, public access blocked
- **IAM roles** — Least privilege, no wildcard (`*`) permissions
- **Security groups** — No SSH/RDP open to the world
- **State files** — Encrypted in S3 with versioning
- **Sensitive data** — `.gitignore` excludes `.tfstate`, `.tfvars`, `.env`

---

## Cost Safety

- Default budget: **$1/month** with email alerts
- All templates use **free-tier** resources
- `terraform destroy` reminder shown after every deployment
- Policy engine warns on expensive instance types
- Infracost shows cost estimate before deployment

---

## License

MIT

---

## Author

**A. Prithiviraj** — [GitHub](https://github.com/Eternal-prithivi)
