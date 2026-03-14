"""
apps/nowpattern/reader_vote_system.py
読者投票システム — 読者の予測参加 + コミュニティ統計

Nowpatternの読者参加型予測プラットフォームの中核コンポーネント。
reader_predictions.db (SQLite) と連携し、UUIDベースの匿名投票を管理する。
"""

import sys
import json
import os
import uuid
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_DB_PATH = "data/reader_predictions.db"


class ReaderVoteSystem:
    """
    読者投票の管理・統計・ランキング

    - UUID匿名投票（登録不要）
    - シナリオ別確率投票（5〜95、5刻み）
    - コミュニティ集計（平均・分布）
    - AI vs 読者比較
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    # ── DBセットアップ ──────────────────────────────────────

    def _init_db(self):
        """SQLiteスキーマを初期化する"""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id TEXT NOT NULL,
                    voter_uuid TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    probability INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(prediction_id, voter_uuid)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_prediction_id ON votes(prediction_id)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reader_scores (
                    voter_uuid TEXT PRIMARY KEY,
                    total_votes INTEGER DEFAULT 0,
                    resolved_votes INTEGER DEFAULT 0,
                    hits INTEGER DEFAULT 0,
                    total_brier REAL DEFAULT 0.0,
                    updated_at TEXT NOT NULL
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── 投票 ──────────────────────────────────────

    def cast_vote(self,
                  prediction_id: str,
                  voter_uuid: str,
                  scenario: str,
                  probability: int) -> Dict:
        """
        投票を記録する

        Args:
            prediction_id: 予測ID
            voter_uuid: 読者UUID（localStorageから）
            scenario: "optimistic" / "base" / "pessimistic"
            probability: 5〜95（5刻み）

        Returns:
            {"success", "vote_id", "community_stats"}
        """
        # バリデーション
        if scenario not in ("optimistic", "base", "pessimistic"):
            return {"success": False, "error": f"Invalid scenario: {scenario}"}
        if not (5 <= probability <= 95 and probability % 5 == 0):
            return {"success": False, "error": f"Invalid probability: {probability} (must be 5-95, step 5)"}

        now = datetime.now(timezone.utc).isoformat()

        try:
            with self._connect() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO votes
                    (prediction_id, voter_uuid, scenario, probability, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (prediction_id, voter_uuid, scenario, probability, now))

                # reader_scores を upsert
                conn.execute("""
                    INSERT INTO reader_scores (voter_uuid, total_votes, resolved_votes, hits, total_brier, updated_at)
                    VALUES (?, 1, 0, 0, 0.0, ?)
                    ON CONFLICT(voter_uuid) DO UPDATE SET
                        total_votes = total_votes + 1,
                        updated_at = ?
                """, (voter_uuid, now, now))

            stats = self.get_prediction_stats(prediction_id)
            return {"success": True, "community_stats": stats}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── 統計 ──────────────────────────────────────

    def get_prediction_stats(self, prediction_id: str) -> Dict:
        """予測別コミュニティ統計を返す"""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT scenario, probability, COUNT(*) as count
                FROM votes WHERE prediction_id = ?
                GROUP BY scenario, probability
                ORDER BY scenario, probability
            """, (prediction_id,)).fetchall()

            total_rows = conn.execute("""
                SELECT COUNT(*) as cnt, AVG(probability) as avg_prob
                FROM votes WHERE prediction_id = ?
            """, (prediction_id,)).fetchone()

        vote_count = total_rows["cnt"] if total_rows else 0
        avg_prob = round(total_rows["avg_prob"] or 0) if total_rows else 0

        # シナリオ別集計
        by_scenario: Dict[str, Dict] = {"optimistic": {}, "base": {}, "pessimistic": {}}
        for row in rows:
            s = row["scenario"]
            if s in by_scenario:
                by_scenario[s][row["probability"]] = row["count"]

        # 最頻値（モード）
        if rows:
            mode_row = max(rows, key=lambda r: r["count"])
            community_consensus = mode_row["probability"]
        else:
            community_consensus = 50

        return {
            "prediction_id": prediction_id,
            "total_votes": vote_count,
            "avg_probability": avg_prob,
            "community_consensus": community_consensus,
            "by_scenario": by_scenario,
        }

    def get_bulk_stats(self, prediction_ids: List[str]) -> Dict[str, Dict]:
        """複数予測の統計を一括取得する"""
        return {pid: self.get_prediction_stats(pid) for pid in prediction_ids}

    def get_reader_track_record(self, voter_uuid: str) -> Dict:
        """読者のトラックレコードを返す"""
        with self._connect() as conn:
            score = conn.execute("""
                SELECT * FROM reader_scores WHERE voter_uuid = ?
            """, (voter_uuid,)).fetchone()

            votes = conn.execute("""
                SELECT prediction_id, scenario, probability, created_at
                FROM votes WHERE voter_uuid = ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (voter_uuid,)).fetchall()

        if not score:
            return {"voter_uuid": voter_uuid, "total_votes": 0, "hit_rate": 0, "votes": []}

        avg_brier = (score["total_brier"] / max(score["resolved_votes"], 1))
        hit_rate = score["hits"] / max(score["resolved_votes"], 1) if score["resolved_votes"] > 0 else 0

        return {
            "voter_uuid": voter_uuid,
            "total_votes": score["total_votes"],
            "resolved_votes": score["resolved_votes"],
            "hits": score["hits"],
            "hit_rate": round(hit_rate, 3),
            "avg_brier": round(avg_brier, 4),
            "votes": [dict(v) for v in votes],
        }

    def resolve_reader_votes(self, prediction_id: str, result: str) -> Dict:
        """
        予測解決時に読者のBrier Scoreを計算・更新する

        Args:
            prediction_id: 予測ID
            result: "HIT" / "MISS"

        Returns:
            更新した読者数・平均Brier
        """
        outcome = 1 if result == "HIT" else 0
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            rows = conn.execute("""
                SELECT voter_uuid, probability FROM votes WHERE prediction_id = ?
            """, (prediction_id,)).fetchall()

            updated = 0
            total_brier = 0.0

            for row in rows:
                voter = row["voter_uuid"]
                prob = row["probability"] / 100
                brier = round((prob - outcome) ** 2, 4)
                is_hit = 1 if (result == "HIT" and prob >= 0.5) or (result == "MISS" and prob < 0.5) else 0
                total_brier += brier

                conn.execute("""
                    UPDATE reader_scores SET
                        resolved_votes = resolved_votes + 1,
                        hits = hits + ?,
                        total_brier = total_brier + ?,
                        updated_at = ?
                    WHERE voter_uuid = ?
                """, (is_hit, brier, now, voter))
                updated += 1

        avg_brier = round(total_brier / max(updated, 1), 4)
        return {"updated_voters": updated, "avg_reader_brier": avg_brier}

    def get_leaderboard(self, min_votes: int = 3, limit: int = 10) -> List[Dict]:
        """
        リーダーボード（Brier Score優秀順）

        Args:
            min_votes: 最低解決済み投票数
            limit: 返す件数

        Returns:
            [{rank, voter_uuid, hit_rate, avg_brier, resolved_votes}]
        """
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT voter_uuid, resolved_votes, hits,
                       CASE WHEN resolved_votes > 0 THEN total_brier / resolved_votes ELSE 1.0 END as avg_brier,
                       CASE WHEN resolved_votes > 0 THEN CAST(hits AS REAL) / resolved_votes ELSE 0 END as hit_rate
                FROM reader_scores
                WHERE resolved_votes >= ?
                ORDER BY avg_brier ASC, hit_rate DESC
                LIMIT ?
            """, (min_votes, limit)).fetchall()

        leaderboard = []
        for rank, row in enumerate(rows, 1):
            leaderboard.append({
                "rank": rank,
                "voter_uuid": row["voter_uuid"][:8] + "...",  # プライバシー保護
                "hit_rate": round(row["hit_rate"], 3),
                "avg_brier": round(row["avg_brier"], 4),
                "resolved_votes": row["resolved_votes"],
            })

        return leaderboard


if __name__ == "__main__":
    system = ReaderVoteSystem("data/reader_predictions.db")

    # デモ: 投票
    voter = str(uuid.uuid4())
    result = system.cast_vote("2026-03-01-001", voter, "base", 65)
    print(f"投票結果: {result['success']}")

    stats = system.get_prediction_stats("2026-03-01-001")
    print(f"コミュニティ統計: 総票数={stats['total_votes']}, 平均={stats['avg_probability']}%")
