#!/usr/bin/env python3
"""
NORTH STAR GUARD — PreToolUse + PostToolUse Hook
=================================================
2つの役割を1ファイルで担う:

[PreToolUse / Write] → docs/ への新規 .md 作成をブロック
  - docs/archive/ 配下は許可（アーカイブへの移動はOK）
  - NORTH_STAR.md / KNOWN_MISTAKES.md 以外の docs/*.md 新規作成を禁止

[PostToolUse / Edit] → NORTH_STAR.md の変更後に CHANGELOG 未更新をブロック
  - NORTH_STAR.md を編集した場合、今日の日付が CHANGELOG に含まれているか確認
  - 含まれていなければ exit 2 でブロック（Claudeに追記を促す）
"""
import json
import sys
import os
import re
from pathlib import Path
from datetime import date

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))

# ── stdin を読む ─────────────────────────────────────────────────────────
try:
    raw = sys.stdin.read().strip()
    data = json.loads(raw) if raw else {}
except Exception:
    sys.exit(0)

hook_event = data.get("hook_event_name", "")
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# ── [PreToolUse] Write: docs/ への新規 .md 作成をブロック ────────────────
if tool_name == "Write":
    file_path = tool_input.get("file_path", "")

    # パスを正規化（バックスラッシュ → スラッシュ）
    normalized = file_path.replace("\\", "/").lower()

    # docs/ 配下の .md ファイルか？
    # - docs/archive/ は許可（アーカイブ移動）
    # - docs/KNOWN_MISTAKES.md は許可（唯一の正式ドキュメント）
    is_docs_md = "/docs/" in normalized and normalized.endswith(".md")
    is_archive = "/docs/archive/" in normalized
    is_known_mistakes = normalized.endswith("/docs/known_mistakes.md")

    if is_docs_md and not is_archive and not is_known_mistakes:
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🚫 [NORTH STAR GUARD] docs/ への新規 .md 作成をブロック\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  対象ファイル: {file_path}\n"
            "\n"
            "  docs/ フォルダには新しい .md を作らないルールです。\n"
            "\n"
            "  ✅ 正しい選択肢:\n"
            "     1. 内容を NORTH_STAR.md に統合する\n"
            "        → .claude/rules/NORTH_STAR.md\n"
            "     2. ミス記録なら KNOWN_MISTAKES.md に追記する\n"
            "        → docs/KNOWN_MISTAKES.md\n"
            "     3. アーカイブに移動するなら docs/archive/ に置く\n"
            "\n"
            "  情報の断片化を防ぐため、この制約は物理的に強制されています。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        sys.exit(2)

# ── [PostToolUse] Edit: NORTH_STAR.md の CHANGELOG 未更新をブロック ───────
if tool_name == "Edit":
    file_path = tool_input.get("file_path", "")
    normalized = file_path.replace("\\", "/")

    # NORTH_STAR.md の編集か？
    if not normalized.endswith("NORTH_STAR.md"):
        sys.exit(0)

    # ファイルを読んで CHANGELOG セクションに今日の日付があるか確認
    north_star_path = PROJECT_DIR / ".claude" / "rules" / "NORTH_STAR.md"
    if not north_star_path.exists():
        sys.exit(0)

    today = date.today().strftime("%Y-%m-%d")
    content = north_star_path.read_text(encoding="utf-8")

    # CHANGELOGセクションを探す
    changelog_section = ""
    if "## CHANGELOG" in content:
        changelog_section = content[content.index("## CHANGELOG"):]

    if today not in changelog_section:
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️  [NORTH STAR GUARD] CHANGELOG の更新が必要です\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  NORTH_STAR.md を編集しましたが、今日（{today}）の\n"
            "  CHANGELOG エントリが見つかりません。\n"
            "\n"
            "  ✅ NORTH_STAR.md の末尾 CHANGELOG に以下の形式で追記してください:\n"
            f"  | {today} | （変更内容を一行で記述） |\n"
            "\n"
            "  なぜ必要か:\n"
            "    前の内容が消えても、何がどう変わったか履歴で追跡できるようにするため。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        sys.exit(2)

sys.exit(0)
