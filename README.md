# Smart AWS Infrastructure Provisioning System

> An intelligent, policy-driven infrastructure-as-code system for deploying AWS resources safely and cost-effectively.

[![Terraform CI/CD](https://github.com/Eternal-prithivi/aws-provision-using-terraform/actions/workflows/terraform.yml/badge.svg)](https://github.com/Eternal-prithivi/aws-provision-using-terraform/actions/workflows/terraform.yml)

---

## Features

- **Modern Web UI Dashboard** — Next.js 14 frontend with a premium, glassmorphic design and Framer Motion animations.
- **FastAPI Backend** — Robust Python backend handling 19 REST endpoints, SSE streaming, and async background tasks.
- **Interactive Deploy Wizard** — Deploy infrastructure step-by-step with real-time Terraform plan/apply streaming.
- **Dual Policy Engine (YAML + OPA)** — 8 built-in security & governance rules plus Open Policy Agent (Rego) integration. Custom policies can be added via the UI.
- **Team Management & RBAC** — Role-based access control (Admin, DevOps, Developer, Viewer) managing permissions dynamically.
- **Approval Workflows & Slack Integration** — Deployment requests are routed to an approval queue with real-time Slack webhook notifications.
- **Cost Estimation** — Infracost integration shows monthly costs before you deploy.
- **Drift Detection & Remediation** — Daily GitHub Actions job detects unauthorized changes. "Dry Run" and "Apply" fixes can be triggered directly from the Web UI.
- **Free-Tier Safe** — Default configuration stays within AWS Free Tier ($0/month).
- **Modular Architecture** — 7 independent Terraform modules (VPC, EC2, S3, IAM, CloudWatch, Billing, DynamoDB).
- **221 Tests** — Extensive coverage for policy engines, API endpoints, team collaboration, and deployment flows.

## Documentation

Project-facing documentation lives in the [`docs/`](docs) folder:

- [Documentation Hub](docs/README.md)
- [Product Overview](docs/product-overview.md)
- [Architecture](docs/architecture.md)
- [Getting Started](docs/getting-started.md)
- [Operations Guide](docs/operations.md)
- [Roadmap](docs/roadmap.md)

## Roadmap

**Project Complete: Phases 1-15 successfully delivered.**
All core CLI features, multi-user collaboration, OPA integration, and the full-stack Web UI Dashboard (FastAPI + Next.js) have been implemented.

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

### 4. Run the Web UI Dashboard (Recommended)

The Web UI provides the most complete experience, including team management and policy authoring.

**Terminal 1 (Backend):**
```bash
cd web-ui/api
uvicorn server:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd web-ui/frontend
npm install
npm run dev
```
Then navigate to `http://localhost:3000` in your browser. Use your GitHub token to log in.

### 5. Run the CLI Wizard (Alternative)

```bash
python cli-wizard/wizard.py
```

### 6. Destroy Resources

```bash
terraform destroy -auto-approve
```

---

## Project Structure

```
├── main.tf                     # Root Terraform configuration
├── variables.tf                # Input variables with defaults
├── outputs.tf                  # Deployment outputs
├── backend.tf                  # S3 remote state backend
│
├── web-ui/                     # Next.js + FastAPI Dashboard
│   ├── api/                    # Python FastAPI backend (server.py)
│   └── frontend/               # Next.js React frontend application
│
├── modules/                    # 7 AWS Terraform modules
│   ├── vpc/, ec2/, s3/, iam/, cloudwatch/, billing/, dynamodb/
│
├── policy-engine/              # Python evaluation engine
│   ├── engine.py               # PolicyEngine class
│   └── rules.yaml              # Extensible YAML security rules
│
├── opa-policies/               # Open Policy Agent configuration
│   └── aws_security.rego       # Rego-based security policies
│
├── team-management/            # RBAC and workflow engine
│   └── teams.yaml              # Team permissions & approval settings
│
├── drift-detection/            # Automated drift detection
│   ├── detect.sh               # Bash scanner
│   └── remediation.py          # Python auto-remediator
│
├── tests/                      # 221 passing unit & integration tests
│   ├── unit/, integration/, fixtures/
│
└── .github/workflows/          # CI/CD Pipelines
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

# Run API-specific tests
pytest tests/unit/test_api.py -v
```

**Current: 221 tests, 99% coverage**

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
