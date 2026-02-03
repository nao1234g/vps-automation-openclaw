#!/bin/bash
# OpenClaw Docker Entrypoint Script
# 初回起動時に設定を自動生成し、Gateway を起動

set -e

OPENCLAW_HOME="${HOME}/.openclaw"
OPENCLAW_CONFIG="${OPENCLAW_HOME}/openclaw.json"

echo "🦞 OpenClaw Docker Entrypoint"
echo "================================"

# 設定ディレクトリ作成
mkdir -p "${OPENCLAW_HOME}"

# 設定ファイルが存在しない場合は作成（最小限の設定）
if [ ! -f "${OPENCLAW_CONFIG}" ]; then
    echo "📝 Creating OpenClaw configuration..."

    cat > "${OPENCLAW_CONFIG}" << EOF
{
  "gateway": {
    "mode": "local",
    "port": 3000,
    "bind": "lan"
  }
}
EOF

    echo "✅ Configuration created at ${OPENCLAW_CONFIG}"
fi

# ANTHROPIC_API_KEY を環境変数で設定（OpenClaw が自動検出）
if [ -n "${ANTHROPIC_API_KEY}" ]; then
    echo "🔑 Anthropic API key detected in environment"
    export ANTHROPIC_API_KEY
fi

echo "🚀 Starting OpenClaw Gateway..."
echo "   Port: ${OPENCLAW_PORT:-3000}"
echo "   Bind: lan"
echo ""

# Gateway を起動
exec openclaw gateway run \
    --port "${OPENCLAW_PORT:-3000}" \
    --bind lan \
    --token "${OPENCLAW_GATEWAY_TOKEN:-openclaw-dev-token}" \
    --allow-unconfigured \
    --verbose
