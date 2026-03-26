#!/usr/bin/env python3
"""Debug: stdin の構造を state/debug_stdin.json に保存"""
import json, sys
from pathlib import Path

try:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {"empty": True}
    out = Path(__file__).parent / "state" / "debug_stdin.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2)[:3000], encoding="utf-8")
except Exception as e:
    err = Path(__file__).parent / "state" / "debug_error.txt"
    err.write_text(str(e))

sys.exit(0)
