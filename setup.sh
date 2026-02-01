#!/bin/bash
#
# OpenClaw VPS Master Setup Script
# VPS環境の完全セットアップを対話的にガイド
#
# 使用方法: sudo ./setup.sh
#

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# スクリプトディレクトリ
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ログ出力関数
log_header() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  $1"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_step() {
    echo -e "${CYAN}▶${NC} ${BLUE}$1${NC}"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# rootユーザーチェック
if [ "$EUID" -ne 0 ]; then
    log_error "このスクリプトはroot権限で実行してください。"
    echo "使用方法: sudo $0"
    exit 1
fi

# ウェルカムメッセージ
clear
log_header "OpenClaw VPS セットアップウィザード"

cat << "EOF"
    ____                   ________
   / __ \____  ___  ____  / ____/ /___ __      __
  / / / / __ \/ _ \/ __ \/ /   / / __ `/ | /| / /
 / /_/ / /_/ /  __/ / / / /___/ / /_/ /| |/ |/ /
 \____/ .___/\___/_/ /_/\____/_/\__,_/ |__/|__/
     /_/

      VPS Automation & Security Setup

EOF

echo -e "${CYAN}このウィザードは以下の設定を行います:${NC}"
echo ""
echo "  1. VPSの初期セキュリティ設定（UFW, Fail2ban）"
echo "  2. Dockerのセキュアインストール"
echo "  3. SSL証明書の取得（オプション）"
echo "  4. Cron自動化の設定"
echo "  5. 環境変数の設定"
echo ""

read -p "セットアップを開始しますか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "セットアップをキャンセルしました。"
    exit 0
fi

# ============================================
# Step 1: VPSセキュリティ設定
# ============================================
log_header "Step 1/5: VPS初期セキュリティ設定"

log_step "UFW、Fail2ban、自動アップデートを設定します"
echo ""

read -p "VPSセキュリティ設定を実行しますか？ (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if [ -f "$SCRIPT_DIR/scripts/setup_vps_security.sh" ]; then
        log_info "実行中..."
        bash "$SCRIPT_DIR/scripts/setup_vps_security.sh"
        log_success "VPSセキュリティ設定が完了しました"
    else
        log_error "setup_vps_security.sh が見つかりません"
    fi
else
    log_warn "スキップしました"
fi

# ============================================
# Step 2: SSH鍵認証の確認
# ============================================
log_header "Step 2/5: SSH鍵認証の確認"

log_info "SSH鍵認証が設定されていることを確認してください"
echo ""
echo "まだ設定していない場合は、以下のドキュメントを参照:"
echo "  docs/SSH_KEY_SETUP.md"
echo ""
echo "重要な設定:"
echo "  ✓ SSH鍵ペアの生成"
echo "  ✓ 公開鍵をVPSに登録"
echo "  ✓ SSH鍵認証のテスト"
echo "  ✓ パスワード認証の無効化"
echo ""

read -p "SSH鍵認証の設定は完了していますか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "SSH鍵認証の設定を完了してから続行してください"
    log_info "セットアップを中断します。設定後に再度実行してください。"
    exit 0
fi

log_success "SSH鍵認証の設定を確認しました"

# ============================================
# Step 3: Dockerセキュリティ設定
# ============================================
log_header "Step 3/5: Dockerのセキュアインストール"

log_step "Docker、Trivy、Docker Bench をインストールします"
echo ""

read -p "Dockerセキュリティ設定を実行しますか？ (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if [ -f "$SCRIPT_DIR/scripts/setup_docker_security.sh" ]; then
        log_info "実行中..."
        bash "$SCRIPT_DIR/scripts/setup_docker_security.sh"
        log_success "Dockerセキュリティ設定が完了しました"
    else
        log_error "setup_docker_security.sh が見つかりません"
    fi
else
    log_warn "スキップしました"
fi

# ============================================
# Step 4: 環境変数の設定
# ============================================
log_header "Step 4/5: 環境変数の設定"

log_step ".env ファイルを作成します"
echo ""

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    log_info ".env.example から .env を作成します"

    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    chmod 600 "$SCRIPT_DIR/.env"

    log_success ".env ファイルを作成しました"
    echo ""
    log_warn "重要: .env ファイルを編集して、以下を設定してください:"
    echo "  - データベースパスワード"
    echo "  - API キー（Anthropic, OpenAI, など）"
    echo "  - Telegram Bot トークン"
    echo "  - N8N パスワード"
    echo "  - ドメイン名（SSL証明書用）"
    echo ""
    echo "パスワード生成: openssl rand -base64 32"
    echo ""

    read -p "今すぐ .env を編集しますか？ (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        ${EDITOR:-nano} "$SCRIPT_DIR/.env"
    fi
else
    log_info ".env ファイルは既に存在します"
fi

# ============================================
# Step 5: SSL証明書の取得（オプション）
# ============================================
log_header "Step 5/5: SSL証明書の取得（オプション）"

log_step "Let's Encrypt でSSL証明書を取得できます"
echo ""
log_info "SSL証明書を取得するには、ドメイン名が必要です"
echo ""

read -p "SSL証明書を取得しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "ドメイン名を入力してください: " DOMAIN
    read -p "メールアドレスを入力してください: " EMAIL

    if [ ! -z "$DOMAIN" ] && [ ! -z "$EMAIL" ]; then
        if [ -f "$SCRIPT_DIR/scripts/setup_ssl.sh" ]; then
            log_info "SSL証明書を取得中..."
            bash "$SCRIPT_DIR/scripts/setup_ssl.sh" "$DOMAIN" "$EMAIL"
            log_success "SSL証明書の取得が完了しました"
        else
            log_error "setup_ssl.sh が見つかりません"
        fi
    else
        log_warn "ドメイン名またはメールアドレスが入力されませんでした"
    fi
else
    log_info "SSL証明書の取得をスキップしました"
    log_info "後で取得する場合: sudo ./scripts/setup_ssl.sh <ドメイン> <メール>"
fi

# ============================================
# Cron自動化の設定
# ============================================
log_header "追加設定: Cron自動化"

log_step "セキュリティスキャンとメンテナンスを自動化します"
echo ""

read -p "Cron自動化を設定しますか？ (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if [ -f "$SCRIPT_DIR/scripts/setup_cron_jobs.sh" ]; then
        log_info "Cronジョブを設定中..."
        bash "$SCRIPT_DIR/scripts/setup_cron_jobs.sh"
        log_success "Cron自動化の設定が完了しました"
    else
        log_error "setup_cron_jobs.sh が見つかりません"
    fi
else
    log_warn "スキップしました"
fi

# ============================================
# セットアップ完了
# ============================================
clear
log_header "🎉 セットアップ完了！"

cat << EOF
${GREEN}OpenClaw VPS 環境のセットアップが完了しました！${NC}

${CYAN}次のステップ:${NC}

  ${BLUE}1. アプリケーションのデプロイ${NC}
     cd $SCRIPT_DIR
     docker compose up -d

  ${BLUE}2. ヘルスチェック${NC}
     ./scripts/health_check.sh

  ${BLUE}3. セキュリティスキャン${NC}
     ./scripts/security_scan.sh

  ${BLUE}4. バックアップの設定${NC}
     sudo ./scripts/backup.sh

${CYAN}運用ガイド:${NC}

  ${YELLOW}毎日${NC}
    - バックアップ: sudo ./scripts/backup.sh
    - ヘルスチェック: ./scripts/health_check.sh

  ${YELLOW}毎週${NC}
    - セキュリティスキャン: ./scripts/security_scan.sh

  ${YELLOW}毎月${NC}
    - メンテナンス: sudo ./scripts/maintenance.sh

${CYAN}ドキュメント:${NC}

  - セキュリティチェックリスト: SECURITY_CHECKLIST.md
  - クイックスタート: QUICKSTART_SECURITY.md
  - SSH設定: docs/SSH_KEY_SETUP.md

${CYAN}トラブルシューティング:${NC}

  - ログ確認: docker compose logs -f
  - コンテナ状態: docker compose ps
  - システム状態: systemctl status docker

${GREEN}安全で自動化されたVPS運用をお楽しみください！${NC}

EOF

log_info "詳細なドキュメントは README.md を参照してください"

exit 0
