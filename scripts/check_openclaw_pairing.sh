#!/bin/bash
# OpenClaw Gateway ペアリング状態確認スクリプト
#
# 使用方法:
#   ./scripts/check_openclaw_pairing.sh
#
# 機能:
#   - OpenClaw Gatewayの起動状態確認
#   - ペアリング設定の確認
#   - Control UI接続のテスト

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ロギング関数
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# ============================================
# Step 1: コンテナ状態確認
# ============================================
log_header "OpenClaw Gateway 状態確認"

if ! docker ps --filter "name=openclaw-agent" --format "{{.Names}}" | grep -q "openclaw-agent"; then
    log_error "OpenClaw コンテナが起動していません"
    log_info "起動方法: make quick-deploy または docker compose -f docker-compose.quick.yml up -d"
    exit 1
fi

log_success "OpenClaw コンテナは起動中"

# ============================================
# Step 2: 環境変数確認
# ============================================
log_header "ペアリング設定確認"

DISABLE_PAIRING=$(docker exec openclaw-agent env | grep "OPENCLAW_DISABLE_PAIRING" | cut -d'=' -f2 || echo "not_set")

echo "現在の設定:"
if [ "$DISABLE_PAIRING" = "true" ]; then
    log_success "  OPENCLAW_DISABLE_PAIRING=true (ペアリング無効 - ブラウザ接続可能)"
elif [ "$DISABLE_PAIRING" = "false" ]; then
    log_warn "  OPENCLAW_DISABLE_PAIRING=false (ペアリング必須)"
    log_info "  ブラウザからの接続にはデバイスペアリングが必要です"
else
    log_warn "  OPENCLAW_DISABLE_PAIRING が設定されていません（デフォルト: ペアリング必須）"
    log_info "  .env ファイルに OPENCLAW_DISABLE_PAIRING=true を追加してください"
fi

# ============================================
# Step 3: Gatewayプロセス確認
# ============================================
log_header "Gateway プロセス確認"

GATEWAY_PROCESS=$(docker exec openclaw-agent ps aux | grep "openclaw gateway" | grep -v grep || echo "")

if [ -z "$GATEWAY_PROCESS" ]; then
    log_error "OpenClaw Gateway プロセスが見つかりません"
    log_info "コンテナログを確認してください: docker logs openclaw-agent"
    exit 1
fi

log_success "Gateway プロセスは実行中"
echo "$GATEWAY_PROCESS"

# Gatewayコマンドライン引数確認
if echo "$GATEWAY_PROCESS" | grep -q "\-\-no-pairing"; then
    log_success "  --no-pairing オプションが有効です"
else
    log_warn "  --no-pairing オプションが見つかりません"
    log_info "  コンテナを再起動してください: docker compose -f docker-compose.quick.yml restart openclaw"
fi

# ============================================
# Step 4: ヘルスチェック
# ============================================
log_header "接続テスト"

log_info "Gateway エンドポイントにアクセス中..."

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ || echo "000")

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
    log_success "Gateway は正常に応答しています (HTTP $HTTP_STATUS)"
else
    log_error "Gateway が応答していません (HTTP $HTTP_STATUS)"
    log_info "コンテナログを確認してください: docker logs openclaw-agent"
    exit 1
fi

# ============================================
# Step 5: WebSocket接続テスト
# ============================================
log_header "WebSocket接続テスト"

log_info "WebSocketエンドポイントを確認中..."

# wscat があるか確認
if command -v wscat &> /dev/null; then
    log_info "wscat を使用してWebSocket接続をテスト..."
    
    # タイムアウト付きでWebSocket接続テスト
    timeout 5s wscat -c ws://localhost:3000/ --no-check 2>&1 | head -n 5 || {
        log_warn "WebSocket接続テストがタイムアウトしました"
        log_info "これは正常な場合もあります（接続は成功しているが応答待ち）"
    }
else
    log_info "wscat がインストールされていません"
    log_info "インストール方法: npm install -g wscat"
    log_info "WebSocket接続テストをスキップします"
fi

# ============================================
# Step 6: ログ確認
# ============================================
log_header "最近のログ（最新20行）"

docker logs openclaw-agent --tail 20 2>&1 | grep -E "(Starting|Gateway|pairing|Connected|Error|Warning)" || {
    log_info "関連するログエントリが見つかりませんでした"
    log_info "全ログを表示: docker logs openclaw-agent"
}

# ============================================
# まとめ
# ============================================
log_header "診断結果まとめ"

echo "✅ 確認項目:"
echo "  1. コンテナ状態: 起動中"
echo "  2. ペアリング設定: ${DISABLE_PAIRING}"
echo "  3. Gateway プロセス: 実行中"
echo "  4. HTTP接続: HTTP ${HTTP_STATUS}"
echo ""

if [ "$DISABLE_PAIRING" = "true" ] && [ "$HTTP_STATUS" = "200" ]; then
    log_success "OpenClaw Gateway は正常に動作しています！"
    echo ""
    echo "🌐 Control UI アクセス方法:"
    echo "  1. ブラウザで http://localhost:3000 を開く"
    echo "  2. パスワード入力を求められたら、.env の OPENCLAW_GATEWAY_TOKEN を入力"
    echo "  3. ペアリングは不要です（自動的にスキップ）"
    echo ""
else
    log_warn "設定の確認が必要です"
    echo ""
    echo "🔧 トラブルシューティング:"
    echo "  1. .env ファイルを確認"
    echo "     OPENCLAW_DISABLE_PAIRING=true が設定されているか確認"
    echo ""
    echo "  2. コンテナを再起動"
    echo "     docker compose -f docker-compose.quick.yml restart openclaw"
    echo ""
    echo "  3. ログを確認"
    echo "     docker logs -f openclaw-agent"
    echo ""
fi

# ============================================
# オプション: 設定ファイル出力
# ============================================
if [ "$1" = "--verbose" ]; then
    log_header "詳細情報（--verbose）"
    
    echo "OpenClaw 設定ファイル:"
    docker exec openclaw-agent cat /home/appuser/.openclaw/openclaw.json 2>/dev/null || {
        log_warn "設定ファイルが見つかりません"
    }
    
    echo ""
    echo "全環境変数:"
    docker exec openclaw-agent env | grep -E "(OPENCLAW|PORT|ANTHROPIC)" | sort
fi

echo ""
log_info "スクリプト完了"
