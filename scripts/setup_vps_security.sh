#!/bin/bash
#
# VPS Security Setup Script
# セキュアなVPS環境のセットアップを自動化
#
# 使用方法: sudo ./setup_vps_security.sh
#

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ログ出力関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# rootユーザーチェック
if [ "$EUID" -ne 0 ]; then
    log_error "このスクリプトはroot権限で実行してください。"
    echo "使用方法: sudo $0"
    exit 1
fi

log_info "=== VPSセキュリティセットアップ開始 ==="

# 1. システムアップデート
log_info "システムをアップデート中..."
apt update && apt upgrade -y

# 2. 必要なパッケージのインストール
log_info "セキュリティパッケージをインストール中..."
apt install -y \
    ufw \
    fail2ban \
    unattended-upgrades \
    apt-listchanges \
    net-tools \
    curl \
    wget \
    git

# 3. UFW（ファイアウォール）の設定
log_info "UFWファイアウォールを設定中..."

# デフォルトポリシー設定
ufw default deny incoming
ufw default allow outgoing

# SSH許可（ポート番号は環境に合わせて変更）
SSH_PORT=${SSH_PORT:-22}
ufw allow ${SSH_PORT}/tcp comment 'SSH'

# HTTP/HTTPS許可
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# UFW有効化（既に有効な場合はスキップ）
if ! ufw status | grep -q "Status: active"; then
    log_warn "UFWを有効化します。SSH接続が切断される可能性があります。"
    echo "y" | ufw enable
else
    log_info "UFWは既に有効です。"
fi

ufw status verbose

# 4. Fail2banの設定
log_info "Fail2banを設定中..."

# Fail2ban jail.local作成
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
destemail = root@localhost
sendername = Fail2Ban
action = %(action_mwl)s

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200
EOF

# Fail2ban起動
systemctl enable fail2ban
systemctl restart fail2ban

log_info "Fail2ban設定完了。"
fail2ban-client status

# 5. 自動セキュリティアップデート設定
log_info "自動セキュリティアップデートを設定中..."

cat > /etc/apt/apt.conf.d/50unattended-upgrades <<'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Automatic-Reboot-Time "02:00";
EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF

# 6. SSH強化設定のバックアップと推奨設定表示
log_info "SSH設定を確認中..."

if [ -f /etc/ssh/sshd_config ]; then
    # バックアップ作成
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)
    log_info "SSH設定のバックアップを作成しました。"

    log_warn "SSH設定の手動確認が必要です:"
    echo "  /etc/ssh/sshd_config を編集して以下を設定してください:"
    echo "  - PermitRootLogin no"
    echo "  - PasswordAuthentication no (鍵認証設定後)"
    echo "  - PubkeyAuthentication yes"
    echo "  - MaxAuthTries 3"
    echo "  - Port 2222 (オプション: デフォルトポート変更)"
    echo ""
    echo "  設定後、以下のコマンドで反映:"
    echo "  sudo systemctl restart sshd"
fi

# 7. システム情報表示
log_info "=== セキュリティセットアップ完了 ==="
echo ""
echo "セットアップサマリー:"
echo "===================="
echo "UFWステータス:"
ufw status numbered
echo ""
echo "Fail2banステータス:"
fail2ban-client status
echo ""
echo "次のステップ:"
echo "1. SSH鍵認証を設定してください"
echo "2. /etc/ssh/sshd_config を編集してSSHを強化してください"
echo "3. 不要なサービスを停止してください: systemctl list-units --type=service"
echo "4. Docker セキュリティセットアップを実行: sudo ./setup_docker_security.sh"
echo ""
log_info "セキュリティセットアップが完了しました。"
