#!/usr/bin/env bash
# =============================================================================
# Hey Loop Intelligence Feed v2.0 — VPS配置スクリプト
# =============================================================================
set -e

VPS="root@163.44.124.123"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_SCRIPT="/opt/shared/scripts/intelligence-feed-v2.py"

echo "=== Hey Loop v2.0 VPS配置 ==="

# 1. スクリプトをVPSにコピー
echo "→ スクリプトをVPSにコピー中..."
scp "${SCRIPT_DIR}/intelligence-feed-v2.py" "${VPS}:${REMOTE_SCRIPT}"
ssh "${VPS}" "chmod +x ${REMOTE_SCRIPT}"
echo "  ✅ ${REMOTE_SCRIPT}"

# 2. ディレクトリ作成
echo "→ ディレクトリ作成中..."
ssh "${VPS}" "mkdir -p /opt/shared/intelligence/raw /opt/shared/intelligence/synthesis /opt/shared/intelligence/weekly"
echo "  ✅ /opt/shared/intelligence/ 以下作成完了"

# 3. 動作確認（ドライラン）
echo "→ 動作確認（collect --dry-run）..."
ssh "${VPS}" "source /opt/cron-env.sh && python3 ${REMOTE_SCRIPT} --collect --no-grok" | head -20
echo ""

# 4. cron 登録
echo "→ cron 登録中..."
ssh "${VPS}" bash << 'SSHEOF'
crontab -l 2>/dev/null | grep -v "intelligence-feed-v2" > /tmp/crontab_new || true
cat >> /tmp/crontab_new << 'CRONEOF'
# Hey Loop v2.0 — Intelligence Feed
*/30 * * * *  source /opt/cron-env.sh && python3 /opt/shared/scripts/intelligence-feed-v2.py --collect >> /opt/shared/intelligence/collect.log 2>&1
0 */3 * * *   source /opt/cron-env.sh && python3 /opt/shared/scripts/intelligence-feed-v2.py --synth >> /opt/shared/intelligence/synth.log 2>&1
0 23 * * 0    source /opt/cron-env.sh && python3 /opt/shared/scripts/intelligence-feed-v2.py --evolve >> /opt/shared/intelligence/evolve.log 2>&1
CRONEOF
crontab /tmp/crontab_new
echo "  ✅ cron 登録完了"
crontab -l | grep intelligence-feed
SSHEOF

echo ""
echo "=== 配置完了 ==="
echo ""
echo "確認コマンド:"
echo "  ssh ${VPS} 'python3 ${REMOTE_SCRIPT} --collect --dry-run'"
echo "  ssh ${VPS} 'python3 ${REMOTE_SCRIPT} --synth --dry-run'"
echo "  ssh ${VPS} 'tail -f /opt/shared/intelligence/synth.log'"
