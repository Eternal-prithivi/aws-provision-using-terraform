# tests/fixtures/valid_config.tfvars
# A config that passes ALL 8 policy rules.
# Used as a reference for what a safe, compliant deployment looks like.

aws_region = "ap-south-1"

enable_vpc        = true
enable_ec2        = true
enable_s3         = true
enable_iam        = false
enable_cloudwatch = false

vpc_cidr      = "10.0.0.0/16"
instance_type = "t2.micro"
ami_id        = "ami-0f58b397bc5c1f2e8"
bucket_name   = "my-valid-private-bucket-12345"

budget_limit = "1"
budget_email = "owner@example.com"

tags = {
  Owner   = "developer"
  Project = "aws-provisioner"
  Env     = "dev"
}
