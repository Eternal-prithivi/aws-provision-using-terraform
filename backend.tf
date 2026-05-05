# backend.tf — Remote State Configuration (S3 + DynamoDB)
#
# SETUP REQUIRED (Phase 4 — one-time manual steps):
# 1. Create S3 bucket in AWS console named: terraform-state-<YOUR_ACCOUNT_ID>
# 2. Create DynamoDB table named: terraform-state-lock (partition key: LockID, type: String)
# 3. Replace REPLACE_WITH_YOUR_ACCOUNT_ID below with your actual AWS account ID
# 4. Run: terraform init
#
# Both resources are within free tier permanently.
# DO NOT run terraform init until Phase 4 is reached.

# terraform {
#   backend "s3" {
#     bucket         = "terraform-state-REPLACE_WITH_YOUR_ACCOUNT_ID"
#     key            = "terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "terraform-state-lock"
#     encrypt        = true
#   }
# }
#
# --- backend.tf is commented out until Phase 4 remote state setup is complete ---
