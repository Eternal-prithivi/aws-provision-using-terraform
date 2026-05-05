# templates/static-site/terraform.tfvars.tpl
# Template: Static Website Hosting (S3 only)
# Expected monthly cost: $0.00 (within free tier for 12 months)
# Use case: HTML/CSS/JS static website hosted on S3

aws_region        = "us-east-1"

# Feature flags — only S3 enabled for static site
enable_vpc        = false
enable_ec2        = false
enable_s3         = true
enable_iam        = false
enable_cloudwatch = false

# S3 — replace with your desired globally unique bucket name
bucket_name       = "my-static-site-REPLACE_ME"

# Billing alert
budget_limit      = "1"
budget_email      = "REPLACE_WITH_YOUR_EMAIL"

# Tags — required by governance policy
tags = {
  Owner   = "REPLACE_WITH_YOUR_NAME"
  Project = "aws-provisioner"
  Env     = "dev"
  Purpose = "static-site"
}
