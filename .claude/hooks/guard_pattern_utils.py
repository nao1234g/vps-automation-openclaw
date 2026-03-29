#!/usr/bin/env python3
"""Helpers for parsing GUARD_PATTERN blocks from KNOWN_MISTAKES.md."""

import json
import re
from pathlib import Path

STANDARD_GUARD_PATTERN_RE = re.compile(
    r'\*\*GUARD_PATTERN\*\*\s*:\s*`(\{[^`]+\})`',
    re.MULTILINE,
)
ALT_GUARD_PATTERN_RE = re.compile(
    r'`GUARD_PATTERN:\s*(\{[^`]+\})`',
    re.MULTILINE,
)


def extract_guard_pattern_names(text: str) -> set[str]:
    names: set[str] = set()
    for raw in STANDARD_GUARD_PATTERN_RE.findall(text) + ALT_GUARD_PATTERN_RE.findall(text):
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        name = parsed.get("name", "")
        if name:
            names.add(name)
    return names


def load_guard_pattern_names(path: Path) -> set[str]:
    return extract_guard_pattern_names(path.read_text(encoding="utf-8"))
