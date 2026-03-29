#!/bin/bash
# codex-review.sh v2 — Claude Code → Codex コードレビュー パイプライン
# ============================================================
# 改善点（v2 — 2026-03-29 Codex critique反映）:
#   1. JSON構造化プロトコル（request/response）
#   2. full diff（500行切り捨て廃止）→ ファイル経由
#   3. セキュリティファイル優先フィルタ（--security モード）
#   4. HEAD→GET フォールバック（URLチェック改善済み）
#
# 使い方:
#   bash scripts/codex-review.sh                    # 全変更をレビュー
#   bash scripts/codex-review.sh .claude/hooks/     # hooks/のみレビュー
#   bash scripts/codex-review.sh --security          # セキュリティファイルのみ
#   bash scripts/codex-review.sh [files...]          # 指定ファイルのみ
#
# 前提: WSL2 Ubuntu上でtmuxセッション "agents" が起動中
#       codex paneにCodexが待機中

set -euo pipefail

MAILBOX=".agent-mailbox"
REVIEW_REQ="$MAILBOX/review-request.json"
REVIEW_RESP="$MAILBOX/review-response.md"
DIFF_FILE="$MAILBOX/review-diff.patch"
BRIDGE="$HOME/.smux/tmux-bridge"
MAX_WAIT=180  # v2: タイムアウト延長（full diffレビューのため）

mkdir -p "$MAILBOX"

# --- 0. モード判定 ---
SECURITY_MODE=false
FILES_ARG=()
for arg in "$@"; do
    if [ "$arg" = "--security" ]; then
        SECURITY_MODE=true
    else
        FILES_ARG+=("$arg")
    fi
done

# --- 1. diff取得（unstaged → staged → HEAD → HEAD~1 フォールバック） ---
get_diff() {
    local files=("$@")
    local diff=""
    if [ ${#files[@]} -gt 0 ]; then
        diff=$(git diff -- "${files[@]}" 2>/dev/null)
        [ -z "$diff" ] && diff=$(git diff --staged -- "${files[@]}" 2>/dev/null)
        [ -z "$diff" ] && diff=$(git diff HEAD -- "${files[@]}" 2>/dev/null)
        [ -z "$diff" ] && diff=$(git diff HEAD~1 -- "${files[@]}" 2>/dev/null)
    else
        diff=$(git diff 2>/dev/null)
        [ -z "$diff" ] && diff=$(git diff --staged 2>/dev/null)
        [ -z "$diff" ] && diff=$(git diff HEAD 2>/dev/null)
        [ -z "$diff" ] && diff=$(git diff HEAD~1 2>/dev/null)
    fi
    echo "$diff"
}

if $SECURITY_MODE; then
    # セキュリティファイル優先: hooks/, scripts/*guard*, scripts/*check*
    SECURITY_PATTERNS=(".claude/hooks/" "scripts/*guard*" "scripts/*check*" "scripts/*validator*")
    DIFF=""
    for pattern in "${SECURITY_PATTERNS[@]}"; do
        # shellcheck disable=SC2086
        partial=$(git diff -- $pattern 2>/dev/null)
        [ -z "$partial" ] && partial=$(git diff HEAD -- $pattern 2>/dev/null)
        [ -z "$partial" ] && partial=$(git diff HEAD~1 -- $pattern 2>/dev/null)
        DIFF="$DIFF$partial"
    done
    FILES_DESC="security files (.claude/hooks/, scripts/*guard|check|validator*)"
elif [ ${#FILES_ARG[@]} -gt 0 ]; then
    DIFF=$(get_diff "${FILES_ARG[@]}")
    FILES_DESC="${FILES_ARG[*]}"
else
    DIFF=$(get_diff)
    FILES_DESC="(all changed files)"
fi

DIFF=${DIFF:-"No diff found"}
DIFF_LINES=$(echo "$DIFF" | wc -l)

if [ "$DIFF_LINES" -lt 3 ]; then
    echo "❌ No changes to review."
    exit 1
fi

echo "📋 Diff: $DIFF_LINES lines from $FILES_DESC"

# --- 2. full diffをファイルに書き出し（切り捨てなし） ---
echo "$DIFF" > "$DIFF_FILE"
echo "📄 Full diff saved to $DIFF_FILE ($DIFF_LINES lines, no truncation)"

# --- 3. JSON構造化リクエスト作成 ---
# JSONエスケープ用: jqがあれば使う、なければpython
json_escape() {
    if command -v jq &>/dev/null; then
        echo "$1" | jq -Rs '.'
    else
        python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" <<< "$1" 2>/dev/null \
        || python -c "import json,sys; print(json.dumps(sys.stdin.read()))" <<< "$1"
    fi
}

TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
ESCAPED_FILES=$(json_escape "$FILES_DESC")
ESCAPED_DIFF_PATH=$(json_escape "$DIFF_FILE")

cat > "$REVIEW_REQ" <<ENDJSON
{
  "version": "2.0",
  "timestamp": "$TIMESTAMP",
  "reviewer": "codex",
  "requester": "claude-code",
  "scope": "$FILES_DESC",
  "diff_file": "$DIFF_FILE",
  "diff_lines": $DIFF_LINES,
  "security_mode": $SECURITY_MODE,
  "checklist": [
    "correctness: Does the logic do what it claims?",
    "security: Any injection, data leak, or auth bypass?",
    "nowpattern_invariants: Does it violate prediction_db integrity or Brier Score rules?",
    "edge_cases: What could break?",
    "regression_risk: Could this break existing tests?"
  ],
  "response_format": {
    "file": ".agent-mailbox/review-response.md",
    "structure": "## Findings\\n1. **Severity** [file:line]: description\\n   - **Concrete fix:** ..."
  }
}
ENDJSON

echo "📝 JSON review request written to $REVIEW_REQ"

# --- 4. 古いレスポンスを削除 ---
rm -f "$REVIEW_RESP"

# --- 5. Codexにメッセージ送信 ---
MSG="Code review request ready. Read .agent-mailbox/review-request.json for details. Full diff is at .agent-mailbox/review-diff.patch (${DIFF_LINES} lines). Write your review to .agent-mailbox/review-response.md using the format specified in the request JSON. Focus on: correctness, security, edge cases. Be specific with line numbers."

$BRIDGE read codex 3 >/dev/null 2>&1
$BRIDGE type codex "$MSG"
sleep 0.5
$BRIDGE read codex 3 >/dev/null 2>&1
$BRIDGE keys codex Enter

echo "📨 Sent to Codex. Waiting for review (max ${MAX_WAIT}s)..."

# --- 6. レスポンス待ち ---
ELAPSED=0
INTERVAL=5
while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))

    if [ -f "$REVIEW_RESP" ]; then
        RESP_SIZE=$(wc -c < "$REVIEW_RESP")
        if [ "$RESP_SIZE" -gt 50 ]; then
            echo ""
            echo "✅ Review received! (${ELAPSED}s, ${RESP_SIZE} bytes)"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            cat "$REVIEW_RESP"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            exit 0
        fi
    fi

    printf "."
done

# --- 7. タイムアウト → tmux paneから直接取得 ---
echo ""
echo "⏰ File response timeout. Reading Codex pane directly..."
PANE_OUTPUT=$(tmux capture-pane -t agents:0.1 -p -S -60 2>/dev/null || echo "Cannot read pane")
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$PANE_OUTPUT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
