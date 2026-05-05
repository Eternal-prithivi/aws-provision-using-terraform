# templates/backend-app/terraform.tfvars.tpl
# Template: Backend Application (VPC + EC2 + IAM)
# Expected monthly cost: $0.00 (t2.micro within free tier for 12 months)
# Use case: Small backend application running on EC2

aws_region        = "ap-south-1"

# Feature flags — VPC + EC2 + IAM for backend app
enable_vpc        = true
enable_ec2        = true
enable_s3         = false
enable_iam        = true
enable_cloudwatch = false

# VPC
vpc_cidr          = "10.0.0.0/16"

# EC2 — t2.micro is free tier eligible
instance_type     = "t2.micro"
# Find the latest Amazon Linux 2 AMI for your region in the AWS console
ami_id            = "REPLACE_WITH_REGION_AMI_ID"

# IAM
role_name         = "backend-app-role"

# Billing alert
budget_limit      = "1"
budget_email      = "REPLACE_WITH_YOUR_EMAIL"

# Tags — required by governance policy
tags = {
  Owner   = "REPLACE_WITH_YOUR_NAME"
  Project = "aws-provisioner"
  Env     = "dev"
  Purpose = "backend-app"
}
