#!/usr/bin/env python3
"""run_failure_regressions.py

failure_memory.json に対応する regression test を全て実行し、
結果を failure_regression_index.json に記録する。

Exit codes:
  0 — 全テスト PASS / SKIP
  1 — medium / low severity の FAIL が 1 件以上
  2 — critical / high severity の FAIL が 1 件以上

Usage:
    python scripts/eval/run_failure_regressions.py
    python scripts/eval/run_failure_regressions.py --verbose
    python scripts/eval/run_failure_regressions.py --failure-id F001
    python scripts/eval/run_failure_regressions.py --no-update  # インデックス更新しない
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR",
    os.path.abspath(os.path.join(_HERE, "..", ".."))
)

_FAILURE_MEMORY_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "failure_memory.json")
_REGRESSION_INDEX_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "failure_regression_index.json")
_TEST_DIR = os.path.join(_PROJECT_ROOT, "scripts", "eval", "tests", "failure_regressions")

# severity → exit code の優先度（高いほど重大）
_SEVERITY_PRIORITY = {"critical": 2, "high": 2, "medium": 1, "low": 1}


def _load_failure_memory() -> dict:
    if not os.path.exists(_FAILURE_MEMORY_PATH):
        print(f"[WARN] failure_memory.json が見つかりません: {_FAILURE_MEMORY_PATH}", file=sys.stderr)
        return {"failures": []}
    with open(_FAILURE_MEMORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_index() -> dict:
    if os.path.exists(_REGRESSION_INDEX_PATH):
        with open(_REGRESSION_INDEX_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "_schema_version": "1.0",
        "_description": "failure_memory.json の各失敗に対応する regression test の管理インデックス",
        "generated_by": "scripts/eval/generate_regression_from_failure.py",
        "failures": []
    }


def _save_index(data: dict) -> None:
    os.makedirs(os.path.dirname(_REGRESSION_INDEX_PATH), exist_ok=True)
    with open(_REGRESSION_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_severity(failure_id: str, memory_data: dict) -> str:
    """failure_memory.json から severity を取得。見つからなければ 'low'。"""
    for f in memory_data.get("failures", []):
        if f.get("failure_id") == failure_id:
            return f.get("severity", "low")
    return "low"


def _discover_tests(filter_id: str = None) -> list:
    """test_F*.py ファイルを探してリストアップする。"""
    pattern = os.path.join(_TEST_DIR, "test_F*.py")
    files = sorted(glob.glob(pattern))
    if filter_id:
        files = [f for f in files if f.endswith(f"test_{filter_id}.py")]
    return files


def _run_test(test_path: str, verbose: bool = False) -> str:
    """テストを実行して 'PASS' / 'FAIL' / 'SKIP' / 'ERROR' を返す。"""
    try:
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if verbose and (stdout or stderr):
            if stdout:
                print(f"    stdout: {stdout}")
            if stderr:
                print(f"    stderr: {stderr}")

        if result.returncode == 0:
            # SKIP を明示的に判定（標準出力に [SKIP] が含まれる場合）
            if "[SKIP]" in stdout:
                return "SKIP"
            return "PASS"
        else:
            return "FAIL"
    except subprocess.TimeoutExpired:
        return "ERROR"
    except Exception as e:
        print(f"    [ERROR] テスト実行例外: {e}", file=sys.stderr)
        return "ERROR"


def _failure_id_from_path(test_path: str) -> str:
    """test_F001.py → F001"""
    basename = os.path.basename(test_path)
    return basename.replace("test_", "").replace(".py", "")


def _update_index_entry(index: dict, failure_id: str, result: str, test_path: str) -> None:
    """インデックスの last_run / last_result を更新する。"""
    now = datetime.now(timezone.utc).isoformat()
    rel_path = os.path.relpath(test_path, _PROJECT_ROOT).replace("\\", "/")

    existing = next((e for e in index["failures"] if e["failure_id"] == failure_id), None)
    if existing:
        existing["last_run"] = now
        existing["last_result"] = result
        existing["test_file"] = rel_path
    else:
        # インデックスにないテストも記録する
        index["failures"].append({
            "failure_id": failure_id,
            "test_file": rel_path,
            "generated_at": now,
            "last_run": now,
            "last_result": result,
            "severity": "unknown",
            "resolved_status": "open",
        })


def main() -> None:
    parser = argparse.ArgumentParser(description="Failure regression tests を実行する")
    parser.add_argument("--verbose", "-v", action="store_true", help="テスト出力を表示")
    parser.add_argument("--failure-id", help="特定の failure_id のみ実行（例: F001）")
    parser.add_argument("--no-update", action="store_true", help="インデックスを更新しない")
    args = parser.parse_args()

    memory_data = _load_failure_memory()
    index = _load_index()

    tests = _discover_tests(filter_id=args.failure_id)

    if not tests:
        if args.failure_id:
            print(f"[WARN] test_{args.failure_id}.py が見つかりません: {_TEST_DIR}")
        else:
            print(f"[WARN] テストファイルが見つかりません: {_TEST_DIR}")
        sys.exit(0)

    print(f"[REGRESSION] {len(tests)} 件のテストを実行します")
    print()

    results = {}  # failure_id → result
    max_exit_code = 0

    for test_path in tests:
        failure_id = _failure_id_from_path(test_path)
        severity = _get_severity(failure_id, memory_data)

        print(f"  [{failure_id}] severity={severity} ... ", end="", flush=True)
        result = _run_test(test_path, verbose=args.verbose)
        print(result)

        results[failure_id] = result

        if result == "FAIL":
            exit_code = _SEVERITY_PRIORITY.get(severity, 1)
            max_exit_code = max(max_exit_code, exit_code)

        if not args.no_update:
            _update_index_entry(index, failure_id, result, test_path)

    # 集計
    print()
    total = len(results)
    pass_count = sum(1 for r in results.values() if r == "PASS")
    skip_count = sum(1 for r in results.values() if r == "SKIP")
    fail_count = sum(1 for r in results.values() if r == "FAIL")
    error_count = sum(1 for r in results.values() if r == "ERROR")

    print(f"[REGRESSION] 結果: {total}件 / PASS:{pass_count} SKIP:{skip_count} FAIL:{fail_count} ERROR:{error_count}")

    if fail_count > 0:
        print(f"[REGRESSION] FAIL 一覧:")
        for fid, r in results.items():
            if r == "FAIL":
                sev = _get_severity(fid, memory_data)
                print(f"  ❌ {fid} (severity={sev})")

    if not args.no_update:
        _save_index(index)
        print(f"[REGRESSION] インデックス更新: {os.path.relpath(_REGRESSION_INDEX_PATH, _PROJECT_ROOT)}")

    if max_exit_code == 2:
        print("[REGRESSION] ⛔ critical/high severity の FAIL あり → exit 2")
    elif max_exit_code == 1:
        print("[REGRESSION] ⚠️  medium/low severity の FAIL あり → exit 1")
    else:
        print("[REGRESSION] ✅ 全テスト PASS/SKIP → exit 0")

    sys.exit(max_exit_code)


if __name__ == "__main__":
    main()
