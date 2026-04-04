#!/usr/bin/env python3
"""Regression checks for authoritative report loading."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import report_authority as authority  # noqa: E402


def test_local_mode_uses_local_payload() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "report.json"
        payload = {"ok": True, "generated_at": "2026-04-03T00:00:00Z"}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        original_mode = authority.AUTHORITY_MODE
        authority.AUTHORITY_MODE = "local"
        try:
            loaded = authority.load_authoritative_json(path, sync_local=False)
        finally:
            authority.AUTHORITY_MODE = original_mode
        assert loaded == payload


def run() -> None:
    test_local_mode_uses_local_payload()
    print("PASS: report authority regression checks")


if __name__ == "__main__":
    run()
