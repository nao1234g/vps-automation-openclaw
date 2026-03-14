"""
scripts/guard/release_gate.py
デプロイ前ゲート — 未解決の critical/high 失敗がある場合はブロックする

動作:
  1. .claude/state/failure_memory.json を読む
  2. resolved_status が "open" または "regressed" の失敗を抽出
  3. severity が "critical" または "high" の未解決失敗があれば exit 2（ブロック）
  4. 警告のみの失敗 ("medium"/"low") はレポートして exit 0

使い方:
  # VPSへのデプロイ前に実行
  python scripts/guard/release_gate.py
  python scripts/guard/release_gate.py --strict  # medium も含めてブロック
  python scripts/guard/release_gate.py --report  # 全未解決をレポートして exit 0

PreToolUse (Bash) での使用:
  VPS SSH/SCP コマンドの前に settings.local.json の PreToolUse Bash に追加:
  python \"$CLAUDE_PROJECT_DIR/scripts/guard/release_gate.py\"

終了コード:
  0 = リリース可能
  1 = 警告あり（medium/low のみ）
  2 = ブロック（critical または high の未解決失敗あり）

Geneenの原則: 「ノーサプライズ原則。本番がサイレントに壊れることは許さない」
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── VPS ターゲット ──────────────────────────────────────────────────────────
_VPS_IP = "163.44.124.123"
_VPS_HOSTNAME = "nowpattern"  # 追加キーワード（オプション）

# ── night_mode チェック ────────────────────────────────────────────────────
_HERE_GATE = os.path.dirname(os.path.abspath(__file__))
_NIGHT_MODE_FLAG = os.path.join(
    os.environ.get("CLAUDE_PROJECT_DIR",
                   os.path.abspath(os.path.join(_HERE_GATE, "..", ".."))),
    ".claude", "hooks", "state", "night_mode.flag"
)


def _is_night_mode() -> bool:
    return os.path.exists(_NIGHT_MODE_FLAG)


def _is_vps_command(cmd: str) -> bool:
    """stdin から読んだ Bash コマンドが VPS SSH/SCP かどうか判定する"""
    if not cmd:
        return False
    has_ssh_scp = ("ssh " in cmd or "scp " in cmd or "\nssh " in cmd or "\nscp " in cmd)
    has_vps = (_VPS_IP in cmd or _VPS_HOSTNAME in cmd)
    return has_ssh_scp and has_vps


def _read_bash_command_from_stdin() -> str:
    """Claude Code が PreToolUse で stdin に渡す JSON から command を取得する"""
    try:
        if sys.stdin.isatty():
            return ""
        raw = sys.stdin.read()
        if not raw.strip():
            return ""
        data = json.loads(raw)
        # tool_input.command が Bash の実行コマンド
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""

# ── パス定義 ──────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR",
    os.path.abspath(os.path.join(_HERE, "..", ".."))
)
_FAILURE_MEMORY_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "failure_memory.json")
_GATE_LOG_PATH = os.path.join(_PROJECT_ROOT, ".claude", "hooks", "state", "release_gate.log")

# ブロック対象の severity
BLOCKING_SEVERITIES = {"critical", "high"}
WARNING_SEVERITIES = {"medium", "low"}

# ブロック対象の resolved_status
UNRESOLVED_STATUSES = {"open", "regressed"}


# ── 失敗メモリ読み込み ────────────────────────────────────────────────

def _load_failures() -> list:
    if not os.path.exists(_FAILURE_MEMORY_PATH):
        return []
    try:
        data = json.load(open(_FAILURE_MEMORY_PATH, encoding="utf-8"))
        return data.get("failures", [])
    except Exception as e:
        print(f"[RELEASE GATE] failure_memory.json 読み込みエラー: {e}", file=sys.stderr)
        return []


def _get_unresolved(failures: list, strict: bool = False) -> tuple:
    """
    未解決の失敗を severity 別に分類する

    Returns:
        (blocking: list, warnings: list)
        blocking = critical/high の未解決
        warnings = medium/low の未解決（strict=True なら blocking に含める）
    """
    blocking = []
    warnings = []

    for f in failures:
        status = f.get("resolved_status", "open")
        severity = f.get("severity", "medium").lower()

        if status not in UNRESOLVED_STATUSES:
            continue

        if severity in BLOCKING_SEVERITIES:
            blocking.append(f)
        elif severity in WARNING_SEVERITIES:
            if strict:
                blocking.append(f)
            else:
                warnings.append(f)

    return blocking, warnings


def _format_failure(f: dict) -> str:
    """失敗エントリを人間が読める形式に整形"""
    fid = f.get("failure_id", "???")
    severity = f.get("severity", "?").upper()
    status = f.get("resolved_status", "?")
    symptom = f.get("symptom", "")[:80]
    last_seen = f.get("last_seen", "")[:10]
    recurrence = f.get("recurrence_count", 0)
    return (
        f"  [{fid}] [{severity}] [{status}] last={last_seen} recurrence={recurrence}\n"
        f"    症状: {symptom}"
    )


def _log_gate_result(result: str, blocking_count: int, warning_count: int):
    """ゲート結果をログに記録する"""
    try:
        os.makedirs(os.path.dirname(_GATE_LOG_PATH), exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(_GATE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                f"{timestamp} result={result} blocking={blocking_count} warnings={warning_count}\n"
            )
        # ログローテーション（200行上限）
        with open(_GATE_LOG_PATH, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 200:
            with open(_GATE_LOG_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines[-150:])
    except Exception:
        pass


# ── メイン ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Release Gate — デプロイ前 failure_memory チェック")
    parser.add_argument("--strict", action="store_true",
                        help="medium/low の未解決もブロック対象にする")
    parser.add_argument("--report", action="store_true",
                        help="レポートのみ出力（always exit 0）")
    parser.add_argument("--summary", action="store_true",
                        help="簡潔なサマリーのみ出力")
    parser.add_argument("--ssh-only", action="store_true",
                        help="VPS SSH/SCP コマンドのみゲートを実行（それ以外はサイレント exit 0）")
    args = parser.parse_args()

    # ── --ssh-only モード: VPS コマンド以外はスキップ ──────────────────────
    if args.ssh_only:
        # night_mode.flag があれば即スキップ
        if _is_night_mode():
            sys.exit(0)
        bash_cmd = _read_bash_command_from_stdin()
        if not _is_vps_command(bash_cmd):
            sys.exit(0)
        # VPS コマンド確認 → blocking failures のみチェック（PASS=サイレント）
        failures = _load_failures()
        blocking, warnings = _get_unresolved(failures, strict=args.strict)
        if not blocking:
            # PASS: 音なしで exit 0
            sys.exit(0)
        # BLOCKED: エラーだけ出力
        print(f"\n❌ RELEASE GATE BLOCKED — VPS SSH/SCP をブロック")
        print(f"  {len(blocking)}件の critical/high 失敗が未解決です:")
        for f in blocking:
            print(_format_failure(f))
        _log_gate_result("BLOCKED", len(blocking), len(warnings))
        sys.exit(2)

    failures = _load_failures()
    blocking, warnings = _get_unresolved(failures, strict=args.strict)
    total_failures = len(failures)
    resolved_count = total_failures - len(blocking) - len(warnings)

    # サマリー出力
    print(f"\n=== 🔍 Release Gate ===")
    print(f"  全失敗数: {total_failures}")
    print(f"  解決済み: {resolved_count}")
    print(f"  ブロッキング未解決 (critical/high): {len(blocking)}")
    print(f"  警告のみ未解決 (medium/low): {len(warnings)}")

    if args.summary:
        if blocking:
            print(f"  ❌ BLOCKED — {len(blocking)} critical/high failures unresolved")
        elif warnings:
            print(f"  ⚠️ WARN — {len(warnings)} medium/low failures unresolved")
        else:
            print(f"  ✅ PASS — No blocking failures")
        _log_gate_result(
            "PASS" if not blocking else "BLOCKED",
            len(blocking), len(warnings)
        )
        sys.exit(0 if (not blocking or args.report) else 2)

    # 詳細出力
    if blocking:
        print(f"\n❌ ブロッキング失敗 ({len(blocking)}件) — リリース不可:")
        for f in blocking:
            print(_format_failure(f))
            prevention = f.get("prevention_rule", "")
            if prevention and not prevention.startswith("[未記入"):
                print(f"    防止策: {prevention[:100]}")

    if warnings:
        print(f"\n⚠️ 警告のみ失敗 ({len(warnings)}件) — リリース可（推奨: 解決後にデプロイ）:")
        for f in warnings:
            print(_format_failure(f))

    if not blocking and not warnings:
        print("\n✅ 全失敗が解決済みです。リリース可能です。")

    # ゲート判定
    if blocking and not args.report:
        print(
            f"\n❌ RELEASE BLOCKED\n"
            f"  {len(blocking)}件の critical/high 失敗が未解決です。\n"
            f"  failure_memory.json の resolved_status を 'fixed' に更新してからリリースしてください。\n"
            f"  ファイル: {_FAILURE_MEMORY_PATH}"
        )
        _log_gate_result("BLOCKED", len(blocking), len(warnings))
        sys.exit(2)
    elif warnings and not args.report:
        print(f"\n⚠️ RELEASE ALLOWED WITH WARNINGS")
        _log_gate_result("WARN", len(blocking), len(warnings))
        sys.exit(1)
    else:
        print(f"\n✅ RELEASE GATE: PASS")
        _log_gate_result("PASS", len(blocking), len(warnings))
        sys.exit(0)


if __name__ == "__main__":
    main()
