#!/usr/bin/env python3
"""
CHANGE TRACKER — PostToolUse Hook (State-Based Verification Engine)
====================================================================
世界最高基準の状態ベース検証:

  テキストパターン（語彙）に依存しない完了詐称検出
  「変更しました」「更新しました」「対応しました」等の
  語彙バイパスを根本的に解決する。

動作:
  Edit/Write → 変更ファイルを state/pending_verification.json に記録
  Bash（検証コマンド） → verified_at 更新 + pending_edits をクリア
  Stop hook (fact-checker.py) → 未検証変更があればブロック

CI/CD との対応:
  [GitHub Actions] commit → tests run → pass/fail
  [このシステム]  Edit    → Bash verify → verified/block

根拠（世界の実装例から）:
  Devin AI: 変更追跡 + 自動テスト実行 + テスト失敗時ブロック
  SWE-bench: タスク完了 = テスト通過の証拠が必須
  GitHub CI: テキストで言ってもCIは動く（何を言ったかではなく何をしたかで判定）
"""
import json
import sys
import time
import re
from pathlib import Path

# Windows cp932 環境での絵文字出力対応
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

STATE_DIR = Path(__file__).parent / "state"
STATE_FILE = STATE_DIR / "pending_verification.json"
STATE_DIR.mkdir(exist_ok=True)

# 検証を必要とするファイル拡張子（コードファイルのみ）
REQUIRES_VERIFICATION = re.compile(
    r"\.(py|sh|js|ts)$",
    re.IGNORECASE
)

# 検証不要ファイル（ドキュメント・設定・状態ファイル）
SKIP_VERIFICATION = re.compile(
    r"(CLAUDE\.md|KNOWN_MISTAKES|AGENT_WISDOM|"
    r"settings.*\.json|config.*\.json|package.*\.json|"
    r"[/\\]docs[/\\]|[/\\]memory[/\\]|\.claude[/\\]rules[/\\]|hooks[/\\]state[/\\]|"
    r"\.md$|\.txt$|\.yml$|\.yaml$|\.json$)",
    re.IGNORECASE
)

# 検証コマンドとして認めるパターン
# （SSH接続・テスト実行・ヘルスチェック・構文チェック）
VERIFICATION_COMMANDS = re.compile(
    r"(^ssh\s|python3?\s.*(verify|check|test|health|validate|site_health)|"
    r"pytest|unittest|bash\s.*(test|verify)|"
    r"/opt/shared/scripts/|site_health_check|prediction_page_builder|"
    r"systemctl\s+(status|is-active)|docker\s.*(ps|inspect)|"
    r"curl\s.*(nowpattern|localhost|127\.0\.0\.1)|"
    r"python3\s+-c\s+|python3?\s+[\"'].*(import|ast)|"
    r"python3?\s+.*/\.claude/hooks/)",
    re.IGNORECASE
)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"pending_edits": [], "verified_at": 0, "last_verification_cmd": ""}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def is_verification_required(file_path: str) -> bool:
    """このファイルの変更は動作確認が必要か？"""
    if SKIP_VERIFICATION.search(file_path):
        return False
    return bool(REQUIRES_VERIFICATION.search(file_path))


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    state = load_state()
    now = time.time()

    # ── Edit / Write → 変更記録 ────────────────────────────────────────────────
    if tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        if file_path and is_verification_required(file_path):
            # 同じファイルへの重複エントリを上書き
            state["pending_edits"] = [
                e for e in state["pending_edits"]
                if e.get("file") != file_path
            ]
            state["pending_edits"].append({
                "file": file_path,
                "at": now,
                "tool": tool_name
            })
            save_state(state)

            # prediction_page_builder.py の編集後はUIレイアウト承認フラグをリセット
            if "prediction_page_builder.py" in file_path:
                ui_flag = STATE_DIR / "ui_layout_approved.flag"
                if ui_flag.exists():
                    ui_flag.unlink()
                # proposal_shown.flag も念のためリセット（未使用分の残留を防ぐ）
                proposal_flag = STATE_DIR / "proposal_shown.flag"
                if proposal_flag.exists():
                    proposal_flag.unlink()

    # ── Bash → 検証コマンドなら pending_edits をクリア ─────────────────────────
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if VERIFICATION_COMMANDS.search(command):
            state["pending_edits"] = []
            state["verified_at"] = now
            state["last_verification_cmd"] = command[:120]
            save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
