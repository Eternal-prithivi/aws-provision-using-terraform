# modules/ec2/main.tf — EC2 Instance (default: t2.micro free tier)
# SECURITY: SSH port 22 is NOT open to 0.0.0.0/0 — policy engine blocks that.

resource "aws_security_group" "ec2_sg" {
  count       = var.enable_ec2 ? 1 : 0
  name        = "ec2-security-group"
  description = "Security group for EC2 instance. No unrestricted inbound access."
  vpc_id      = var.vpc_id

  egress {
    description = "Allow all outbound traffic."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "ec2-sg"
  })
}

resource "aws_instance" "main" {
  count                  = var.enable_ec2 ? 1 : 0
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.ec2_sg[0].id]

  tags = merge(var.tags, {
    Name = "main-instance"
  })
}
