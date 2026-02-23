#!/usr/bin/env python3
"""
RESEARCH GATE - PreToolUse Hook (v2 — enforcement mode)
1. BLOCK Write/Edit if content contains banned/deleted terms (exit 2)
2. BLOCK new code file creation without prior research (exit 2)
3. WARN (not block) for small edits to existing files without research
4. Track Read operations as research (5+ reads = research_done)
"""
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_FILE = STATE_DIR / "session.json"
SCORECARD = PROJECT_DIR / ".claude" / "SCORECARD.md"

STATE_DIR.mkdir(parents=True, exist_ok=True)

# ── 禁止用語リスト（AGENT_KNOWLEDGE.mdの「存在しないもの」と同期） ──
BANNED_TERMS = [
    "@aisaintel",
    "aisaintel",
    "AISA pipeline",
    "AISAパイプライン",
    "AISA Pipeline",
    "rss-post-quote-rt",   # AISA投稿スクリプト（停止中）
    "rss-news-pipeline",   # AISA収集スクリプト（停止中）
]

# Read stdin
try:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# Load state
state = {"research_done": False, "search_count": 0, "errors": [], "task_started": False}
if STATE_FILE.exists():
    try:
        state = json.loads(STATE_FILE.read_text())
    except Exception:
        pass

# ── Track research: WebSearch/WebFetch ──
if tool_name in ("WebSearch", "WebFetch"):
    state["research_done"] = True
    state["search_count"] = state.get("search_count", 0) + 1
    STATE_FILE.write_text(json.dumps(state))
    sys.exit(0)

# ── Track research: Read operations (5+ reads = context understood) ──
if tool_name == "Read":
    file_path = tool_input.get("file_path", "")
    if "KNOWN_MISTAKES" in file_path.upper() or "AGENT_WISDOM" in file_path.upper():
        state["mistakes_checked"] = True
        state["research_done"] = True  # reading mistakes/wisdom = research
    else:
        read_count = state.get("read_count", 0) + 1
        state["read_count"] = read_count
        if read_count >= 5:
            state["research_done"] = True  # 5+ file reads = context understood
    STATE_FILE.write_text(json.dumps(state))
    sys.exit(0)

# ── Write/Edit/Bash: 禁止用語チェック（ブロック） ──
if tool_name in ("Edit", "Write", "Bash"):
    content = (
        tool_input.get("new_string", "")
        or tool_input.get("content", "")
        or tool_input.get("command", "")  # Bashコマンドも検査
        or ""
    )
    content_lower = content.lower()

    for term in BANNED_TERMS:
        if term.lower() in content_lower:
            # BLOCK this tool call
            msg = (
                f"🚫 BLOCKED: コンテンツに廃止済み用語 '{term}' が含まれています。\n"
                f"  → @aisaintel は削除済み。AISAパイプラインはSUSPENDED。\n"
                f"  → /opt/shared/AGENT_KNOWLEDGE.md を確認してから書き直してください。\n"
                f"  → 現在アクティブなX: @nowpattern"
            )
            print(json.dumps({"decision": "block", "reason": msg}))
            sys.exit(2)

    # ── Research check before Edit/Write ──
    research_done = state.get("research_done", False)
    if not research_done:
        # 新規コードファイル作成 or 大規模編集 → 物理BLOCK (exit 2)
        fp = tool_input.get("file_path", "")
        content = (
            tool_input.get("new_string", "")
            or tool_input.get("content", "")
            or ""
        )
        CODE_EXTENSIONS = ('.py', '.sh', '.js', '.ts', '.yaml', '.yml')
        is_new_code = tool_name == "Write" and any(fp.endswith(ext) for ext in CODE_EXTENSIONS)
        is_large_edit = tool_name == "Edit" and len(content) > 200

        if is_new_code or is_large_edit:
            state["task_started"] = True
            state["started_without_research"] = True
            STATE_FILE.write_text(json.dumps(state))
            msg = (
                "🚫 BLOCKED: 新規コード作成・大規模編集にはリサーチが必要です。\n"
                "OPERATING_PRINCIPLES原則 (P↑): 実装前に実装例を検索すること。\n"
                "→ WebSearch で「ツール名 + やりたいこと + config/example」を検索\n"
                "→ docs/KNOWN_MISTAKES.md を確認\n"
                "→ 検索後に再度試みてください。\n"
                "（このブロックはexit 2による物理的強制です — テキスト原則ではない）"
            )
            print(json.dumps({"decision": "block", "reason": msg}))
            sys.exit(2)
        else:
            # 小規模編集・設定変更 → 警告のみ（止めない）
            state["task_started"] = True
            state["started_without_research"] = True
            STATE_FILE.write_text(json.dumps(state))
            print("⚠️  WARNING: リサーチなしでファイルを編集しています（小規模編集のため許可）。")
            print("KNOWN_MISTAKES.md を確認しましたか？WebSearchで解決策を探しましたか？")
    else:
        state["task_started"] = True
        STATE_FILE.write_text(json.dumps(state))

sys.exit(0)
