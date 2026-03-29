#!/usr/bin/env python3
"""Run lightweight UI guard jobs with locks, timeouts, and load-aware skipping."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


LOCK_DIR = Path("/opt/shared/locks")
STATE_DIR = Path("/opt/shared/reports/site_guard")
LOG_DIR = Path("/opt/shared/logs")
SCRIPT_DIR = Path("/opt/shared/scripts")
BASE_URL = "https://nowpattern.com"

JOBS = {
    "lang": {
        "command": ["python3", str(SCRIPT_DIR / "fix_global_language_switcher.py")],
        "timeout": 120,
        "load_guard": False,
        "health_guard": True,
    },
    "en-routes": {
        "command": ["python3", str(SCRIPT_DIR / "install_en_article_route_guard.py"), "--quiet"],
        "timeout": 120,
        "load_guard": False,
        "health_guard": True,
    },
    "source-links": {
        "command": ["python3", str(SCRIPT_DIR / "fix_ghost_content_links.py"), "--quiet"],
        "timeout": 180,
        "load_guard": True,
        "health_guard": True,
    },
    "smoke": {
        "command": [
            "python3",
            str(SCRIPT_DIR / "site_ui_smoke_audit.py"),
            "--base-url",
            BASE_URL,
            "--skip-articles",
            "--json-out",
            "/opt/shared/reports/site_ui_smoke/latest.json",
        ],
        "timeout": 480,
        "load_guard": True,
        "health_guard": True,
    },
}


def ensure_dirs() -> None:
    for path in (LOCK_DIR, STATE_DIR, LOG_DIR, Path("/opt/shared/reports/site_ui_smoke")):
        path.mkdir(parents=True, exist_ok=True)


def state_path(job: str) -> Path:
    return STATE_DIR / f"{job}.json"


def load_state(job: str) -> dict:
    path = state_path(job)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(job: str, state: dict) -> None:
    state["updated_at_epoch"] = int(time.time())
    state_path(job).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def acquire_lock(job: str):
    import fcntl

    lock_path = LOCK_DIR / f"site_guard_{job}.lock"
    fd = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(f"{os.getpid()} {int(time.time())}\n")
        fd.flush()
        return fd
    except OSError:
        fd.close()
        return None


def load_average_too_high() -> tuple[bool, str]:
    try:
        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        threshold = max(2.0, cpu_count * 1.25)
        return load1 > threshold, f"load1={load1:.2f} threshold={threshold:.2f}"
    except Exception as exc:
        return False, f"loadavg unavailable: {exc}"


def public_site_healthy() -> tuple[bool, str]:
    cmd = [
        "python3",
        str(SCRIPT_DIR / "live_site_availability_check.py"),
        "--base-url",
        BASE_URL,
        "--slugs",
        "home-ja,reader-api-health",
        "--timeout-seconds",
        "6",
        "--slow-ms",
        "5000",
        "--critical-ms",
        "10000",
        "--json-out",
        "/opt/shared/reports/site_guard/live_site_availability.json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=90)
    if result.returncode == 0:
        return True, "public site availability green"
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip().splitlines()
    detail = stdout[-1] if stdout else stderr or "availability probe failed"
    return False, detail


def should_skip_smoke(job: str) -> tuple[bool, str]:
    state = load_state(job)
    pause_until = float(state.get("pause_until_epoch", 0) or 0)
    now = time.time()
    if pause_until and now < pause_until:
        wait_seconds = int(pause_until - now)
        return True, f"cooldown active ({wait_seconds}s remaining)"

    too_high, load_detail = load_average_too_high()
    if too_high:
        state["last_skip_reason"] = f"load guard: {load_detail}"
        state["pause_until_epoch"] = now + 20 * 60
        save_state(job, state)
        return True, state["last_skip_reason"]

    if JOBS[job].get("health_guard", False):
        healthy, detail = public_site_healthy()
        if not healthy:
            consecutive = int(state.get("availability_failures", 0) or 0) + 1
            state["availability_failures"] = consecutive
            state["last_skip_reason"] = f"public site unhealthy: {detail}"
            if consecutive >= 2:
                state["pause_until_epoch"] = now + 30 * 60
            save_state(job, state)
            return True, state["last_skip_reason"]

        if state:
            state["availability_failures"] = 0
            state["pause_until_epoch"] = 0
            state["last_skip_reason"] = ""
            save_state(job, state)
    return False, "ready"


def run_job(job: str) -> int:
    if job not in JOBS:
        raise KeyError(job)

    ensure_dirs()
    lock_fd = acquire_lock(job)
    if lock_fd is None:
        print(f"SKIP: {job} guard already running")
        return 0

    try:
        if JOBS[job]["load_guard"]:
            skip, reason = should_skip_smoke(job)
            if skip:
                print(f"SKIP: {job} guard {reason}")
                return 0

        started = time.time()
        result = subprocess.run(
            JOBS[job]["command"],
            capture_output=True,
            text=True,
            check=False,
            timeout=JOBS[job]["timeout"],
        )
        elapsed = int(time.time() - started)
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)

        state = load_state(job)
        state["last_exit_code"] = result.returncode
        state["last_elapsed_seconds"] = elapsed
        state["last_ran_epoch"] = int(time.time())
        if result.returncode == 0:
            state["last_ok_epoch"] = int(time.time())
            state["availability_failures"] = 0
            if "pause_until_epoch" not in state:
                state["pause_until_epoch"] = 0
        save_state(job, state)
        return result.returncode
    except subprocess.TimeoutExpired:
        state = load_state(job)
        state["last_exit_code"] = 124
        state["last_error"] = "timeout"
        state["last_ran_epoch"] = int(time.time())
        save_state(job, state)
        print(f"FAIL: {job} guard timed out", file=sys.stderr)
        return 124
    finally:
        lock_fd.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a guarded site maintenance job.")
    parser.add_argument("--job", required=True, choices=sorted(JOBS.keys()))
    args = parser.parse_args()
    return run_job(args.job)


if __name__ == "__main__":
    raise SystemExit(main())
