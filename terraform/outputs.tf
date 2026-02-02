/**
 * Terraform Outputs
 *
 * プロビジョニング後に表示される情報
 */

output "instance_id" {
  description = "EC2インスタンスID"
  value       = aws_instance.openclaw.id
}

output "instance_public_ip" {
  description = "EC2インスタンスのパブリックIP"
  value       = aws_eip.openclaw.public_ip
}

output "instance_public_dns" {
  description = "EC2インスタンスのパブリックDNS"
  value       = aws_instance.openclaw.public_dns
}

output "security_group_id" {
  description = "セキュリティグループID"
  value       = aws_security_group.openclaw.id
}

output "ssh_command" {
  description = "SSH接続コマンド"
  value       = "ssh -i ${replace(var.ssh_public_key_path, ".pub", "")} ubuntu@${aws_eip.openclaw.public_ip}"
}

output "application_url" {
  description = "アプリケーションURL"
  value       = "https://${var.domain_name}"
}

output "grafana_url" {
  description = "Grafana URL"
  value       = "https://${var.domain_name}/grafana"
}

output "n8n_url" {
  description = "N8N URL"
  value       = "https://${var.domain_name}/n8n"
}

output "prometheus_url" {
  description = "Prometheus URL"
  value       = "https://${var.domain_name}/prometheus"
}

output "backup_vault_name" {
  description = "バックアップボルト名"
  value       = var.enable_aws_backup ? aws_backup_vault.openclaw[0].name : "N/A"
}

output "cloudwatch_alarms" {
  description = "CloudWatch アラーム"
  value = {
    cpu_high           = aws_cloudwatch_metric_alarm.cpu_high.alarm_name
    status_check_failed = aws_cloudwatch_metric_alarm.status_check_failed.alarm_name
  }
}

output "dns_records" {
  description = "DNSレコード"
  value = var.route53_zone_id != "" ? {
    main = aws_route53_record.openclaw[0].fqdn
    www  = aws_route53_record.openclaw_www[0].fqdn
  } : {}
}

# セキュリティ情報（機密情報は出力しない）
output "security_information" {
  description = "セキュリティ情報"
  value = {
    allowed_ssh_ips    = var.allowed_ssh_ips
    imdsv2_enabled     = aws_instance.openclaw.metadata_options[0].http_tokens == "required"
    ebs_encrypted      = true
    security_group_id  = aws_security_group.openclaw.id
  }
}

# 接続情報
output "connection_info" {
  description = "接続情報"
  value = {
    ssh_user    = "ubuntu"
    ssh_key     = basename(var.ssh_public_key_path)
    public_ip   = aws_eip.openclaw.public_ip
    domain_name = var.domain_name
  }
}

# コスト見積もり情報
output "cost_estimate" {
  description = "月次コスト見積もり（USD）"
  value = {
    instance_type       = var.instance_type
    estimated_ec2_cost  = "~$15-30/month"
    estimated_ebs_cost  = "~$3-6/month (${var.root_volume_size}GB)"
    estimated_eip_cost  = "~$3.65/month"
    estimated_total     = "~$22-40/month"
    note                = "実際のコストは使用状況により変動します"
  }
}
