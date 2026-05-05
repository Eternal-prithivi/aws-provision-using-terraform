# tests/fixtures/insecure_config.tfvars
# A config that triggers ALL block-level policy violations.
# Used in tests to verify the policy engine correctly blocks insecure deployments.
# DO NOT use this for real deployments.

aws_region = "us-east-1"

enable_vpc        = true
enable_ec2        = true
enable_s3         = true
enable_iam        = true
enable_cloudwatch = false

vpc_cidr      = "10.0.0.0/16"
instance_type = "m5.4xlarge" # triggers: expensive_ec2_instance (warning)
ami_id        = "ami-0c02fb55956c7d316"
bucket_name   = "my-public-bucket-danger"

budget_limit = "1"
budget_email = "owner@example.com"

# NOTE: The following would be set via config dict in tests:
# s3_bucket_public   = true   → triggers: public_s3_bucket (BLOCK)
# ssh_open_to_world  = true   → triggers: open_ssh_port (BLOCK)
# rdp_open_to_world  = true   → triggers: open_rdp_port (BLOCK)
# iam_wildcard       = true   → triggers: iam_wildcard_permissions (BLOCK)
# s3_encryption      = false  → triggers: missing_s3_encryption (warning)
# tags               = {}     → triggers: missing_resource_tags (warning)
# cloudtrail_enabled = false  → triggers: cloudtrail_disabled (warning)
