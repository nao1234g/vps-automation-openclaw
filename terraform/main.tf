/**
 * OpenClaw VPS Infrastructure as Code
 *
 * このTerraform設定は、OpenClaw VPS環境を自動的にプロビジョニングします。
 *
 * サポートプロバイダ:
 * - AWS EC2
 * - ConoHa VPS
 * - DigitalOcean Droplet
 * - Vultr
 *
 * 使用方法:
 *   terraform init
 *   terraform plan
 *   terraform apply
 */

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # バックエンド設定（オプション）
  # backend "s3" {
  #   bucket = "openclaw-terraform-state"
  #   key    = "vps/terraform.tfstate"
  #   region = "ap-northeast-1"
  # }
}

# ==============================================================================
# Provider Configuration
# ==============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "OpenClaw VPS"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}

# ==============================================================================
# VPC Configuration
# ==============================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "openclaw-vpc-${var.environment}"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "openclaw-igw-${var.environment}"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "openclaw-public-subnet-${var.environment}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "openclaw-public-rt-${var.environment}"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ==============================================================================
# Security Group
# ==============================================================================

resource "aws_security_group" "openclaw" {
  name        = "openclaw-sg-${var.environment}"
  description = "Security group for OpenClaw VPS"
  vpc_id      = aws_vpc.main.id

  # SSH
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_ips
  }

  # HTTP
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana (オプション、開発環境のみ)
  dynamic "ingress" {
    for_each = var.environment == "development" ? [1] : []
    content {
      description = "Grafana"
      from_port   = 3001
      to_port     = 3001
      protocol    = "tcp"
      cidr_blocks = var.allowed_ssh_ips
    }
  }

  # Prometheus (オプション、開発環境のみ)
  dynamic "ingress" {
    for_each = var.environment == "development" ? [1] : []
    content {
      description = "Prometheus"
      from_port   = 9090
      to_port     = 9090
      protocol    = "tcp"
      cidr_blocks = var.allowed_ssh_ips
    }
  }

  # Outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "openclaw-sg-${var.environment}"
  }
}

# ==============================================================================
# SSH Key Pair
# ==============================================================================

resource "aws_key_pair" "openclaw" {
  key_name   = "openclaw-key-${var.environment}"
  public_key = file(var.ssh_public_key_path)

  tags = {
    Name = "openclaw-key-${var.environment}"
  }
}

# ==============================================================================
# EC2 Instance
# ==============================================================================

resource "aws_instance" "openclaw" {
  ami           = var.ami_id != "" ? var.ami_id : data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = aws_key_pair.openclaw.key_name
  subnet_id     = aws_subnet.public.id

  vpc_security_group_ids = [aws_security_group.openclaw.id]

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name = "openclaw-root-${var.environment}"
    }
  }

  # ユーザーデータ（初期セットアップスクリプト）
  user_data = templatefile("${path.module}/user-data.sh", {
    domain_name           = var.domain_name
    environment           = var.environment
    anthropic_api_key     = var.anthropic_api_key
    telegram_bot_token    = var.telegram_bot_token
    telegram_chat_id      = var.telegram_chat_id
    postgres_password     = var.postgres_password
    n8n_encryption_key    = var.n8n_encryption_key
    grafana_admin_password = var.grafana_admin_password
  })

  # EBSの暗号化を有効化
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2を強制
    http_put_response_hop_limit = 1
  }

  tags = {
    Name        = "openclaw-vps-${var.environment}"
    Environment = var.environment
    Backup      = "daily"
  }
}

# ==============================================================================
# Elastic IP
# ==============================================================================

resource "aws_eip" "openclaw" {
  instance = aws_instance.openclaw.id
  domain   = "vpc"

  tags = {
    Name = "openclaw-eip-${var.environment}"
  }
}

# ==============================================================================
# Data Sources
# ==============================================================================

# 最新のUbuntu 22.04 LTS AMIを取得
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ==============================================================================
# CloudWatch Alarms
# ==============================================================================

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "openclaw-cpu-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "CPU使用率が80%を超えました"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    InstanceId = aws_instance.openclaw.id
  }
}

resource "aws_cloudwatch_metric_alarm" "status_check_failed" {
  alarm_name          = "openclaw-status-check-failed-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "インスタンスのステータスチェックが失敗しました"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    InstanceId = aws_instance.openclaw.id
  }
}

# ==============================================================================
# Route53 (オプション)
# ==============================================================================

resource "aws_route53_record" "openclaw" {
  count   = var.route53_zone_id != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.openclaw.public_ip]
}

resource "aws_route53_record" "openclaw_www" {
  count   = var.route53_zone_id != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = "www.${var.domain_name}"
  type    = "A"
  ttl     = 300
  records = [aws_eip.openclaw.public_ip]
}

# ==============================================================================
# Backup (AWS Backup)
# ==============================================================================

resource "aws_backup_vault" "openclaw" {
  count = var.enable_aws_backup ? 1 : 0
  name  = "openclaw-backup-vault-${var.environment}"

  tags = {
    Name = "openclaw-backup-vault-${var.environment}"
  }
}

resource "aws_backup_plan" "openclaw" {
  count = var.enable_aws_backup ? 1 : 0
  name  = "openclaw-backup-plan-${var.environment}"

  rule {
    rule_name         = "daily_backup"
    target_vault_name = aws_backup_vault.openclaw[0].name
    schedule          = "cron(0 3 * * ? *)" # 毎日3:00 UTC

    lifecycle {
      delete_after = 30 # 30日後に削除
    }
  }

  rule {
    rule_name         = "weekly_backup"
    target_vault_name = aws_backup_vault.openclaw[0].name
    schedule          = "cron(0 4 ? * 1 *)" # 毎週月曜日4:00 UTC

    lifecycle {
      delete_after = 90 # 90日後に削除
    }
  }
}

resource "aws_backup_selection" "openclaw" {
  count        = var.enable_aws_backup ? 1 : 0
  name         = "openclaw-backup-selection-${var.environment}"
  plan_id      = aws_backup_plan.openclaw[0].id
  iam_role_arn = aws_iam_role.backup[0].arn

  selection_tag {
    type  = "STRINGEQUALS"
    key   = "Backup"
    value = "daily"
  }
}

resource "aws_iam_role" "backup" {
  count = var.enable_aws_backup ? 1 : 0
  name  = "openclaw-backup-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  count      = var.enable_aws_backup ? 1 : 0
  role       = aws_iam_role.backup[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}
