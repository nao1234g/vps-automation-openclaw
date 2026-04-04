#!/usr/bin/env python3
"""Central change-freeze state and enforcement helpers for public release surfaces."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime_boundary import shared_or_local_path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_STATE_PATH = shared_or_local_path(
    script_file=__file__,
    shared_path="/opt/shared/state/change_freeze.json",
    local_path=REPO_ROOT / "reports" / "change_freeze.json",
)
STATE_PATH = Path(os.environ.get("NOWPATTERN_CHANGE_FREEZE_STATE_PATH", str(DEFAULT_STATE_PATH)))
DEFAULT_SCOPES = ["public_release", "distribution", "governed_write"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_state() -> dict[str, Any]:
    return {
        "enabled": False,
        "reason": "",
        "scopes": list(DEFAULT_SCOPES),
        "enabled_by": "",
        "enabled_at": "",
        "expires_at": "",
        "ticket": "",
        "notes": "",
    }


def load_change_freeze_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return default_state()
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return default_state()
    state = default_state()
    if isinstance(payload, dict):
        state.update({k: v for k, v in payload.items() if v is not None})
    scopes = state.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        state["scopes"] = list(DEFAULT_SCOPES)
    return state


def write_change_freeze_state(state: dict[str, Any]) -> dict[str, Any]:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    canonical = default_state()
    canonical.update({k: v for k, v in state.items() if v is not None})
    canonical["scopes"] = list(canonical.get("scopes") or DEFAULT_SCOPES)
    STATE_PATH.write_text(json.dumps(canonical, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return canonical


def enable_change_freeze(
    *,
    reason: str,
    enabled_by: str = "unknown",
    scopes: list[str] | None = None,
    ticket: str = "",
    notes: str = "",
    expires_at: str = "",
) -> dict[str, Any]:
    state = default_state()
    state.update(
        {
            "enabled": True,
            "reason": reason.strip(),
            "enabled_by": enabled_by.strip(),
            "enabled_at": _utc_now(),
            "expires_at": expires_at.strip(),
            "ticket": ticket.strip(),
            "notes": notes.strip(),
            "scopes": list(scopes or DEFAULT_SCOPES),
        }
    )
    return write_change_freeze_state(state)


def disable_change_freeze(*, disabled_by: str = "unknown", notes: str = "") -> dict[str, Any]:
    previous = load_change_freeze_state()
    state = default_state()
    state["notes"] = "disabled_by=" + disabled_by.strip()
    if notes.strip():
        state["notes"] += f"; {notes.strip()}"
    if previous.get("enabled"):
        state["notes"] += f"; previously_enabled_at={previous.get('enabled_at', '')}"
    return write_change_freeze_state(state)


def evaluate_change_freeze(scope: str) -> dict[str, Any]:
    state = load_change_freeze_state()
    active = bool(state.get("enabled")) and scope in set(state.get("scopes") or [])
    return {
        "active": active,
        "scope": scope,
        "state": state,
    }


def assert_change_window(
    *,
    scope: str,
    actor: str,
    purpose: str,
    allow_override: bool = False,
) -> dict[str, Any]:
    result = evaluate_change_freeze(scope)
    if result["active"] and not allow_override:
        state = result["state"]
        raise ValueError(
            "CHANGE_FREEZE_ACTIVE:"
            f"scope={scope}; actor={actor}; purpose={purpose}; "
            f"reason={state.get('reason', '')}; enabled_by={state.get('enabled_by', '')}; "
            f"enabled_at={state.get('enabled_at', '')}"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or change the central release freeze state.")
    parser.add_argument("--status", action="store_true", help="Print current change-freeze status")
    parser.add_argument("--enable", action="store_true", help="Enable change freeze")
    parser.add_argument("--disable", action="store_true", help="Disable change freeze")
    parser.add_argument("--reason", default="", help="Reason when enabling")
    parser.add_argument("--by", default="unknown", help="Actor enabling/disabling the freeze")
    parser.add_argument("--scopes", default=",".join(DEFAULT_SCOPES), help="Comma-separated scopes")
    parser.add_argument("--ticket", default="", help="Optional incident or change ticket")
    parser.add_argument("--notes", default="", help="Optional notes")
    parser.add_argument("--expires-at", default="", help="Optional ISO timestamp")
    args = parser.parse_args()

    if args.enable:
        if not args.reason.strip():
            raise SystemExit("--reason is required with --enable")
        scopes = [item.strip() for item in args.scopes.split(",") if item.strip()]
        payload = enable_change_freeze(
            reason=args.reason,
            enabled_by=args.by,
            scopes=scopes,
            ticket=args.ticket,
            notes=args.notes,
            expires_at=args.expires_at,
        )
    elif args.disable:
        payload = disable_change_freeze(disabled_by=args.by, notes=args.notes)
    else:
        payload = load_change_freeze_state()

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
