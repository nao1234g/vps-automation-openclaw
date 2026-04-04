#!/usr/bin/env python3
"""Regression tests for prediction ops scheduler due-map."""

from __future__ import annotations

from datetime import datetime, timezone

import prediction_ops_scheduler as pos


def _keys(hour: int, minute: int) -> list[str]:
    report = pos.run_due(datetime(2026, 4, 2, hour, minute, tzinfo=timezone.utc), dry_run=True)
    return [item["key"] for item in report["executed"]]


def run() -> None:
    assert set(_keys(0, 0)) == {"prediction_auto_verifier", "polymarket_updater", "market_history_crawler"}
    assert _keys(0, 10) == ["apply_polymarket_matches"]
    assert _keys(1, 0) == ["prediction_resolver"]
    assert _keys(1, 10) == ["sync_stats"]
    assert _keys(6, 0) == ["prediction_verifier"]
    assert set(_keys(15, 0)) == {"daily_learning_0", "inject_live_panel_15"}
    assert _keys(16, 0) == ["prediction_cron_update"]
    assert _keys(22, 0) == ["prediction_page_builder_ja"]
    assert _keys(22, 30) == ["prediction_page_builder_en"]
    assert _keys(20, 55) == ["polymarket_monitor_20"]
    assert _keys(20, 57) == ["polymarket_delta_20"]
    print("PASS: prediction ops scheduler regression checks")


if __name__ == "__main__":
    run()
