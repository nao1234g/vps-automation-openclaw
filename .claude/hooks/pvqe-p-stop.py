#!/usr/bin/env python3
"""
PVQE-P STOP — Stop Hook
========================
タスク完了報告の前に「証拠計画（evidence_plan）が実際に実行されたか」を検証する。

設計根拠:
  SWE-bench / Devin AI: 「言葉ではなくツール呼び出し系列で判定する」
  Google SRE Postmortem: 修正後には必ず確認コマンドを実行する
  Reflexion: 失敗した原因を記録 → 次回のコンテキストに注入

動作:
  1. pvqe_p.json が存在するか確認
  2. 最後のアシスタントメッセージが完了を示しているか確認
  3. transcript のBashツール呼び出しから evidence_plan が実行されたか確認
  4. 未実行の場合:
     - exit(2) でブロック + 実行すべきコマンドを表示
     - pvqe_p_failures.json に失敗記録を追記（次回参照用）
     - KNOWN_MISTAKES.md に AUTO-DRAFT を追記（永久記録 + GUARD_PATTERN化）

失敗記録は mistake-auto-guard.py の PVQE_P_EVIDENCE_SKIPPED タイプとして扱われる。
"""
import json
import sys
import re
import os
import time
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
PVQE_P_FILE = STATE_DIR / "pvqe_p.json"
PVQE_P_FAILURES_FILE = STATE_DIR / "pvqe_p_failures.json"
MISTAKES_FILE = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"

# ── 完了宣言パターン（これがあるときのみ証拠チェックが必要）─────────────────
COMPLETION_PATTERN = re.compile(
    r"("
    r"完了しました|完了です|実装しました|修正しました|追加しました|"
    r"変更しました|対応しました|直しました|できました|"
    r"以上で完了|これで完了|実装完了|修正完了|"
    r"適用しました|デプロイしました|設定しました"
    r")",
    re.IGNORECASE
)

# ── stdin 読み込み ────────────────────────────────────────────────────────
try:
    raw = sys.stdin.read().strip()
    data = json.loads(raw) if raw else {}
except Exception:
    sys.exit(0)

# ── Night Mode bypass ─────────────────────────────────────────────────────
_NIGHT_MODE_FLAG = STATE_DIR / "night_mode.flag"
if _NIGHT_MODE_FLAG.exists():
    sys.exit(0)  # Night Mode中はPVQE-P証拠チェックをバイパス（自律運転モード）

# ── pvqe_p.json 読み込み ───────────────────────────────────────────────────
if not PVQE_P_FILE.exists():
    sys.exit(0)  # pvqe_p.json なし → このhookは関係ない

try:
    pvqe_age = time.time() - PVQE_P_FILE.stat().st_mtime
    if pvqe_age > 14400:  # 4時間以上古い → セッションが変わっている
        sys.exit(0)
    pvqe = json.loads(PVQE_P_FILE.read_text(encoding="utf-8"))
    evidence_plan = pvqe.get("evidence_plan", "").strip()
    task_name = pvqe.get("task", "（不明）")
except Exception:
    sys.exit(0)  # 読み込みエラー → サイレント無視

if not evidence_plan:
    sys.exit(0)  # evidence_plan が未設定 → チェック不要

# ── 最後のアシスタントメッセージを取得 ────────────────────────────────────
def get_last_assistant_message(transcript_path: str) -> str:
    try:
        p = Path(transcript_path)
        if not p.exists():
            return ""
        for line in reversed(p.read_text(encoding="utf-8", errors="replace").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("type") == "assistant":
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, list):
                        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                        return " ".join(texts)
                    return str(content)
            except Exception:
                continue
    except Exception:
        pass
    return ""


last_msg = get_last_assistant_message(data.get("transcript_path", ""))
if not last_msg:
    sys.exit(0)

# 完了宣言がない → チェック不要
if not COMPLETION_PATTERN.search(last_msg):
    sys.exit(0)

# ── Transcript からBashツール呼び出しを収集 ────────────────────────────────
def get_bash_commands_from_transcript(transcript_path: str) -> list:
    """transcript JSONL から Bash ツールの command 引数を全て収集する"""
    if not transcript_path:
        return []
    try:
        p = Path(transcript_path)
        if not p.exists():
            return []
        commands = []
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("type") == "assistant":
                    content = entry.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if block.get("type") == "tool_use" and block.get("name") == "Bash":
                                cmd = block.get("input", {}).get("command", "")
                                if cmd:
                                    commands.append(cmd)
            except Exception:
                continue
        return commands
    except Exception:
        return []


bash_commands = get_bash_commands_from_transcript(data.get("transcript_path", ""))

# ── evidence_plan がBashコマンドに含まれているか確認 ──────────────────────
# evidence_plan の「核心キーワード」（最初の重要なキーワード）を抽出して照合
def extract_evidence_keywords(evidence_plan: str) -> list:
    """evidence_plan から照合用キーワードを抽出する"""
    # SSHコマンドなら、コマンド本体を抽出
    ssh_match = re.search(r"ssh\s+[^\s]+\s+'([^']+)'", evidence_plan)
    if ssh_match:
        inner = ssh_match.group(1)
        return [w for w in re.split(r'[\s/|]+', inner) if len(w) > 4][:3]

    # python/pytest などのスクリプト名を抽出
    script_match = re.findall(r"[\w_]+\.py", evidence_plan)
    if script_match:
        return script_match[:2]

    # curl コマンドのURL部分
    curl_match = re.findall(r"https?://[^\s\"']+", evidence_plan)
    if curl_match:
        return [re.sub(r'https?://', '', curl_match[0])[:40]]

    # 最初の意味ある単語を3つ
    words = [w for w in re.split(r'[\s/\\|]+', evidence_plan) if len(w) > 4]
    return words[:3]


evidence_keywords = extract_evidence_keywords(evidence_plan)

evidence_found = False
if evidence_keywords:
    combined_bash = " ".join(bash_commands)
    # 全キーワードの50%以上がBashコマンドに含まれていれば「実行済み」とみなす
    matched = sum(1 for kw in evidence_keywords if kw.lower() in combined_bash.lower())
    if matched >= max(1, len(evidence_keywords) * 0.5):
        evidence_found = True
else:
    # キーワード抽出できなかった → チェックスキップ（フォールスポジティブ防止）
    sys.exit(0)

if evidence_found:
    sys.exit(0)  # ✅ 証拠計画が実行済み → 通過

# ── ブロック: 証拠計画が未実行 ──────────────────────────────────────────────
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
date_header = datetime.now().strftime("%Y-%m-%d")

print(
    "\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "⛔ [PVQE-P STOP] 証拠計画が未実行です\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"\n"
    f"  タスク: {task_name}\n"
    f"\n"
    f"  📋 事前に定義した証拠計画:\n"
    f"    {evidence_plan}\n"
    f"\n"
    f"  このコマンドが実行された記録がありません。\n"
    f"\n"
    f"  ✅ 次にすること:\n"
    f"    1. 上記コマンドを実行する\n"
    f"    2. 出力結果を回答に含める\n"
    f"    3. その後に完了報告する\n"
    f"\n"
    f"  💡 証拠計画を変更する場合: pvqe_p.json の evidence_plan を更新してください\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
)

# ── 失敗記録を pvqe_p_failures.json に追記 ────────────────────────────────
failure_entry = {
    "date": now_str,
    "task": task_name,
    "evidence_plan": evidence_plan,
    "what_was_missing": "evidence_plan was declared but not executed before completion report",
    "keywords_searched": evidence_keywords
}

try:
    failures = []
    if PVQE_P_FAILURES_FILE.exists():
        failures = json.loads(PVQE_P_FAILURES_FILE.read_text(encoding="utf-8"))
    failures.append(failure_entry)
    # 最新50件のみ保持
    if len(failures) > 50:
        failures = failures[-50:]
    PVQE_P_FAILURES_FILE.write_text(
        json.dumps(failures, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
except Exception:
    pass  # ファイル書き込み失敗は無視

# ── KNOWN_MISTAKES.md に AUTO-DRAFT 追記 ──────────────────────────────────
# ECC Pipeline に乗せる: auto-codifier.py が次回 GUARD_PATTERN を登録する
if MISTAKES_FILE.exists():
    draft_marker = f"PVQE-P-FAIL-{date_header}-{task_name[:30]}"
    existing = MISTAKES_FILE.read_text(encoding="utf-8")
    if draft_marker not in existing:
        draft = f"""
### {date_header} AUTO-DRAFT: PVQE-P証拠計画未実行 ← Claudeが詳細を記入すること
- **症状**: タスク「{task_name}」の完了報告で証拠計画が未実行だった
- **未実行コマンド**: `{evidence_plan}`
- **根本原因**: TODO — なぜ証拠計画を実行しなかったか
- **正しい解決策**: TODO — 証拠計画を実行してから完了報告する
- **教訓**: 「完了しました」の前に必ず evidence_plan を実行する
<!-- {draft_marker} -->
"""
        try:
            with open(MISTAKES_FILE, "a", encoding="utf-8") as f:
                f.write(draft)
        except Exception:
            pass

sys.exit(2)
