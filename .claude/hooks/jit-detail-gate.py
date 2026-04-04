#!/usr/bin/env python3
"""
JIT DETAIL GATE — PreToolUse + PostToolUse Hook (v2)
====================================================
JIT強制: 予測クリティカルファイルを編集する前に NORTH_STAR_DETAIL.md を
十分に読んでいることを強制する。

[PostToolUse / Read] → NORTH_STAR_DETAIL.md の読み込みを検知 → 読み込み行数を累積記録
[PreToolUse / Edit|Write] → 予測クリティカルファイル編集時に十分なDETAIL読み込み済みか確認

v2 改善（致命的欠陥修正）:
  - セッション単位リセット: session-start.sh が detail_loaded.json を毎回削除
  - Read量チェック: limit=1 でヘッダーだけ読んでもパスできない。累積100行以上を要求
  - offset/limit 追跡: どの範囲を���んだかを記録し、十分な量を読んだかを判定
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_FILE = STATE_DIR / "detail_loaded.json"

# DETAIL ファイルの実体パス（行数計算用）
DETAIL_FILE = PROJECT_DIR / ".claude" / "reference" / "NORTH_STAR_DETAIL.md"

# 十分な読み込みと判定する最低行数（DETAILは約780行。100行 ≈ 13%以上を要求）
MIN_LINES_READ = 100

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
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    ensure_state_dir()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def normalize_path(file_path: str) -> str:
    return file_path.replace("\\", "/").lower()


def is_detail_path(file_path: str) -> bool:
    norm = normalize_path(file_path)
    return "north_star_detail.md" in norm


def get_required_section(file_path: str):
    norm = normalize_path(file_path)
    basename = norm.split("/")[-1] if "/" in norm else norm
    for pattern, section, reason in CRITICAL_FILES:
        if pattern.lower() in basename:
            return (section, reason)
    return None


def estimate_lines_read(tool_input: dict) -> int:
    """Read toolのinputから読み込み行数を推定する"""
    limit = tool_input.get("limit")
    offset = tool_input.get("offset", 0)

    if limit is not None:
        # 明示的なlimit指定あり
        return int(limit)

    # limitなし = デフォルト2000行（Read toolのデフォルト）
    # ただし実ファイル行数を超えない
    if DETAIL_FILE.exists():
        try:
            total = sum(1 for _ in open(DETAIL_FILE, encoding="utf-8"))
            return max(0, total - int(offset or 0))
        except Exception:
            pass
    return 2000  # フォールバック


# ═══════════════════════════════════════════════════════════════════════
# PostToolUse / Read → DETAIL 読み込み行数を累積記録
# ═══════════════════════════════════════════════════════════════════════
if hook_event == "PostToolUse" and tool_name == "Read":
    file_path = tool_input.get("file_path", "")
    if is_detail_path(file_path):
        lines_this_read = estimate_lines_read(tool_input)
        state = load_state()
        state["total_lines_read"] = state.get("total_lines_read", 0) + lines_this_read
        state["read_count"] = state.get("read_count", 0) + 1
        state["last_read"] = datetime.now().isoformat()
        state["loaded"] = state["total_lines_read"] >= MIN_LINES_READ
        # 読み込み履歴（デバッグ用）
        reads = state.get("reads", [])
        reads.append({
            "offset": tool_input.get("offset", 0),
            "limit": tool_input.get("limit"),
            "lines": lines_this_read,
            "at": datetime.now().isoformat(),
        })
        state["reads"] = reads[-20:]  # 最新20件まで保持
        save_state(state)
    sys.exit(0)

# ═══════════════════════════════════════════════════════════════════════
# PreToolUse / Edit|Write → 十分なDETAIL読み込み済みか確認
# ═══════════════════════════════════════════════════════════════════════
if hook_event == "PreToolUse" and tool_name in ("Edit", "Write"):
    file_path = tool_input.get("file_path", "")

    # DETAIL自体の編集は常に許可（自己参照ループ防止）
    if is_detail_path(file_path):
        sys.exit(0)

    # NORTH_STAR.md の編集は常に許可（north-star-guard.py が管理）
    norm = normalize_path(file_path)
    if "north_star.md" in norm and "detail" not in norm:
        sys.exit(0)

    # クリティカルファイルかチェック
    required = get_required_section(file_path)
    if required is None:
        sys.exit(0)

    section, reason = required

    # DETAIL が十分に読み込まれているかチェック
    state = load_state()
    total_lines = state.get("total_lines_read", 0)

    if state.get("loaded") and total_lines >= MIN_LINES_READ:
        sys.exit(0)  # ���分な量を読み込み済み → 許可

    # ブロック: DETAIL未読 or 読み込み不足
    basename = file_path.split("/")[-1].split("\\")[-1]
    if total_lines > 0:
        # 読んだが不十分
        status_msg = f"  現在の読み込み: {total_lines}行 / 必要: {MIN_LINES_READ}行以上"
        action_msg = (
            "  DETAILをもっと読んでください（offset/limitを変えて追加Read）:\n"
            "  例: Read .claude/reference/NORTH_STAR_DETAIL.md offset=200 limit=200"
        )
    else:
        # 全く読んでいない
        status_msg = "  現在の読み込み: 0行（未読）"
        action_msg = (
            "  編集する前に NORTH_STAR_DETAIL.md を Read してください:\n"
            "  Read .claude/reference/NORTH_STAR_DETAIL.md"
        )

    print(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️  [JIT DETAIL GATE] NORTH_STAR_DETAIL.md 読み込み不足\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  編集対象: {basename}\n"
        f"  必要セクション: {section}\n"
        f"  理由: {reason}\n"
        "\n"
        f"{status_msg}\n"
        "\n"
        f"{action_msg}\n"
        "\n"
        "  JIT参照設計: セッション内でDETAILを100行以上読むと解除されます。\n"
        "  ヘッダーだけ読んでも通過できません（v2: Read量チェック）。\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    sys.exit(2)

# その他のイベントは素通り
sys.exit(0)
