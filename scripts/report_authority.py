#!/usr/bin/env python3
"""Load canonical reports from the authoritative source of truth."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
LOCAL_REPORT_DIR = REPO_ROOT / "reports"
LOCAL_DATA_DIR = REPO_ROOT / "data"
IS_LIVE_RUNTIME = Path(__file__).resolve().as_posix().startswith("/opt/shared/")
REMOTE_HOST = os.environ.get("NOWPATTERN_VPS_HOST", "root@163.44.124.123")
AUTHORITY_MODE = os.environ.get("NOWPATTERN_REPORT_AUTHORITY_MODE", "prefer_live").strip().lower()
SSH_TIMEOUT_SECONDS = int(os.environ.get("NOWPATTERN_REPORT_AUTHORITY_TIMEOUT_SECONDS", "8"))

REMOTE_REPORT_MAP = {
    str(LOCAL_REPORT_DIR / "content_release_snapshot.json"): "/opt/shared/reports/content_release_snapshot.json",
    str(LOCAL_REPORT_DIR / "ecosystem_governance_audit.json"): "/opt/shared/reports/ecosystem_governance_audit.json",
    str(LOCAL_REPORT_DIR / "one_pass_completion_gate.json"): "/opt/shared/reports/one_pass_completion_gate.json",
    str(LOCAL_REPORT_DIR / "article_release_manifest.json"): "/opt/shared/reports/article_release_manifest.json",
    str(LOCAL_REPORT_DIR / "prediction_article_integrity.json"): "/opt/shared/reports/prediction_article_integrity.json",
    str(LOCAL_REPORT_DIR / "site_guard" / "prediction_maturity_audit.json"): "/opt/shared/reports/site_guard/prediction_maturity_audit.json",
    str(LOCAL_DATA_DIR / "mistake_registry.json"): "/opt/shared/data/mistake_registry.json",
}


def _read_local_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _fetch_remote_json(remote_path: str) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ssh",
            "-o",
            f"ConnectTimeout={SSH_TIMEOUT_SECONDS}",
            REMOTE_HOST,
            (
                "python3 - <<'PY'\n"
                "import json, pathlib\n"
                f"path = pathlib.Path({remote_path!r})\n"
                "if not path.exists():\n"
                "    raise SystemExit(3)\n"
                "print(path.read_text(encoding='utf-8'))\n"
                "PY"
            ),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        return {}
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_authoritative_json(local_path: Path, *, sync_local: bool = True) -> dict[str, Any]:
    if IS_LIVE_RUNTIME:
        return _read_local_json(local_path)

    path_key = str(local_path.resolve())
    remote_path = REMOTE_REPORT_MAP.get(path_key)
    if AUTHORITY_MODE == "local" or not remote_path:
        return _read_local_json(local_path)

    remote_payload = _fetch_remote_json(remote_path)
    if remote_payload:
        if sync_local:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(json.dumps(remote_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return remote_payload
    return _read_local_json(local_path)
