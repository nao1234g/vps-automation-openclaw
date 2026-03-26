"""
Atomic JSON read/write utilities for .claude/hooks/state/*.json files.

All state files (session.json, etc.) are written by multiple hooks concurrently.
Using os.replace() provides near-atomic writes:
  - POSIX (Linux/macOS): atomic via rename(2) syscall
  - Windows: atomic via MoveFileExW (fast, not 100% atomic but safe for our use)

Usage:
    from _state_utils import safe_read_json, safe_write_json

    state = safe_read_json(STATE_FILE, default={})
    state["key"] = "value"
    safe_write_json(STATE_FILE, state)
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def safe_read_json(path: Path, default: Any = None) -> Any:
    """Read a JSON file safely. Returns default if file missing or corrupt."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def safe_write_json(path: Path, data: Any, indent: int = None) -> bool:
    """
    Write JSON to path atomically via temp file + os.replace().

    Returns True on success, False on failure (never raises).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, ensure_ascii=False, indent=indent)
        # Write to temp file in same directory (ensures same filesystem for rename)
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.tmp"
        )
        try:
            os.write(fd, text.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp_path, path)
        return True
    except Exception:
        # On failure, try to clean up temp file
        try:
            if "tmp_path" in dir():
                os.unlink(tmp_path)
        except Exception:
            pass
        return False
