#!/usr/bin/env python3
"""Shared runtime boundary helpers for local vs live path resolution."""

from __future__ import annotations

from pathlib import Path


def is_live_runtime(script_file: str | Path) -> bool:
    """Return True only when the running script itself lives under /opt/shared/."""
    return Path(script_file).resolve().as_posix().startswith("/opt/shared/")


def shared_or_local_path(
    *,
    script_file: str | Path,
    shared_path: str | Path,
    local_path: str | Path,
) -> Path:
    """Pick the live shared path only when executing from the live runtime."""
    return Path(shared_path) if is_live_runtime(script_file) else Path(local_path)
