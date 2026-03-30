#!/usr/bin/env python3
"""Verify that recent published Ghost article routes resolve, and self-heal via restart if needed."""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


DEFAULT_DB = Path("/var/www/nowpattern/content/data/ghost.db")
DEFAULT_STATE = Path("/opt/shared/state/ghost_route_guard.json")
DEFAULT_REPORT = Path("/opt/shared/reports/site_guard/ghost_article_routes.json")
HOST_HEADER = "nowpattern.com"
SERVICE_NAME = "ghost-nowpattern.service"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check recent Ghost article routes and optionally self-heal.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Ghost sqlite database path")
    parser.add_argument("--limit", type=int, default=8, help="How many recent published posts to verify")
    parser.add_argument("--timeout-seconds", type=float, default=8.0, help="Per-route HTTP timeout")
    parser.add_argument("--repair", action="store_true", help="Restart Ghost if route failures are detected")
    parser.add_argument("--cooldown-minutes", type=int, default=30, help="Minimum minutes between self-heal restarts")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE, help="Restart cooldown state file")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_REPORT, help="Optional JSON report output path")
    parser.add_argument("--quiet", action="store_true", help="Print only essential output")
    return parser.parse_args()


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at_epoch"] = int(time.time())
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def recent_published_posts(db_path: Path, limit: int) -> list[dict]:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT id, slug, title, published_at
        FROM posts
        WHERE type='post' AND status='published' AND visibility='public'
        ORDER BY datetime(published_at) DESC, published_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    posts: list[dict] = []
    for row in rows:
        tags = con.execute(
            """
            SELECT t.slug
            FROM tags t
            JOIN posts_tags pt ON pt.tag_id = t.id
            WHERE pt.post_id = ?
            ORDER BY pt.sort_order ASC, t.slug ASC
            """,
            (row["id"],),
        ).fetchall()
        tag_slugs = [item["slug"] for item in tags]
        slug = row["slug"]
        exact_lang = "lang-en" if "lang-en" in tag_slugs else ("lang-ja" if "lang-ja" in tag_slugs else None)
        is_en = exact_lang == "lang-en" or slug.startswith("en-")
        path = f"/en/{slug[3:]}/" if slug.startswith("en-") else (f"/en/{slug}/" if is_en else f"/{slug}/")
        posts.append(
            {
                "id": row["id"],
                "slug": slug,
                "title": row["title"],
                "published_at": row["published_at"],
                "tags": tag_slugs,
                "path": path,
                "lang": "en" if is_en else "ja",
                "route_eligible": bool(exact_lang or slug.startswith("en-")),
                "skip_reason": "" if (exact_lang or slug.startswith("en-")) else "missing exact lang tag",
            }
        )
    con.close()
    return posts


def probe_route(path: str, timeout_seconds: float) -> dict:
    url = f"http://127.0.0.1:2368{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Host": HOST_HEADER,
            "X-Forwarded-Proto": "https",
            "User-Agent": "nowpattern-ghost-route-guard/1.0",
        },
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            body = response.read(1024).decode("utf-8", errors="ignore")
            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "elapsed_ms": int((time.time() - started) * 1000),
                "body_has_404": "404" in body[:512],
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": 0,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": repr(exc),
        }


def evaluate(posts: list[dict], timeout_seconds: float) -> tuple[list[dict], list[dict]]:
    checks: list[dict] = []
    failures: list[dict] = []
    for post in posts:
        if not post.get("route_eligible", True):
            check = {
                **post,
                "ok": True,
                "status": -1,
                "elapsed_ms": 0,
                "skipped": True,
            }
            checks.append(check)
            continue
        result = probe_route(post["path"], timeout_seconds)
        check = {**post, **result}
        checks.append(check)
        if not result["ok"]:
            failures.append(check)
    return checks, failures


def wait_for_ghost_http(timeout_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = probe_route("/favicon.ico", 5.0)
        if result.get("status", 0) > 0:
            return True
        time.sleep(3)
    return False


def wait_for_route_recovery(posts: list[dict], timeout_seconds: float, probe_timeout_seconds: float) -> tuple[list[dict], list[dict], bool]:
    deadline = time.time() + timeout_seconds
    last_checks: list[dict] = []
    last_failures: list[dict] = []
    while time.time() < deadline:
        last_checks, last_failures = evaluate(posts, probe_timeout_seconds)
        if not last_failures:
            return last_checks, last_failures, True
        time.sleep(5)
    return last_checks, last_failures, False


def parse_published_epoch(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def restart_ghost() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", "restart", SERVICE_NAME],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def print_checks(checks: list[dict], *, quiet: bool) -> None:
    if quiet:
        return
    for check in checks:
        status = check.get("status")
        elapsed_ms = check.get("elapsed_ms")
        marker = "OK" if check.get("ok") else "FAIL"
        extra = check.get("error") or ""
        print(f"{marker} {check['path']} status={status} elapsed_ms={elapsed_ms} {extra}".rstrip())


def main() -> int:
    args = parse_args()
    posts = recent_published_posts(args.db, args.limit)
    checks, failures = evaluate(posts, args.timeout_seconds)
    report = {
        "checked_count": len(checks),
        "failures_before_repair": len(failures),
        "checks": checks,
        "repaired": False,
        "repair_skipped": False,
    }
    print_checks(checks, quiet=args.quiet)

    state = load_state(args.state_file)
    now = int(time.time())

    if failures and args.repair:
        cooldown_seconds = max(0, args.cooldown_minutes) * 60
        last_restart = int(state.get("last_restart_epoch", 0) or 0)
        newer_failure_than_restart = any(parse_published_epoch(item.get("published_at")) > last_restart for item in failures)
        if cooldown_seconds and now - last_restart < cooldown_seconds and not newer_failure_than_restart:
            report["repair_skipped"] = True
            report["repair_skip_reason"] = f"cooldown active ({cooldown_seconds - (now - last_restart)}s remaining)"
            report["newer_failure_than_restart"] = False
        else:
            report["newer_failure_than_restart"] = newer_failure_than_restart
            restart = restart_ghost()
            report["repair_exit_code"] = restart.returncode
            report["repair_stdout"] = (restart.stdout or "").strip()
            report["repair_stderr"] = (restart.stderr or "").strip()
            if restart.returncode == 0:
                state["last_restart_epoch"] = now
                save_state(args.state_file, state)
                report["waited_for_http_ready"] = wait_for_ghost_http(90.0)
                checks_after, failures_after, recovered = wait_for_route_recovery(posts, 90.0, args.timeout_seconds)
                report["repaired"] = True
                report["checks_after_repair"] = checks_after
                report["failures_after_repair"] = len(failures_after)
                report["route_recovery_complete"] = recovered
                if not args.quiet:
                    print("REPAIRED: restarted ghost-nowpattern.service")
                    print_checks(checks_after, quiet=False)
                failures = failures_after
            else:
                failures = failures

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if failures:
        if args.quiet:
            print(f"FAIL: {len(failures)} broken article routes detected")
        return 1

    if args.quiet:
        print(f"PASS: checked {len(checks)} published article routes")
    else:
        print(f"PASS: checked {len(checks)} published article routes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
