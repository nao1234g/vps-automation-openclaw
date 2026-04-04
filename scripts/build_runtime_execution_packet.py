#!/usr/bin/env python3
"""
scripts/build_runtime_execution_packet.py
-------------------------------------------
RUNTIME_EXECUTION_PACKET.md を生成するスクリプト。

役割: このスクリプトが AI Civilization OS の "compiled artifact" を生成する。
     NORTH_STAR.md + OPERATING_PRINCIPLES.md + IMPLEMENTATION_REF.md +
     現在のタスク + 既知の失敗パターンを一つのパケットに圧縮する。

設計原則:
  - このスクリプトが生成するパケットは「コンパイル済みアーティファクト」であり SSOT ではない
  - 元のファイル (NORTH_STAR.md 等) を直接変更してから再生成する
  - パケットは状態を持たない — 再生成するたびに SSOT から再読み込みする

生成物:
    .claude/RUNTIME_EXECUTION_PACKET.md

使い方:
    python scripts/build_runtime_execution_packet.py
    python scripts/build_runtime_execution_packet.py --check-only  # 鮮度確認のみ

終了コード:
    0 = 生成成功（または check-only で fresh）
    1 = 生成エラー
    2 = check-only で stale または task mismatch
"""

import sys
import os
import json
import argparse
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── パス定義 ──────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
REPO_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", str(_HERE.parent)))

NORTH_STAR_PATH = REPO_ROOT / ".claude" / "rules" / "NORTH_STAR.md"
OPERATING_PRINCIPLES_PATH = REPO_ROOT / ".claude" / "reference" / "OPERATING_PRINCIPLES.md"
IMPLEMENTATION_REF_PATH = REPO_ROOT / ".claude" / "reference" / "IMPLEMENTATION_REF.md"
TASK_LEDGER_PATH = REPO_ROOT / ".claude" / "state" / "task_ledger.json"
ACTIVE_TASK_ID_PATH = REPO_ROOT / ".claude" / "hooks" / "state" / "active_task_id.txt"
FAILURE_MEMORY_PATH = REPO_ROOT / ".claude" / "state" / "failure_memory.json"
MISTAKE_PATTERNS_PATH = REPO_ROOT / ".claude" / "hooks" / "state" / "mistake_patterns.json"

OUTPUT_PATH = REPO_ROOT / ".claude" / "RUNTIME_EXECUTION_PACKET.md"

# 鮮度上限（秒）— 24 時間
FRESHNESS_THRESHOLD_SEC = 24 * 3600

# ── ユーティリティ ────────────────────────────────────────────────────

def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"[PACKET] ⚠️  {path.name} 読み込み失敗: {e}", file=sys.stderr)
        return ""


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        print(f"[PACKET] ⚠️  {path.name} JSON 読み込み失敗: {e}", file=sys.stderr)
        return {}


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except Exception:
        return "????????"


def _extract_between_headers(content: str, start_keyword: str, stop_keywords: list) -> list:
    """start_keyword を含む行から stop_keywords のいずれかを含む行の直前まで返す"""
    lines = content.split("\n")
    capturing = False
    result = []
    for line in lines:
        if start_keyword in line:
            capturing = True
        elif capturing and any(kw in line for kw in stop_keywords) and line.startswith("##"):
            break
        if capturing:
            result.append(line)
    return result


# ── セクション生成 ────────────────────────────────────────────────────

def build_section1_mission_lock() -> str:
    """SECTION 1: MISSION LOCK — NORTH_STAR.md から核心部分を抽出"""
    content = _read_text(NORTH_STAR_PATH)
    if not content:
        return "## SECTION 1: MISSION LOCK\n\n⚠️  NORTH_STAR.md が見つかりません\n"

    lines = content.split("\n")
    out = ["## SECTION 1: MISSION LOCK", ""]

    # 1) 最初のタイトル〜最初の ## セクションまで（ミッション宣言）
    preamble = []
    for line in lines:
        if line.startswith("## ") and preamble:
            break
        preamble.append(line)
    out.extend(preamble[:20])
    out.append("")

    # 2) The Eternal Directives セクション
    eternal = _extract_between_headers(
        content,
        "## The Eternal Directives",
        ["## Nowpatternのモート", "## 予測フライホイール", "## 読者参加型", "## ECC原則"]
    )
    if eternal:
        out.extend(eternal[:30])
        out.append("")

    # 3) PVQE セクション（短く）
    pvqe = _extract_between_headers(
        content,
        "## PVQE",
        ["## Pが正しいとは", "## 毎回この順番", "## 強制の仕組み"]
    )
    if pvqe:
        out.extend(pvqe[:15])
        out.append("")

    # 4) 毎回この順番で動く
    seq = _extract_between_headers(
        content,
        "## 毎回この順番で動く",
        ["## 強制の仕組み", "## 詳細ドキュメント", "## The Yanai"]
    )
    if seq:
        out.extend(seq[:20])
        out.append("")

    sha = _file_sha256(NORTH_STAR_PATH)
    out.append(f"> 原本: `.claude/rules/NORTH_STAR.md` (sha256: `{sha}`)")

    return "\n".join(out)


def build_section2_operating_principles() -> str:
    """SECTION 2: OPERATING PRINCIPLES — 見出し一覧（圧縮ビュー）"""
    content = _read_text(OPERATING_PRINCIPLES_PATH)
    if not content:
        return "## SECTION 2: OPERATING PRINCIPLES\n\n⚠️  OPERATING_PRINCIPLES.md が見つかりません\n"

    lines = content.split("\n")
    headings = [l for l in lines if l.startswith("## ") or l.startswith("### ")]

    out = [
        "## SECTION 2: OPERATING PRINCIPLES（見出し圧縮ビュー）",
        "",
        "詳細は `.claude/reference/OPERATING_PRINCIPLES.md` を参照。以下は構造の概要:",
        "",
    ]
    for h in headings[:50]:
        out.append(h)
    out.append("")

    sha = _file_sha256(OPERATING_PRINCIPLES_PATH)
    out.append(f"> 原本: `.claude/reference/OPERATING_PRINCIPLES.md` (sha256: `{sha}`)")

    return "\n".join(out)


def build_section3_governance_rules() -> str:
    """SECTION 3: GOVERNANCE RULES — IMPLEMENTATION_REF.md から LEVEL / INVARIANTS"""
    content = _read_text(IMPLEMENTATION_REF_PATH)
    if not content:
        return "## SECTION 3: GOVERNANCE RULES\n\n⚠️  IMPLEMENTATION_REF.md が見つかりません\n"

    out = ["## SECTION 3: GOVERNANCE RULES（抜粋）", ""]

    # 統治レベルセクション (LEVEL 1/2/3)
    governance = _extract_between_headers(
        content,
        "## 統治レベル",
        ["## 禁止操作の技術的強制", "## STRUCTURAL CHANGE", "## AIエージェントの役割"]
    )
    if governance:
        out.extend(governance[:80])
        out.append("")

    # INVARIANTS
    invariants = _extract_between_headers(
        content,
        "## 安全原則",
        ["## SYSTEM GOVERNOR の自己診断", "## Nowpattern への接続", "## 優先順位"]
    )
    if invariants:
        out.extend(invariants[:40])
        out.append("")

    # AIエージェントの共通原則 (短く)
    agent_principles = _extract_between_headers(
        content,
        "### AIエージェントの共通原則",
        ["---", "## STRUCTURAL"]
    )
    if agent_principles:
        out.extend(agent_principles[:15])
        out.append("")

    sha = _file_sha256(IMPLEMENTATION_REF_PATH)
    out.append(f"> 原本: `.claude/reference/IMPLEMENTATION_REF.md` (sha256: `{sha}`)")

    return "\n".join(out)


def build_section4_active_task() -> str:
    """SECTION 4: ACTIVE TASK — task_ledger.json + active_task_id.txt から"""
    active_id = ""
    try:
        active_id = ACTIVE_TASK_ID_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    if not active_id:
        return (
            "## SECTION 4: ACTIVE TASK\n\n"
            "⚠️  現在アクティブなタスクなし（`active_task_id.txt` が空）\n\n"
            "新しいタスクを開始するには:\n"
            "1. `.claude/state/task_ledger.json` にタスクを追加\n"
            "2. `.claude/hooks/state/active_task_id.txt` にIDを書く\n"
        )

    ledger = _read_json(TASK_LEDGER_PATH)
    tasks = ledger.get("tasks", []) if isinstance(ledger, dict) else []
    task = next((t for t in tasks if t.get("id") == active_id), None)

    if not task:
        return (
            f"## SECTION 4: ACTIVE TASK\n\n"
            f"⚠️  タスク `{active_id}` が台帳に見つかりません\n"
        )

    out = [
        "## SECTION 4: ACTIVE TASK",
        "",
        f"| フィールド | 値 |",
        f"|------------|-----|",
        f"| **ID** | {task.get('id', '?')} |",
        f"| **タイトル** | {task.get('title', '?')} |",
        f"| **ステータス** | {task.get('status', '?')} |",
        f"| **担当** | {task.get('owner', '?')} |",
        "",
    ]

    objectives = task.get("objectives") or task.get("acceptance_criteria", [])
    if objectives:
        out.append("### 目標 / 完了条件")
        for obj in objectives:
            out.append(f"- {obj}")
        out.append("")

    if task.get("related_failures"):
        out.append("### 関連失敗ID")
        for fid in task["related_failures"]:
            out.append(f"- {fid}")
        out.append("")

    return "\n".join(out)


def build_section5_known_mistakes() -> str:
    """SECTION 5: RELEVANT KNOWN MISTAKES — failure_memory.json + mistake_patterns.json"""
    failure_data = _read_json(FAILURE_MEMORY_PATH)
    failures = failure_data.get("failures", []) if isinstance(failure_data, dict) else []

    patterns_data = _read_json(MISTAKE_PATTERNS_PATH)
    patterns = patterns_data.get("patterns", []) if isinstance(patterns_data, dict) else []

    out = ["## SECTION 5: RELEVANT KNOWN MISTAKES", ""]

    # 未解決の失敗
    open_f = [f for f in failures if f.get("resolved_status") not in ("fixed", "wont_fix")]
    if open_f:
        out.append("### ⚠️ 未解決の失敗（優先的に確認）")
        for f in open_f:
            out.append(f"- **{f.get('failure_id', '?')}** `{f.get('category', '?')}`")
            out.append(f"  - 症状: {f.get('symptom', '?')}")
            out.append(f"  - 防止: {f.get('prevention_rule', '?')}")
        out.append("")

    # 解決済みの失敗（防止ルール参照用）
    fixed_f = [f for f in failures if f.get("resolved_status") == "fixed"]
    if fixed_f:
        out.append("### ✅ 解決済み失敗（防止ルール参照）")
        for f in fixed_f:
            out.append(
                f"- **{f.get('failure_id', '?')}** `{f.get('category', '?')}`: "
                f"{f.get('prevention_rule', 'ルールなし')}"
            )
        out.append("")

    # fact-checker が使うパターン（先頭10件）
    if patterns:
        out.append(f"### 🛡️ アクティブブロックパターン（fact-checker.py、計 {len(patterns)} 件）")
        for p in patterns[:10]:
            pid = p.get("id", "?")
            name = p.get("name", "?")
            pat = str(p.get("pattern", "?"))[:60]
            out.append(f"- `{pid}` {name}: `{pat}...`")
        if len(patterns) > 10:
            out.append(f"  _...他 {len(patterns) - 10} パターン（{MISTAKE_PATTERNS_PATH.name} 参照）_")
        out.append("")

    return "\n".join(out)


def build_section6_mandatory_close_conditions() -> str:
    """SECTION 6: MANDATORY CLOSE CONDITIONS"""
    out = [
        "## SECTION 6: MANDATORY CLOSE CONDITIONS",
        "",
        "タスクを閉じる前に **すべての条件** を満たすこと:",
        "",
        "### 必須ステップ",
        "1. `python scripts/doctor.py` を実行し、**0 FAIL** を確認する",
        "2. `/tmp/notes.json` に completion_notes を作成する（テンプレート ↓）",
        "3. `python scripts/task/close_task.py {TASK_ID} --notes-file /tmp/notes.json` を実行する",
        "",
        "### completion_notes テンプレート（dict 必須）",
        "",
        "```json",
        "{",
        '  "what_changed": "何を変えたか（技術的説明、10文字以上）",',
        '  "root_cause":   "なぜ変更が必要だったか（根本原因、10文字以上）",',
        '  "memory_updates": ["変更ファイル1", "変更ファイル2"],',
        '  "tests_run":    "python scripts/doctor.py → XX/XX PASS",',
        '  "remaining_risks": "残課題（なければ \'無し\'）"',
        "}",
        "```",
        "",
        "### 禁止事項（close_task.py がブロック）",
        "- ❌ task_ledger.json を Python で直接編集して `done` にする",
        "- ❌ `completion_notes` に `[未記入]`, `[自動記録]`, `TODO`, `FIXME` を含める",
        "- ❌ `doctor.py` が FAIL のままタスクを閉じる",
        "- ❌ `close_task.py` をバイパスする",
        "",
        "> ヘルプ: `python scripts/task/close_task.py --help`",
    ]
    return "\n".join(out)


def build_section7_packet_metadata(sources: dict) -> str:
    """SECTION 7: PACKET METADATA"""
    now_iso = datetime.now(timezone.utc).isoformat()

    active_id = ""
    try:
        active_id = ACTIVE_TASK_ID_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    out = [
        "## SECTION 7: PACKET METADATA",
        "",
        f"- **generated_at**: {now_iso}",
        f"- **active_task_id**: {active_id or '(none)'}",
        f"- **generator**: `scripts/build_runtime_execution_packet.py`",
        f"- **packet_version**: 1.0",
        f"- **freshness_threshold**: {FRESHNESS_THRESHOLD_SEC // 3600}h",
        "",
        "### ソースファイル チェックサム",
        "",
        "| ファイル | sha256[:12] | 存在 |",
        "|----------|-------------|------|",
    ]

    for name, path in sources.items():
        exists = "✅" if path.exists() else "❌"
        sha = _file_sha256(path) if path.exists() else "NOT_FOUND"
        out.append(f"| `{name}` | `{sha}` | {exists} |")

    out.append("")
    out.append("### doctor.py がチェックする条件")
    out.append(f"- パケットが `{FRESHNESS_THRESHOLD_SEC // 3600}` 時間以上古い → **WARN**")
    out.append("- パケットの `active_task_id` が `active_task_id.txt` と異なる → **FAIL**")
    out.append("- SSOTファイルが存在しない → **FAIL**")

    return "\n".join(out)


# ── check-only モード ─────────────────────────────────────────────────

def check_freshness() -> int:
    """パケットの鮮度をチェック。0=fresh, 2=stale/mismatch"""
    if not OUTPUT_PATH.exists():
        print("[PACKET] パケットが存在しません", file=sys.stderr)
        return 2

    content = _read_text(OUTPUT_PATH)

    # generated_at を抽出
    match = re.search(r"\*\*generated_at\*\*:\s*(.+)", content)
    if not match:
        print("[PACKET] generated_at が見つかりません", file=sys.stderr)
        return 2

    try:
        gen_at = datetime.fromisoformat(match.group(1).strip())
        now = datetime.now(timezone.utc)
        age_sec = (now - gen_at).total_seconds()
        if age_sec > FRESHNESS_THRESHOLD_SEC:
            print(f"[PACKET] パケットが古すぎます: {age_sec / 3600:.1f}h > {FRESHNESS_THRESHOLD_SEC // 3600}h")
            return 2
    except Exception as e:
        print(f"[PACKET] 日時パース失敗: {e}", file=sys.stderr)
        return 2

    # active_task_id の一致確認
    current_id = ""
    try:
        current_id = ACTIVE_TASK_ID_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    packet_id_match = re.search(r"\*\*active_task_id\*\*:\s*(.+)", content)
    packet_id = packet_id_match.group(1).strip() if packet_id_match else ""

    if packet_id != current_id:
        print(
            f"[PACKET] タスクIDミスマッチ: packet='{packet_id}' vs current='{current_id}'"
        )
        return 2

    print(f"[PACKET] ✅ fresh  age={age_sec / 3600:.1f}h  task={current_id or '(none)'}")
    return 0


# ── メイン ────────────────────────────────────────────────────────────

def build_packet() -> int:
    """パケットを生成して OUTPUT_PATH に書き出す。0=成功, 1=エラー"""
    sources = {
        "NORTH_STAR.md": NORTH_STAR_PATH,
        "OPERATING_PRINCIPLES.md": OPERATING_PRINCIPLES_PATH,
        "IMPLEMENTATION_REF.md": IMPLEMENTATION_REF_PATH,
        "task_ledger.json": TASK_LEDGER_PATH,
        "failure_memory.json": FAILURE_MEMORY_PATH,
        "mistake_patterns.json": MISTAKE_PATTERNS_PATH,
    }

    missing = [name for name, path in sources.items() if not path.exists()]
    if missing:
        print(f"[PACKET] ⚠️  ソースファイルが見つかりません: {missing}", file=sys.stderr)
        # 欠落ファイルがあっても部分的なパケットを生成する（継続）

    now_iso = datetime.now(timezone.utc).isoformat()
    active_id = ""
    try:
        active_id = ACTIVE_TASK_ID_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    sections = [
        "# RUNTIME EXECUTION PACKET",
        "",
        "> **WARNING**: このファイルは自動生成された「コンパイル済みアーティファクト」です。",
        "> 直接編集しないでください。ソースSSOTを変更してから `python scripts/build_runtime_execution_packet.py` で再生成してください。",
        ">",
        f"> generated_at: {now_iso}",
        f"> active_task: {active_id or '(none)'}",
        "",
        "---",
        "",
        build_section1_mission_lock(),
        "",
        "---",
        "",
        build_section2_operating_principles(),
        "",
        "---",
        "",
        build_section3_governance_rules(),
        "",
        "---",
        "",
        build_section4_active_task(),
        "",
        "---",
        "",
        build_section5_known_mistakes(),
        "",
        "---",
        "",
        build_section6_mandatory_close_conditions(),
        "",
        "---",
        "",
        build_section7_packet_metadata(sources),
    ]

    packet_content = "\n".join(sections)

    try:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(packet_content, encoding="utf-8")
        size_kb = len(packet_content.encode("utf-8")) / 1024
        print(f"[PACKET] ✅ 生成完了: {OUTPUT_PATH.name}")
        print(f"  サイズ: {size_kb:.1f} KB | タスク: {active_id or '(none)'} | {now_iso[:19]}Z")
        return 0
    except Exception as e:
        print(f"[PACKET] ❌ 書き込みエラー: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="RUNTIME_EXECUTION_PACKET.md を生成する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="パケットの鮮度確認のみ（生成しない）。0=fresh, 2=stale/mismatch",
    )
    args = parser.parse_args()

    if args.check_only:
        sys.exit(check_freshness())
    else:
        sys.exit(build_packet())


if __name__ == "__main__":
    main()
