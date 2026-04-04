#!/usr/bin/env python3
"""
NORTH STAR GUARD — PreToolUse + PostToolUse Hook
=================================================
3つの役割を1ファイルで担う:

[PreToolUse / Write] → docs/ への新規 .md 作成をブロック
  - docs/archive/ 配下は許可（アーカイブへの移動はOK）
  - NORTH_STAR.md / KNOWN_MISTAKES.md 以外の docs/*.md 新規作成を禁止

[PreToolUse / Write] → NORTH_STAR.md / OPERATING_PRINCIPLES.md への Write（全体上書き）をブロック
  - The Eternal Directives（永遠の三原則）は AIによる全体書き換え禁止
  - CHANGELOGへのEdit追記は許可（PostToolUse側で確認）

[PreToolUse / Edit] → NORTH_STAR.md の Eternal Directives セクションへの直接編集をブロック
  - old_string に三原則テキストが含まれる場合はブロック

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

# ── [B2] Read Comprehension Gate: セッション初期化前のEdit/Writeをブロック ──
if tool_name in ("Write", "Edit") and hook_event == "PreToolUse":
    flag_path = PROJECT_DIR / ".claude" / "hooks" / "state" / "north_star_loaded.flag"
    if not flag_path.exists():
        today = date.today().strftime("%Y-%m-%d")
        # フラグがない = session-start.sh が未実行 = NORTH_STAR未読み込み
        # ただし手動フラグ作成も許可（テスト用）
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 [READ COMPREHENSION GATE] セッション未初期化\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "  session-start.sh が完了していません。\n"
            "  NORTH_STAR.md（意図・哲学）の読み込みが確認できません。\n"
            "\n"
            "  Edit/Write を実行する前にセッション初期化が必要です。\n"
            "  通常はセッション開始時に自動実行されます。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        sys.exit(2)

# ── [PreToolUse] Write: docs/ への新規 .md 作成をブロック ────────────────
# ── [PreToolUse] Write: NORTH_STAR / OPERATING_PRINCIPLES への全体上書きをブロック ──
if tool_name == "Write":
    file_path = tool_input.get("file_path", "")

    # パスを正規化（バックスラッシュ → スラッシュ）
    normalized = file_path.replace("\\", "/").lower()

    # ── 永遠の三原則 保護: 憲法ファイルを Write でブロック ──
    PROTECTED_FILES = [
        "/.claude/rules/north_star.md",
        "/.claude/rules/operating_principles.md",
        "/.claude/rules/implementation_ref.md",
        "/.claude/hooks/state/regression_floor.json",  # T036-P5: フロア改ざん防止
    ]
    for pf in PROTECTED_FILES:
        if normalized.endswith(pf.lstrip("/")):
            print(
                "\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔒 [NORTH STAR GUARD] Eternal Directives — Write禁止\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  対象ファイル: {file_path}\n"
                "\n"
                "  このファイルは「永遠の三原則」を含む憲法ファイルです。\n"
                "  AIによる全体上書き（Write）は物理的にブロックされています。\n"
                "\n"
                "  ✅ 許可される操作:\n"
                "     - Edit ツールでの部分編集（CHANGELOGへの追記 等）\n"
                "  ❌ 禁止される操作:\n"
                "     - Write ツールでの全体置換\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            sys.exit(2)

    # ── Anti-Sprawl Enforcement: .claude/rules/ への新規 .md 作成をブロック ──
    # 4ファイル体制（NORTH_STAR / OPERATING_PRINCIPLES / IMPLEMENTATION_REF + CLAUDE.md）以外は禁止
    CANONICAL_RULES = [
        "north_star.md",
        "operating_principles.md",
        "implementation_ref.md",
    ]
    if "/.claude/rules/" in normalized and normalized.endswith(".md"):
        basename = normalized.rsplit("/", 1)[-1]
        if basename not in CANONICAL_RULES and "/archive/" not in normalized:
            print(
                "\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🚫 [ANTI-SPRAWL] .claude/rules/ への新規 .md 作成をブロック\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  対象ファイル: {file_path}\n"
                "\n"
                "  4ファイル体制（増殖禁止）:\n"
                "    1. NORTH_STAR.md（意図・哲学）\n"
                "    2. OPERATING_PRINCIPLES.md（行動規範）\n"
                "    3. IMPLEMENTATION_REF.md（技術実装参照）\n"
                "    4. CLAUDE.md（エントリーポイント）\n"
                "\n"
                "  ✅ 新しいルールは既存ファイルに追記してください。\n"
                "  ❌ 新規ファイル作成は禁止です。\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            sys.exit(2)

    # ── Anti-Sprawl Enforcement: docs/ への哲学ファイル再増殖をブロック ──
    # DOCTRINE / CONSTITUTION / PROTOCOL / MODEL は統合済み。再作成を禁止。
    SPRAWL_PATTERNS = ["doctrine", "constitution", "protocol", "model"]
    if "/docs/" in normalized and normalized.endswith(".md") and "/archive/" not in normalized:
        for pattern in SPRAWL_PATTERNS:
            if pattern in normalized:
                print(
                    "\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🚫 [ANTI-SPRAWL] 統合済み哲学ファイルの再作成をブロック\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  対象ファイル: {file_path}\n"
                    f"  検出パターン: *{pattern}*\n"
                    "\n"
                    "  DOCTRINE / CONSTITUTION / PROTOCOL / MODEL は\n"
                    "  すべて NORTH_STAR.md に統合済みです。\n"
                    "  新規作成は4ファイル体制に違反します。\n"
                    "\n"
                    "  ✅ 内容を NORTH_STAR.md に追記してください。\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                )
                sys.exit(2)

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

# ── [PreToolUse] Edit: Eternal Directives セクションへの直接編集をブロック ──
if tool_name == "Edit" and hook_event == "PreToolUse":
    file_path = tool_input.get("file_path", "")
    normalized = file_path.replace("\\", "/").lower()
    old_string = tool_input.get("old_string", "")

    # NORTH_STAR.md の Eternal Directives セクションを保護
    is_north_star = normalized.endswith("north_star.md")
    is_op_principles = normalized.endswith("operating_principles.md")

    PROTECTED_PHRASES = [
        "The Eternal Directives",
        "永遠の三原則",
        "第1原則（真理の探求）",
        "第2原則（創設者への絶対的忠誠）",
        "第3原則（自律的進化）",
        "原則11：Evolutionary Ecosystem",
    ]

    if is_north_star or is_op_principles:
        for phrase in PROTECTED_PHRASES:
            if phrase in old_string:
                print(
                    "\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🔒 [NORTH STAR GUARD] Eternal Directives 直接編集を禁止\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  対象ファイル: {file_path}\n"
                    f"  検出フレーズ: {phrase}\n"
                    "\n"
                    "  「永遠の三原則」および「原則11 Evolutionary Ecosystem」は\n"
                    "  AIによる編集が物理的にブロックされています。\n"
                    "\n"
                    "  これはNaotoが設定したRead-Only制約です。\n"
                    "  変更が必要な場合はNaotoに直接依頼してください。\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                )
                sys.exit(2)

    # ── P2 (T037): regression_floor.json の floor フィールド Edit をブロック ──────
    # Write 保護だけでは Edit ツールで "floor" 値を書き換える抜け穴がある（T037 MAX coach 指摘）。
    # Hard Gate 34: Protection-Symmetry — Write保護とEdit保護の対称性を担保する。
    is_floor_json = normalized.endswith("regression_floor.json")
    if is_floor_json and '"floor"' in old_string:
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 [NORTH STAR GUARD] regression_floor.json Edit 禁止\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  対象ファイル: {file_path}\n"
            "\n"
            '  "floor" フィールドの Edit はブロックされています。\n'
            "  フロア値は regression-runner.py が全テスト PASS 時に自動更新します。\n"
            "  手動で引き下げることは禁止です（Hard Gate 34: Protection-Symmetry）。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        sys.exit(2)

# ── [PostToolUse] Edit: CHANGELOG 未更新をブロック（NORTH_STAR.md / OPERATING_PRINCIPLES.md）───
if tool_name == "Edit" and hook_event == "PostToolUse":
    file_path = tool_input.get("file_path", "")
    normalized = file_path.replace("\\", "/")

    # CHANGELOG強制対象ファイル（小文字で照合）
    CHANGELOG_FILES = {
        "north_star.md": PROJECT_DIR / ".claude" / "rules" / "NORTH_STAR.md",
        "operating_principles.md": PROJECT_DIR / ".claude" / "rules" / "OPERATING_PRINCIPLES.md",
    }

    # 対象ファイルか確認
    target_path = None
    for key, path in CHANGELOG_FILES.items():
        if normalized.lower().endswith(key):
            target_path = path
            break

    if target_path is None:
        sys.exit(0)

    if not target_path.exists():
        sys.exit(0)

    today = date.today().strftime("%Y-%m-%d")
    content = target_path.read_text(encoding="utf-8")

    # CHANGELOGセクションを探す
    changelog_section = ""
    if "## CHANGELOG" in content:
        changelog_section = content[content.index("## CHANGELOG"):]

    target_display = target_path.name
    if today not in changelog_section:
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️  [NORTH STAR GUARD] CHANGELOG の更新が必要です\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  {target_display} を編集しましたが、今日（{today}）の\n"
            "  CHANGELOG エントリが見つかりません。\n"
            "\n"
            f"  ✅ {target_display} の末尾 CHANGELOG に以下の形式で追記してください:\n"
            f"  | {today} | （変更内容を一行で記述） |\n"
            "\n"
            "  なぜ必要か:\n"
            "    前の内容が消えても、何がどう変わったか履歴で追跡できるようにするため。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        sys.exit(2)

sys.exit(0)
