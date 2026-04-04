#!/usr/bin/env python3
"""Regression tests for the shared release governor wrapper."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from release_governor import (  # noqa: E402
    GOVERNOR_POLICY_VERSION,
    assert_governed_release_ready,
    evaluate_governed_release,
)


def test_governor_marks_payload_as_governed() -> None:
    result = evaluate_governed_release(
        title="Analysis with official source",
        html='<article><a href="https://openai.com/index/gpt-6/">Source</a></article>',
        source_urls=["https://openai.com/index/gpt-6/"],
        tags=["frontier-ai", "human-approved"],
        site_url="https://nowpattern.com",
        status="published",
        channel="public",
        require_external_sources=True,
    )
    assert result["governed"] is True
    assert result["governor_policy_version"] == GOVERNOR_POLICY_VERSION
    assert result["mission_contract_version"]
    assert result["mission_contract_hash"]
    assert result["lexicon_version"]


def test_assert_governor_raises_on_invalid_release() -> None:
    try:
        assert_governed_release_ready(
            title="GPT-9 launched today",
            html="<article><p>Rumor only</p></article>",
            source_urls=[],
            tags=["frontier-ai"],
            site_url="https://nowpattern.com",
            status="published",
            channel="public",
            require_external_sources=True,
        )
    except ValueError:
        return
    raise AssertionError("shared release governor allowed invalid frontier release")


def test_assert_governor_respects_change_freeze() -> None:
    import os
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "change_freeze.json"
        original_state_path = None
        os.environ["NOWPATTERN_CHANGE_FREEZE_STATE_PATH"] = str(state_path)
        try:
            import change_freeze_guard as guard  # noqa: WPS433

            original_state_path = guard.STATE_PATH
            guard.STATE_PATH = state_path
            guard.write_change_freeze_state(guard.default_state())
            guard.enable_change_freeze(
                reason="integration test",
                enabled_by="test",
                scopes=["public_release", "distribution"],
            )
            try:
                assert_governed_release_ready(
                    title="Source-backed article",
                    html='<article><a href="https://openai.com/index/gpt-5-4/">Source</a></article>',
                    source_urls=["https://openai.com/index/gpt-5-4/"],
                    tags=["analysis"],
                    site_url="https://nowpattern.com",
                    status="published",
                    channel="public",
                    require_external_sources=True,
                )
            except ValueError as exc:
                assert "CHANGE_FREEZE_ACTIVE" in str(exc)
            else:
                raise AssertionError("release governor bypassed active change freeze")
        finally:
            if original_state_path is not None:
                guard.STATE_PATH = original_state_path
            os.environ.pop("NOWPATTERN_CHANGE_FREEZE_STATE_PATH", None)


def test_assert_governor_respects_credibility_budget() -> None:
    import json
    import os
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "one_pass_completion_gate.json"
        state_path = Path(tmpdir) / "change_freeze.json"
        original_state_path = None
        report_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "checks": {
                        "prediction_deploy_gate": {
                            "json": {
                                "manifest_counts": {
                                    "published_total": 10,
                                    "truth_blocked": 1,
                                    "high_risk_unapproved": 0,
                                },
                                "tracker_summary": {"orphan_oracle_articles": 0},
                                "operational_metrics": {
                                    "distribution_allowed_ratio_pct": 100.0,
                                    "approval_backlog_ratio_pct": 0.0,
                                },
                            }
                        },
                        "ecosystem_governance_audit": {"failed": 0},
                        "synthetic_user_crawler": {"failed": 0},
                        "site_ui_smoke_audit": {"summary": {"failed": 0}},
                        "playwright_e2e_predictions": {"ok": True},
                        "check_live_repo_drift": {"ok": True},
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.environ["NOWPATTERN_ONE_PASS_REPORT_PATH"] = str(report_path)
        os.environ["NOWPATTERN_CHANGE_FREEZE_STATE_PATH"] = str(state_path)
        try:
            import change_freeze_guard as guard  # noqa: WPS433

            original_state_path = guard.STATE_PATH
            guard.STATE_PATH = state_path
            guard.write_change_freeze_state(guard.default_state())
            try:
                assert_governed_release_ready(
                    title="Source-backed article",
                    html='<article><a href="https://openai.com/index/gpt-5-4/">Source</a></article>',
                    source_urls=["https://openai.com/index/gpt-5-4/"],
                    tags=["analysis"],
                    site_url="https://nowpattern.com",
                    status="published",
                    channel="public",
                    require_external_sources=True,
                )
            except ValueError as exc:
                assert "CREDIBILITY_BUDGET_EXCEEDED" in str(exc)
            else:
                raise AssertionError("release governor bypassed exceeded credibility budget")
        finally:
            if original_state_path is not None:
                guard.STATE_PATH = original_state_path
            os.environ.pop("NOWPATTERN_ONE_PASS_REPORT_PATH", None)
            os.environ.pop("NOWPATTERN_CHANGE_FREEZE_STATE_PATH", None)


def run() -> None:
    test_governor_marks_payload_as_governed()
    test_assert_governor_raises_on_invalid_release()
    test_assert_governor_respects_change_freeze()
    test_assert_governor_respects_credibility_budget()
    print("PASS: release governor regression checks")


if __name__ == "__main__":
    run()
