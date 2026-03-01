#!/usr/bin/env python3
"""
UI Layout Guard — PreToolUse Hook
prediction_page_builder.py のレイアウト関数を変更しようとしたとき BLOCK する。
明示的な承認（ユーザーが「UIレイアウト変更を承認」と発言）がない限り、
ページ構造に影響する変更を物理的に停止させる。
"""
import json
import sys
import os
import re
from pathlib import Path

# ── 保護対象ファイル ──
PROTECTED_FILES = [
    "prediction_page_builder.py",
]

# ── 保護対象関数（これらを触る編集はブロック） ──
PROTECTED_FUNCTIONS = [
    "_scoreboard_block",
    "_build_card",
    "build_page_html",
    "_resolved_section",
    "_pending_section",
    "_build_row_html",
    "def build_rows",
    "_pending_block",
    "_resolved_block",
    "np-tracking-list",   # HTML ID
    "np-scoreboard",
    "np-resolved",
]

# ── セッション状態ファイル（承認フラグ） ──
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
UI_APPROVAL_FILE = STATE_DIR / "ui_layout_approved.flag"


def is_layout_approved():
    """ユーザーが明示的にUIレイアウト変更を承認したか確認"""
    return UI_APPROVAL_FILE.exists()


def check_content_for_layout(content: str) -> list:
    """コンテンツ中にレイアウト関数が含まれているかチェック。ヒットしたキーワードリストを返す"""
    hits = []
    for func in PROTECTED_FUNCTIONS:
        if func in content:
            hits.append(func)
    return hits


def is_protected_file(file_path: str) -> bool:
    return any(pf in file_path for pf in PROTECTED_FILES)


# ── stdin からツール情報を読み込み ──
try:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# ── Edit ツール: ファイルパスとold/new_stringをチェック ──
if tool_name == "Edit":
    file_path = tool_input.get("file_path", "")
    if is_protected_file(file_path):
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        combined = old_string + "\n" + new_string
        hits = check_content_for_layout(combined)
        if hits and not is_layout_approved():
            reason = (
                "🛡️ UIレイアウト変更ガード: BLOCKED\n\n"
                f"  ファイル: prediction_page_builder.py\n"
                f"  検出されたレイアウト関数: {', '.join(hits[:3])}\n\n"
                "  このスクリプトのページレイアウト（スコアボード・カード構造・セクション）は\n"
                "  Naoto の明示的な承認なしに変更できません。\n\n"
                "  ✅ 変更を承認する場合は、次のように発言してください:\n"
                "     「UIレイアウト変更を承認する: [変更内容の説明]」\n\n"
                "  ❌ 承認なしにレイアウト変更を行うと、ページが予期せず壊れる可能性があります。\n"
                "  （例: 2026-02-26のB2リストラクチャ — Naoto承認なしで大幅変更）"
            )
            print(json.dumps({"decision": "block", "reason": reason}))
            sys.exit(2)

# ── Write ツール: ファイルパスとcontentをチェック ──
elif tool_name == "Write":
    file_path = tool_input.get("file_path", "")
    if is_protected_file(file_path):
        content = tool_input.get("content", "")
        hits = check_content_for_layout(content)
        if hits and not is_layout_approved():
            reason = (
                "🛡️ UIレイアウト変更ガード: BLOCKED\n\n"
                f"  ファイル: prediction_page_builder.py への書き込みは\n"
                f"  Naoto の明示的な承認なしに実行できません。\n\n"
                "  ✅ 変更を承認する場合は:\n"
                "     「UIレイアウト変更を承認する: [変更内容の説明]」"
            )
            print(json.dumps({"decision": "block", "reason": reason}))
            sys.exit(2)

# ── Bash ツール: SSH経由でprediction_page_builder.pyを触るコマンドをチェック ──
elif tool_name == "Bash":
    command = tool_input.get("command", "")
    # SSHでVPS上のprediction_page_builder.pyを編集するパターンを検出
    if "prediction_page_builder.py" in command and not is_layout_approved():
        # sed/awk/python patchなど、ファイル書き換え系コマンドを検出
        WRITE_PATTERNS = [
            r"sed\s+-i",
            r">\s*/opt/shared/scripts/prediction_page_builder",
            r"patch\b",
            r"python3\s+/tmp/add_snapshot",  # 許可: スナップショット追加
        ]
        # スナップショット追加は許可（自分でやっている作業）
        ALLOW_PATTERNS = [
            "take_page_snapshot",
            "take_snapshot",
            "add_snapshot",
            "PAGE_HISTORY",
            "bak",   # バックアップ操作
            "py_compile",  # 構文チェック
            "grep",   # 検索
            "wc -l",  # 行数確認
            "cat ",   # 表示
            "sed -n",  # 表示
            "head", "tail",  # 表示
        ]
        is_write_op = bool(re.search(r"sed\s+-i|python3\s+/tmp/add_(?!snapshot)|>\s+/opt/shared/scripts/prediction_page", command))
        is_allowed = any(pat in command for pat in ALLOW_PATTERNS)

        if is_write_op and not is_allowed and not is_layout_approved():
            reason = (
                "🛡️ UIレイアウト変更ガード: BLOCKED\n\n"
                f"  VPS上の prediction_page_builder.py への書き込みコマンドを検出しました。\n\n"
                "  ✅ 変更を承認する場合は:\n"
                "     「UIレイアウト変更を承認する: [変更内容の説明]」"
            )
            print(json.dumps({"decision": "block", "reason": reason}))
            sys.exit(2)

# ── 承認フラグのリセット: ファイルを書いたら次は再承認が必要 ──
# (Edit/Write完了後にフラグを消す処理はPostToolUseで行う想定)

sys.exit(0)
