"""
prediction_engine/prediction_registry.py
予測登録簿 — prediction_db.json のローカル管理インターフェース

VPS上の prediction_db.json との同期を管理し、
ローカルでも予測の作成・読み込み・更新ができるようにする。
"""

import sys
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ローカルキャッシュパス
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "prediction_db.json")
VPS_DB_PATH = "/opt/shared/prediction_db.json"


class PredictionRegistry:
    """
    予測登録簿 — AIの予測を永続的に管理する

    このレジストリが「Nowpatternのトラックレコード」の実体。
    一度記録された予測は削除できない（不変性原則）。
    """

    def __init__(self, db_path: str = LOCAL_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._predictions: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        if os.path.exists(self.db_path):
            with open(self.db_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return list(data.values()) if data else []
        return []

    def _save(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self._predictions, f, ensure_ascii=False, indent=2)

    def add(self, prediction: Dict) -> str:
        """
        新しい予測を追加する

        必須フィールド:
        - id: 予測ID (例: "2026-03-14-001")
        - title: タイトル
        - our_pick: YES / NO / 具体的予測
        - our_pick_prob: 確率 (0〜100)
        - resolution_question: 判定質問
        - triggers: [{date, description}]
        """
        required = ["id", "title", "our_pick", "our_pick_prob", "resolution_question"]
        for field in required:
            if field not in prediction:
                raise ValueError(f"必須フィールドが不足: {field}")

        # 既存IDチェック
        existing_ids = {p["id"] for p in self._predictions}
        if prediction["id"] in existing_ids:
            raise ValueError(f"予測ID {prediction['id']} は既に存在します")

        # タイムスタンプ追加
        prediction.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        prediction.setdefault("resolved", False)
        prediction.setdefault("result", None)
        prediction.setdefault("brier_score", None)

        self._predictions.append(prediction)
        self._save()
        return prediction["id"]

    def get(self, prediction_id: str) -> Optional[Dict]:
        """IDで予測を取得"""
        for p in self._predictions:
            if p["id"] == prediction_id:
                return p
        return None

    @staticmethod
    def calc_brier_score(our_pick_prob: float, result: str) -> float:
        """
        Brier Score を計算する（2項予測用）

        BS = (forecast - outcome)^2
          forecast: 確率 0〜1（our_pick_prob / 100）
          outcome:  HIT=1.0, MISS=0.0

        完璧な予測: BS=0.0（HIT & prob=1.0 または MISS & prob=0.0）
        最悪の予測: BS=1.0（HIT & prob=0.0 または MISS & prob=1.0）
        ランダム:   BS=0.25（prob=0.5 でどちらの結果でも）
        """
        forecast = max(0.0, min(1.0, our_pick_prob / 100.0))
        outcome = 1.0 if result == "HIT" else 0.0
        return round((forecast - outcome) ** 2, 6)

    def update_resolution(self, prediction_id: str, result: str,
                          resolution_date: str = None, brier_score: float = None) -> bool:
        """
        予測の解決結果を記録する（一度だけ更新可能）

        Args:
            result: "HIT" または "MISS"
            resolution_date: 解決日 (ISO format)
            brier_score: Brier Score（省略時は our_pick_prob から自動計算）
        """
        for p in self._predictions:
            if p["id"] == prediction_id:
                if p.get("resolved"):
                    raise ValueError(f"予測 {prediction_id} は既に解決済みです（変更不可）")

                p["resolved"] = True
                p["result"] = result
                p["resolution_date"] = resolution_date or datetime.now(timezone.utc).isoformat()

                # Brier Score: 明示指定がなければ our_pick_prob から自動計算
                if brier_score is not None:
                    p["brier_score"] = brier_score
                elif "our_pick_prob" in p and p["our_pick_prob"] is not None:
                    p["brier_score"] = self.calc_brier_score(p["our_pick_prob"], result)
                else:
                    p["brier_score"] = None

                self._save()
                return True
        return False

    def get_open(self) -> List[Dict]:
        """未解決の予測一覧"""
        return [p for p in self._predictions if not p.get("resolved")]

    def get_resolved(self) -> List[Dict]:
        """解決済みの予測一覧"""
        return [p for p in self._predictions if p.get("resolved")]

    def get_by_tag(self, tag: str) -> List[Dict]:
        """タグで検索"""
        return [p for p in self._predictions if tag in p.get("tags", [])]

    def stats(self) -> Dict:
        """統計サマリー（Brier Score 含む）"""
        total = len(self._predictions)
        resolved = self.get_resolved()
        open_preds = self.get_open()
        hits = [p for p in resolved if p.get("result") == "HIT"]

        # Brier Score 集計（None を除外）
        brier_scores = [p["brier_score"] for p in resolved if p.get("brier_score") is not None]
        mean_brier = round(sum(brier_scores) / len(brier_scores), 6) if brier_scores else None

        return {
            "total": total,
            "open": len(open_preds),
            "resolved": len(resolved),
            "hits": len(hits),
            "misses": len(resolved) - len(hits),
            "hit_rate": round(len(hits) / len(resolved), 4) if resolved else 0,
            "mean_brier_score": mean_brier,
            "brier_scored_count": len(brier_scores),
        }

    def generate_prediction_id(self) -> str:
        """新しい予測IDを自動生成"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_preds = [p for p in self._predictions if p.get("id", "").startswith(today)]
        seq = len(today_preds) + 1
        return f"{today}-{seq:03d}"


if __name__ == "__main__":
    registry = PredictionRegistry()
    stats = registry.stats()
    print(f"[PredictionRegistry] Total: {stats['total']} | Open: {stats['open']} | Hit Rate: {stats['hit_rate']*100:.1f}%")
