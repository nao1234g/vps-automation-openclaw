#!/bin/bash
# deploy-static-files.sh
# nowpattern.com の静的ファイル（llms.txt 等）をVPSにデプロイする
# 実行: bash scripts/deploy-static-files.sh [--dry-run]
# VPS Caddy設定に /llms.txt ルートを追加し、実際にアクセスできることをcurlで確認する

set -e

VPS="root@163.44.124.123"
STATIC_DIR="/var/www/nowpattern-static"
CADDYFILE="/etc/caddy/Caddyfile"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLMS_TXT="$SCRIPT_DIR/llms.txt"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

log()  { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}⛔ $*${NC}"; exit 1; }

[[ -f "$LLMS_TXT" ]] || err "llms.txt が見つかりません: $LLMS_TXT"

echo "=== nowpattern.com 静的ファイルデプロイ ==="
$DRY_RUN && warn "DRY-RUN モード（実際には変更しません）"

# ── Step1: VPSにディレクトリ作成 & llms.txtをコピー ─────────────────────────
log "Step1: /var/www/nowpattern-static/ をVPSに作成..."
if ! $DRY_RUN; then
    ssh "$VPS" "mkdir -p $STATIC_DIR && chmod 755 $STATIC_DIR"
    scp "$LLMS_TXT" "$VPS:$STATIC_DIR/llms.txt"
    ssh "$VPS" "chmod 644 $STATIC_DIR/llms.txt"
    log "llms.txt → VPS $STATIC_DIR/llms.txt にコピー完了"
else
    echo "  [DRY] mkdir -p $STATIC_DIR"
    echo "  [DRY] scp llms.txt → $VPS:$STATIC_DIR/llms.txt"
fi

# ── Step2: Caddyfileに /llms.txt ルートを追加（重複チェック付き） ──────────────
log "Step2: Caddyfileを確認・更新..."
if ! $DRY_RUN; then
    EXISTING=$(ssh "$VPS" "grep -c 'llms.txt' $CADDYFILE 2>/dev/null || echo 0")
    if [ "$EXISTING" -gt 0 ]; then
        warn "Caddyfileにすでに llms.txt ルートが存在します（スキップ）"
    else
        # バックアップを取ってから編集
        ssh "$VPS" "cp $CADDYFILE ${CADDYFILE}.bak-$(date +%Y%m%d-%H%M%S)"

        # nowpattern.com のブロックの先頭に /llms.txt ルートを挿入
        # 「nowpattern.com {」の直後に追加
        ssh "$VPS" "sed -i '/^nowpattern\.com {/a\\    # Static files (llms.txt etc.)\n    handle /llms.txt {\n        root * $STATIC_DIR\n        file_server\n        header Content-Type \"text/plain; charset=utf-8\"\n    }' $CADDYFILE"
        log "Caddyfile更新完了"

        # Caddy設定を検証してリロード
        ssh "$VPS" "caddy validate --config $CADDYFILE && systemctl reload caddy"
        log "Caddy リロード完了"
    fi
else
    echo "  [DRY] Caddyfileに /llms.txt ルートを追加"
    echo "  [DRY] caddy validate && systemctl reload caddy"
fi

# ── Step3: 実際にアクセスして確認（証拠を出力） ───────────────────────────────
log "Step3: curl で動作確認..."
sleep 2  # Caddyリロードを待つ

if ! $DRY_RUN; then
    echo "--- curl https://nowpattern.com/llms.txt ---"
    HTTP_STATUS=$(curl -s -o /tmp/llms_verify.txt -w "%{http_code}" --max-time 10 "https://nowpattern.com/llms.txt" || echo "000")

    if [ "$HTTP_STATUS" = "200" ]; then
        log "HTTP 200 OK — llms.txt が正常に配信されています"
        echo "--- 先頭10行 ---"
        head -10 /tmp/llms_verify.txt
    else
        err "HTTP $HTTP_STATUS — llms.txt にアクセスできません。Caddyfileを確認してください。"
    fi
else
    echo "  [DRY] curl https://nowpattern.com/llms.txt"
fi

echo ""
log "=== デプロイ完了 ==="
echo "  URL: https://nowpattern.com/llms.txt"
echo "  ファイル: $STATIC_DIR/llms.txt"
