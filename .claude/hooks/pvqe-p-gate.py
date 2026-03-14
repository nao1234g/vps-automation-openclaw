#!/usr/bin/env python3
"""
PVQE-P GATE — PreToolUse Hook
================================
実装の前にPVQE-P定義（正しい方向の定義 + 完了条件 + 証拠計画）を強制する。

設計根拠（世界標準）:
  Reflexion (Stanford 2023): "生成前に受容基準を明示すると精度3倍向上"
  BDD (Behavior-Driven Development): Given/When/Then を先に書く
  Google SRE: インシデント対応前に「完了の定義」を書く
  NASA Mission Rules: go/no-go criteria をチェックリストで管理

動作:
  1. Edit/Write の前に実行（pvqe_p.json 自体の書き込みは除外）
  2. intent_confirmed.flag が存在する（ユーザーが指示を承認した）
  3. pvqe_p.json が存在しない or intent_confirmed.flag より古い → exit(2) でブロック
  4. Claude は pvqe_p.json を Write ツールで作成 → 解放

pvqe_p.json フォーマット（Writeで作成する）:
{
  "task": "タスクの一行説明（例: prediction_page_builder.pyにFileLockを追加する）",
  "pvqe_p": "この文脈でのP（正しい方向）の定義（例: Oracle化に貢献し、既知ミスを繰り返さない）",
  "success_looks_like": "完了時に何が目視/コマンドで確認できるか（具体的）",
  "evidence_plan": "完了後に実行する検証コマンド（SSH/Python/curlで実行可能なもの）",
  "anti_patterns": ["やってはいけないこと1", "やってはいけないこと2"],
  "created_at": "ISO datetime"
}
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
INTENT_CONFIRMED_FLAG = STATE_DIR / "intent_confirmed.flag"

# NIGHT MODE: 自律運転中はPVQE-P要件をバイパス
NIGHT_MODE_FLAG = STATE_DIR / "night_mode.flag"
if NIGHT_MODE_FLAG.exists():
    sys.exit(0)

# pvqe_p.json の有効期限（この時間を超えたら再定義が必要）
PVQE_P_MAX_AGE_SEC = 7200  # 2時間

# ── stdin 読み込み ────────────────────────────────────────────────────────
try:
    raw = sys.stdin.read().strip()
    data = json.loads(raw) if raw else {}
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# Edit / Write のみ対象（Read, Bash, WebSearch は対象外）
if tool_name not in ("Edit", "Write"):
    sys.exit(0)

file_path = str(tool_input.get("file_path", tool_input.get("path", "")))

# ── 除外パス（これらへの書き込みはPVQE-P不要） ───────────────────────────
EXEMPT_PATHS = re.compile(
    r"(pvqe_p\.json|"                       # pvqe_p.json 自体
    r"KNOWN_MISTAKES|AGENT_WISDOM|"          # 記録・知識系
    r"CLAUDE\.md|NORTH_STAR|FLASH_CARDS|"   # 設定・ルール系
    r"SCORECARD|session\.json|"              # 状態ファイル
    r"[/\\]docs[/\\]|"                       # docs ディレクトリ
    r"[/\\]memory[/\\]|"                     # memory ディレクトリ
    r"\.claude[/\\]rules[/\\]|"              # rules ディレクトリ
    r"hooks[/\\]state[/\\]|"                 # hooks/state ディレクトリ
    r"hooks[/\\].*\.py|"                     # hookファイル自体
    r"settings.*\.json|"                     # 設定ファイル
    r"\.md$|\.txt$|\.yml$|\.yaml$|\.sh$|"   # 設定・ドキュメント系
    r"task_goal|pvqe|prediction_db)",        # タスク管理系
    re.IGNORECASE
)

if EXEMPT_PATHS.search(file_path):
    sys.exit(0)

# ── intent_confirmed.flag チェック ─────────────────────────────────────────
# フラグがない = まだ意図確認フェーズ → pvqe_p不要（intent-confirm.py が担当）
if not INTENT_CONFIRMED_FLAG.exists():
    sys.exit(0)

# ── pvqe_p.json の鮮度チェック ─────────────────────────────────────────────
confirmed_at = INTENT_CONFIRMED_FLAG.stat().st_mtime if INTENT_CONFIRMED_FLAG.exists() else 0

if PVQE_P_FILE.exists():
    pvqe_mtime = PVQE_P_FILE.stat().st_mtime
    pvqe_age = time.time() - pvqe_mtime

    # pvqe_p.json が intent_confirmed.flag より新しい（このタスク用に書かれた）
    # かつ 有効期限内
    if pvqe_mtime >= (confirmed_at - 30) and pvqe_age < PVQE_P_MAX_AGE_SEC:
        try:
            pdata = json.loads(PVQE_P_FILE.read_text(encoding="utf-8"))
            # 必須フィールドが揃っているか確認
            if pdata.get("task") and pdata.get("evidence_plan"):
                sys.exit(0)  # ✅ 有効なpvqe_p.json → 通過
        except Exception:
            pass  # JSONパース失敗 → 再定義が必要

# ── ブロック: pvqe_p.json がない or 期限切れ ───────────────────────────────
print(
    "\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🧭 [PVQE-P GATE] 実装の前にPVQE-P定義が必要です\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "\n"
    "  設計根拠: Reflexion論文「受容基準を先に書くと精度3倍向上」\n"
    "\n"
    "  ✅ 次にすること:\n"
    "     Write ツールで以下のファイルを作成してください:\n"
    f"     {PVQE_P_FILE}\n"
    "\n"
    "  📋 テンプレート（コピペして使う）:\n"
    "  {\n"
    '    "task": "（タスクを一行で説明）",\n'
    '    "pvqe_p": "この実装が正しい方向かを確認: （理由）",\n'
    '    "success_looks_like": "完了時の具体的な確認方法",\n'
    '    "evidence_plan": "（実行可能な検証コマンド: ssh/python/curlなど）",\n'
    '    "anti_patterns": ["やってはいけないこと1", "やってはいけないこと2"],\n'
    f'    "created_at": "{datetime.now().isoformat()}"\n'
    "  }\n"
    "\n"
    "  ⚡ 記入例 (FileLock実装の場合):\n"
    '    "task": "prediction_page_builder.pyにfcntlロックを追加する",\n'
    '    "evidence_plan": "ssh root@163.44.124.123 \'python3 /opt/.../pred_page_builder.py --dry-run\'",\n'
    '    "anti_patterns": ["UIレイアウトを変更しない", "fcntlをWindowsで直接importしない"]\n'
    "\n"
    "  このブロックは pvqe_p.json が作成されると自動解除されます。\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
)
sys.exit(2)
