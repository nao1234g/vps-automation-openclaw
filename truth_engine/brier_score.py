"""
truth_engine/brier_score.py
Brier Score 計算モジュール — 予測精度の数値言語

Brier Score = (1/N) * Σ (predicted_probability - actual_outcome)^2
- 0.0  = 完璧な予測
- 0.25 = ランダム予測（無価値な基準線）
- 1.0  = 最悪の予測（完全に逆）
"""

import sys
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Prediction:
    """単一予測のデータ構造"""
    prediction_id: str
    predicted_probability: float   # 0.0 〜 1.0
    actual_outcome: Optional[int] = None   # 1=的中, 0=外れ, None=未解決
    title: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class BrierResult:
    """Brier Score 計算結果"""
    score: float                  # 個別スコア
    calibration_error: float      # 校正誤差
    resolution: float             # 解像度（0〜1）
    is_better_than_random: bool   # ランダム予測(0.25)より良いか

    @property
    def grade(self) -> str:
        if self.score < 0.05:
            return "EXCEPTIONAL"   # 超一流の予測者
        elif self.score < 0.10:
            return "EXCELLENT"
        elif self.score < 0.15:
            return "GOOD"
        elif self.score < 0.20:
            return "DECENT"
        elif self.score < 0.25:
            return "AVERAGE"
        else:
            return "POOR"          # ランダム以下


class BrierScoreEngine:
    """
    Brier Score 計算エンジン
    Nowpattern の予測精度をリアルタイムで計算・評価する
    """

    RANDOM_BASELINE = 0.25   # ランダム予測の基準スコア

    def calculate_single(self, pred: Prediction) -> Optional[BrierResult]:
        """
        単一予測の Brier Score を計算する
        actual_outcome が None（未解決）の場合は None を返す
        """
        if pred.actual_outcome is None:
            return None

        p = pred.predicted_probability
        o = pred.actual_outcome

        # Brier Score の基本公式
        score = (p - o) ** 2

        # 校正誤差: 予測した確率と実際の結果のズレ
        calibration_error = abs(p - o)

        # 解像度: 確率を0.5から離すほど高い（0.9の予測が当たると高スコア）
        resolution = abs(p - 0.5)

        return BrierResult(
            score=score,
            calibration_error=calibration_error,
            resolution=resolution,
            is_better_than_random=(score < self.RANDOM_BASELINE),
        )

    def calculate_batch(self, predictions: List[Prediction]) -> Dict:
        """
        複数予測の集計 Brier Score を計算する
        Returns: {
            mean_brier_score, count, hit_rate, grade, breakdown_by_tag
        }
        """
        resolved = [p for p in predictions if p.actual_outcome is not None]

        if not resolved:
            return {
                "mean_brier_score": None,
                "count": 0,
                "resolved_count": 0,
                "hit_rate": None,
                "grade": "N/A",
                "message": "解決済み予測がありません",
            }

        scores = []
        hits = 0

        for pred in resolved:
            result = self.calculate_single(pred)
            if result:
                scores.append(result.score)
                if pred.actual_outcome == 1:
                    hits += 1

        mean_score = sum(scores) / len(scores)
        hit_rate = hits / len(resolved)

        # タグ別ブレークダウン
        breakdown = self._breakdown_by_tag(resolved)

        # 総合グレード
        dummy_result = BrierResult(
            score=mean_score,
            calibration_error=0,
            resolution=0,
            is_better_than_random=(mean_score < self.RANDOM_BASELINE),
        )

        return {
            "mean_brier_score": round(mean_score, 4),
            "count": len(predictions),
            "resolved_count": len(resolved),
            "open_count": len(predictions) - len(resolved),
            "hit_rate": round(hit_rate, 4),
            "grade": dummy_result.grade,
            "better_than_random": mean_score < self.RANDOM_BASELINE,
            "vs_random_delta": round(self.RANDOM_BASELINE - mean_score, 4),
            "breakdown_by_tag": breakdown,
        }

    def _breakdown_by_tag(self, resolved: List[Prediction]) -> Dict[str, Dict]:
        """タグ別のBrier Score分析"""
        tag_data: Dict[str, List[float]] = {}

        for pred in resolved:
            result = self.calculate_single(pred)
            if not result:
                continue
            for tag in pred.tags:
                tag_data.setdefault(tag, []).append(result.score)

        breakdown = {}
        for tag, scores in tag_data.items():
            breakdown[tag] = {
                "mean_brier": round(sum(scores) / len(scores), 4),
                "count": len(scores),
            }

        # スコアで昇順ソート（最も精度の高いタグが上）
        return dict(sorted(breakdown.items(), key=lambda x: x[1]["mean_brier"]))

    def evaluate_calibration(self, predictions: List[Prediction]) -> Dict:
        """
        校正曲線分析: 「70%と言った予測が実際に70%当たるか」を検証する
        """
        buckets = {
            "0-10": [], "10-20": [], "20-30": [], "30-40": [], "40-50": [],
            "50-60": [], "60-70": [], "70-80": [], "80-90": [], "90-100": [],
        }

        resolved = [p for p in predictions if p.actual_outcome is not None]

        for pred in resolved:
            pct = pred.predicted_probability * 100
            for bucket in buckets:
                lo, hi = map(int, bucket.split("-"))
                if lo <= pct < hi or (hi == 100 and pct == 100):
                    buckets[bucket].append(pred.actual_outcome)
                    break

        calibration = {}
        for bucket, outcomes in buckets.items():
            if outcomes:
                lo, hi = map(int, bucket.split("-"))
                expected = (lo + hi) / 2 / 100
                actual = sum(outcomes) / len(outcomes)
                calibration[bucket] = {
                    "expected_probability": expected,
                    "actual_hit_rate": round(actual, 4),
                    "calibration_error": round(abs(expected - actual), 4),
                    "count": len(outcomes),
                }

        return calibration


# ─────────────────────────────
# CLI 実行サポート
# ─────────────────────────────
if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    engine = BrierScoreEngine()

    # デモデータ
    sample_predictions = [
        Prediction("P001", 0.80, 1, "イランがホルムズ海峡を封鎖する", ["地政学・安全保障"]),
        Prediction("P002", 0.65, 0, "BTCが100K突破する", ["暗号資産"]),
        Prediction("P003", 0.90, 1, "米中関税強化", ["経済・貿易"]),
        Prediction("P004", 0.40, 0, "Fed が利下げ", ["金融・市場"]),
        Prediction("P005", 0.75, 1, "AI規制法案成立", ["ガバナンス・法", "テクノロジー"]),
    ]

    result = engine.calculate_batch(sample_predictions)
    print(f"[BrierScore] Mean: {result['mean_brier_score']} | Grade: {result['grade']}")
    print(f"  Hit Rate: {result['hit_rate']*100:.1f}% | vs Random: +{result['vs_random_delta']:.4f}")
    print(f"  Resolved: {result['resolved_count']}/{result['count']}")
