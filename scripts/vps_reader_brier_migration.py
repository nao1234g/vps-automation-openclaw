#!/usr/bin/env python3
"""
vps_reader_brier_migration.py — reader_predictions.db Brier Score マイグレーション

I5: 読者Brier Score自動計算 — VPS側の実行スクリプト

このスクリプトは VPS 上で直接実行する（ローカルPCからではない）:
    python3 /opt/shared/scripts/vps_reader_brier_migration.py [--dry-run] [--verbose]

実行内容:
  1. reader_predictions.db に brier_score / resolved_at / outcome カラムを追加（なければ）
  2. prediction_db.json から解決済み予測の結果（outcome）を取得
  3. 該当する読者投票行の brier_score を計算・書き込み
  4. Telegram に完了通知を送信（--notify フラグ時）

計算式: brier_score = (probability/100 - outcome)^2
  - outcome: 1.0 = 予測が的中, 0.0 = 予測が外れ
  - 読者が投票した scenario が actual_outcome と一致すれば outcome=1.0

依存:
  - /opt/shared/reader_predictions.db
  - /opt/shared/polymarket/prediction_db.json
  - /opt/cron-env.sh（Telegram 通知用）
"""

import sys
import os
import json
import sqlite3
import argparse
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── パス定義 ────────────────────────────────────────────────────────────
DB_PATH = os.environ.get(
    "READER_PREDICTIONS_DB",
    "/opt/shared/reader_predictions.db"
)
PREDICTION_DB_PATH = os.environ.get(
    "PREDICTION_DB_PATH",
    "/opt/shared/polymarket/prediction_db.json"
)
CRON_ENV_PATH = "/opt/cron-env.sh"


# ─── Brier Score 計算 ────────────────────────────────────────────────────

def calc_brier(probability: float, outcome: float) -> float:
    """brier_score = (probability/100 - outcome)^2"""
    p = max(0.0, min(100.0, float(probability))) / 100.0
    o = float(outcome)
    return round((p - o) ** 2, 6)


# ─── DB マイグレーション ─────────────────────────────────────────────────

def migrate_schema(conn: sqlite3.Connection, verbose: bool = False) -> dict:
    """brier_score / resolved_at / outcome カラムを追加する（既存なければ）"""
    cur = conn.cursor()
    added = []

    # 現在のカラム一覧を取得
    cur.execute("PRAGMA table_info(reader_votes)")
    existing_cols = {row[1] for row in cur.fetchall()}

    new_cols = [
        ("brier_score", "REAL"),
        ("resolved_at", "TEXT"),
        ("outcome",     "REAL"),
    ]

    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            sql = f"ALTER TABLE reader_votes ADD COLUMN {col_name} {col_type}"
            if verbose:
                print(f"  [SQL] {sql}")
            cur.execute(sql)
            added.append(col_name)
            print(f"  [SCHEMA] カラム追加: {col_name} ({col_type})")
        else:
            if verbose:
                print(f"  [SCHEMA] {col_name}: 既存（スキップ）")

    conn.commit()
    return {"added_columns": added}


# ─── 解決済み予測の読み込み ──────────────────────────────────────────────

def load_resolved_predictions(path: str) -> dict:
    """prediction_db.json から解決済み予測を読み込む。

    Returns:
        {prediction_id: {"actual_outcome": "base"|"optimistic"|"pessimistic",
                         "resolved_at": "2026-MM-DD",
                         "resolved": True}}
    """
    if not os.path.exists(path):
        print(f"[WARN] prediction_db.json が見つからない: {path}", file=sys.stderr)
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] prediction_db.json の読み込み失敗: {e}", file=sys.stderr)
        return {}

    predictions = data if isinstance(data, list) else data.get("predictions", [])
    resolved = {}
    for p in predictions:
        if not p.get("resolved"):
            continue
        pid = p.get("id") or p.get("prediction_id")
        if not pid:
            continue
        # actual_outcome: どのシナリオが的中したか
        actual = p.get("actual_outcome") or p.get("outcome")
        resolved_at = p.get("resolved_at") or p.get("resolution_date")
        resolved[str(pid)] = {
            "actual_outcome": actual,
            "resolved_at":    resolved_at,
            "resolved":       True,
        }

    return resolved


# ─── シナリオ → outcome 変換 ─────────────────────────────────────────────

def scenario_to_outcome(voted_scenario: str, actual_outcome: str) -> float:
    """読者の投票シナリオと実際の結果を比較して outcome (0.0/1.0) を返す。

    outcome = 1.0: 読者が正しいシナリオに投票した
    outcome = 0.0: 読者が外れたシナリオに投票した

    actual_outcome が None の場合は None を返す（未確定）。
    """
    if actual_outcome is None:
        return None
    vs = (voted_scenario or "").lower().strip()
    ao = (actual_outcome or "").lower().strip()
    return 1.0 if vs == ao else 0.0


# ─── Brier Score 更新 ────────────────────────────────────────────────────

def update_brier_scores(
    conn: sqlite3.Connection,
    resolved: dict,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """解決済み予測に対応する読者投票行の brier_score を更新する。"""
    cur = conn.cursor()

    # 更新対象: brier_score が NULL で prediction_id が解決済みのもの
    prediction_ids = list(resolved.keys())
    if not prediction_ids:
        return {"updated": 0, "skipped": 0, "errors": 0}

    placeholders = ",".join("?" * len(prediction_ids))
    cur.execute(
        f"""
        SELECT id, prediction_id, voter_uuid, scenario, probability
        FROM reader_votes
        WHERE prediction_id IN ({placeholders})
          AND brier_score IS NULL
        """,
        prediction_ids,
    )
    rows = cur.fetchall()

    updated = 0
    skipped = 0
    errors = 0

    for row_id, pred_id, voter_uuid, scenario, probability in rows:
        info = resolved.get(str(pred_id), {})
        actual = info.get("actual_outcome")
        resolved_at = info.get("resolved_at")

        outcome = scenario_to_outcome(scenario, actual)
        if outcome is None:
            if verbose:
                print(f"  [SKIP] vote_id={row_id} pred={pred_id}: actual_outcome 未確定")
            skipped += 1
            continue

        try:
            score = calc_brier(probability or 50, outcome)
        except Exception as e:
            print(f"  [ERROR] vote_id={row_id}: Brier 計算失敗: {e}", file=sys.stderr)
            errors += 1
            continue

        if verbose:
            print(
                f"  [UPDATE] vote_id={row_id} pred={pred_id} "
                f"scenario={scenario} prob={probability} "
                f"outcome={outcome} brier={score}"
            )

        if not dry_run:
            cur.execute(
                """
                UPDATE reader_votes
                SET brier_score = ?, resolved_at = ?, outcome = ?
                WHERE id = ?
                """,
                (score, resolved_at, outcome, row_id),
            )
        updated += 1

    if not dry_run:
        conn.commit()

    return {"updated": updated, "skipped": skipped, "errors": errors}


# ─── Telegram 通知 ──────────────────────────────────────────────────────

def send_telegram(msg: str) -> bool:
    """Telegram にメッセージを送信する。"""
    import urllib.request

    env = {}
    if os.path.exists(CRON_ENV_PATH):
        try:
            for line in open(CRON_ENV_PATH):
                if line.startswith("export "):
                    k, _, v = line[7:].strip().partition("=")
                    env[k] = v.strip().strip('"').strip("'")
        except Exception:
            pass

    token = env.get("TELEGRAM_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    chat_id = env.get("TELEGRAM_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", ""))

    if not token or not chat_id:
        print("[WARN] Telegram 認証情報が見つからない — 通知をスキップ", file=sys.stderr)
        return False

    data = json.dumps({
        "chat_id": chat_id, "text": msg, "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        print(f"[WARN] Telegram 送信失敗: {e}", file=sys.stderr)
        return False


# ─── メイン ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="reader_predictions.db Brier Score マイグレーション（VPS上で実行）"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="実際の DB 書き込みをスキップ（テスト実行）")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="詳細ログを表示")
    parser.add_argument("--notify", action="store_true",
                        help="完了後に Telegram 通知を送信")
    parser.add_argument("--db", default=DB_PATH,
                        help=f"DB パス（デフォルト: {DB_PATH}）")
    parser.add_argument("--prediction-db", default=PREDICTION_DB_PATH,
                        help=f"prediction_db.json パス（デフォルト: {PREDICTION_DB_PATH}）")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== Brier Score Migration {ts} ===")
    if args.dry_run:
        print("[DRY-RUN] DB への書き込みはスキップします")

    # DB 接続
    if not os.path.exists(args.db):
        print(f"[ERROR] DB が見つからない: {args.db}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        # Step 1: スキーママイグレーション
        print("\n[Step 1] スキーママイグレーション...")
        schema_result = migrate_schema(conn, verbose=args.verbose)

        # Step 2: 解決済み予測の読み込み
        print(f"\n[Step 2] 解決済み予測を読み込み: {args.prediction_db}")
        resolved = load_resolved_predictions(args.prediction_db)
        print(f"  解決済み予測: {len(resolved)} 件")

        # Step 3: Brier Score 更新
        print("\n[Step 3] Brier Score を計算・更新...")
        result = update_brier_scores(
            conn, resolved,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        print(f"  更新: {result['updated']} 件")
        print(f"  スキップ（未確定）: {result['skipped']} 件")
        print(f"  エラー: {result['errors']} 件")

        # Step 4: サマリー
        print(f"\n{'─'*50}")
        print(f"[{'DRY-RUN ' if args.dry_run else ''}COMPLETE]")
        print(f"  スキーマ追加カラム: {schema_result['added_columns']}")
        print(f"  Brier Score 更新: {result['updated']} 行")

        if args.notify and not args.dry_run:
            msg = (
                f"✅ *Brier Score マイグレーション完了*\n"
                f"更新: {result['updated']} 件\n"
                f"エラー: {result['errors']} 件\n"
                f"実行: {ts}"
            )
            send_telegram(msg)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
