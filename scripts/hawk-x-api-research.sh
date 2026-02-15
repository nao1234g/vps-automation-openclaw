#!/bin/bash
# Hawk X API自動調査スクリプト
# 毎日8時、12時、18時に実行

set -e

LOG_FILE="/opt/shared/hawk-research.log"
RESULT_DIR="/opt/shared/reports"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting X API research..." >> "$LOG_FILE"

# HawkにX API調査を依頼
docker exec openclaw-agent openclaw agent \
  --agent hawk-xresearch \
  --message "X（Twitter）APIの最新情報を調査してください。以下の点を確認：
1. APIの仕様変更（v2 API）
2. レート制限の変更
3. 新機能の追加
4. 非推奨となった機能
5. 価格変更

重要な変更があれば、詳細をレポートしてください。変更がなければ「変更なし」と報告してください。" \
  --deliver \
  --channel telegram \
  --json > "$RESULT_DIR/hawk_x_api_$(date +%Y%m%d_%H%M%S).json" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] X API research completed" >> "$LOG_FILE"
