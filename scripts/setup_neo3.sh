#!/bin/bash
# ════════════════════════════════════════════════════════════════
# NEO-GPT VPS セットアップスクリプト
# ════════════════════════════════════════════════════════════════
# Codex CLI + Telegram Bot を VPS にデプロイする
#
# 使い方:
#   scp setup_neo3.sh root@163.44.124.123:/tmp/
#   ssh root@163.44.124.123 'bash /tmp/setup_neo3.sh'
# ════════════════════════════════════════════════════════════════

set -euo pipefail

# ──────────── 設定 ────────────
INSTALL_DIR="/opt/neo3-codex"
WORKSPACE_DIR="${INSTALL_DIR}/workspace"
LOG_DIR="${INSTALL_DIR}/logs"
REPO_URL="https://github.com/nao1234g/vps-automation-openclaw.git"
TELEGRAM_BOT_TOKEN="8403014876:AAHZOPGq1lsvfh_Wgncu5YzEpfdb6WHc9L0"

echo "════════════════════════════════════════"
echo "  NEO-GPT セットアップ開始"
echo "════════════════════════════════════════"

# ──────────── 1. Node.js 22+ インストール ────────────
echo ""
echo "▶ Step 1: Node.js インストール..."
if ! command -v node &>/dev/null || [[ $(node -v | sed 's/v//' | cut -d. -f1) -lt 22 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
    echo "  ✅ Node.js $(node -v) インストール完了"
else
    echo "  ✅ Node.js $(node -v) 既にインストール済み"
fi

# ──────────── 2. Codex CLI インストール ────────────
echo ""
echo "▶ Step 2: Codex CLI インストール..."
if ! command -v codex &>/dev/null; then
    npm install -g @openai/codex
    echo "  ✅ Codex CLI インストール完了"
else
    echo "  ✅ Codex CLI 既にインストール済み"
fi

# ──────────── 3. Python依存 ────────────
echo ""
echo "▶ Step 3: Python依存パッケージ..."
pip3 install --quiet python-telegram-bot 2>/dev/null || pip install --quiet python-telegram-bot

# ──────────── 4. ディレクトリ構成 ────────────
echo ""
echo "▶ Step 4: ディレクトリ作成..."
mkdir -p "${INSTALL_DIR}" "${WORKSPACE_DIR}" "${LOG_DIR}"

# ──────────── 5. ファイル配置 ────────────
echo ""
echo "▶ Step 5: ファイル配置..."

# orchestrator.py をコピー（リポジトリが既にあればそこから、なければダウンロード）
if [ -f "/opt/vps-automation/scripts/neo3_orchestrator.py" ]; then
    cp /opt/vps-automation/scripts/neo3_orchestrator.py "${INSTALL_DIR}/neo3_orchestrator.py"
elif [ -f "/tmp/neo3_orchestrator.py" ]; then
    cp /tmp/neo3_orchestrator.py "${INSTALL_DIR}/neo3_orchestrator.py"
else
    echo "  ⚠ neo3_orchestrator.py が見つかりません。手動でコピーしてください:"
    echo "    scp scripts/neo3_orchestrator.py root@VPS:${INSTALL_DIR}/"
fi

# ──────────── 6. .env ファイル ────────────
echo ""
echo "▶ Step 6: .env ファイル作成..."
cat > "${INSTALL_DIR}/.env" << ENVEOF
# NEO-GPT Configuration
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
ALLOWED_USERS=
CODEX_TIMEOUT=300
CODEX_MODEL=o4-mini
CODEX_WORK_DIR=${WORKSPACE_DIR}
LOG_DIR=${LOG_DIR}
ENVEOF

echo "  ✅ .env 作成完了"
echo "  ⚠ ALLOWED_USERS を設定してください:"
echo "    nano ${INSTALL_DIR}/.env"

# ──────────── 7. systemd サービス ────────────
echo ""
echo "▶ Step 7: systemd サービス設定..."

cat > /etc/systemd/system/neo3-telegram.service << 'SERVICEEOF'
[Unit]
Description=NEO-GPT Codex CLI Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/neo3-codex
ExecStart=/usr/bin/python3 /opt/neo3-codex/neo3_orchestrator.py
Restart=always
RestartSec=10
EnvironmentFile=/opt/neo3-codex/.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=neo3-telegram

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
echo "  ✅ systemd サービス設定完了"

# ──────────── 8. Git 初期化 ────────────
echo ""
echo "▶ Step 8: workspace Git 初期化..."
cd "${WORKSPACE_DIR}"
if [ ! -d .git ]; then
    git init
    git config user.name "NEO-GPT"
    git config user.email "neo-gpt@localhost"
    echo "  ✅ Git 初期化完了"
else
    echo "  ✅ Git 既に初期化済み"
fi

# ──────────── 完了 ────────────
echo ""
echo "════════════════════════════════════════"
echo "  ✅ NEO-GPT セットアップ完了！"
echo "════════════════════════════════════════"
echo ""
echo "次のステップ:"
echo "  1. Codex CLI 認証:"
echo "     codex login --device-auth"
echo ""
echo "  2. ALLOWED_USERS 設定:"
echo "     nano ${INSTALL_DIR}/.env"
echo "     # Telegram user ID を設定"
echo ""
echo "  3. サービス起動:"
echo "     systemctl enable neo3-telegram"
echo "     systemctl start neo3-telegram"
echo ""
echo "  4. ログ確認:"
echo "     journalctl -u neo3-telegram -f"
echo ""
echo "  5. Telegram で @neogpt_nn_bot に /start を送信"
echo ""
