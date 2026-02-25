#!/usr/bin/env python3
"""
FEEDBACK TRAP — UserPromptSubmit Hook
=====================================
ユーザーからの訂正/クレームを検出 → KNOWN_MISTAKES.md 更新を Stop hook で強制する。

動作:
1. ユーザーメッセージに訂正/批判パターンを検出
2. 検出したら session.json に correction_needed フラグを設定
3. KNOWN_MISTAKES.md の現在の mtime を記録（Stop hookで比較用）
4. Claudeのコンテキストに「記録必須」リマインダーを注入

Stop hook (fact-checker.py) との連携:
  - correction_needed=True かつ KNOWN_MISTAKES.md が未更新 → exit(2) でブロック
  - KNOWN_MISTAKES.md が更新されたら → フラグをクリアして解除
"""
import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
STATE_FILE = STATE_DIR / "session.json"
KNOWN_MISTAKES = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"

STATE_DIR.mkdir(parents=True, exist_ok=True)

# ── UI承認パターン（ユーザーが目視確認OKと言ったとき） ─────────────────────────
UI_APPROVAL_PATTERNS = re.compile(
    r"("
    r"\bOK\b|ok\b|オーケー|"
    r"確認(した|できた|しました|できました)|"
    r"直(った|ってる|っています)|治(った|ってる)|"
    r"(いい|良い|よさそう|問題ない|大丈夫)(ね|よ|です|ですね)?|"
    r"見えてる|見えました|表示(された|されてる|されています)|"
    r"正しく(表示|動作|見え)|"
    r"ちゃんと(見えてる|表示|動いてる)"
    r")",
    re.IGNORECASE
)

# ── UI拒否パターン（まだ直っていないとき） ────────────────────────────────────
UI_REJECTION_PATTERNS = re.compile(
    r"("
    r"まだ(直って|治って|おかしい|見えない|表示されない)|"
    r"(直って|治って)(ない|いない)|"
    r"(見えない|表示されない|変わってない|変わっていない)|"
    r"また(おかしい|壊れてる|同じ)"
    r")",
    re.IGNORECASE
)

# ── 訂正/クレームを示すパターン ──────────────────────────────────────────
CORRECTION_PATTERNS = re.compile(
    r"("
    r"違う|間違い|間違ってる|間違ってる|おかしい|おかしくない|"
    r"ダメだ|ダメじゃん|だめ|できてない|できていない|"
    r"やり直し|もう一度やって|再度やって|また間違えた|"
    r"って言ったじゃ|って言った|と言ったのに|ちゃんとして|ちゃんとやって|"
    r"バグってる|壊れてる|動かない|起動しない|失敗してる|うまくいかない|"
    r"なんで.{0,30}(の|ん)[!！？?]|"
    r"直してないじゃん|直ってない|治ってない|"
    r"また.{0,30}(間違|エラー|失敗|壊れ|動かな)"
    r")",
    re.IGNORECASE
)

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

# ── stdin を読む ─────────────────────────────────────────────────────────
try:
    raw = sys.stdin.read().strip()
    data = json.loads(raw) if raw else {}
except Exception:
    sys.exit(0)

user_message = data.get("prompt", "")
if not user_message:
    sys.exit(0)

# ── 訂正パターン検出 ─────────────────────────────────────────────────────
if CORRECTION_PATTERNS.search(user_message):
    state = load_state()

    # KNOWN_MISTAKES.md の現在の mtime を記録（Stop hookが「更新されたか」を判定に使う）
    mistakes_mtime = KNOWN_MISTAKES.stat().st_mtime if KNOWN_MISTAKES.exists() else 0

    state["correction_needed"] = True
    state["correction_ts"] = datetime.now().isoformat()
    state["correction_preview"] = user_message[:100]
    state["mistakes_mtime_at_correction"] = mistakes_mtime
    save_state(state)

    # Claudeのコンテキストに強いリマインダーを注入（UserPromptSubmit hookのstdout = context注入）
    print(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️  [FEEDBACK TRAP] ユーザーからの訂正/クレームを検出\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  この問題を解決した後、必ず以下を【両方】実行してください:\n"
        "\n"
        "  1. docs/KNOWN_MISTAKES.md に記録する\n"
        "     フォーマット:\n"
        "       ### YYYY-MM-DD: タイトル\n"
        "       - **症状**: 何が起きたか\n"
        "       - **根本原因**: なぜ起きたか\n"
        "       - **正しい解決策**: どう解決したか\n"
        "       - **教訓**: 次回どうすべきか\n"
        "       - **再発防止コード**: どのファイルにどんなバリデーション/hookを追加したか\n"
        "\n"
        "  2. 【必須】再発防止のコード強制を実装または提案する\n"
        "     - ドキュメントに書くだけでは不十分（LLMは指示を忘れる）\n"
        "     - validator/hook/スクリプトでコードレベルの物理ブロックを作る\n"
        "     - 例: バリデーション関数、pre-commit hook、ビルド時チェック\n"
        "     - 「再発防止コード」欄が空のKNOWN_MISTAKES記録は不完全\n"
        "\n"
        "  3. 記録なしで回答を終了しようとすると Stop hook がブロックします\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

# ── UI承認/拒否の検出 ────────────────────────────────────────────────────────
# ui_task_pending=True のとき、ユーザーのOK/NGを検出してstate更新する
state_for_ui = load_state()
if state_for_ui.get("ui_task_pending"):
    if UI_REJECTION_PATTERNS.search(user_message):
        # NG: まだ直っていない → ui_approved=False を維持 + correction_needed をセット
        mistakes_mtime = KNOWN_MISTAKES.stat().st_mtime if KNOWN_MISTAKES.exists() else 0
        state_for_ui["ui_approved"] = False
        state_for_ui["correction_needed"] = True
        state_for_ui["correction_ts"] = datetime.now().isoformat()
        state_for_ui["correction_preview"] = user_message[:100]
        state_for_ui["mistakes_mtime_at_correction"] = mistakes_mtime
        save_state(state_for_ui)
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⛔ [UI APPROVAL GATE] UIがまだ直っていません（ユーザー報告）\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ui_approved = False のまま継続します。\n"
            "  再修正後、「ブラウザで確認URL を開いて確認してください」と案内してください。\n"
            "  修正完了後は docs/KNOWN_MISTAKES.md に根本原因を記録してください。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
    elif UI_APPROVAL_PATTERNS.search(user_message):
        # OK: ユーザーが目視確認を完了 → ui_approved=True, ui_task_pending=False
        state_for_ui["ui_approved"] = True
        state_for_ui["ui_task_pending"] = False
        state_for_ui["ui_approved_ts"] = datetime.now().isoformat()
        save_state(state_for_ui)
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ [UI APPROVAL GATE] ユーザーが目視確認を完了しました\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ui_approved = True に設定しました。\n"
            "  TodoWrite でタスクを「completed」に更新できます。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

sys.exit(0)
