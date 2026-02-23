#!/bin/bash
# =============================================================================
# DEPLOY MEMORY SYSTEM to VPS
# =============================================================================
# ChromaDB + Gemini Embedding 長期記憶システムをVPSにデプロイ
# =============================================================================

set -e

VPS="root@163.44.124.123"
REMOTE_DIR="/opt/shared/memory"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Deploying Long-Term Memory System to VPS ==="

# 1. VPSにディレクトリ作成
echo "[1/5] Creating directories on VPS..."
ssh -o ConnectTimeout=10 "$VPS" "mkdir -p $REMOTE_DIR/chromadb $REMOTE_DIR/entries /opt/shared/scripts"

# 2. pip install（ChromaDB + google-generativeai）
echo "[2/5] Installing Python dependencies on VPS..."
ssh -o ConnectTimeout=10 "$VPS" "pip3 install chromadb google-generativeai 2>&1 | tail -5"

# 3. スクリプトをVPSにコピー
echo "[3/5] Copying memory scripts to VPS..."
scp -o ConnectTimeout=10 \
    "$SCRIPT_DIR/memory_system.py" \
    "$SCRIPT_DIR/memory_store.py" \
    "$SCRIPT_DIR/memory_search.py" \
    "$SCRIPT_DIR/memory_extract.py" \
    "$VPS:/opt/shared/scripts/"

# 4. KNOWN_MISTAKES.mdを初期インポート
echo "[4/5] Importing KNOWN_MISTAKES.md to memory system..."
ssh -o ConnectTimeout=10 "$VPS" \
    "cd /opt && python3 /opt/shared/scripts/memory_extract.py . --base-dir $REMOTE_DIR --import-mistakes 2>&1 || echo 'Import skipped (no mistakes file or error)'"

# 5. 動作確認
echo "[5/5] Verifying memory system..."
ssh -o ConnectTimeout=10 "$VPS" "python3 /opt/shared/scripts/memory_search.py --base-dir $REMOTE_DIR --stats 2>&1"

echo ""
echo "=== Memory System Deployment Complete ==="
echo "  VPS storage: $REMOTE_DIR/"
echo "  Scripts: /opt/shared/scripts/memory_*.py"
echo ""
echo "Usage on VPS:"
echo "  python3 /opt/shared/scripts/memory_store.py --base-dir $REMOTE_DIR -c 'category' -t 'content'"
echo "  python3 /opt/shared/scripts/memory_search.py --base-dir $REMOTE_DIR 'search query'"
echo "  python3 /opt/shared/scripts/memory_search.py --base-dir $REMOTE_DIR --stats"
