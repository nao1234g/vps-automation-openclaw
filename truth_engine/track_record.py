"""
truth_engine/track_record.py
予測トラックレコード管理 — Nowpatternのモート（競争優位）の実体

このモジュールは prediction_db.json（VPS /opt/shared/）から
予測データを読み込み、Brier Score とトラックレコードを生成する。
"""

import sys
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# prediction_db.json の探索パス（ローカルキャッシュ優先、VPS fallback）
PREDICTION_DB_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "data", "prediction_db.json"),
    "/opt/shared/prediction_db.json",
]


def load_prediction_db(path: Optional[str] = None) -> List[Dict]:
    """prediction_db.json を読み込む"""
    search_paths = [path] if path else PREDICTION_DB_PATHS

    for p in search_paths:
        if p and os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                db = json.load(f)
                # List形式とDict形式の両方に対応
                if isinstance(db, list):
                    return db
                elif isinstance(db, dict):
                    return db.get("predictions", list(db.values()))
    return []


class TrackRecord:
    """
    Nowpatternの予測トラックレコード

    このクラスがNowpatternのモート（競争優位）を数値化する。
    3年分のデータが蓄積されると、競合が追いつけない信頼の壁になる。
    """

    def __init__(self, predictions: Optional[List[Dict]] = None):
        self.predictions = predictions or load_prediction_db()

    def summary(self) -> Dict:
        """トラックレコードのサマリー"""
        total = len(self.predictions)
        resolved = [p for p in self.predictions if p.get("resolved")]
        open_preds = [p for p in self.predictions if not p.get("resolved")]

        hits = [p for p in resolved if p.get("result") == "HIT"]
        misses = [p for p in resolved if p.get("result") == "MISS"]

        hit_rate = len(hits) / len(resolved) if resolved else 0

        # Brier Score (もし保存されていれば)
        brier_scores = [
            p["brier_score"] for p in resolved
            if isinstance(p.get("brier_score"), (int, float))
        ]
        mean_brier = sum(brier_scores) / len(brier_scores) if brier_scores else None

        return {
            "total_predictions": total,
            "resolved": len(resolved),
            "open": len(open_preds),
            "hits": len(hits),
            "misses": len(misses),
            "hit_rate": round(hit_rate, 4),
            "hit_rate_pct": f"{hit_rate*100:.1f}%",
            "mean_brier_score": round(mean_brier, 4) if mean_brier else None,
            "moat_strength": self._moat_strength(len(resolved), hit_rate),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _moat_strength(self, resolved_count: int, hit_rate: float) -> str:
        """
        モートの強さを評価する
        解決済み予測数 × 的中率 = 信頼の厚み
        """
        score = resolved_count * hit_rate
        if score >= 200:
            return "FORTRESS"   # 難攻不落の堀
        elif score >= 100:
            return "STRONG"
        elif score >= 50:
            return "BUILDING"
        elif score >= 20:
            return "EARLY"
        else:
            return "SEED"       # まだ始まったばかり

    def get_open_predictions(self) -> List[Dict]:
        """未解決の予測一覧"""
        return [p for p in self.predictions if not p.get("resolved")]

    def get_by_tag(self, tag: str) -> List[Dict]:
        """特定タグの予測を取得"""
        return [
            p for p in self.predictions
            if tag in p.get("tags", []) or tag in str(p.get("dynamics", []))
        ]

    def get_recent(self, n: int = 10) -> List[Dict]:
        """最新N件の予測"""
        sorted_preds = sorted(
            self.predictions,
            key=lambda p: p.get("created_at", ""),
            reverse=True
        )
        return sorted_preds[:n]

    def accuracy_over_time(self) -> List[Dict]:
        """
        時系列の精度推移
        月別の的中率を返す — 予測プラットフォームの成長を可視化する
        """
        monthly: Dict[str, Dict] = {}

        for pred in self.predictions:
            if not pred.get("resolved"):
                continue

            # 解決日から月を取得
            resolved_date = pred.get("resolution_date") or pred.get("created_at", "")
            if not resolved_date:
                continue

            month = resolved_date[:7]  # "YYYY-MM"
            if month not in monthly:
                monthly[month] = {"hits": 0, "total": 0}

            monthly[month]["total"] += 1
            if pred.get("result") == "HIT":
                monthly[month]["hits"] += 1

        result = []
        for month in sorted(monthly.keys()):
            d = monthly[month]
            rate = d["hits"] / d["total"] if d["total"] > 0 else 0
            result.append({
                "month": month,
                "hit_rate": round(rate, 4),
                "hits": d["hits"],
                "total": d["total"],
            })

        return result

    def generate_report(self) -> str:
        """テキストレポート生成"""
        s = self.summary()
        lines = [
            "=" * 50,
            "NOWPATTERN TRACK RECORD",
            "=" * 50,
            f"総予測数    : {s['total_predictions']}件",
            f"解決済み    : {s['resolved']}件 (未解決: {s['open']}件)",
            f"的中率      : {s['hit_rate_pct']} ({s['hits']} HIT / {s['misses']} MISS)",
        ]
        if s["mean_brier_score"]:
            lines.append(f"Brier Score : {s['mean_brier_score']} (0.25 = ランダム基準)")
        lines += [
            f"モート強度  : {s['moat_strength']}",
            "=" * 50,
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    tr = TrackRecord()
    print(tr.generate_report())
    summary = tr.summary()
    open_preds = tr.get_open_predictions()
    print(f"\n未解決の予測: {len(open_preds)}件")
    if open_preds:
        print("最新3件:")
        for p in open_preds[:3]:
            print(f"  - {p.get('title', p.get('id', '?'))}")
