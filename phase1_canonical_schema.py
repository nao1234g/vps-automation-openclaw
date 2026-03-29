#!/usr/bin/env python3
"""
Phase 1: Canonical Schema + Enum正規化
- hit_miss: correct→HIT, wrong/incorrect→MISS, None→PENDING
- verdict: hit_miss + status から導出 (HIT/MISS/PENDING/NOT_SCORED/VOID)
- status: active→OPEN, open→OPEN, resolving→AWAITING_EVIDENCE, resolved→RESOLVED
- schema_version: 全件に "2.0" を追加
- event_type: Phase 2 用フィールド（既存 question_type ベース）

バックアップ: prediction_db.json.bak-phase1 に保存してから実行
"""
import json
import shutil
import os
from datetime import datetime

DB_PATH = "/opt/shared/scripts/prediction_db.json"
BAK_PATH = f"{DB_PATH}.bak-phase1-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# --- Enum マッピング ---
HIT_MISS_MAP = {
    "correct":   "HIT",
    "hit":       "HIT",
    "wrong":     "MISS",
    "incorrect": "MISS",
    "miss":      "MISS",
}

STATUS_MAP = {
    "active":    "OPEN",
    "open":      "OPEN",
    "resolving": "AWAITING_EVIDENCE",
    "resolved":  "RESOLVED",
    # 既存カノニカル値はそのまま通す
    "DRAFT":               "DRAFT",
    "OPEN":                "OPEN",
    "AWAITING_EVIDENCE":   "AWAITING_EVIDENCE",
    "RESOLVED":            "RESOLVED",
    "EXPIRED_UNRESOLVED":  "EXPIRED_UNRESOLVED",
    "VOID":                "VOID",
    "CANCELLED":           "CANCELLED",
    "SUPERSEDED":          "SUPERSEDED",
}

def derive_verdict(p: dict) -> str:
    """hit_miss + status から verdict を導出"""
    status_canon = STATUS_MAP.get(p.get("status", ""), "OPEN")
    hm = p.get("hit_miss")
    hm_canon = HIT_MISS_MAP.get(str(hm).lower() if hm else "", None)

    if status_canon == "VOID":
        return "VOID"
    if status_canon == "RESOLVED":
        if hm_canon == "HIT":
            return "HIT"
        elif hm_canon == "MISS":
            return "MISS"
        else:
            # resolved だが hit_miss がない = NOT_SCORED
            return "NOT_SCORED"
    # まだ解決してない
    return "PENDING"

def main():
    # バックアップ
    shutil.copy2(DB_PATH, BAK_PATH)
    print(f"Backup: {BAK_PATH}")

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    preds = db["predictions"]
    print(f"Total predictions: {len(preds)}")

    stats = {
        "hit_miss_normalized": 0,
        "status_normalized": 0,
        "verdict_added": 0,
        "schema_version_added": 0,
    }

    for p in preds:
        # 1. hit_miss 正規化
        hm = p.get("hit_miss")
        if hm is not None:
            hm_lower = str(hm).lower()
            if hm_lower in HIT_MISS_MAP:
                p["hit_miss"] = HIT_MISS_MAP[hm_lower]
                stats["hit_miss_normalized"] += 1
            # 既にカノニカル（HIT/MISS）なら何もしない

        # 2. status 正規化
        st = p.get("status")
        if st and st in STATUS_MAP:
            new_st = STATUS_MAP[st]
            if new_st != st:
                p["status"] = new_st
                stats["status_normalized"] += 1

        # 3. verdict 追加（まだない場合）
        if not p.get("verdict"):
            p["verdict"] = derive_verdict(p)
            stats["verdict_added"] += 1

        # 4. schema_version 追加
        if not p.get("schema_version"):
            p["schema_version"] = "2.0"
            stats["schema_version_added"] += 1

    # 保存
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("Done!")
    print(f"  hit_miss normalized:    {stats['hit_miss_normalized']}")
    print(f"  status normalized:      {stats['status_normalized']}")
    print(f"  verdict added:          {stats['verdict_added']}")
    print(f"  schema_version added:   {stats['schema_version_added']}")

    # 事後確認
    from collections import Counter
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db2 = json.load(f)
    p2 = db2["predictions"]
    print("\nPost-run state:")
    print("  hit_miss:", dict(Counter(x.get("hit_miss") for x in p2)))
    print("  status:  ", dict(Counter(x.get("status") for x in p2)))
    print("  verdict: ", dict(Counter(x.get("verdict") for x in p2)))
    print("  schema_version:", dict(Counter(x.get("schema_version") for x in p2)))

if __name__ == "__main__":
    main()
