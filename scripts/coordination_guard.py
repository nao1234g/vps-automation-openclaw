#!/usr/bin/env python3
"""Shared coordination guard/heartbeat CLI for non-hooked agents such as Codex."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import update_operations_board as operations_board
from coordination_utils import (
    active_lock_entries,
    find_conflict,
    resolve_self_agent_name,
    update_agent_state,
)


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    self_agent = args.agent or resolve_self_agent_name("codex")
    conflict = find_conflict(args.path, root=root, self_agent=self_agent)
    if not conflict:
        print(f"OK: no coordination conflict for {args.path}")
        return 0
    print(
        "BLOCKED: "
        f"{args.path} is locked by {conflict.get('agent', 'unknown')} "
        f"({conflict.get('path', '')}) | task={conflict.get('current_task', '')}"
    )
    return 2


def cmd_heartbeat(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    agent = args.agent or resolve_self_agent_name("codex")
    status = args.status or "active"
    update_agent_state(
        agent_name=agent,
        status=status,
        current_task=args.task if args.task is not None else None,
        next_step=args.next_step if args.next_step is not None else None,
        locked_files=_split_csv(args.locked_files) if args.locked_files is not None else None,
        vps_resources=_split_csv(args.vps_resources) if args.vps_resources is not None else None,
        session_id=args.session_id if args.session_id is not None else None,
        root=root,
    )
    operations_board.sync_board(root)
    print(f"OK: heartbeat synced for {agent} ({status})")
    return 0


def cmd_keepalive(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    agent = args.agent or resolve_self_agent_name("codex")
    interval = max(1, int(args.interval))
    iterations = int(args.iterations)
    loops = 0
    while True:
        update_agent_state(
            agent_name=agent,
            status=args.status or "active",
            current_task=args.task if args.task is not None else None,
            next_step=args.next_step if args.next_step is not None else None,
            locked_files=_split_csv(args.locked_files) if args.locked_files is not None else None,
            vps_resources=_split_csv(args.vps_resources) if args.vps_resources is not None else None,
            session_id=args.session_id if args.session_id is not None else None,
            root=root,
        )
        operations_board.sync_board(root)
        loops += 1
        print(f"OK: keepalive tick {loops} for {agent}")
        if iterations and loops >= iterations:
            break
        time.sleep(interval)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    entries = active_lock_entries(root=root)
    if not entries:
        print("OK: no active locks")
        return 0
    print("Active locks:")
    for entry in entries:
        print(f"- {entry['agent']}: {entry['path']} | task={entry.get('current_task', '')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coordination guard/heartbeat CLI.")
    parser.add_argument("--root", default=".", help="Repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Check whether a target path is currently locked.")
    check.add_argument("path", help="Target file path to check")
    check.add_argument("--agent", default="", help="Self agent name")
    check.set_defaults(func=cmd_check)

    heartbeat = sub.add_parser("heartbeat", help="Update agent state and sync derived coordination artifacts.")
    heartbeat.add_argument("--agent", default="", help="Agent name")
    heartbeat.add_argument("--status", default="active", help="State status")
    heartbeat.add_argument("--task", default=None, help="Current task description")
    heartbeat.add_argument("--next-step", dest="next_step", default=None, help="Next exact step")
    heartbeat.add_argument("--locked-files", default=None, help="Comma-separated repo-relative locked files")
    heartbeat.add_argument("--vps-resources", default=None, help="Comma-separated VPS resources")
    heartbeat.add_argument("--session-id", default=None, help="Session identifier")
    heartbeat.set_defaults(func=cmd_heartbeat)

    keepalive = sub.add_parser("keepalive", help="Run recurring heartbeat syncs to avoid stale state.")
    keepalive.add_argument("--agent", default="", help="Agent name")
    keepalive.add_argument("--status", default="active", help="State status")
    keepalive.add_argument("--task", default=None, help="Current task description")
    keepalive.add_argument("--next-step", dest="next_step", default=None, help="Next exact step")
    keepalive.add_argument("--locked-files", default=None, help="Comma-separated repo-relative locked files")
    keepalive.add_argument("--vps-resources", default=None, help="Comma-separated VPS resources")
    keepalive.add_argument("--session-id", default=None, help="Session identifier")
    keepalive.add_argument("--interval", default="300", help="Heartbeat interval in seconds")
    keepalive.add_argument("--iterations", default="0", help="Number of ticks; 0 means infinite")
    keepalive.set_defaults(func=cmd_keepalive)

    show = sub.add_parser("show", help="Show active coordination locks")
    show.set_defaults(func=cmd_show)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
