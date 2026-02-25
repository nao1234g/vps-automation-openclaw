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
import re
import time
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

    # ── 新規コード作成はTodoWriteによるプラン作成も必須 ────────────────────
    fp = tool_input.get("file_path", "")
    CODE_EXTENSIONS = ('.py', '.sh', '.js', '.ts', '.yaml', '.yml')
    is_new_code_check = tool_name == "Write" and any(fp.endswith(ext) for ext in CODE_EXTENSIONS)
    if is_new_code_check:
        plan_created = state.get("plan_created", False)
        if not plan_created:
            state["task_started"] = True
            state["started_without_plan"] = True
            STATE_FILE.write_text(json.dumps(state))
            msg = (
                "🚫 BLOCKED: 新規コードファイルの作成前にTodoWriteでタスク計画が必要です。\n"
                "→ まず TodoWrite ツールで「やること」を箇条書きにしてください。\n"
                "→ タスクボード: ~/.claude/tasks/dashboard.html（ブラウザで開くと10秒ごと更新）\n"
                "→ 計画を書いてから再度コードを作成してください。\n"
                "（このブロックは「コーディング前に計画を書く」原則の物理的強制です）"
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

    # ── UI変更検出: ui_task_pending を設定（要件1 + 要件2の前提） ─────────────────
    # CSS/.html/.hbs ファイル編集、または Ghost codeinjection 変更を検出
    fp_ui = tool_input.get("file_path", "")
    cmd_ui = tool_input.get("command", "") if tool_name == "Bash" else ""
    UI_FILE_EXTS = ('.css', '.html', '.hbs', '.scss')
    _ui_file = any(fp_ui.lower().endswith(ext) for ext in UI_FILE_EXTS)
    _ui_bash = bool(re.search(
        r'(codeinjection_head|codeinjection_foot'
        r'|python3\s+/tmp/fix'
        r'|systemctl\s+restart\s+ghost)',
        cmd_ui, re.IGNORECASE
    ))

    if _ui_file or _ui_bash:
        # 要件1: TodoWrite でテスト計画がない場合はブロック
        try:
            state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else state
        except Exception:
            pass
        plan_ok = state.get("plan_created", False)
        if not plan_ok:
            msg = (
                "🚫 BLOCKED: UI/CSS変更前に視覚テスト計画（TodoWrite）が必要です。\n"
                "→ まず TodoWrite で以下のような確認タスクを含むリストを書いてください:\n"
                "  例: 「ブラウザで /en/ を開いてナビゲーションが正しく表示されるか目視確認」\n"
                "  例: 「修正後 curl で実際のHTMLを取得して期待する文字列があるか確認」\n"
                "→ 計画を書いてから再実行してください。\n"
                "（このブロックは「UI修正前に目視テスト計画を書く」原則の物理的強制です）"
            )
            print(json.dumps({"decision": "block", "reason": msg}))
            sys.exit(2)
        # 要件2: VRT ベースラインチェック（ベースラインなし → ブロック）
        vrt_ctx_path = STATE_DIR / "vrt_context.json"
        vrt_ok = False
        if vrt_ctx_path.exists():
            try:
                vrt_age = time.time() - vrt_ctx_path.stat().st_mtime
                vrt_ctx_data = json.loads(vrt_ctx_path.read_text())
                # 2時間以内のベースラインは有効
                if vrt_age < 7200 and vrt_ctx_data.get("status") == "baseline_ready":
                    vrt_ok = True
            except Exception:
                pass
        if not vrt_ok:
            msg = (
                "🚫 BLOCKED: UI/CSS変更前にVRTベースライン撮影が必要です。\n"
                "→ まず以下のコマンドでベースラインを撮影してください:\n"
                "  python scripts/ui_vrt_runner.py baseline \\\n"
                "    --url https://nowpattern.com/en/ \\\n"
                "    --selector \".gh-navigation-menu\"\n"
                "→ URLとセレクタは変更する対象に合わせて指定してください。\n"
                "→ 撮影後に再度編集を試みてください。\n"
                "（このブロックは「UI修正前にVRTベースラインを撮る」原則の物理的強制です）"
            )
            print(json.dumps({"decision": "block", "reason": msg}))
            sys.exit(2)
        # 計画あり・ベースラインあり → UI作業中フラグON
        state["ui_task_pending"] = True
        state["ui_approved"] = False
        STATE_FILE.write_text(json.dumps(state))

sys.exit(0)
