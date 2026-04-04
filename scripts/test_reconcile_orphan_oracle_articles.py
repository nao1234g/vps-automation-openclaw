#!/usr/bin/env python3
"""Regression tests for orphan oracle reconciliation."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import reconcile_orphan_oracle_articles as roa  # noqa: E402


def _write_prediction_db(path: Path) -> None:
    payload = {
        "predictions": [
            {
                "prediction_id": "NP-TEST-1",
                "resolution_question": "Will the Strait of Hormuz remain open through April 2026?",
                "resolution_question_ja": "2026年4月を通じてホルムズ海峡は開いたまま維持されるか？",
                "article_links": [],
            }
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _init_ghost_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE posts (
            id TEXT PRIMARY KEY,
            slug TEXT,
            title TEXT,
            html TEXT,
            status TEXT,
            type TEXT,
            published_at TEXT
        );
        CREATE TABLE tags (
            id TEXT PRIMARY KEY,
            slug TEXT
        );
        CREATE TABLE posts_tags (
            post_id TEXT,
            tag_id TEXT
        );
        """
    )
    con.execute("INSERT INTO tags (id, slug) VALUES ('t1', 'lang-ja')")
    con.close()


def test_exact_question_match_relinks_prediction() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pred_db = tmp_path / "prediction_db.json"
        ghost_db = tmp_path / "ghost.db"
        _write_prediction_db(pred_db)
        _init_ghost_db(ghost_db)
        con = sqlite3.connect(ghost_db)
        con.execute(
            """
            INSERT INTO posts (id, slug, title, html, status, type, published_at)
            VALUES (?, ?, ?, ?, 'published', 'post', '2026-04-02T00:00:00Z')
            """,
            (
                "p1",
                "hormuz-open-test",
                "ホルムズ海峡テスト",
                """
                <article>
                  <div id="np-oracle">
                    <p>予測質問: <strong>2026年4月を通じてホルムズ海峡は開いたまま維持されるか？</strong></p>
                  </div>
                </article>
                """,
            ),
        )
        con.execute("INSERT INTO posts_tags (post_id, tag_id) VALUES ('p1', 't1')")
        con.commit()
        con.close()

        report = roa.reconcile(
            prediction_db_path=pred_db,
            ghost_db_path=ghost_db,
            strip_unmatched=True,
            dry_run=False,
        )
        payload = json.loads(pred_db.read_text(encoding="utf-8"))
        pred = payload["predictions"][0]
        assert report["matched_predictions"] == 1, report
        assert pred["article_slug"] == "hormuz-open-test", pred
        assert pred["ghost_url"].endswith("/hormuz-open-test/"), pred
        assert pred["article_links"][0]["lang"] == "ja", pred


def test_unmatched_oracle_block_is_stripped() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pred_db = tmp_path / "prediction_db.json"
        ghost_db = tmp_path / "ghost.db"
        _write_prediction_db(pred_db)
        _init_ghost_db(ghost_db)
        con = sqlite3.connect(ghost_db)
        con.execute(
            """
            INSERT INTO posts (id, slug, title, html, status, type, published_at)
            VALUES (?, ?, ?, ?, 'published', 'post', '2026-04-02T00:00:00Z')
            """,
            (
                "p2",
                "unmatched-oracle-test",
                "未接続オラクル",
                """
                <article>
                  <hr>
                  <div id="np-oracle">
                    <p>予測質問: <strong>一致しない質問ですか？</strong></p>
                    <div><p>inner</p></div>
                  </div>
                  <p>本文は残る。</p>
                </article>
                """,
            ),
        )
        con.execute("INSERT INTO posts_tags (post_id, tag_id) VALUES ('p2', 't1')")
        con.commit()

        report = roa.reconcile(
            prediction_db_path=pred_db,
            ghost_db_path=ghost_db,
            strip_unmatched=True,
            dry_run=False,
        )
        html = con.execute("SELECT html FROM posts WHERE id='p2'").fetchone()[0]
        con.close()
        assert report["stripped_to_analysis_only"] == 1, report
        assert "np-oracle" not in html, html
        assert "本文は残る" in html, html


def run() -> None:
    test_exact_question_match_relinks_prediction()
    test_unmatched_oracle_block_is_stripped()
    print("PASS: reconcile_orphan_oracle_articles regression checks")


if __name__ == "__main__":
    run()
