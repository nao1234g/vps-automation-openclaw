"""
apps/nowpattern/prediction_tracker.py
予測トラッカー — prediction_db.json の読み書きと状態管理

Nowpatternの「Intelligence Flywheel」を回す中核:
  記事 → prediction_db登録 → 自動検証 → Brier Score → /predictions/ページ更新
"""

import sys
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_DB_PATH = "data/prediction_db.json"


class PredictionTracker:
    """
    予測DBの管理・照会・更新を担当する

    prediction_db.json に対してCRUD操作を提供し、
    Brier Scoreの計算・集計・ランキングを行う。
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._predictions: List[Dict] = []
        self._load()

    # ── 書き込み ──────────────────────────────────────

    def add_prediction(self,
                       title: str,
                       tags: List[str],
                       our_pick: str,
                       our_pick_prob: int,
                       resolution_question: str,
                       hit_condition: str,
                       trigger_date: str,
                       market_prob: Optional[int] = None,
                       article_slug: Optional[str] = None) -> Dict:
        """
        新しい予測をDBに追加する

        Args:
            title: 予測タイトル
            tags: タクソノミータグ
            our_pick: "YES" / "NO" / 具体的予測
            our_pick_prob: 0〜100 の整数
            resolution_question: 判定質問（日本語）
            hit_condition: 的中条件
            trigger_date: 判定日 "YYYY-MM-DD"
            market_prob: Polymarketの確率（オプション）
            article_slug: 連動記事スラッグ（オプション）

        Returns:
            新規予測エントリー dict
        """
        pred_id = self._generate_id()
        brier_from_market = None
        if market_prob is not None:
            brier_from_market = round(((market_prob / 100) - (our_pick_prob / 100)) ** 2, 4)

        entry = {
            "id": pred_id,
            "title": title,
            "tags": tags,
            "our_pick": our_pick,
            "our_pick_prob": our_pick_prob,
            "resolution_question": resolution_question,
            "hit_condition": hit_condition,
            "triggers": [{"date": trigger_date, "condition": hit_condition}],
            "market_consensus": {"probability": market_prob} if market_prob else None,
            "article_slug": article_slug,
            "resolved": False,
            "result": None,
            "brier_score": None,
            "actual_outcome": None,
            "resolved_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._predictions.append(entry)
        self._save()
        return entry

    def resolve_prediction(self,
                           pred_id: str,
                           actual_outcome: str,
                           result: str) -> Optional[Dict]:
        """
        予測を解決する（HIT / MISS）

        Args:
            pred_id: 予測ID
            actual_outcome: 実際の結果の説明
            result: "HIT" / "MISS"

        Returns:
            更新済み予測エントリー
        """
        pred = self._find(pred_id)
        if not pred:
            print(f"[WARNING] Prediction {pred_id} not found")
            return None

        prob = pred["our_pick_prob"] / 100
        # Brier Score: (予測確率 - 実際の結果)^2
        # HIT = 実際の結果=1, MISS = 実際の結果=0
        outcome_numeric = 1 if result == "HIT" else 0
        brier = round((prob - outcome_numeric) ** 2, 4)

        pred.update({
            "resolved": True,
            "result": result,
            "actual_outcome": actual_outcome,
            "brier_score": brier,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        })

        self._save()
        return pred

    # ── 読み取り ──────────────────────────────────────

    def get_open_predictions(self) -> List[Dict]:
        """未解決の予測一覧を返す"""
        return [p for p in self._predictions if not p.get("resolved")]

    def get_resolved_predictions(self) -> List[Dict]:
        """解決済み予測一覧を返す（最新順）"""
        resolved = [p for p in self._predictions if p.get("resolved")]
        return sorted(resolved, key=lambda p: p.get("resolved_at", ""), reverse=True)

    def get_by_tags(self, tags: List[str]) -> List[Dict]:
        """タグで予測を検索する"""
        return [p for p in self._predictions
                if any(t in p.get("tags", []) for t in tags)]

    def get_stats(self) -> Dict:
        """集計統計を返す"""
        total = len(self._predictions)
        open_count = sum(1 for p in self._predictions if not p.get("resolved"))
        resolved = [p for p in self._predictions if p.get("resolved")]
        hits = [p for p in resolved if p.get("result") == "HIT"]

        brier_scores = [p["brier_score"] for p in resolved if p.get("brier_score") is not None]
        avg_brier = round(sum(brier_scores) / len(brier_scores), 4) if brier_scores else None

        hit_rate = round(len(hits) / max(len(resolved), 1), 3)

        # Brier grade（NORTH_STAR.md基準）
        brier_grade = "N/A"
        if avg_brier is not None:
            if avg_brier < 0.05:
                brier_grade = "EXCEPTIONAL"
            elif avg_brier < 0.10:
                brier_grade = "EXCELLENT"
            elif avg_brier < 0.15:
                brier_grade = "GOOD"
            elif avg_brier < 0.20:
                brier_grade = "DECENT"
            elif avg_brier < 0.25:
                brier_grade = "AVERAGE"
            else:
                brier_grade = "POOR"

        # Moat Strength = resolved_count × hit_rate
        moat_score = len(resolved) * hit_rate
        if moat_score < 5:
            moat = "SEED"
        elif moat_score < 15:
            moat = "EARLY"
        elif moat_score < 30:
            moat = "BUILDING"
        elif moat_score < 60:
            moat = "STRONG"
        else:
            moat = "FORTRESS"

        return {
            "total": total,
            "open": open_count,
            "resolved": len(resolved),
            "hits": len(hits),
            "misses": len(resolved) - len(hits),
            "hit_rate": hit_rate,
            "avg_brier": avg_brier,
            "brier_grade": brier_grade,
            "moat_strength": moat,
            "moat_score": round(moat_score, 1),
        }

    def get_top_predictions(self, limit: int = 5) -> List[Dict]:
        """高品質（低Brier）の予測TOP N を返す"""
        resolved = [p for p in self._predictions
                    if p.get("resolved") and p.get("brier_score") is not None]
        return sorted(resolved, key=lambda p: p["brier_score"])[:limit]

    def get_predictions_due(self, within_days: int = 7) -> List[Dict]:
        """判定期限が近い予測を返す"""
        now = datetime.now(timezone.utc)
        due = []
        for pred in self.get_open_predictions():
            for trigger in pred.get("triggers", []):
                try:
                    trigger_dt = datetime.fromisoformat(trigger["date"])
                    if hasattr(trigger_dt, "tzinfo") and trigger_dt.tzinfo is None:
                        trigger_dt = trigger_dt.replace(tzinfo=timezone.utc)
                    days_until = (trigger_dt - now).days
                    if 0 <= days_until <= within_days:
                        due.append({**pred, "_days_until": days_until})
                        break
                except Exception:
                    pass
        return sorted(due, key=lambda p: p.get("_days_until", 999))

    # ── 永続化 ──────────────────────────────────────

    def _load(self):
        if not os.path.exists(self.db_path):
            return
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # list形式 または {"predictions": [...]} 形式の両方対応
            if isinstance(data, list):
                self._predictions = data
            elif isinstance(data, dict):
                self._predictions = data.get("predictions", [])
        except Exception as e:
            print(f"[WARNING] PredictionTracker load error: {e}")

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self._predictions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] PredictionTracker save error: {e}")

    def _find(self, pred_id: str) -> Optional[Dict]:
        for p in self._predictions:
            if p.get("id") == pred_id:
                return p
        return None

    def _generate_id(self) -> str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = sum(1 for p in self._predictions
                    if p.get("id", "").startswith(date_str)) + 1
        return f"{date_str}-{count:03d}"


if __name__ == "__main__":
    tracker = PredictionTracker("data/prediction_db.json")
    stats = tracker.get_stats()
    print(f"予測DB統計:")
    print(f"  総数: {stats['total']}件 / 未解決: {stats['open']}件 / 解決済み: {stats['resolved']}件")
    print(f"  的中率: {stats['hit_rate']*100:.1f}%")
    print(f"  Brier Score: {stats['avg_brier']} ({stats['brier_grade']})")
    print(f"  Moat強度: {stats['moat_strength']} (スコア: {stats['moat_score']})")
