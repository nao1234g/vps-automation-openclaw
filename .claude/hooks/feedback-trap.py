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

# ── 意図確認ゲート用フラグ ─────────────────────────────────────────────────
INTENT_CONFIRMED_FLAG = STATE_DIR / "intent_confirmed.flag"
INTENT_NEEDS_CONFIRMATION_FLAG = STATE_DIR / "intent_needs_confirmation.flag"

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

# ── UIレイアウト変更承認の検出 ──────────────────────────────────────────────────
# ユーザーが「UIレイアウト変更を承認する」と発言したとき、フラグファイルを作成する
UI_LAYOUT_APPROVAL_PATTERN = re.compile(
    r"(UIレイアウト変更を承認|レイアウト変更.*承認|prediction_page_builder.*承認|承認.*prediction_page_builder|"
    r"ページ.*レイアウト.*変更.*OK|layout.*change.*approve|approve.*layout)",
    re.IGNORECASE
)
UI_LAYOUT_REVOKE_PATTERN = re.compile(
    r"(UIレイアウト変更.*取り消|承認.*取り消|承認を.*キャンセル)",
    re.IGNORECASE
)

UI_APPROVAL_FLAG = STATE_DIR / "ui_layout_approved.flag"
PROPOSAL_SHOWN_FLAG = STATE_DIR / "proposal_shown.flag"

if UI_LAYOUT_APPROVAL_PATTERN.search(user_message):
    # ── Vibe Code Tip #1: ワイヤーフレーム先提示チェック ──────────────────────
    # proposal_shown.flag が存在しない = モックアップを見せずに承認を求めている
    if not PROPOSAL_SHOWN_FLAG.exists():
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️  [UI LAYOUT GUARD] 承認する前にモックアップを見せてください\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  承認を受け付けるには、先に変更内容のASCIIワイヤーフレームを\n"
            "  表示してから以下のコマンドを実行してください:\n"
            "\n"
            "    bash: touch .claude/hooks/state/proposal_shown.flag\n"
            "\n"
            "  その後にもう一度「UIレイアウト変更を承認する」と発言してください。\n"
            "  （これはVibe Code原則: 変更前にビジュアルで合意する）\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
    else:
        # proposal_shown.flag 確認済み → 承認フラグを作成、提案フラグを削除
        UI_APPROVAL_FLAG.write_text(
            f"approved at {datetime.now().isoformat()}\nmessage: {user_message[:200]}\nproposal_verified: true"
        )
        PROPOSAL_SHOWN_FLAG.unlink()
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ [UI LAYOUT GUARD] モックアップ確認済み → レイアウト変更を承認しました\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  proposal_shown.flag を確認 → ui_layout_approved.flag を作成しました。\n"
            "  prediction_page_builder.py のレイアウト変更が許可されました。\n"
            "  変更後は自動的に承認フラグがリセットされます。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
elif UI_LAYOUT_REVOKE_PATTERN.search(user_message):
    if UI_APPROVAL_FLAG.exists():
        UI_APPROVAL_FLAG.unlink()
        print(
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 [UI LAYOUT GUARD] 承認を取り消しました\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  prediction_page_builder.py のレイアウト変更がブロック状態に戻りました。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

# ── 意図確認ゲート: 新しい指示の検出 ──────────────────────────────────────
# ユーザーが新しい実装指示を出したとき → 確認フラグをリセット
NEW_INSTRUCTION_PATTERNS = re.compile(
    r"(して$|してください|してくれ|してほしい|お願い|頼む|やって$|やってくれ|作って|実装して|"
    r"変えて|修正して|直して|追加して|削除して|設定して|更新して|デプロイして|"
    r"移動して|整理して|統合して|減らして|書いて|調べて|なんとかして|"
    r"もう一度|やり直し)",
    re.IGNORECASE
)

# メッセージが実質的な指示かどうか（30文字超かつ指示動詞を含む）
# 2026-03-11: AUTONOMOUS MODE — フラグによるブロックを廃止。アドバイザリーのみ。
# (旧: intent_needs_confirmation.flag作成→intent-confirm.pyがEDIT/WRITEをブロック)
# (新: チェックリスト表示のみ。Claudeは確認なしで即実行可能)
if len(user_message) > 30 and NEW_INSTRUCTION_PATTERNS.search(user_message):
    # フラグ操作を廃止（ブロックなし）
    # INTENT_CONFIRMED_FLAG.unlink(missing_ok=True)  # DISABLED
    # INTENT_NEEDS_CONFIRMATION_FLAG.write_text(...)  # DISABLED
    # pvqe_p_file.unlink(missing_ok=True)             # DISABLED

    # アドバイザリーのみ（表示するが止めない）
    print(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 [新指示検出] 実装前チェックリスト（参考）\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  💡 見積もり前にコードを読むこと（Read/Glob/Grep）\n"
        "  💡 KNOWN_MISTAKES.md で既知ミスを確認\n"
        "  💡 正しい順序: READ CODE → ESTIMATE → IMPLEMENT\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

# ── 意図確認ゲート: ユーザーの承認を検出 ─────────────────────────────────
# intent_needs_confirmation.flag が存在する場合のみ承認を検出
INTENT_APPROVAL_PATTERNS = re.compile(
    r"(そういうことです|その理解で|合ってます|合っています|正しい|その通り|"
    r"^OK$|^ok$|^はい$|^yes$|^そう$|進めて|どうぞ|了解|それでOK|それで大丈夫|"
    r"理解(した|できた)|その解釈でいい|それで合ってる|その認識で)",
    re.IGNORECASE
)

if INTENT_NEEDS_CONFIRMATION_FLAG.exists() and INTENT_APPROVAL_PATTERNS.search(user_message):
    INTENT_CONFIRMED_FLAG.write_text(
        f"confirmed_at: {datetime.now().isoformat()}\n"
        f"by_message: {user_message[:100]}"
    )
    INTENT_NEEDS_CONFIRMATION_FLAG.unlink(missing_ok=True)
    print(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ [意図確認ゲート] 理解が承認されました\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  intent_confirmed.flag を作成しました。\n"
        "  Edit/Write の実行が許可されました。\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

sys.exit(0)
