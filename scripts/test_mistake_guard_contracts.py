#!/usr/bin/env python3
"""Contract tests that the repo still contains guards for historically costly mistakes."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")


def test_m001_ghost_settings_sqlite_guard_documented() -> None:
    text = _read(".claude/CLAUDE.md")
    assert "Ghost Settings API 501" in text
    assert "ghost.db" in text


def test_m002_m020_lowercase_oracle_anchor_guard_present() -> None:
    content_rules = _read(".claude/rules/content-rules.md")
    tracker_test = _read("scripts/test_prediction_tracker_regressions.py")
    assert "nowpattern.com/predictions/#np-2026-0042" in content_rules
    assert "/predictions/#np-2026-0042" in tracker_test


def test_m004_evolution_log_list_guard_documented() -> None:
    text = _read("docs/KNOWN_MISTAKES.md")
    assert "isinstance(entries, list)" in text
    assert "entries[-1]" in text


def test_m008_chromadb_guard_documented() -> None:
    text = _read("docs/AGENT_WISDOM.md")
    assert "chromadb 1.5.5" in text
    assert "daily_memory_harvest.py" in text


def test_m009_null_byte_sanitizer_present() -> None:
    text = _read("scripts/neo_queue_dispatcher.py")
    assert "replace(chr(0), '')" in text


def test_m010_genre_prefix_guard_present() -> None:
    validator = _read("scripts/article_validator.py")
    claude = _read(".claude/CLAUDE.md")
    assert "VALID_GENRE_SLUGS" in validator
    assert "genre-*" in validator
    assert "ENタグ監査で全件FAILと誤検知" in claude


def test_m012_pattern_history_guard_present() -> None:
    builder = _read("scripts/nowpattern_article_builder.py")
    patterns = _read(".claude/hooks/state/mistake_patterns.json")
    assert 'case.get("event"' in builder
    assert 'case.get("pattern"' in builder
    assert 'case.get("lesson"' in builder
    assert "PATTERN_HISTORY_FIELD_MISMATCH" in patterns


def test_m013_en_public_url_contract_documented() -> None:
    text = _read(".claude/CLAUDE.md")
    assert "/en/[name]/" in text
    assert "Ghost slugはen-[name]" in text


def test_m014_time_estimate_guard_pattern_present() -> None:
    checker = _read(".claude/hooks/fact-checker.py")
    mistakes = _read("docs/KNOWN_MISTAKES.md")
    assert "コード未読見積もり" in checker
    assert "Read/Glob/Grep" in checker
    assert "時間見積もり" in mistakes
    assert "Read/Glob/Grep" in mistakes


def test_m015_m016_noindex_contract_present() -> None:
    seo = _read("scripts/seo_monitor_v2.py")
    mistakes = _read("docs/KNOWN_MISTAKES.md")
    assert "X-Robots-Tag" in seo
    assert "noindex, follow" in seo
    assert "robots.txt Disallow" in mistakes


def test_m017_url_404_delivery_guard_present() -> None:
    publisher = _read("scripts/nowpattern_publisher.py")
    patterns = _read(".claude/hooks/state/mistake_patterns.json")
    assert "verify_public_url" in publisher
    assert "URL_404_DELIVERY" in patterns


def test_m018_substack_api_guard_documented() -> None:
    text = _read(".claude/CLAUDE.md")
    assert "Substack CAPTCHA" in text
    assert "connect.sid" in text


def test_m019_openclaw_pairing_guard_documented() -> None:
    text = _read(".claude/CLAUDE.md")
    infra = _read(".claude/rules/infrastructure.md")
    assert "openclaw.json" in text
    assert "CLIフラグではない" in text
    assert "OpenClaw設定" in infra


def test_m021_dev_page_lifecycle_audit_exists() -> None:
    audit = _read("scripts/site_dev_page_audit.py")
    assert "predictions" in audit
    assert "dev_page_visible" in audit


def test_m022_truth_guard_regression_exists() -> None:
    test_file = _read("scripts/test_article_release_guard.py")
    assert "UNSUPPORTED_FRONTIER_RELEASE_CLAIM" in test_file


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failures = []
    for name in tests:
        try:
            globals()[name]()
        except Exception as exc:  # pragma: no cover - standalone runner
            failures.append(f"{name}: {exc}")
    if failures:
        for item in failures:
            print(f"FAIL {item}")
        raise SystemExit(1)
    print(f"PASS: {len(tests)}/{len(tests)} mistake guard contracts")
