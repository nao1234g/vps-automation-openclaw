#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI VRT Runner — Local SSH Wrapper (v1.0)

ローカルから VPS の ui_vrt.py を呼び出し、
state ファイルをローカルにミラーする。

Usage:
  python scripts/ui_vrt_runner.py baseline --url https://nowpattern.com/en/ --selector ".gh-navigation-menu"
  python scripts/ui_vrt_runner.py compare
  python scripts/ui_vrt_runner.py status

State mirror:
  .claude/hooks/state/vrt_context.json  — VPS vrt_context.json のローカルコピー
  .claude/hooks/state/vrt_result.json   — VPS vrt_result.json のローカルコピー
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VPS_HOST   = "root@163.44.124.123"
VPS_SCRIPT = "/opt/shared/scripts/ui_vrt.py"
VPS_STATE  = "/opt/shared/vrt/state"

LOCAL_ROOT  = Path(__file__).parent.parent
STATE_DIR   = LOCAL_ROOT / ".claude" / "hooks" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def ssh(cmd: str, timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", VPS_HOST, cmd],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        timeout=timeout
    )


def mirror_state():
    """VPS の vrt_context.json / vrt_result.json をローカルにコピー"""
    for fname in ["vrt_context.json", "vrt_result.json"]:
        local_path = STATE_DIR / fname
        r = subprocess.run(
            ["scp", f"{VPS_HOST}:{VPS_STATE}/{fname}", str(local_path)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace"
        )
        if r.returncode == 0:
            print(f"  [mirror] {fname} -> {local_path}")
        else:
            # ファイルが存在しない場合は削除
            if local_path.exists():
                local_path.unlink()


def cmd_baseline(args):
    url      = args.url
    selector = args.selector
    print(f"[VRT] Baseline: {url}  selector={selector}")
    print("[VRT] SSH into VPS...")

    r = ssh(
        f"python3 {VPS_SCRIPT} baseline --url {url!r} --selector {selector!r}",
        timeout=120
    )
    # 出力をそのまま表示
    for line in r.stdout.splitlines():
        print(f"  {line}")
    if r.stderr.strip():
        for line in r.stderr.splitlines():
            print(f"  [stderr] {line}", file=sys.stderr)

    if r.returncode != 0:
        print(f"[VRT] FAILED (exit {r.returncode})")
        sys.exit(r.returncode)

    print("[VRT] Mirroring state files...")
    mirror_state()

    if (STATE_DIR / "vrt_context.json").exists():
        ctx = json.loads((STATE_DIR / "vrt_context.json").read_text())
        print(f"[VRT] Done. Baseline ready for: {ctx.get('url')}  {ctx.get('selector')}")
        print("BASELINE_DONE")
    else:
        print("[VRT] WARNING: vrt_context.json not found after mirror")


def cmd_compare(args):
    threshold = getattr(args, "threshold", 0.001) or 0.001
    print(f"[VRT] Compare (threshold={threshold*100:.2f}%)...")
    print("[VRT] SSH into VPS...")

    r = ssh(
        f"python3 {VPS_SCRIPT} compare --threshold {threshold}",
        timeout=120
    )
    for line in r.stdout.splitlines():
        print(f"  {line}")
    if r.stderr.strip():
        for line in r.stderr.splitlines():
            print(f"  [stderr] {line}", file=sys.stderr)

    # SSH コマンド自体が失敗した場合（Playwright 失敗等）は古い state を上書きしない
    if r.returncode not in (0, 2):
        print(f"[VRT] SSH ERROR (exit {r.returncode}) — stale state preserved")
        sys.exit(r.returncode)

    print("[VRT] Mirroring state files...")
    mirror_state()

    # ローカルの vrt_result.json を読んで結果を表示
    result_path = STATE_DIR / "vrt_result.json"
    if result_path.exists():
        res = json.loads(result_path.read_text())
        verdict = res.get("verdict", "UNKNOWN")
        outside_pct = res.get("diff_ratio_outside", 0) * 100
        print(f"\n[VRT] Result: {verdict}")
        print(f"[VRT] Outside diff: {outside_pct:.4f}%")
        if verdict == "PASS":
            print("VRT_PASS")
            sys.exit(0)
        else:
            print("VRT_FAIL")
            print(f"[VRT] Diff image on VPS: {res.get('diff_path', 'N/A')}")
            sys.exit(2)
    else:
        print("[VRT] ERROR: vrt_result.json not found")
        sys.exit(1)


def cmd_status(_args):
    print("=== VRT Status (local mirror) ===")
    ctx_path = STATE_DIR / "vrt_context.json"
    res_path = STATE_DIR / "vrt_result.json"

    if ctx_path.exists():
        ctx = json.loads(ctx_path.read_text())
        print(f"  Baseline: {ctx.get('url')}  {ctx.get('selector')}")
        print(f"  Captured: {ctx.get('captured_at')}")
    else:
        print("  Baseline: NONE")

    if res_path.exists():
        res = json.loads(res_path.read_text())
        outside_pct = res.get("diff_ratio_outside", 0) * 100
        print(f"  Last compare: {res.get('verdict')}  at {res.get('compared_at')}")
        print(f"  Outside diff: {outside_pct:.4f}%")
    else:
        print("  Last compare: NONE")

    print("\n[VRT] Fetching live status from VPS...")
    r = ssh(f"python3 {VPS_SCRIPT} status", timeout=30)
    for line in r.stdout.splitlines():
        print(f"  {line}")


def main():
    parser = argparse.ArgumentParser(description="UI VRT Runner (local SSH wrapper)")
    sub = parser.add_subparsers(dest="cmd")

    p_base = sub.add_parser("baseline", help="ベースライン撮影")
    p_base.add_argument("--url",      required=True, help="対象URL (例: https://nowpattern.com/en/)")
    p_base.add_argument("--selector", required=True, help="CSS セレクタ (例: .gh-navigation-menu)")

    p_cmp = sub.add_parser("compare", help="After撮影 + 比較")
    p_cmp.add_argument("--threshold", type=float, default=0.001,
                        help="外部変化の許容閾値 (デフォルト 0.001 = 0.1%%)")

    sub.add_parser("status", help="状態確認")

    args = parser.parse_args()
    if args.cmd == "baseline":
        cmd_baseline(args)
    elif args.cmd == "compare":
        cmd_compare(args)
    elif args.cmd == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
