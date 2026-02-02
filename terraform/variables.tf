/**
 * Terraform Variables
 *
 * 変数は terraform.tfvars ファイルで設定します
 */

# ==============================================================================
# General
# ==============================================================================

variable "environment" {
  description = "環境名 (development, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "環境は development, staging, production のいずれかである必要があります"
  }
}

variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "openclaw-vps"
}

# ==============================================================================
# AWS Configuration
# ==============================================================================

variable "aws_region" {
  description = "AWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR ブロック"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "パブリックサブネット CIDR ブロック"
  type        = string
  default     = "10.0.1.0/24"
}

# ==============================================================================
# EC2 Configuration
# ==============================================================================

variable "instance_type" {
  description = "EC2インスタンスタイプ"
  type        = string
  default     = "t3.small"

  validation {
    condition     = can(regex("^t[23]\\.(nano|micro|small|medium|large)", var.instance_type))
    error_message = "t2またはt3ファミリーのインスタンスタイプを推奨します"
  }
}

variable "ami_id" {
  description = "AMI ID（空の場合は最新のUbuntu 22.04 LTSを使用）"
  type        = string
  default     = ""
}

variable "root_volume_size" {
  description = "ルートボリュームサイズ (GB)"
  type        = number
  default     = 30

  validation {
    condition     = var.root_volume_size >= 20 && var.root_volume_size <= 100
    error_message = "ルートボリュームサイズは20GB～100GBの範囲である必要があります"
  }
}

# ==============================================================================
# Security
# ==============================================================================

variable "ssh_public_key_path" {
  description = "SSH公開鍵のパス"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "allowed_ssh_ips" {
  description = "SSH接続を許可するIPアドレス（CIDR形式）"
  type        = list(string)
  default     = ["0.0.0.0/0"] # 本番環境では特定のIPに制限することを推奨
}

# ==============================================================================
# Application Configuration
# ==============================================================================

variable "domain_name" {
  description = "ドメイン名"
  type        = string
}

variable "anthropic_api_key" {
  description = "Anthropic API キー"
  type        = string
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram ボットトークン"
  type        = string
  sensitive   = true
}

variable "telegram_chat_id" {
  description = "Telegram チャットID"
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL パスワード"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.postgres_password) >= 16
    error_message = "PostgreSQLパスワードは16文字以上である必要があります"
  }
}

variable "n8n_encryption_key" {
  description = "N8N 暗号化キー"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.n8n_encryption_key) >= 32
    error_message = "N8N暗号化キーは32文字以上である必要があります"
  }
}

variable "grafana_admin_password" {
  description = "Grafana 管理者パスワード"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.grafana_admin_password) >= 12
    error_message = "Grafana管理者パスワードは12文字以上である必要があります"
  }
}

# ==============================================================================
# DNS (Route53)
# ==============================================================================

variable "route53_zone_id" {
  description = "Route53 ゾーンID（オプション）"
  type        = string
  default     = ""
}

# ==============================================================================
# Monitoring
# ==============================================================================

variable "sns_topic_arn" {
  description = "SNSトピックARN（アラート通知用、オプション）"
  type        = string
  default     = ""
}

# ==============================================================================
# Backup
# ==============================================================================

variable "enable_aws_backup" {
  description = "AWS Backupを有効化"
  type        = bool
  default     = true
}

# ==============================================================================
# Tags
# ==============================================================================

variable "additional_tags" {
  description = "追加のタグ"
  type        = map(string)
  default     = {}
}
