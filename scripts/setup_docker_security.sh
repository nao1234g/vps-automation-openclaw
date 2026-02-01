#!/bin/bash
#
# Docker Security Setup Script
# Dockerの安全なインストールとセキュリティ強化を自動化
#
# 使用方法: sudo ./setup_docker_security.sh
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

log_info "=== Docker セキュリティセットアップ開始 ==="

# 1. 古いバージョンのDockerを削除
log_info "古いバージョンのDockerを削除中..."
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# 2. 必要なパッケージのインストール
log_info "必要なパッケージをインストール中..."
apt update
apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 3. DockerのGPGキーを追加
log_info "Docker公式GPGキーを追加中..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# 4. Dockerリポジトリを追加
log_info "Docker公式リポジトリを追加中..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Dockerのインストール
log_info "Dockerをインストール中..."
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. Docker Daemonのセキュリティ設定
log_info "Docker Daemonのセキュリティ設定を作成中..."

mkdir -p /etc/docker

cat > /etc/docker/daemon.json <<'EOF'
{
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "icc": false,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "userns-remap": "default"
}
EOF

log_info "daemon.json設定完了。"

# 7. Docker Socketのパーミッション設定
log_info "Docker Socketのパーミッションを設定中..."
chmod 660 /var/run/docker.sock 2>/dev/null || true

# 8. Dockerサービスの再起動
log_info "Dockerサービスを再起動中..."
systemctl daemon-reload
systemctl restart docker
systemctl enable docker

# 9. Dockerグループの作成とユーザー追加（オプション）
if [ ! -z "$SUDO_USER" ]; then
    log_info "ユーザー $SUDO_USER をdockerグループに追加中..."
    usermod -aG docker $SUDO_USER
    log_warn "dockerグループの変更を有効にするには、再ログインが必要です。"
fi

# 10. Docker Benchのインストール（セキュリティ監査ツール）
log_info "Docker Bench Securityをインストール中..."
if [ ! -d /opt/docker-bench-security ]; then
    git clone https://github.com/docker/docker-bench-security.git /opt/docker-bench-security
    chmod +x /opt/docker-bench-security/docker-bench-security.sh
    log_info "Docker Bench Securityのインストール完了。"
    log_info "実行方法: sudo /opt/docker-bench-security/docker-bench-security.sh"
else
    log_info "Docker Bench Securityは既にインストールされています。"
fi

# 11. Trivyのインストール（脆弱性スキャナー）
log_info "Trivyをインストール中..."
if ! command -v trivy &> /dev/null; then
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /etc/apt/keyrings/trivy.gpg
    echo "deb [signed-by=/etc/apt/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee -a /etc/apt/sources.list.d/trivy.list
    apt update
    apt install -y trivy
    log_info "Trivyのインストール完了。"
else
    log_info "Trivyは既にインストールされています。"
fi

# 12. Docker情報表示
log_info "=== Docker セキュリティセットアップ完了 ==="
echo ""
echo "Dockerバージョン:"
docker --version
docker compose version
echo ""
echo "Dockerサービスステータス:"
systemctl status docker --no-pager | head -10
echo ""
echo "次のステップ:"
echo "1. Docker Bench Securityを実行: sudo /opt/docker-bench-security/docker-bench-security.sh"
echo "2. イメージスキャン: trivy image <イメージ名>"
echo "3. セキュアなDocker Composeテンプレートを使用してください"
echo "4. 定期的にセキュリティ監査を実行してください"
echo ""
log_info "セキュリティセットアップが完了しました。"
