#!/usr/bin/env python3
"""
prediction_tracker.py — Nowpattern Prediction Tracking System

フライホイールの核心: 全記事の予測（3シナリオ+確率）を構造化DBに記録し、
結果判定→Brier Score計算→精度レポート生成を自動化する。

使い方:
  # 記事JSONから予測を自動記録（breaking_pipeline_helper.pyから呼ばれる）
  python3 prediction_tracker.py record /tmp/article_12345.json

  # 予測の結果を手動判定
  python3 prediction_tracker.py judge NP-2026-0042 --outcome base

  # 全予測のステータスを表示
  python3 prediction_tracker.py status

  # 四半期レポート生成
  python3 prediction_tracker.py report --quarter 2026-Q1

  # 未判定の予測でトリガー日を過ぎたものをリスト
  python3 prediction_tracker.py overdue

データ構造（prediction_db.json）:
{
  "predictions": [
    {
      "prediction_id": "NP-2026-0042",
      "article_title": "...",
      "ghost_url": "...",
      "published_at": "2026-02-21T...",
      "dynamics_tags": "力学タグ × 力学タグ",
      "genre_tags": "ジャンル",
      "scenarios": [
        {"label": "楽観", "probability": 0.30, "content": "..."},
        {"label": "基本", "probability": 0.50, "content": "..."},
        {"label": "悲観", "probability": 0.20, "content": "..."}
      ],
      "triggers": [["トリガー名", "2026-03-15"]],
      "open_loop_trigger": "2026年3月15日のFOMC声明",
      "status": "open",        # open / resolved
      "outcome": null,         # "楽観" / "基本" / "悲観"
      "resolved_at": null,
      "brier_score": null,
      "resolution_note": ""
    }
  ],
  "stats": {
    "total": 42,
    "resolved": 15,
    "open": 27,
    "avg_brier_score": 0.18,
    "last_updated": "2026-02-21T..."
  }
}
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone

PREDICTION_DB = "/opt/shared/scripts/prediction_db.json"
COUNTER_START = 1


def load_db():
    if os.path.exists(PREDICTION_DB):
        with open(PREDICTION_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"predictions": [], "stats": {"total": 0, "resolved": 0, "open": 0, "avg_brier_score": None, "last_updated": ""}}


def save_db(db):
    db["stats"] = compute_stats(db)
    with open(PREDICTION_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def compute_stats(db):
    preds = db["predictions"]
    total = len(preds)
    resolved = [p for p in preds if p["status"] == "resolved"]
    brier_scores = [p["brier_score"] for p in resolved if p["brier_score"] is not None]
    return {
        "total": total,
        "resolved": len(resolved),
        "open": total - len(resolved),
        "avg_brier_score": round(sum(brier_scores) / len(brier_scores), 4) if brier_scores else None,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def generate_prediction_id(db):
    """NP-YYYY-XXXX 形式のIDを生成"""
    year = datetime.now().year
    existing = [p["prediction_id"] for p in db["predictions"]]
    for i in range(COUNTER_START, 99999):
        pid = f"NP-{year}-{i:04d}"
        if pid not in existing:
            return pid
    return f"NP-{year}-{len(existing)+1:04d}"


def parse_probability(prob_str):
    """'30%' → 0.30, '0.3' → 0.30"""
    s = str(prob_str).strip().replace("%", "")
    try:
        val = float(s)
        if val > 1:
            val = val / 100.0
        return round(val, 4)
    except (ValueError, TypeError):
        return 0.0


def record_prediction(article_json_path):
    """記事JSONから予測を抽出してDBに記録"""
    with open(article_json_path, "r", encoding="utf-8") as f:
        article = json.load(f)

    db = load_db()

    # 重複チェック（同じtweet_idの予測が既にあるか）
    tweet_id = article.get("tweet_id", "")
    for p in db["predictions"]:
        if p.get("tweet_id") == tweet_id and tweet_id:
            print(f"  SKIP: tweet_id={tweet_id} の予測は既に記録済み（{p['prediction_id']}）")
            return p["prediction_id"]

    prediction_id = generate_prediction_id(db)

    # シナリオを構造化
    scenarios = []
    for s in article.get("scenarios", []):
        if isinstance(s, (list, tuple)) and len(s) >= 3:
            scenarios.append({
                "label": s[0],
                "probability": parse_probability(s[1]),
                "content": s[2],
                "action": s[3] if len(s) > 3 else "",
            })
        elif isinstance(s, dict):
            scenarios.append({
                "label": s.get("label", ""),
                "probability": parse_probability(s.get("probability", "0")),
                "content": s.get("content", ""),
                "action": s.get("action", ""),
            })

    # トリガーを構造化
    triggers = []
    for t in article.get("triggers", []):
        if isinstance(t, (list, tuple)) and len(t) >= 2:
            triggers.append({"name": t[0], "date": t[1]})

    now_iso = datetime.now(timezone.utc).isoformat()
    article_id = article.get("article_id", "")

    prediction = {
        "prediction_id": prediction_id,
        "article_id": article_id,
        "tweet_id": tweet_id,
        "article_title": article.get("title", ""),
        "ghost_url": "",  # 投稿後にupdate_ghost_urlで更新
        "published_at": now_iso,
        "dynamics_tags": article.get("dynamics_tags", ""),
        "genre_tags": article.get("genre_tags", ""),
        "scenarios": scenarios,
        "triggers": triggers,
        "open_loop_trigger": article.get("open_loop_trigger", ""),
        "open_loop_series": article.get("open_loop_series", ""),
        "status": "open",
        "outcome": None,
        "resolved_at": None,
        "brier_score": None,
        "resolution_note": "",
        # v5.0: Delta — probability change tracking
        "probability_history": [
            {
                "date": now_iso[:10],
                "article_id": article_id,
                "scenarios": [
                    {"label": s["label"], "probability": s["probability"]}
                    for s in scenarios
                ],
            }
        ],
    }

    db["predictions"].append(prediction)
    save_db(db)

    print(f"  📊 予測記録: {prediction_id} | {article.get('title', '')[:50]}")
    print(f"     シナリオ: {len(scenarios)}件 | トリガー: {len(triggers)}件")

    return prediction_id


def update_probability(prediction_id, new_scenarios, article_id="", reason=""):
    """同じトピックの新記事でシナリオ確率を更新し、履歴に追記（v5.0 Delta）"""
    db = load_db()
    for p in db["predictions"]:
        if p["prediction_id"] == prediction_id and p["status"] == "open":
            # 現在のシナリオを更新
            for i, s in enumerate(new_scenarios):
                if i < len(p["scenarios"]):
                    p["scenarios"][i]["probability"] = parse_probability(s.get("probability", 0))

            # 履歴に追記
            if "probability_history" not in p:
                p["probability_history"] = []
            p["probability_history"].append({
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "article_id": article_id,
                "scenarios": [
                    {"label": s.get("label", ""), "probability": parse_probability(s.get("probability", 0))}
                    for s in new_scenarios
                ],
                "reason": reason,
            })

            save_db(db)
            print(f"  📊 確率更新: {prediction_id} | 履歴{len(p['probability_history'])}件")
            return True
    return False


def update_ghost_url(prediction_id, ghost_url):
    """投稿後にGhost URLを更新"""
    db = load_db()
    for p in db["predictions"]:
        if p["prediction_id"] == prediction_id:
            p["ghost_url"] = ghost_url
            save_db(db)
            return True
    return False


def calculate_brier_score(scenarios, outcome_label):
    """Brier Scoreを計算
    outcome_label: 実際に起きたシナリオのラベル（例: "基本"）
    """
    score = 0.0
    for s in scenarios:
        actual = 1.0 if s["label"] == outcome_label else 0.0
        predicted = s["probability"]
        score += (predicted - actual) ** 2
    return round(score / len(scenarios), 4) if scenarios else None


def judge_prediction(prediction_id, outcome, note=""):
    """予測の結果を判定"""
    db = load_db()
    for p in db["predictions"]:
        if p["prediction_id"] == prediction_id:
            if p["status"] == "resolved":
                print(f"  ⚠️ {prediction_id} は既に判定済み（結果: {p['outcome']}）")
                return False

            p["status"] = "resolved"
            p["outcome"] = outcome
            p["resolved_at"] = datetime.now(timezone.utc).isoformat()
            p["brier_score"] = calculate_brier_score(p["scenarios"], outcome)
            p["resolution_note"] = note

            save_db(db)
            print(f"  ✅ 判定完了: {prediction_id}")
            print(f"     結果: {outcome}")
            print(f"     Brier Score: {p['brier_score']}")
            return True

    print(f"  ❌ {prediction_id} が見つかりません")
    return False


def show_status():
    """全予測のステータスを表示"""
    db = load_db()
    stats = db["stats"]

    print(f"📊 Nowpattern Prediction Tracker")
    print(f"   予測総数: {stats['total']}")
    print(f"   未判定: {stats['open']}")
    print(f"   判定済: {stats['resolved']}")
    if stats['avg_brier_score'] is not None:
        print(f"   平均Brier Score: {stats['avg_brier_score']}")
        if stats['avg_brier_score'] < 0.15:
            print(f"   → Superforecaster級 🏆")
        elif stats['avg_brier_score'] < 0.20:
            print(f"   → 優秀（上位10%）")
        elif stats['avg_brier_score'] < 0.25:
            print(f"   → 平均以上")
        else:
            print(f"   → 改善余地あり")

    # 直近5件の未判定予測
    open_preds = [p for p in db["predictions"] if p["status"] == "open"]
    if open_preds:
        print(f"\n📋 未判定の予測（直近5件）:")
        for p in open_preds[-5:]:
            trigger_info = p.get("open_loop_trigger", "")
            print(f"   {p['prediction_id']} | {p['article_title'][:40]}...")
            if trigger_info:
                print(f"     次のトリガー: {trigger_info}")

    # 直近5件の判定済み
    resolved = [p for p in db["predictions"] if p["status"] == "resolved"]
    if resolved:
        print(f"\n✅ 判定済みの予測（直近5件）:")
        for p in resolved[-5:]:
            print(f"   {p['prediction_id']} | {p['outcome']} | Brier: {p['brier_score']} | {p['article_title'][:30]}...")


def show_overdue():
    """トリガー日を過ぎた未判定予測をリスト"""
    db = load_db()
    now = datetime.now(timezone.utc)
    overdue = []

    for p in db["predictions"]:
        if p["status"] != "open":
            continue
        for trigger in p.get("triggers", []):
            trigger_date_str = trigger.get("date", "")
            try:
                # 日付パース（様々な形式に対応）
                for fmt in ["%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d"]:
                    try:
                        trigger_dt = datetime.strptime(trigger_date_str, fmt).replace(tzinfo=timezone.utc)
                        if trigger_dt < now:
                            overdue.append((p, trigger))
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

    if overdue:
        print(f"⚠️ トリガー日超過の未判定予測: {len(overdue)}件")
        for p, trigger in overdue:
            print(f"   {p['prediction_id']} | トリガー: {trigger['name']} ({trigger['date']})")
            print(f"     記事: {p['article_title'][:50]}...")
    else:
        print("✅ トリガー日超過の未判定予測はありません")


def generate_report(quarter=None):
    """四半期予測精度レポートを生成"""
    db = load_db()
    resolved = [p for p in db["predictions"] if p["status"] == "resolved"]

    if not resolved:
        print("判定済みの予測がまだありません。記事が蓄積されるのを待ちましょう。")
        return

    # Brier Scoreの分布
    scores = [p["brier_score"] for p in resolved if p["brier_score"] is not None]
    avg_score = sum(scores) / len(scores) if scores else 0

    # 力学タグ別の精度
    dynamics_scores = {}
    for p in resolved:
        dtag = p.get("dynamics_tags", "other")
        if dtag not in dynamics_scores:
            dynamics_scores[dtag] = []
        if p["brier_score"] is not None:
            dynamics_scores[dtag].append(p["brier_score"])

    # 結果分布
    outcome_counts = {}
    for p in resolved:
        o = p.get("outcome", "unknown")
        outcome_counts[o] = outcome_counts.get(o, 0) + 1

    print(f"═══ Nowpattern Prediction Report ═══")
    print(f"判定済み: {len(resolved)}件")
    print(f"平均Brier Score: {avg_score:.4f}")
    print()

    print("力学タグ別精度:")
    for dtag, s_list in sorted(dynamics_scores.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else 1):
        avg = sum(s_list) / len(s_list) if s_list else 0
        print(f"   {dtag}: {avg:.4f} ({len(s_list)}件)")

    print()
    print("結果分布:")
    for outcome, count in sorted(outcome_counts.items()):
        print(f"   {outcome}: {count}件 ({count/len(resolved)*100:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description="Nowpattern Prediction Tracker")
    subparsers = parser.add_subparsers(dest="command")

    # record
    record_parser = subparsers.add_parser("record", help="記事JSONから予測を記録")
    record_parser.add_argument("json_file", help="記事JSONファイルのパス")

    # judge
    judge_parser = subparsers.add_parser("judge", help="予測の結果を判定")
    judge_parser.add_argument("prediction_id", help="予測ID（NP-YYYY-XXXX）")
    judge_parser.add_argument("--outcome", required=True, help="実際に起きたシナリオ（楽観/基本/悲観）")
    judge_parser.add_argument("--note", default="", help="判定メモ")

    # status
    subparsers.add_parser("status", help="全予測のステータスを表示")

    # overdue
    subparsers.add_parser("overdue", help="トリガー日超過の未判定予測")

    # report
    report_parser = subparsers.add_parser("report", help="予測精度レポート生成")
    report_parser.add_argument("--quarter", default=None, help="四半期（例: 2026-Q1）")

    args = parser.parse_args()

    if args.command == "record":
        record_prediction(args.json_file)
    elif args.command == "judge":
        judge_prediction(args.prediction_id, args.outcome, args.note)
    elif args.command == "status":
        show_status()
    elif args.command == "overdue":
        show_overdue()
    elif args.command == "report":
        generate_report(args.quarter)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
