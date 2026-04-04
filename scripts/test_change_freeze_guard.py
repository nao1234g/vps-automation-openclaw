#!/usr/bin/env python3
"""Regression tests for central change-freeze enforcement."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def run() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "change_freeze.json"
        os.environ["NOWPATTERN_CHANGE_FREEZE_STATE_PATH"] = str(state_path)
        try:
            import change_freeze_guard as guard  # noqa: WPS433

            state = guard.load_change_freeze_state()
            assert state["enabled"] is False

            enabled = guard.enable_change_freeze(
                reason="incident containment",
                enabled_by="test",
                scopes=["public_release", "distribution"],
            )
            assert enabled["enabled"] is True
            assert "public_release" in enabled["scopes"]

            blocked = False
            try:
                guard.assert_change_window(
                    scope="public_release",
                    actor="test-agent",
                    purpose="publish article",
                )
            except ValueError as exc:
                blocked = "CHANGE_FREEZE_ACTIVE" in str(exc)
            assert blocked, "change freeze did not block the governed release scope"

            allowed = guard.assert_change_window(
                scope="maintenance",
                actor="test-agent",
                purpose="repair-only",
            )
            assert allowed["active"] is False

            disabled = guard.disable_change_freeze(disabled_by="test")
            assert disabled["enabled"] is False
        finally:
            os.environ.pop("NOWPATTERN_CHANGE_FREEZE_STATE_PATH", None)

    print("PASS: change freeze guard regression checks")


if __name__ == "__main__":
    run()
