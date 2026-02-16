#!/bin/bash
# OpenClaw Docker Entrypoint Script
# NEO Dual Agent 構成対応
# 起動時に openclaw.json のボットトークンを環境変数から注入

set -e

OPENCLAW_HOME="${HOME}/.openclaw"
OPENCLAW_CONFIG="${OPENCLAW_HOME}/openclaw.json"
MOUNTED_CONFIG="/app/config/openclaw.json"
SOUL_FILE="/app/config/SOUL.md"

echo "🦞 OpenClaw Docker Entrypoint (NEO Dual Agent)"
echo "================================================"

# 設定ディレクトリ作成
mkdir -p "${OPENCLAW_HOME}"

# マウントされた設定ファイルをコピー（書き込み可能にするため）
if [ -f "${MOUNTED_CONFIG}" ]; then
    cp "${MOUNTED_CONFIG}" "${OPENCLAW_CONFIG}"
    echo "📝 Config copied from mounted file"
else
    echo "⚠️  No mounted config found, creating default..."
    cat > "${OPENCLAW_CONFIG}" << 'DEFAULTEOF'
{
  "gateway": {
    "mode": "local",
    "port": 3000,
    "bind": "lan",
    "trustedProxies": ["0.0.0.0/0"]
  }
}
DEFAULTEOF
fi

# Telegramボットトークンを環境変数から注入
if [ -n "${TELEGRAM_BOT_TOKEN}" ]; then
    sed -i "s|\${TELEGRAM_BOT_TOKEN}|${TELEGRAM_BOT_TOKEN}|g" "${OPENCLAW_CONFIG}"
    echo "🟢 NEO-ONE Telegram token injected"
fi

if [ -n "${TELEGRAM_BOT_TOKEN_NEO2}" ]; then
    sed -i "s|\${TELEGRAM_BOT_TOKEN_NEO2}|${TELEGRAM_BOT_TOKEN_NEO2}|g" "${OPENCLAW_CONFIG}"
    echo "🔵 NEO-TWO Telegram token injected"
fi

# SOUL.md をワークスペースにコピー（両NEOで共有）
if [ -f "${SOUL_FILE}" ]; then
    mkdir -p "${OPENCLAW_HOME}/workspace"
    cp "${SOUL_FILE}" "${OPENCLAW_HOME}/workspace/SOUL.md"
    echo "🧠 NEO personality (SOUL.md) loaded"
fi

# API キー検出
if [ -n "${ANTHROPIC_API_KEY}" ]; then
    echo "🔑 Anthropic API key detected"
fi

if [ -n "${GOOGLE_API_KEY}" ]; then
    echo "🔑 Google API key detected"
fi

echo ""
echo "🚀 Starting OpenClaw Gateway..."
echo "   Port: ${OPENCLAW_PORT:-3000}"
echo "   Agents: NEO-ONE 🟢 + NEO-TWO 🔵"
echo "   Auth: token"
echo ""

# Gateway 起動（トークン認証 + NEO Dual Agent）
exec openclaw gateway run \
    --port "${OPENCLAW_PORT:-3000}" \
    --bind lan \
    --auth token \
    --token "${OPENCLAW_GATEWAY_TOKEN}" \
    --verbose
