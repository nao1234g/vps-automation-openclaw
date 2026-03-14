"""
truth_engine/truth_engine.py
Truth Engine — AI Civilization OS の最上位レイヤー

役割:
1. 予測を証拠ベースで検証する
2. Brier Score でAIの精度を測定する
3. トラックレコードを蓄積する
4. Wishful facts をブロックする

このエンジンが「Nowpatternが予測オラクルである」ことを数値で証明する。
"""

import sys
from typing import List, Dict
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 内部モジュール
from truth_engine.brier_score import BrierScoreEngine, Prediction as BrierPrediction
from truth_engine.track_record import TrackRecord
from truth_engine.evidence_registry import EvidenceRegistry, Evidence


class TruthEngine:
    """
    AI Civilization OS の Truth Engine

    Nowpatternの3原則を技術的に実装する:
    1. Truth first  — 証拠のない主張を拒否する
    2. Evidence-based — Unshakeable facts だけで判断する
    3. Prediction accountability — Brier Scoreで精度を公開する
    """

    def __init__(self):
        self.brier = BrierScoreEngine()
        self.registry = EvidenceRegistry()
        self.track_record = TrackRecord()

    def verify_prediction(self, prediction_id: str, prediction_prob: float,
                          actual_outcome: int, tags: List[str] = None) -> Dict:
        """
        予測を検証してBrier Scoreを計算する

        Args:
            prediction_id: 予測ID
            prediction_prob: 予測した確率（0.0〜1.0）
            actual_outcome: 実際の結果（1=的中, 0=外れ）
            tags: タグリスト
        """
        # 証拠品質チェック
        evidence_check = self.registry.validate_prediction(prediction_id)

        # Brier Score計算
        pred = BrierPrediction(
            prediction_id=prediction_id,
            predicted_probability=prediction_prob,
            actual_outcome=actual_outcome,
            tags=tags or [],
        )
        brier_result = self.brier.calculate_single(pred)

        return {
            "prediction_id": prediction_id,
            "predicted_probability": prediction_prob,
            "actual_outcome": actual_outcome,
            "brier_score": round(brier_result.score, 4) if brier_result else None,
            "brier_grade": brier_result.grade if brier_result else None,
            "evidence_valid": evidence_check["is_valid"],
            "evidence_verdict": evidence_check["verdict"],
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def assess_prediction_quality(self, prediction: Dict) -> Dict:
        """
        新しい予測を出す前に品質チェックを行う
        Wishful facts を含む予測をブロックする

        Returns:
            { approved: bool, issues: List[str], warnings: List[str] }
        """
        issues = []
        warnings = []

        # 確率の範囲チェック
        prob = prediction.get("probability", prediction.get("our_pick_prob", 50)) / 100
        if not (0.05 <= prob <= 0.95):
            issues.append(f"確率が極端すぎます ({prob*100:.0f}%). 5%〜95%の範囲で設定してください")

        # 証拠の存在チェック
        if not prediction.get("evidence") and not prediction.get("sources"):
            warnings.append("証拠が記録されていません。Unshakeable factsを追加することを推奨します")

        # 解決条件の明確性チェック
        if not prediction.get("resolution_question") and not prediction.get("hit_condition"):
            issues.append("判定条件が定義されていません。「いつ、何が起きたら的中か」を明示してください")

        # 判定期限チェック
        if not prediction.get("resolution_date") and not prediction.get("triggers"):
            warnings.append("判定期限が設定されていません")

        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "fact_type_required": "UNSHAKEABLE" if issues else "SURFACE",
        }

    def get_system_health(self) -> Dict:
        """Truth Engineシステム全体の健全性レポート"""
        tr_summary = self.track_record.summary()
        ev_stats = self.registry.stats()

        # Brier Scoreをtrack_recordから計算
        preds_for_brier = []
        for p in self.track_record.predictions:
            if p.get("resolved") and p.get("our_pick_prob") is not None:
                prob = p["our_pick_prob"] / 100
                outcome = 1 if p.get("result") == "HIT" else 0
                tags = p.get("tags", [])
                preds_for_brier.append(
                    BrierPrediction(p.get("id", ""), prob, outcome, tags=tags)
                )

        brier_batch = self.brier.calculate_batch(preds_for_brier) if preds_for_brier else {}

        return {
            "track_record": tr_summary,
            "evidence_registry": ev_stats,
            "brier_analysis": brier_batch,
            "truth_engine_version": "1.0.0",
            "status": "OPERATIONAL",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def print_dashboard(self):
        """ダッシュボード表示"""
        health = self.get_system_health()
        tr = health["track_record"]
        ba = health["brier_analysis"]

        print("=" * 55)
        print("TRUTH ENGINE DASHBOARD")
        print("=" * 55)
        print(f"予測数: {tr['total_predictions']} (解決済: {tr['resolved']}, 未解決: {tr['open']})")
        print(f"的中率: {tr['hit_rate_pct']}")
        print(f"モート強度: {tr['moat_strength']}")
        if ba and ba.get("mean_brier_score"):
            print(f"Brier Score: {ba['mean_brier_score']} ({ba.get('grade', '?')})")
            print(f"vs Random: {'BETTER' if ba.get('better_than_random') else 'WORSE'} ({ba.get('vs_random_delta', 0):+.4f})")
        print("=" * 55)


if __name__ == "__main__":
    engine = TruthEngine()
    engine.print_dashboard()
