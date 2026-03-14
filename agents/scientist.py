"""
agents/scientist.py
科学者エージェント — データ・証拠・統計の専門家

「数字は嘘をつかない。解釈が嘘をつく。」

Wishful facts を最も強くブロックするエージェント。
証拠がなければ確率を50%に押し戻す。
"""

import sys
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.base_agent import BaseAgent


class ScientistAgent(BaseAgent):
    """
    科学者エージェント

    専門:
    - Brier Score を使った予測精度の統計分析
    - 証拠の強さを数値化（UNSHAKEABLE / SURFACE / ASSUMED）
    - 過信バイアスの検出と修正
    """

    def __init__(self):
        super().__init__(
            name="scientist",
            role="scientist",
            description="データ分析・統計・証拠検証の専門家。Wishful factsをブロックする番犬。",
        )

    def analyze(self, topic: str, context: Dict) -> Dict:
        """
        科学的・証拠ベースの分析

        - 証拠の強さを評価
        - 確率の根拠を数値で検証
        - 過信バイアスを補正
        """
        tags = context.get("tags", [])
        base_prob = context.get("base_probability", 50)
        evidence = context.get("evidence", [])
        market_prob = context.get("market_probability")

        # 証拠の強さ評価
        evidence_score = self._evaluate_evidence(evidence)

        # 市場確率との整合性チェック
        if market_prob is not None:
            delta = abs(base_prob - market_prob)
            if delta > 20:
                # 市場と大きく乖離している場合は保守的に
                adjusted_prob = round(base_prob * 0.7 + market_prob * 0.3)
                market_note = f"市場確率({market_prob}%)との乖離{delta}%が大きい → 保守的に調整"
            else:
                adjusted_prob = base_prob
                market_note = f"市場確率({market_prob}%)と概ね一致"
        else:
            adjusted_prob = base_prob
            market_note = "市場データなし — ベースレートを維持"

        # 証拠が少ない場合は50%に引き寄せる（不確実性の正直な反映）
        if evidence_score < 0.3:
            adjusted_prob = round(adjusted_prob * 0.7 + 50 * 0.3)
            evidence_note = f"証拠不足(スコア={evidence_score:.2f}) — 50%に引き寄せ"
        else:
            evidence_note = f"証拠スコア: {evidence_score:.2f}"

        adjusted_prob = max(5, min(95, adjusted_prob))
        confidence = min(0.90, 0.40 + evidence_score * 0.5)

        analysis = (
            f"証拠評価: {evidence_note}。"
            f"{market_note}。"
            f"調整後確率: {adjusted_prob}%。"
        )

        key_claims = [
            f"証拠スコア: {evidence_score:.2f}",
            market_note,
            f"調整後確率: {adjusted_prob}%",
        ]

        result = self._format_analysis_result(
            analysis=analysis,
            probability=adjusted_prob,
            confidence=confidence,
            key_claims=key_claims,
            fact_type="UNSHAKEABLE" if evidence_score >= 0.7 else "SURFACE",
        )

        self.remember_analysis(topic, analysis, tags, importance=0.6)
        return result

    def _evaluate_evidence(self, evidence: List) -> float:
        """
        証拠リストの強さを0.0〜1.0でスコアリング

        UNSHAKEABLE = 1.0, SURFACE = 0.6, REPORTED = 0.4, ASSUMED = 0.2
        """
        if not evidence:
            return 0.2  # 証拠なし

        SCORES = {
            "UNSHAKEABLE": 1.0,
            "SURFACE": 0.6,
            "REPORTED": 0.4,
            "ASSUMED": 0.2,
            "WISHFUL": 0.0,
        }

        total = 0.0
        for ev in evidence:
            fact_type = ev.get("fact_type", "ASSUMED") if isinstance(ev, dict) else "ASSUMED"
            total += SCORES.get(fact_type, 0.3)

        return min(1.0, total / len(evidence))

    def fact_check(self, claim: str, fact_type: str) -> Dict:
        """
        主張をファクトチェックする

        Returns:
            {"valid": bool, "concern": str, "recommendation": str}
        """
        if fact_type == "WISHFUL":
            return {
                "valid": False,
                "concern": "WISHFUL fact は予測の根拠に使えません",
                "recommendation": "Unshakeable facts（検証済みデータ）に置き換えてください",
            }
        if fact_type == "ASSUMED":
            return {
                "valid": True,
                "concern": "ASSUMED fact — 検証を推奨します",
                "recommendation": "可能であれば一次ソースを確認してください",
            }
        return {
            "valid": True,
            "concern": "",
            "recommendation": "",
        }
