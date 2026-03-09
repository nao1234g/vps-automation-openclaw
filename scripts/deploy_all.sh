#!/bin/bash
# ============================================
# deploy_all.sh — ローカル→VPS 全スクリプト一括デプロイ
# ============================================
# SSH鍵登録後にローカルPCから実行:
#   bash scripts/deploy_all.sh
#
# 実行内容:
#   1. 新規/更新スクリプトをVPSにSCPコピー
#   2. prediction_cron_update.py のcronジョブを登録
#   3. distribution_check.py で全チャネル状態確認
#   4. seo_setup.py --indexnow でBing/YandexにURL通知
# ============================================

set -euo pipefail

VPS="root@163.44.124.123"
REMOTE_DIR="/opt/shared/scripts"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_err()  { echo -e "${RED}❌ $1${NC}"; }

echo "========================================"
echo "  Nowpattern VPS Full Deploy"
echo "========================================"
echo ""

# ──────── Step 0: SSH接続確認 ────────
echo "▶ Step 0: SSH接続確認..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$VPS" "echo OK" >/dev/null 2>&1; then
    log_err "VPSに接続できません。SSH鍵を先に登録してください。"
    echo ""
    echo "  公開鍵（ConoHaコンソールで登録）:"
    cat ~/.ssh/conoha_vps.pub
    echo ""
    echo "  手順: https://manage.conoha.jp → VPS → コンソール"
    echo "  → /root/.ssh/authorized_keys に上記の公開鍵を追記"
    exit 1
fi
log_ok "VPS接続 OK"

# ──────── Step 1: スクリプトをVPSにコピー ────────
echo ""
echo "▶ Step 1: スクリプトをVPSにコピー..."

SCRIPTS=(
    "prediction_cron_update.py"
    "prediction_page_builder.py"
    "prediction_tracker.py"
    "prediction_resolver.py"
    "prediction_auto_verifier.py"
    "nowpattern_publisher.py"
    "seo_setup.py"
    "x_pipeline_check.py"
    "distribution_check.py"
    "article_validator.py"
    "nowpattern_taxonomy.json"
)

copied=0
for script in "${SCRIPTS[@]}"; do
    src="${LOCAL_DIR}/${script}"
    if [ -f "$src" ]; then
        scp -o BatchMode=yes "$src" "${VPS}:${REMOTE_DIR}/${script}"
        echo "  → ${script}"
        ((copied++))
    else
        log_warn "${script} not found locally, skipping"
    fi
done
log_ok "${copied}個のファイルをコピー完了"

# ──────── Step 2: VPS上でパーミッション設定 ────────
echo ""
echo "▶ Step 2: パーミッション設定..."
ssh "$VPS" "chmod +x ${REMOTE_DIR}/prediction_cron_update.py ${REMOTE_DIR}/seo_setup.py ${REMOTE_DIR}/x_pipeline_check.py ${REMOTE_DIR}/distribution_check.py 2>/dev/null; echo OK"
log_ok "パーミッション設定完了"

# ──────── Step 3: cronジョブ登録 ────────
echo ""
echo "▶ Step 3: cronジョブ登録..."

# prediction_cron_update.py — 毎日 01:00 JST (16:00 UTC)
CRON_LINE="0 16 * * * /usr/bin/python3 ${REMOTE_DIR}/prediction_cron_update.py >> /var/log/prediction-cron.log 2>&1"

ssh "$VPS" "
    # 既存のprediction_cron_updateエントリを除去して新しく追加
    (crontab -l 2>/dev/null | grep -v 'prediction_cron_update') | crontab -
    (crontab -l 2>/dev/null; echo '${CRON_LINE}') | crontab -
    echo 'Cron registered'
    crontab -l | grep prediction_cron
"
log_ok "prediction_cron_update.py を毎日01:00 JSTで登録"

# ──────── Step 4: 全チャネル状態確認 ────────
echo ""
echo "▶ Step 4: 全チャネル状態確認..."
ssh "$VPS" "cd ${REMOTE_DIR} && python3 distribution_check.py 2>&1" || log_warn "distribution_check.py 実行エラー"

# ──────── Step 5: SEO IndexNow送信 ────────
echo ""
echo "▶ Step 5: IndexNow URL送信（Bing/Yandex）..."
ssh "$VPS" "cd ${REMOTE_DIR} && python3 seo_setup.py --indexnow 2>&1" || log_warn "seo_setup.py 実行エラー"

# ──────── Step 6: X API認証確認 ────────
echo ""
echo "▶ Step 6: X API認証確認..."
ssh "$VPS" "cd ${REMOTE_DIR} && python3 x_pipeline_check.py --check 2>&1" || log_warn "x_pipeline_check.py 実行エラー"

# ──────── 完了 ────────
echo ""
echo "========================================"
echo "  デプロイ完了！"
echo "========================================"
echo ""
echo "次のアクション:"
echo "  1. X API認証が❌の場合 → developer.x.comでキー再生成"
echo "  2. note Cookie期限切れの場合 → Selenium再ログイン"
echo "  3. GSC確認 → https://search.google.com/search-console"
echo ""
