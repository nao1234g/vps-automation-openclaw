#!/usr/bin/env python
"""
build_canonical_outputs.py — canonical policy の生成物ビルド・VPS同期・整合性検証
使い方: python scripts/build_canonical_outputs.py [--dry-run] [--vps-sync] [--verify] [--json]

  --dry-run    実際の書き込み/同期は行わず、計画を表示するだけ
  --vps-sync   VPS への同期（SSH 必要）
  --verify     ビルド後に doctor.py + audit_retired_refs.py を実行して整合性確認
  --json       JSON 形式で出力

終了コード:
  0 = 全てのタスク成功
  1 = 一部スキップ / 警告あり
  2 = エラーあり
"""

import os
import sys
import json
import shutil

# Windows CP932 環境で絵文字・日本語を含む出力が壊れないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import hashlib
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent
VPS_HOST = "root@163.44.124.123"

# ──────────────────────────────────────────────
# ビルドタスク定義
# ──────────────────────────────────────────────

BUILD_TASKS = [
    {
        "id": "validate_canonical_yamls",
        "description": "policy/canonical/ の YAML 5本が全て存在・読み込み可能か確認",
        "type": "validate",
        "targets": [
            "policy/canonical/runtime_truth_registry.yaml",
            "policy/canonical/retirement_registry.yaml",
            "policy/canonical/doctrine_index.yaml",
            "policy/canonical/cli_permissions_policy.yaml",
            "policy/canonical/generated_artifacts.yaml",
        ],
    },
    {
        "id": "sync_rules_to_vps",
        "description": ".claude/rules/ の canonical ルールファイルを VPS /opt/shared/rules/ に同期",
        "type": "vps_sync",
        "local_files": [
            ".claude/rules/NORTH_STAR.md",
            ".claude/rules/OPERATING_PRINCIPLES.md",
            ".claude/rules/IMPLEMENTATION_REF.md",
        ],
        "remote_dir": "/opt/shared/rules/",
        "requires_vps": True,
    },
    {
        "id": "sync_policy_to_vps",
        "description": "policy/canonical/ を VPS /opt/shared/policy/ に同期",
        "type": "vps_sync",
        "local_files": [
            "policy/canonical/runtime_truth_registry.yaml",
            "policy/canonical/retirement_registry.yaml",
            "policy/canonical/doctrine_index.yaml",
            "policy/canonical/cli_permissions_policy.yaml",
            "policy/canonical/generated_artifacts.yaml",
        ],
        "remote_dir": "/opt/shared/policy/",
        "requires_vps": True,
    },
    {
        "id": "sync_scripts_to_vps",
        "description": "doctor.py / audit_retired_refs.py を VPS /opt/shared/scripts/ に同期",
        "type": "vps_sync",
        "local_files": [
            "scripts/doctor.py",
            "scripts/audit_retired_refs.py",
            "scripts/build_canonical_outputs.py",
        ],
        "remote_dir": "/opt/shared/scripts/",
        "requires_vps": True,
    },
    {
        "id": "ensure_vps_dirs",
        "description": "VPS 上の必要ディレクトリを作成（存在しない場合）",
        "type": "vps_mkdir",
        "dirs": [
            "/opt/shared/rules",
            "/opt/shared/policy",
            "/opt/shared/policy/canonical",
        ],
        "requires_vps": True,
    },
    {
        "id": "generate_file_manifest",
        "description": "canonical ファイルの SHA256 マニフェストを生成（整合性証明）",
        "type": "generate_manifest",
        "output": ".claude/hooks/state/canonical_manifest.json",
        "source_files": [
            "policy/canonical/runtime_truth_registry.yaml",
            "policy/canonical/retirement_registry.yaml",
            "policy/canonical/doctrine_index.yaml",
            "policy/canonical/cli_permissions_policy.yaml",
            "policy/canonical/generated_artifacts.yaml",
            ".claude/rules/NORTH_STAR.md",
            ".claude/settings.json",
        ],
    },
]


# ──────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────

def c(color, text):
    colors = {
        "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
        "blue": "\033[94m", "reset": "\033[0m", "bold": "\033[1m", "cyan": "\033[96m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def run_ssh(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", VPS_HOST, cmd],
        capture_output=True, text=True, timeout=timeout, errors="replace"
    )
    return result.returncode, result.stdout, result.stderr


def scp_file(local_path: Path, remote_path: str, dry_run: bool = False) -> bool:
    if dry_run:
        print(f"    [DRY-RUN] scp {local_path} {VPS_HOST}:{remote_path}")
        return True
    try:
        result = subprocess.run(
            ["scp", "-o", "ConnectTimeout=5", str(local_path), f"{VPS_HOST}:{remote_path}"],
            capture_output=True, text=True, timeout=30, errors="replace"
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    SCP error: {e}")
        return False


# ──────────────────────────────────────────────
# タスク実行
# ──────────────────────────────────────────────

def task_validate_yamls(task: dict, dry_run: bool) -> tuple[bool, str]:
    """YAML ファイルの存在確認"""
    missing = []
    for rel in task["targets"]:
        p = REPO_ROOT / rel
        if not p.exists():
            missing.append(rel)
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, f"{len(task['targets'])} files OK"


def task_ensure_vps_dirs(task: dict, dry_run: bool) -> tuple[bool, str]:
    """VPS ディレクトリ作成"""
    if dry_run:
        return True, f"[DRY-RUN] would mkdir -p {' '.join(task['dirs'])}"
    dirs_str = " ".join(task["dirs"])
    rc, out, err = run_ssh(f"mkdir -p {dirs_str} && echo OK")
    if rc == 0:
        return True, f"Dirs ensured: {', '.join(task['dirs'])}"
    return False, f"SSH error: {err.strip()}"


def task_vps_sync(task: dict, dry_run: bool) -> tuple[bool, str]:
    """ローカルファイルを VPS に SCP"""
    remote_dir = task["remote_dir"]
    results = []
    errors = []

    for rel in task["local_files"]:
        local = REPO_ROOT / rel
        if not local.exists():
            errors.append(f"NOT FOUND: {rel}")
            continue
        remote_path = remote_dir + local.name
        ok = scp_file(local, remote_path, dry_run)
        if ok:
            results.append(local.name)
        else:
            errors.append(f"FAIL: {local.name}")

    if errors:
        return False, f"Errors: {'; '.join(errors)}"
    return True, f"Synced: {', '.join(results)}"


def task_generate_manifest(task: dict, dry_run: bool) -> tuple[bool, str]:
    """canonical ファイルの SHA256 マニフェスト生成"""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "files": {},
    }
    missing = []
    for rel in task["source_files"]:
        p = REPO_ROOT / rel
        if p.exists():
            manifest["files"][rel] = sha256_file(p)
        else:
            missing.append(rel)

    output_path = REPO_ROOT / task["output"]

    if dry_run:
        return True, f"[DRY-RUN] would write manifest to {task['output']} ({len(manifest['files'])} files)"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    if missing:
        return True, f"Manifest written ({len(manifest['files'])} files). Missing: {', '.join(missing)}"
    return True, f"Manifest written: {len(manifest['files'])} files → {task['output']}"


# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────

def run_task(task: dict, dry_run: bool, include_vps: bool) -> dict:
    tid = task["id"]
    ttype = task["type"]
    requires_vps = task.get("requires_vps", False)

    if requires_vps and not include_vps:
        return {"id": tid, "status": "SKIP", "msg": "VPS sync skipped (use --vps-sync)"}

    try:
        if ttype == "validate":
            ok, msg = task_validate_yamls(task, dry_run)
        elif ttype == "vps_mkdir":
            ok, msg = task_ensure_vps_dirs(task, dry_run)
        elif ttype == "vps_sync":
            ok, msg = task_vps_sync(task, dry_run)
        elif ttype == "generate_manifest":
            ok, msg = task_generate_manifest(task, dry_run)
        else:
            ok, msg = False, f"Unknown task type: {ttype}"
    except Exception as e:
        ok, msg = False, f"Exception: {e}"

    status = "OK" if ok else "FAIL"
    return {"id": tid, "status": status, "msg": msg}


def run_verifier(json_output: bool) -> int:
    """doctor.py + audit_retired_refs.py を実行して整合性確認"""
    python = sys.executable
    results = []

    for script, label in [
        ("scripts/doctor.py", "doctor"),
        ("scripts/audit_retired_refs.py", "audit_retired_refs"),
    ]:
        script_path = REPO_ROOT / script
        if not script_path.exists():
            results.append({"script": label, "status": "MISSING", "exit_code": None})
            continue
        try:
            proc = subprocess.run(
                [python, str(script_path)],
                capture_output=True, text=True, timeout=60, errors="replace"
            )
            results.append({
                "script": label,
                "status": "PASS" if proc.returncode == 0 else "FAIL",
                "exit_code": proc.returncode,
                "output": proc.stdout[-500:] if proc.stdout else "",
            })
        except Exception as e:
            results.append({"script": label, "status": "ERROR", "exit_code": None, "error": str(e)})

    if not json_output:
        print(f"\n{c('bold', '--- Verification ---')}")
        for r in results:
            icon = "[OK] " if r["status"] == "PASS" else "[FAIL]"
            print(f"{icon} {r['script']}: {r['status']} (exit {r.get('exit_code', '?')})")

    return 0 if all(r["status"] == "PASS" for r in results) else 1


def main():
    parser = argparse.ArgumentParser(description="canonical outputs ビルド・VPS同期")
    parser.add_argument("--dry-run", action="store_true", help="実際の書き込み/同期は行わない")
    parser.add_argument("--vps-sync", action="store_true", help="VPS への同期を実行")
    parser.add_argument("--verify", action="store_true", help="ビルド後に doctor + audit を実行")
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力")
    args = parser.parse_args()

    if not args.json:
        dry_label = " [DRY-RUN]" if args.dry_run else ""
        print(f"\n{c('bold', '=== Build Canonical Outputs ===')} ({REPO_ROOT.name}){dry_label}\n")

    all_results = []
    fail_count = 0
    skip_count = 0

    for task in BUILD_TASKS:
        result = run_task(task, args.dry_run, args.vps_sync)
        all_results.append(result)

        if not args.json:
            status = result["status"]
            icon = {"OK": "[OK] ", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(status, "?")
            col = {"OK": "green", "FAIL": "red", "SKIP": "yellow"}.get(status, "reset")
            print(f"{icon} {c(col, status)} {task['id']}")
            print(f"   {task['description']}")
            print(f"   → {result['msg']}\n")

        if result["status"] == "FAIL":
            fail_count += 1
        elif result["status"] == "SKIP":
            skip_count += 1

    verify_rc = 0
    if args.verify and not args.dry_run:
        verify_rc = run_verifier(args.json)

    if args.json:
        out = {
            "summary": {
                "total": len(all_results),
                "ok": sum(1 for r in all_results if r["status"] == "OK"),
                "fail": fail_count,
                "skip": skip_count,
                "verify_exit": verify_rc,
                "exit_code": 2 if fail_count > 0 else (1 if skip_count > 0 or verify_rc > 0 else 0),
            },
            "tasks": all_results,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("─" * 50)
        if fail_count > 0:
            print(c("red", f"[FAIL] {fail_count} error(s), {skip_count} skipped"))
        elif skip_count > 0 or verify_rc > 0:
            print(c("yellow", f"[PARTIAL] {skip_count} skipped, verify={verify_rc}"))
        else:
            print(c("green", "[ALL OK]"))
        if not args.vps_sync:
            print(c("blue", "  [INFO] VPS sync skipped. Run with --vps-sync to sync to VPS."))
        if not args.verify:
            print(c("blue", "  [INFO] Run with --verify to run doctor.py + audit_retired_refs.py"))
        print()

    return 2 if fail_count > 0 else (1 if skip_count > 0 or verify_rc > 0 else 0)


if __name__ == "__main__":
    sys.exit(main())
