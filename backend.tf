# backend.tf — Remote State Configuration
#
# SETUP REQUIRED (Phase 4 — one-time manual steps):
# 1. Create S3 bucket in AWS console (ap-south-1):
#    - Bucket name: terraform-state-<YOUR_ACCOUNT_ID>
#    - Enable versioning: YES
#    - Block all public access: YES
#    - Estimated cost: ~$0.00 (tiny state files, fractions of a cent)
#
# 2. (OPTIONAL) Create DynamoDB table for state locking:
#    - Table name: terraform-state-lock
#    - Partition key: LockID (String)
#    - DynamoDB has a PERMANENT free tier: 25 WCU + 25 RCU free forever.
#    - Terraform uses ~5-10 reads/writes per month. Cost = $0.00.
#    - Only needed if multiple people run terraform simultaneously.
#    - As a solo developer, S3-only (Option B below) is completely safe.
#
# -----------------------------------------------------------------------
# OPTION A — S3 + DynamoDB (recommended, still free for this use case)
# -----------------------------------------------------------------------
# terraform {
#   backend "s3" {
#     bucket         = "terraform-state-REPLACE_WITH_YOUR_ACCOUNT_ID"
#     key            = "terraform.tfstate"
#     region         = "ap-south-1"
#     dynamodb_table = "terraform-state-lock"
#     encrypt        = true
#   }
# }

# -----------------------------------------------------------------------
# OPTION B — S3 only, no DynamoDB (safe for solo developers)
# -----------------------------------------------------------------------
# terraform {
#   backend "s3" {
#     bucket  = "terraform-state-REPLACE_WITH_YOUR_ACCOUNT_ID"
#     key     = "terraform.tfstate"
#     region  = "ap-south-1"
#     encrypt = true
#   }
# }

# --- Uncomment ONE option above after creating the S3 bucket in Phase 4 ---
