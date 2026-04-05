#!/usr/bin/env python3
"""Shared helpers for local multi-agent coordination state."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
COORD_DIR = REPO_ROOT / ".coordination"
PROTOCOL_PATH = COORD_DIR / "protocol.json"
LOCK_REGISTRY_PATH = COORD_DIR / "lock-registry.json"
STATE_EXCLUDE = {"protocol.json", "lock-registry.json"}


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def protocol_rules(root: Path | None = None) -> dict:
    base = (root or REPO_ROOT).resolve()
    return read_json(base / ".coordination" / "protocol.json").get("rules", {})


def stale_threshold_seconds(root: Path | None = None) -> int:
    rules = protocol_rules(root)
    try:
        return int(rules.get("stale_threshold_seconds", 600))
    except Exception:
        return 600


def resolve_self_agent_name(default: str = "") -> str:
    for key in ("COORD_AGENT_NAME", "CLAUDE_AGENT_NAME", "AGENT_NAME"):
        value = str(os.environ.get(key) or "").strip()
        if value:
            return value
    return default


def normalize_repo_relative_path(path_value: str, root: Path | None = None) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return ""

    normalized = raw.replace("\\", "/")
    win_drive = re.match(r"^([a-zA-Z]):/(.*)$", normalized)
    if win_drive:
        drive = win_drive.group(1).lower()
        remainder = win_drive.group(2)
        normalized = f"/mnt/{drive}/{remainder}"

    repo_root = (root or REPO_ROOT).resolve().as_posix().replace("\\", "/")
    if normalized.startswith(repo_root + "/"):
        normalized = normalized[len(repo_root) + 1 :]
    elif normalized == repo_root:
        normalized = ""
    elif normalized.startswith("./"):
        normalized = normalized[2:]
    elif normalized.startswith("/"):
        normalized = normalized.lstrip("/")

    while "//" in normalized:
        normalized = normalized.replace("//", "/")

    return normalized.rstrip("/")


def path_compare_key(path_value: str, root: Path | None = None) -> str:
    return normalize_repo_relative_path(path_value, root).lower()


def basename(path_value: str) -> str:
    normalized = str(path_value or "").replace("\\", "/").rstrip("/")
    if not normalized:
        return ""
    return normalized.split("/")[-1].lower()


def path_is_locked(target_path: str, locked_path: str, root: Path | None = None) -> bool:
    target_norm = path_compare_key(target_path, root)
    locked_norm = path_compare_key(locked_path, root)
    if not target_norm or not locked_norm:
        return False
    if target_norm == locked_norm:
        return True
    if "/" not in locked_norm:
        return basename(target_norm) == locked_norm
    return False


def state_file_path(agent_name: str, root: Path | None = None) -> Path:
    base = (root or REPO_ROOT).resolve()
    return base / ".coordination" / f"{agent_name}.json"


def agent_state_files(root: Path | None = None) -> list[Path]:
    base = (root or REPO_ROOT).resolve()
    coord_dir = base / ".coordination"
    if not coord_dir.exists():
        return []
    return sorted(path for path in coord_dir.glob("*.json") if path.name not in STATE_EXCLUDE)


def load_agent_states(root: Path | None = None) -> list[dict]:
    rows: list[dict] = []
    for path in agent_state_files(root):
        payload = read_json(path)
        if payload:
            payload["_state_file"] = path.name
            if not str(payload.get("agent") or "").strip():
                payload["agent"] = path.stem
            rows.append(payload)
    return rows


def is_state_stale(state: dict, root: Path | None = None) -> bool:
    updated = str(state.get("updated_at") or "").strip()
    if not updated:
        return False
    try:
        ts = datetime.fromisoformat(updated)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds()
        return age > stale_threshold_seconds(root)
    except Exception:
        return False


def active_lock_entries(root: Path | None = None, skip_agent: str = "") -> list[dict]:
    entries: list[dict] = []
    for state in load_agent_states(root):
        if str(state.get("status") or "").strip().lower() == "idle":
            continue
        if is_state_stale(state, root):
            continue
        agent_name = str(state.get("agent") or "").strip()
        if skip_agent and agent_name == skip_agent:
            continue
        for locked in list(state.get("locked_files") or []) + list(state.get("vps_resources") or []):
            normalized = normalize_repo_relative_path(locked, root)
            if not normalized:
                continue
            entries.append(
                {
                    "agent": agent_name,
                    "path": normalized,
                    "compare_key": path_compare_key(normalized, root),
                    "current_task": str(state.get("current_task") or "").strip(),
                    "updated_at": str(state.get("updated_at") or "").strip(),
                }
            )
    return entries


def find_conflict(target_path: str, root: Path | None = None, self_agent: str = "") -> dict | None:
    for entry in active_lock_entries(root=root, skip_agent=self_agent):
        if path_is_locked(target_path, entry["compare_key"], root=root):
            return entry
    return None


def sync_lock_registry(root: Path | None = None) -> dict:
    base = (root or REPO_ROOT).resolve()
    payload = {
        "generated_from": ".coordination/*.json",
        "authoritative_machine_source": ".coordination/{agent}.json",
        "locks": [
            {"agent": entry["agent"], "path": entry["path"]}
            for entry in active_lock_entries(base)
        ],
        "updated_at": now_iso(),
    }
    write_json(base / ".coordination" / "lock-registry.json", payload)
    return payload


def update_agent_state(
    *,
    agent_name: str,
    status: str | None = None,
    current_task: str | None = None,
    next_step: str | None = None,
    locked_files: list[str] | None = None,
    vps_resources: list[str] | None = None,
    session_id: str | None = None,
    root: Path | None = None,
) -> dict:
    base = (root or REPO_ROOT).resolve()
    path = state_file_path(agent_name, base)
    state = read_json(path)
    state["agent"] = agent_name
    if status is not None:
        state["status"] = status
    if current_task is not None:
        state["current_task"] = current_task
    if next_step is not None:
        state["next_step"] = next_step
    if locked_files is not None:
        state["locked_files"] = [normalize_repo_relative_path(item, base) for item in locked_files if str(item).strip()]
    if vps_resources is not None:
        state["vps_resources"] = [normalize_repo_relative_path(item, base) for item in vps_resources if str(item).strip()]
    if session_id is not None:
        state["session_id"] = session_id
    state["updated_at"] = now_iso()
    write_json(path, state)
    return state
