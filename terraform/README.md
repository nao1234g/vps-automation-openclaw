# Terraform Infrastructure as Code

## 概要

このディレクトリには、OpenClaw VPS環境を自動的にプロビジョニングするためのTerraform設定が含まれています。

## サポートクラウドプロバイダ

- ✅ **AWS EC2** (推奨)
- 🚧 ConoHa VPS (計画中)
- 🚧 DigitalOcean (計画中)
- 🚧 Vultr (計画中)

## 前提条件

### 1. Terraform のインストール

```bash
# macOS (Homebrew)
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# バージョン確認
terraform version
```

### 2. AWS CLIの設定

```bash
# AWS CLI インストール
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# AWS 認証情報設定
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: ap-northeast-1
# Default output format: json
```

### 3. SSH キーペアの生成

```bash
# SSH キーペアが存在しない場合は生成
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
```

## セットアップ手順

### 1. 変数ファイルの作成

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

### 2. 変数の設定

`terraform.tfvars` を編集して、環境に合わせて変数を設定します。

**必須項目**:
- `domain_name`: ドメイン名
- `anthropic_api_key`: Anthropic API キー
- `postgres_password`: PostgreSQLパスワード (16文字以上)
- `n8n_encryption_key`: N8N暗号化キー (32文字以上)
- `grafana_admin_password`: Grafana管理者パスワード (12文字以上)

**推奨設定**:
- `allowed_ssh_ips`: 本番環境では特定のIPに制限
- `instance_type`: `t3.small` (2 vCPU, 2GB RAM)
- `enable_aws_backup`: `true` (バックアップを有効化)

### 3. Terraform 初期化

```bash
terraform init
```

### 4. プランの確認

```bash
terraform plan
```

作成されるリソースを確認:
- VPC, サブネット, インターネットゲートウェイ
- セキュリティグループ (SSH, HTTP, HTTPS)
- EC2インスタンス (Ubuntu 22.04 LTS)
- Elastic IP
- CloudWatch アラーム
- AWS Backup (オプション)
- Route53レコード (オプション)

### 5. インフラストラクチャのデプロイ

```bash
terraform apply
```

確認プロンプトで `yes` を入力すると、デプロイが開始されます。

**所要時間**: 約5-10分

### 6. デプロイ完了後

```bash
# 出力情報の確認
terraform output

# SSH接続
terraform output -raw ssh_command | bash

# または手動で接続
ssh -i ~/.ssh/id_rsa ubuntu@<PUBLIC_IP>
```

## リソース一覧

### ネットワーク
- **VPC**: 10.0.0.0/16
- **パブリックサブネット**: 10.0.1.0/24
- **インターネットゲートウェイ**
- **ルートテーブル**

### コンピューティング
- **EC2インスタンス**: t3.small (デフォルト)
- **Elastic IP**: 固定IPアドレス
- **EBSボリューム**: 30GB gp3 (暗号化済み)

### セキュリティ
- **セキュリティグループ**:
  - SSH (22): 指定したIPのみ
  - HTTP (80): 全て許可
  - HTTPS (443): 全て許可
- **IMDSv2**: 有効化
- **EBS暗号化**: 有効化

### 監視
- **CloudWatch アラーム**:
  - CPU使用率高 (>80%)
  - ステータスチェック失敗

### バックアップ (オプション)
- **AWS Backup**:
  - 日次バックアップ (30日保持)
  - 週次バックアップ (90日保持)

### DNS (オプション)
- **Route53レコード**:
  - Aレコード (メインドメイン)
  - Aレコード (www)

## 管理コマンド

### インフラストラクチャの更新

```bash
# 変更内容を確認
terraform plan

# 変更を適用
terraform apply
```

### 出力情報の表示

```bash
# 全ての出力を表示
terraform output

# 特定の出力を表示
terraform output instance_public_ip
terraform output ssh_command
```

### リソースの削除

```bash
# 削除内容を確認
terraform plan -destroy

# 全てのリソースを削除
terraform destroy
```

**警告**: `terraform destroy` を実行すると、全てのリソースが削除されます。バックアップを確認してから実行してください。

### 状態の管理

```bash
# 状態ファイルの表示
terraform show

# 特定のリソースの状態を表示
terraform state show aws_instance.openclaw

# 状態ファイルのリスト
terraform state list
```

## トラブルシューティング

### SSH接続ができない

**原因**: セキュリティグループの設定

**解決策**:
```bash
# セキュリティグループを確認
terraform output security_group_id

# AWS コンソールでセキュリティグループのインバウンドルールを確認
# または terraform.tfvars の allowed_ssh_ips を確認
```

### インスタンスが起動しない

**原因**: AMIが見つからない、リソース不足

**解決策**:
```bash
# ログを確認
terraform apply -debug

# EC2コンソールでインスタンスのシステムログを確認
```

### user-data スクリプトの実行失敗

**原因**: スクリプトエラー

**解決策**:
```bash
# SSH接続してログを確認
ssh -i ~/.ssh/id_rsa ubuntu@<PUBLIC_IP>
sudo cat /var/log/user-data.log

# 手動で再実行
cd /opt/openclaw
sudo ./scripts/setup.sh
```

### コストが予想より高い

**原因**: 不要なリソース、データ転送

**解決策**:
```bash
# 使用していないリソースを削除
terraform destroy

# インスタンスタイプを小さくする
# terraform.tfvars で instance_type = "t3.micro" に変更
```

## セキュリティベストプラクティス

### ✅ DO

- `terraform.tfvars` は **絶対に** Gitにコミットしない
- SSH接続を特定のIPアドレスのみに制限
- 強力なパスワードを使用 (16文字以上)
- AWS Backupを有効化
- CloudWatch アラームを設定
- 定期的にセキュリティスキャンを実行

### ❌ DON'T

- デフォルトのパスワードを使用しない
- 全てのIP (0.0.0.0/0) からSSHを許可しない (本番環境)
- terraform.tfvars に機密情報を直接記載しない (代わりに環境変数を使用)
- 本番環境でデバッグモードを有効化しない

## コスト最適化

### 推奨インスタンスタイプ

| 用途 | インスタンスタイプ | vCPU | メモリ | 月額コスト (概算) |
|------|------------------|------|--------|------------------|
| 開発/テスト | t3.micro | 2 | 1GB | ~$7.5 |
| 小規模本番 | t3.small | 2 | 2GB | ~$15 |
| 中規模本番 | t3.medium | 2 | 4GB | ~$30 |
| 大規模本番 | t3.large | 2 | 8GB | ~$60 |

### コスト削減のヒント

1. **リザーブドインスタンス**: 1年または3年契約で最大72%割引
2. **Savings Plans**: 柔軟なコミットメントで最大72%割引
3. **スポットインスタンス**: 開発/テスト環境で最大90%割引
4. **適切なインスタンスタイプ選択**: 過剰スペックを避ける
5. **使用していないリソースの削除**: 定期的に確認

## 高度な設定

### バックエンドの設定 (S3)

```hcl
# main.tf に追加
terraform {
  backend "s3" {
    bucket = "openclaw-terraform-state"
    key    = "vps/terraform.tfstate"
    region = "ap-northeast-1"
    encrypt = true
  }
}
```

### 複数環境の管理

```bash
# 開発環境
terraform workspace new development
terraform workspace select development
terraform apply -var-file="development.tfvars"

# 本番環境
terraform workspace new production
terraform workspace select production
terraform apply -var-file="production.tfvars"
```

### カスタムモジュールの使用

```hcl
module "openclaw_vps" {
  source = "./modules/openclaw"

  environment = "production"
  domain_name = "example.com"
  # その他の変数...
}
```

## 参考資料

- [Terraform Documentation](https://www.terraform.io/docs)
- [AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

## サポート

問題が発生した場合:

1. [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) を確認
2. [GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues) で報告
3. [GitHub Discussions](https://github.com/nao1234g/vps-automation-openclaw/discussions) で質問

---

## まとめ

Terraformを使用することで、OpenClaw VPS環境を:

✅ **自動化**: 手動設定不要で一貫した環境構築
✅ **再現可能**: 同じ設定で何度でも環境を作成
✅ **バージョン管理**: インフラストラクチャの変更履歴を管理
✅ **スケーラブル**: 簡単に複数環境を管理
✅ **セキュア**: ベストプラクティスに基づいた設定

Infrastructure as Code により、効率的で信頼性の高いデプロイメントを実現できます。
