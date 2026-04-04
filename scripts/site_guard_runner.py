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

from mission_contract import assert_mission_handshake

MISSION_HANDSHAKE = assert_mission_handshake(
    "site_guard_runner",
    "run recurring self-check and self-heal jobs under the shared founder mission contract",
)

LOCK_DIR = Path("/opt/shared/locks")
STATE_DIR = Path("/opt/shared/reports/site_guard")
LOG_DIR = Path("/opt/shared/logs")
SCRIPT_DIR = Path("/opt/shared/scripts")
BASE_URL = "https://nowpattern.com"

JOBS = {
    "ghost-routes": {
        "command": [
            "python3",
            str(SCRIPT_DIR / "check_ghost_article_routes.py"),
            "--repair",
            "--quiet",
        ],
        "timeout": 180,
        "load_guard": False,
        "health_guard": False,
        "bypass_global_breaker": True,
    },
    "lang": {
        "command": ["python3", str(SCRIPT_DIR / "fix_global_language_switcher.py")],
        "timeout": 120,
        "load_guard": True,
        "health_guard": True,
    },
    "en-routes": {
        "command": ["python3", str(SCRIPT_DIR / "install_en_article_route_guard.py"), "--quiet"],
        "timeout": 120,
        "load_guard": True,
        "health_guard": True,
    },
    "preview-routes": {
        "command": ["python3", str(SCRIPT_DIR / "install_uuid_preview_route_guard.py"), "--quiet"],
        "timeout": 180,
        "load_guard": True,
        "health_guard": True,
    },
    "source-links": {
        "command": ["python3", str(SCRIPT_DIR / "fix_ghost_content_links.py"), "--quiet"],
        "timeout": 180,
        "load_guard": True,
        "health_guard": True,
    },
    "theme-en-urls": {
        "command": ["python3", str(SCRIPT_DIR / "patch_ghost_theme_en_urls.py")],
        "timeout": 180,
        "load_guard": True,
        "health_guard": True,
    },
    "ghost-authors": {
        "command": ["python3", str(SCRIPT_DIR / "repair_ghost_post_authors.py")],
        "timeout": 180,
        "load_guard": True,
        "health_guard": True,
    },
    "draft-links": {
        "command": ["python3", str(SCRIPT_DIR / "repair_internal_draft_links.py")],
        "timeout": 240,
        "load_guard": True,
        "health_guard": True,
    },
    "article-sources": {
        "command": ["python3", str(SCRIPT_DIR / "repair_article_source_urls.py")],
        "timeout": 240,
        "load_guard": True,
        "health_guard": True,
    },
    "cross-lang-links": {
        "command": ["python3", str(SCRIPT_DIR / "repair_cross_language_article_links.py")],
        "timeout": 300,
        "load_guard": True,
        "health_guard": True,
    },
    "content-integrity": {
        "subjobs": ["theme-en-urls", "ghost-authors", "draft-links", "article-sources", "cross-lang-links"],
        "timeout": 540,
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
    "governance": {
        "command": [
            "python3",
            str(SCRIPT_DIR / "ecosystem_governance_audit.py"),
            "--json-out",
            "/opt/shared/reports/site_guard/ecosystem_governance.json",
        ],
        "timeout": 420,
        "load_guard": True,
        "health_guard": False,
    },
}

GLOBAL_BREAKER_NAME = "_global"
LOAD_COOLDOWN_SECONDS = 20 * 60
HEALTH_COOLDOWN_SECONDS = 30 * 60


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


def global_state() -> dict:
    return load_state(GLOBAL_BREAKER_NAME)


def save_global_state(state: dict) -> None:
    save_state(GLOBAL_BREAKER_NAME, state)


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


def set_pause(state: dict, seconds: int, reason: str) -> None:
    pause_until = int(time.time()) + seconds
    state["pause_until_epoch"] = max(int(state.get("pause_until_epoch", 0) or 0), pause_until)
    state["last_skip_reason"] = reason


def should_skip_job(job: str) -> tuple[bool, str]:
    state = load_state(job)
    global_guard = global_state()
    pause_until = float(state.get("pause_until_epoch", 0) or 0)
    now = time.time()
    global_pause_until = float(global_guard.get("pause_until_epoch", 0) or 0)
    bypass_global_breaker = JOBS[job].get("bypass_global_breaker", False)
    if not bypass_global_breaker and global_pause_until and now < global_pause_until:
        wait_seconds = int(global_pause_until - now)
        reason = global_guard.get("last_skip_reason") or "global breaker active"
        return True, f"{reason} ({wait_seconds}s remaining)"
    if pause_until and now < pause_until:
        wait_seconds = int(pause_until - now)
        return True, f"cooldown active ({wait_seconds}s remaining)"

    if JOBS[job].get("health_guard", False):
        healthy, detail = public_site_healthy()
        if not healthy:
            consecutive = int(state.get("availability_failures", 0) or 0) + 1
            state["availability_failures"] = consecutive
            reason = f"public site unhealthy: {detail}"
            state["last_skip_reason"] = reason
            set_pause(global_guard, HEALTH_COOLDOWN_SECONDS, reason)
            if consecutive >= 2:
                set_pause(state, HEALTH_COOLDOWN_SECONDS, reason)
            save_global_state(global_guard)
            save_state(job, state)
            return True, state["last_skip_reason"]

        state["availability_failures"] = 0
        state["pause_until_epoch"] = 0
        state["last_skip_reason"] = ""
        save_state(job, state)

    if JOBS[job].get("load_guard", False):
        too_high, load_detail = load_average_too_high()
        if too_high:
            reason = f"load guard: {load_detail}"
            set_pause(state, LOAD_COOLDOWN_SECONDS, reason)
            set_pause(global_guard, LOAD_COOLDOWN_SECONDS, reason)
            save_state(job, state)
            save_global_state(global_guard)
            return True, reason

    if global_guard:
        global_guard["pause_until_epoch"] = 0
        global_guard["last_skip_reason"] = ""
        save_global_state(global_guard)
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
        skip, reason = should_skip_job(job)
        if skip:
            print(f"SKIP: {job} guard {reason}")
            return 0

        started = time.time()
        if "subjobs" in JOBS[job]:
            last_returncode = 0
            for subjob in JOBS[job]["subjobs"]:
                result = subprocess.run(
                    JOBS[subjob]["command"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=JOBS[subjob]["timeout"],
                )
                if result.stdout:
                    print(result.stdout.rstrip())
                if result.stderr:
                    print(result.stderr.rstrip(), file=sys.stderr)
                last_returncode = result.returncode
                if result.returncode != 0:
                    break
            returncode = last_returncode
        else:
            result = subprocess.run(
                JOBS[job]["command"],
                capture_output=True,
                text=True,
                check=False,
                timeout=JOBS[job]["timeout"],
            )
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip(), file=sys.stderr)
            returncode = result.returncode
        elapsed = int(time.time() - started)

        state = load_state(job)
        state["last_exit_code"] = returncode
        state["last_elapsed_seconds"] = elapsed
        state["last_ran_epoch"] = int(time.time())
        if returncode == 0:
            state["last_ok_epoch"] = int(time.time())
            state["availability_failures"] = 0
            if "pause_until_epoch" not in state:
                state["pause_until_epoch"] = 0
        save_state(job, state)
        return returncode
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
