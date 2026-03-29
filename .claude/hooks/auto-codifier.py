#!/usr/bin/env python3
"""
AUTO-CODIFIER — PostToolUse Hook (ECC Pipeline: Error → Codify → Check)
========================================================================
KNOWN_MISTAKES.md が編集されたとき:
  1. `**GUARD_PATTERN**:` フィールドを持つエントリを検出
  2. `.claude/hooks/state/mistake_patterns.json` に自動登録
  3. fact-checker.py が次回から物理ブロックに使用する

使い方:
  KNOWN_MISTAKES.md の新エントリに以下フィールドを追加するだけ:
  - **GUARD_PATTERN**: `{"pattern": "正規表現", "feedback": "ブロックメッセージ", "name": "GUARD_ID"}`

  → 追記後、次のツール呼び出しで自動的に fact-checker.py の検出対象に加わる。

世界標準の根拠:
  Reflexion (Stanford 2023): 失敗記憶 → 次回ブロック
  Google SRE: インシデント → 自動テスト化
  Constitutional AI: ルール → 推論時強制（hook = inference-time）
"""
import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
PATTERNS_FILE = STATE_DIR / "mistake_patterns.json"
MISTAKES_FILE = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"

STATE_DIR.mkdir(parents=True, exist_ok=True)

# stdin から hook データを読む
try:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
edited_file = tool_input.get("file_path", "")

# KNOWN_MISTAKES.md の編集時のみ動作
if not ("KNOWN_MISTAKES" in edited_file or "KNOWN_MISTAKES" in str(edited_file)):
    sys.exit(0)

# ── KNOWN_MISTAKES.md を解析 ──────────────────────────────────────────────────
# 標準フォーマット: **GUARD_PATTERN**: `{...}`
GUARD_PATTERN_RE = re.compile(
    r"\*\*GUARD_PATTERN\*\*\s*:\s*`(\{[^`]+\})`",
    re.MULTILINE
)
# T031修正: 非標準フォーマット (backtick-first): `GUARD_PATTERN: {...}`
# KNOWN_MISTAKES.md L25等で使われていた形式。auto-codifier が検出できなかった sync gap の根本原因。
GUARD_PATTERN_RE_ALT = re.compile(
    r"`GUARD_PATTERN:\s*(\{[^`]+\})`",
    re.MULTILINE
)

if not MISTAKES_FILE.exists():
    sys.exit(0)

mistakes_text = MISTAKES_FILE.read_text(encoding="utf-8")
# 両フォーマットをマージ（重複排除、順序保持）
_seen_raw = set()
found = []
for raw in GUARD_PATTERN_RE.findall(mistakes_text) + GUARD_PATTERN_RE_ALT.findall(mistakes_text):
    if raw not in _seen_raw:
        _seen_raw.add(raw)
        found.append(raw)

if not found:
    sys.exit(0)

# ── 既存の mistake_patterns.json を読み込み ───────────────────────────────────
existing = []
if PATTERNS_FILE.exists():
    try:
        existing = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
    except Exception:
        existing = []

existing_names = {e.get("name", "") for e in existing}
existing_patterns = {e.get("pattern", "") for e in existing}

# ── 新規パターンを追加 ─────────────────────────────────────────────────────────
added = []
for raw_json in found:
    try:
        entry = json.loads(raw_json)
    except json.JSONDecodeError:
        continue

    name = entry.get("name", "")
    pattern = entry.get("pattern", "")
    feedback = entry.get("feedback", "")

    if not name or not pattern or not feedback:
        continue

    # 重複チェック
    if name in existing_names or pattern in existing_patterns:
        continue

    # パターンが有効な正規表現か確認
    try:
        re.compile(pattern)
    except re.error as e:
        print(f"[AUTO-CODIFIER] WARN: Invalid regex in GUARD_PATTERN '{name}': {e}")
        continue

    entry["added_at"] = datetime.now().strftime("%Y-%m-%d")
    entry["source"] = "auto-codifier"
    existing.append(entry)
    existing_names.add(name)
    existing_patterns.add(pattern)
    added.append(name)

if not added:
    # 新規なし（全パターン既登録）
    sys.exit(0)

# ── mistake_patterns.json に書き込み ──────────────────────────────────────────
PATTERNS_FILE.write_text(
    json.dumps(existing, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"[AUTO-CODIFIER] ✅ {len(added)}件の新ガードパターンを登録しました: {', '.join(added)}")
print(f"  保存先: {PATTERNS_FILE}")
print(f"  合計: {len(existing)}件のパターンが fact-checker.py で有効")
