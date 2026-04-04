#!/usr/bin/env python3
"""Regression tests for synthetic user freshness audit."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from synthetic_user_freshness_audit import run_audit


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "latest.json"
        report_path.write_text(
            json.dumps({"generated_at_epoch": int(time.time()), "failed": 0, "total": 3}),
            encoding="utf-8",
        )
        ok = run_audit(report_path, 3600)
        assert not ok["failures"], ok

        stale_path = Path(tmpdir) / "stale.json"
        stale_path.write_text(
            json.dumps({"generated_at_epoch": int(time.time()) - 7200, "failed": 0, "total": 3}),
            encoding="utf-8",
        )
        stale = run_audit(stale_path, 3600)
        assert any(item.startswith("full_crawl_stale:") for item in stale["failures"]), stale
    print("PASS: synthetic user freshness audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

