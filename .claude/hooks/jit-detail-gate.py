#!/usr/bin/env python3
"""
JIT DETAIL GATE — PreToolUse + PostToolUse Hook
================================================
JIT強制: 予測クリティカルファイルを編集する前に NORTH_STAR_DETAIL.md を
読んでいることを強制する。

[PostToolUse / Read] → NORTH_STAR_DETAIL.md の読み込みを検知 → state に記録
[PreToolUse / Edit|Write] → 予測クリティカルファイル編集時に DETAIL 未読ならブロック

設計根拠:
  NORTH_STAR.md はサマリー版で毎セッション自動読み込みされるが、
  DETAIL はJIT参照。予測・検証・LTV系ファイルを編集するには
  §12/§13/§14/§15 の詳細知識が必要。このhookがそれを強制する。
"""
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_FILE = STATE_DIR / "detail_loaded.json"
DETAIL_PATH = ".claude/reference/NORTH_STAR_DETAIL.md"

# ── 予測クリティカルファイル → 必要なDETAILセクション ──────────────────
# パターン: (ファイルパスの部分一致, 必要な§番号, 理由)
CRITICAL_FILES = [
    # §12: 読者参加型PF / AI Notion
    ("prediction_page_builder", "§12", "予測ページ生成は§12(読者参加型PF/AI Notion)の理解が必要"),
    ("prediction_similarity_search", "§12", "類似予測検索は§12(AI Notion)の理解が必要"),
    ("update_leaderboard", "§12", "リーダーボードは§12(読者参加型PF)の理解が必要"),
    ("reader_prediction_api", "§12", "読者投票APIは§12(読者参加型PF)の理解が必要"),
    ("update_prediction_methodology", "§12", "予測方法論ページは§12の理解が必要"),
    ("update_prediction_tracker", "§12", "予測トラッカーは§12の理解が必要"),
    # §13: AI Civilization
    ("civilization", "§13", "文明モデルは§13(AI Civilization)の理解が必要"),
    ("agent_civilization", "§13", "エージェント文明は§13の理解が必要"),
    # §14: Truth Protocol / Prediction Integrity
    ("prediction_db", "§14", "予測DBは§14(Truth Protocol)の理解が必要"),
    ("prediction_state", "§14", "予測状態管理は§14の理解が必要"),
    ("auto_verifier", "§14", "自動検証は§14(Prediction Integrity)の理解が必要"),
    ("brier", "§14", "Brier計算は§14の理解が必要"),
    ("ghost_guardian", "§14", "Ghost監視は§14の理解が必要"),
    ("ots_", "§14", "OTSタイムスタンプは§14の理解が必要"),
    # §15: Long-Term Value
    ("ltv_", "§15", "LTV計算は§15(Long-Term Value)の理解が必要"),
    ("long_term_value", "§15", "長期価値判断は§15の理解が必要"),
]

# ── stdin を読む ──────────────────────────────────────────────────────
try:
    raw = sys.stdin.read().strip()
    data = json.loads(raw) if raw else {}
except Exception:
    sys.exit(0)

hook_event = data.get("hook_event_name", "")
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})


def ensure_state_dir():
    """state ディレクトリが存在することを確認"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> dict:
    """state ファイルを読み込む"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    """state ファイルを保存"""
    ensure_state_dir()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def normalize_path(file_path: str) -> str:
    """パスを正規化して比較しやすくする"""
    return file_path.replace("\\", "/").lower()


def is_detail_read(file_path: str) -> bool:
    """読み込まれたファイルが NORTH_STAR_DETAIL.md かどうか"""
    norm = normalize_path(file_path)
    return "north_star_detail.md" in norm


def get_required_section(file_path: str) -> tuple[str, str] | None:
    """ファイルパスから必要なDETAILセクションを返す"""
    norm = normalize_path(file_path)
    basename = norm.split("/")[-1] if "/" in norm else norm
    for pattern, section, reason in CRITICAL_FILES:
        if pattern.lower() in basename:
            return (section, reason)
    return None


# ═══════════════════════════════════════════════════════════════════════
# PostToolUse / Read → DETAIL 読み込みを記録
# ═══════════════════════════════════════════════════════════════════════
if hook_event == "PostToolUse" and tool_name == "Read":
    file_path = tool_input.get("file_path", "")
    if is_detail_read(file_path):
        state = load_state()
        state["loaded"] = True
        state["timestamp"] = datetime.now().isoformat()
        state["file_path"] = file_path
        # セッション内で読み込まれた回数を追跡
        state["read_count"] = state.get("read_count", 0) + 1
        save_state(state)
    sys.exit(0)

# ═══════════════════════════════════════════════════════════════════════
# PreToolUse / Edit|Write → クリティカルファイル編集時にDETAIL読み込み済みか確認
# ═══════════════════════════════════════════════════════════════════════
if hook_event == "PreToolUse" and tool_name in ("Edit", "Write"):
    file_path = tool_input.get("file_path", "")

    # DETAIL自体の編集は常に許可（自己参照ループ防止）
    if is_detail_read(file_path):
        sys.exit(0)

    # NORTH_STAR.md の編集は常に許可（north-star-guard.py が管理）
    norm = normalize_path(file_path)
    if "north_star.md" in norm and "detail" not in norm:
        sys.exit(0)

    # クリティカルファイルかチェック
    required = get_required_section(file_path)
    if required is None:
        sys.exit(0)  # クリティカルでないファイルは素通り

    section, reason = required

    # DETAIL が読み込まれているかチェック
    state = load_state()
    if state.get("loaded"):
        sys.exit(0)  # 読み込み済み → 許可

    # ブロック: DETAIL未読でクリティカルファイル編集
    basename = file_path.split("/")[-1].split("\\")[-1]
    print(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️  [JIT DETAIL GATE] NORTH_STAR_DETAIL.md 未読\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  編集対象: {basename}\n"
        f"  必要セクション: {section}\n"
        f"  理由: {reason}\n"
        "\n"
        "  このファイルは予測クリティカルファイルです。\n"
        "  編集する前に NORTH_STAR_DETAIL.md を Read してください:\n"
        "\n"
        "  Read .claude/reference/NORTH_STAR_DETAIL.md\n"
        "\n"
        "  JIT参照設計: サマリー(NORTH_STAR.md)は自動読み込みされますが、\n"
        "  詳細版(DETAIL)は必要時にReadする設計です。\n"
        "  予測系ファイルの編集にはDETAILの知識が必要です。\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    sys.exit(2)

# その他のイベントは素通り
sys.exit(0)
