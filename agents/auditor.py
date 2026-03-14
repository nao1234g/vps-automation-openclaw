"""
agents/auditor.py
監査官エージェント — リスク評価・品質管理・批判的思考の専門家

「楽観は戦略の敵。最悪のシナリオを先に潰せ。」
"""

import sys
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.base_agent import BaseAgent


# 認知バイアスカタログ
COGNITIVE_BIASES = {
    "overconfidence": {
        "name": "過信バイアス",
        "trigger": lambda prob: prob >= 75,
        "adjustment": -10,
        "warning": "確率≥75%は過信の典型。過去の強気予測は平均12%低く実現した",
    },
    "narrative_fallacy": {
        "name": "物語バイアス",
        "trigger": lambda prob: False,  # 常時チェック対象
        "adjustment": -5,
        "warning": "一貫したストーリーは確率を過大評価させる",
    },
    "recency_bias": {
        "name": "近接バイアス",
        "trigger": lambda prob: False,
        "adjustment": -3,
        "warning": "最近の出来事を過剰に重視している可能性",
    },
    "anchoring": {
        "name": "アンカリング",
        "trigger": lambda prob: abs(prob - 50) <= 5,
        "adjustment": 0,
        "warning": "50%近辺は中立アンカーに引っ張られている可能性",
    },
}

# リスクカテゴリ
RISK_CATEGORIES = {
    "black_swan": "ブラックスワン（未知の低確率・高影響イベント）",
    "model_error": "モデル誤差（因果関係の誤認）",
    "missing_data": "データ欠如（重要情報が入手できていない）",
    "regime_change": "レジームチェンジ（ルール・構造の根本変化）",
    "coordination_failure": "協調失敗（合理的アクターが非合理的行動を取る）",
}


class AuditorAgent(BaseAgent):
    """
    監査官エージェント

    専門:
    - 認知バイアス検出（過信・近接バイアス・物語バイアス等）
    - ブラックスワンリスク評価
    - 他エージェントの分析の批判的レビュー
    - 確率の誇張・過小評価を中央値に引き戻す
    """

    def __init__(self):
        super().__init__(
            name="auditor",
            role="auditor",
            description="リスク評価・品質管理・批判的思考の専門家。バイアスを検出する。",
        )

    def analyze(self, topic: str, context: Dict) -> Dict:
        """リスク評価・批判的視点から分析する"""
        tags = context.get("tags", [])
        base_prob = context.get("base_probability", 50)
        evidence_quality = context.get("evidence_quality", "SURFACE")

        # バイアス検出と修正
        bias_analysis = self._detect_biases(base_prob, evidence_quality, tags)

        # リスク評価
        risk_assessment = self._assess_risks(tags, base_prob)

        # 確率調整（監査官は-5バイアス = 悲観的・保守的）
        adjusted_prob = base_prob + bias_analysis["total_adjustment"] - 5

        # 証拠品質による下方修正
        if evidence_quality in ("WISHFUL", "ASSUMED"):
            adjusted_prob -= 8
        elif evidence_quality == "REPORTED":
            adjusted_prob -= 3

        adjusted_prob = max(5, min(95, adjusted_prob))
        confidence = 0.80  # 監査官は自分の懐疑論に自信がある

        bias_text = ", ".join(b["name"] for b in bias_analysis["detected"]) or "主要バイアスなし"
        risk_text = risk_assessment["primary_risk"]

        analysis = (
            f"監査評価: 検出バイアス={bias_text}。"
            f"主要リスク={risk_text}。"
            f"証拠品質={evidence_quality}。"
            f"保守的確率推定: {adjusted_prob}%。"
            f"（元確率{base_prob}%から{adjusted_prob - base_prob:+d}%調整）"
        )

        result = self._format_analysis_result(
            analysis=analysis,
            probability=adjusted_prob,
            confidence=confidence,
            key_claims=[
                f"検出バイアス: {bias_text}",
                f"主要リスク: {risk_text}",
                f"調整幅: {adjusted_prob - base_prob:+d}%",
            ],
            fact_type="SURFACE",
        )

        self.remember_analysis(topic, analysis, tags, importance=0.9)
        return result

    def _detect_biases(self, prob: float, evidence: str, tags: List[str]) -> Dict:
        """認知バイアスを検出する"""
        detected = []
        total_adjustment = 0

        # 過信バイアス
        if prob >= 75:
            bias = COGNITIVE_BIASES["overconfidence"]
            detected.append({"name": bias["name"], "adjustment": bias["adjustment"]})
            total_adjustment += bias["adjustment"]

        # 低確率すぎる場合も過信の裏返し
        if prob <= 15:
            detected.append({"name": "過小評価バイアス", "adjustment": +5})
            total_adjustment += 5

        # 証拠が弱いのに高確率（物語バイアス）
        if evidence in ("WISHFUL", "ASSUMED") and prob >= 65:
            bias = COGNITIVE_BIASES["narrative_fallacy"]
            detected.append({"name": bias["name"], "adjustment": bias["adjustment"]})
            total_adjustment += bias["adjustment"]

        # 近接バイアス（技術系タグで最新技術への過信）
        if "技術・AI" in tags and prob >= 70:
            bias = COGNITIVE_BIASES["recency_bias"]
            detected.append({"name": bias["name"], "adjustment": bias["adjustment"]})
            total_adjustment += bias["adjustment"]

        return {
            "detected": detected,
            "total_adjustment": total_adjustment,
            "bias_count": len(detected),
        }

    def _assess_risks(self, tags: List[str], prob: float) -> Dict:
        """リスクカテゴリを評価する"""
        # タグから主要リスクを特定
        if "地政学・安全保障" in tags:
            primary = RISK_CATEGORIES["regime_change"]
        elif "経済・金融" in tags or "暗号資産" in tags:
            primary = RISK_CATEGORIES["black_swan"]
        elif "技術・AI" in tags:
            primary = RISK_CATEGORIES["model_error"]
        else:
            primary = RISK_CATEGORIES["missing_data"]

        # 全体的なリスクレベル
        if prob >= 80 or prob <= 20:
            risk_level = "HIGH"  # 極端な確率は根拠が弱い可能性
        elif prob >= 65 or prob <= 35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "primary_risk": primary,
            "risk_level": risk_level,
            "black_swan_possible": "地政学・安全保障" in tags or "経済・金融" in tags,
        }

    def audit_prediction(self, prediction: Dict) -> Dict:
        """
        他エージェントの予測結果を監査する

        Args:
            prediction: ConsensusResult や ProbabilityEstimate の dict

        Returns:
            audit_report: 問題点・推奨事項
        """
        issues = []
        recommendations = []

        prob = prediction.get("probability", 50) or prediction.get("final_probability", 50)
        confidence = prediction.get("confidence", 0.5)

        # 確率と信頼度の矛盾チェック
        if prob >= 80 and confidence < 0.5:
            issues.append("高確率（≥80%）だが信頼度が低い（<50%）— 矛盾あり")
            recommendations.append("証拠の再収集 or 確率を70%以下に下げる")

        if prob <= 20 and confidence < 0.5:
            issues.append("低確率（≤20%）だが信頼度も低い— 判断保留が望ましい")
            recommendations.append("追加情報収集後に再分析")

        # 50%近辺のアンカリングチェック
        if 45 <= prob <= 55:
            issues.append("50%近辺はアンカリングの可能性 — 追加分析で差別化を")

        # ファクトタイプチェック
        fact_type = prediction.get("fact_type", "SURFACE")
        if fact_type in ("WISHFUL", "ASSUMED") and prob >= 70:
            issues.append(f"ファクトタイプ={fact_type}なのに高確率({prob}%) — 根拠強化が必要")

        return {
            "audit_passed": len(issues) == 0,
            "issues": issues,
            "recommendations": recommendations,
            "audited_probability": prob,
            "audit_grade": "PASS" if not issues else ("WARN" if len(issues) == 1 else "FAIL"),
        }

    def generate_devil_advocate(self, topic: str, consensus_prob: float, tags: List[str]) -> str:
        """
        コンセンサスに対する悪魔の代弁者的反論を生成する

        これが監査官の最大の価値 — 「全員が同意している時に反論する者」
        """
        if consensus_prob >= 65:
            return (
                f"⚠️ 悪魔の代弁: 全員が「YES ({consensus_prob}%)」と言う時こそ危険。"
                f"「{topic}」に対して反論する3つの視点: "
                f"① 過去の類似事例が失敗した理由を確認したか？ "
                f"② このシナリオが成立しない条件は何か？ "
                f"③ 最も影響を受ける第三者（無視されているアクター）は誰か？"
            )
        elif consensus_prob <= 35:
            return (
                f"⚠️ 悪魔の代弁: 全員が「NO ({consensus_prob}%)」と言う時こそ危険。"
                f"「{topic}」が成立する意外なシナリオ: "
                f"① 想定外の外部ショック（ブラックスワン）が触媒になる場合 "
                f"② 現在の趨勢が反転するトリガーは何か？ "
                f"③ 市場が既にこの可能性を織り込んでいるか確認したか？"
            )
        else:
            return (
                f"悪魔の代弁: 確率{consensus_prob}%は「どちらとも言えない」範囲。"
                f"追加情報なしに判断するのは早計。判定日まで追跡を推奨。"
            )
