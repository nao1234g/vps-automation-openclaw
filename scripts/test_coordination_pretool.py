#!/usr/bin/env python3
"""Regression checks for path-based local coordination locking."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / ".claude" / "hooks" / "coordination-pretool.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import coordination_utils as cu  # noqa: E402


def _load_module():
    spec = importlib.util.spec_from_file_location("coordination_pretool", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run() -> None:
    _load_module()

    assert cu.normalize_repo_relative_path(
        "/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/docs/OPERATIONS_BOARD.md"
    ) == "docs/OPERATIONS_BOARD.md"
    assert cu.normalize_repo_relative_path(
        "C:\\Users\\user\\OneDrive\\デスクトップ\\vps-automation-openclaw\\docs\\OPERATIONS_BOARD.md"
    ) == "docs/OPERATIONS_BOARD.md"
    assert cu.normalize_repo_relative_path("./scripts/update_operations_board.py") == (
        "scripts/update_operations_board.py"
    )
    assert cu.path_compare_key("./AGENTS.md") == "agents.md"

    assert cu.path_is_locked(
        "/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/update_operations_board.py",
        "scripts/update_operations_board.py",
    )
    assert not cu.path_is_locked(
        "/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/update_operations_board.py",
        "scripts/other_file.py",
    )
    assert cu.path_is_locked(
        "/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/update_operations_board.py",
        "update_operations_board.py",
    )
    assert not cu.path_is_locked(
        "/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/docs/update_operations_board.py",
        "scripts/update_operations_board.py",
    )

    print("PASS: coordination pretool path-lock regression checks")


if __name__ == "__main__":
    run()
