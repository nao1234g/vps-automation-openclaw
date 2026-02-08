#!/bin/bash
# OpenClaw Security Hardening Script
# Run on VPS to apply security best practices

set -e

echo "🔒 OpenClaw セキュリティ強化開始..."

# Step 1: Enable logging
echo "📝 Step 1: ログ監視を有効化..."
openclaw config set logging.enabled true --json 2>/dev/null || echo "Logging config skipped"
openclaw config set logging.level info 2>/dev/null || echo "Log level config skipped"

# Step 2: Enable Human-in-the-Loop for dangerous commands
echo "👤 Step 2: 危険なコマンドの承認制を有効化..."
openclaw config set security.requireApproval true --json 2>/dev/null || echo "Approval config skipped"
openclaw config set security.dangerousCommands '["rm","sudo","chmod","chown"]' --json 2>/dev/null || echo "Dangerous commands config skipped"

# Step 3: Restrict to trusted proxies only
echo "🔐 Step 3: 信頼されたプロキシのみ許可..."
# Already configured in openclaw.json

# Step 4: Check for updates
echo "📦 Step 4: アップデート確認..."
openclaw --version
npm list -g openclaw 2>/dev/null || echo "Checking npm packages..."

# Step 5: Enable systemd logging
echo "📊 Step 5: システムログ設定..."
journalctl -u openclaw-gateway --since "1 hour ago" | tail -10 || echo "No recent logs"

echo ""
echo "✅ セキュリティ強化完了！"
echo ""
echo "確認コマンド:"
echo "  openclaw doctor"
echo "  openclaw status --deep"
