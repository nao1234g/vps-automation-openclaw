#!/usr/bin/env python3
"""
Phase 3: 公式採点エンジン
- brier_score 再計算/追加 (HIT/MISS + our_pick_prob のある全件)
- 集計stats:
    - accuracy_pct: 解決済みのうちHIT率
    - official_brier_avg: 採点済み全件のBrier平均
    - resolution_coverage_pct: 全件のうち解決済み+期限切れ率
    - overconfidence_miss_rate: MISS のうち our_pick_prob > 70% の割合
- これらを prediction_db.json の meta キーに保存
- 個別 brier_score も各予測に書き込む
"""
import json
import shutil
from datetime import datetime
from collections import Counter

DB_PATH = "/opt/shared/scripts/prediction_db.json"

def compute_brier(our_pick_prob: float, verdict: str) -> float:
    """BS = (p - o)^2  p: 0-1, o: 1=HIT, 0=MISS"""
    p = our_pick_prob / 100.0
    o = 1.0 if verdict == "HIT" else 0.0
    return round((p - o) ** 2, 6)

def main():
    # バックアップ
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    bak = f"{DB_PATH}.bak-phase3-{ts}"
    shutil.copy2(DB_PATH, bak)
    print(f"Backup: {bak}")

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    preds = db["predictions"]
    total = len(preds)

    # --- per-prediction Brier Score ---
    bs_updated = 0
    scored_preds = []

    for p in preds:
        verdict = p.get("verdict")
        prob = p.get("our_pick_prob")

        if verdict in ("HIT", "MISS") and prob is not None:
            try:
                bs = compute_brier(float(prob), verdict)
                p["brier_score"] = bs
                bs_updated += 1
                scored_preds.append(p)
            except (TypeError, ValueError):
                pass

    print(f"brier_score computed/updated: {bs_updated}")

    # --- 集計stats ---
    resolved = [p for p in preds if p.get("status") == "RESOLVED"]
    expired  = [p for p in preds if p.get("status") == "EXPIRED_UNRESOLVED"]
    scorable = scored_preds  # HIT/MISS + prob
    miss_preds = [p for p in preds if p.get("verdict") == "MISS" and p.get("our_pick_prob") is not None]

    # Accuracy (解決済みのうちHIT率)
    resolved_with_verdict = [p for p in resolved if p.get("verdict") in ("HIT","MISS")]
    hit_resolved = [p for p in resolved_with_verdict if p.get("verdict") == "HIT"]
    accuracy_pct = (
        round(len(hit_resolved) / len(resolved_with_verdict) * 100, 1)
        if resolved_with_verdict else 0.0
    )

    # Official Brier Average (全採点済み)
    brier_values = [p["brier_score"] for p in scorable if p.get("brier_score") is not None]
    official_brier_avg = round(sum(brier_values) / len(brier_values), 4) if brier_values else None

    # Resolution Coverage (全件のうち解決済み+期限切れ率)
    resolved_and_expired = len(resolved) + len(expired)
    # also count VOID/CANCELLED/SUPERSEDED as "done"
    done_statuses = ("RESOLVED","EXPIRED_UNRESOLVED","VOID","CANCELLED","SUPERSEDED")
    done_count = sum(1 for p in preds if p.get("status") in done_statuses)
    coverage_pct = round(done_count / total * 100, 1) if total else 0.0

    # Overconfidence Miss Rate (MISS のうち our_pick_prob > 70%)
    miss_with_prob = [p for p in miss_preds if p.get("our_pick_prob") is not None]
    overconf = [p for p in miss_with_prob if float(p["our_pick_prob"]) > 70]
    overconf_rate = (
        round(len(overconf) / len(miss_with_prob) * 100, 1)
        if miss_with_prob else 0.0
    )

    # --- meta に書き込む ---
    if "meta" not in db:
        db["meta"] = {}

    db["meta"].update({
        "total_predictions": total,
        "scored_predictions": len(scorable),
        "accuracy_pct": accuracy_pct,
        "official_brier_avg": official_brier_avg,
        "resolution_coverage_pct": coverage_pct,
        "overconfidence_miss_rate": overconf_rate,
        "stats_updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status_counts": dict(Counter(p.get("status") for p in preds)),
        "verdict_counts": dict(Counter(p.get("verdict") for p in preds)),
        "schema_version": "2.0",
    })

    # 保存
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("Done!")
    print(f"\n=== Official Scorecard ===")
    print(f"  Total predictions:           {total}")
    print(f"  Scored (HIT/MISS + prob):    {len(scorable)}")
    print(f"  Accuracy (resolved HIT%):    {accuracy_pct}%")
    print(f"  Official Brier Avg:          {official_brier_avg}")
    print(f"  Resolution Coverage:         {coverage_pct}%  ({done_count}/{total})")
    print(f"  Overconfidence Miss Rate:    {overconf_rate}%  ({len(overconf)}/{len(miss_with_prob)} MISS)")
    print(f"  Verdict breakdown:  HIT={len([p for p in preds if p.get('verdict')=='HIT'])} MISS={len([p for p in preds if p.get('verdict')=='MISS'])} PENDING={len([p for p in preds if p.get('verdict')=='PENDING'])}")

if __name__ == "__main__":
    main()
