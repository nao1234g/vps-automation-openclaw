"""
agents/strategist.py
戦略家エージェント — 地政学・権力構造・リアルポリティク専門家

「国家は感情で動かない。利益で動く。アクターの利益構造を読め。」
"""

import sys
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.base_agent import BaseAgent


# 地政学的力学マトリクス
GEOPOLITICAL_DYNAMICS = {
    "対立の螺旋": {
        "driver": "エスカレーション・ダイナミクス",
        "de_escalation_probability": 0.25,
        "escalation_probability": 0.55,
        "status_quo_probability": 0.20,
    },
    "覇権移行": {
        "driver": "勢力均衡崩壊",
        "conflict_probability": 0.40,
        "negotiation_probability": 0.35,
        "coexistence_probability": 0.25,
    },
    "同盟再編": {
        "driver": "共通の敵または利益",
        "consolidation_probability": 0.60,
        "fragmentation_probability": 0.40,
    },
    "資源争奪": {
        "driver": "希少資源の支配権",
        "conflict_probability": 0.45,
        "cartel_probability": 0.30,
        "substitution_probability": 0.25,
    },
}


class StrategistAgent(BaseAgent):
    """
    戦略家エージェント

    専門:
    - リアルポリティク（国家利益の冷徹な分析）
    - 地政学的力学マトリクス適用
    - アクターの利益・制約・BATNA分析
    - 勢力均衡と覇権移行の確率推定
    """

    def __init__(self):
        super().__init__(
            name="strategist",
            role="strategist",
            description="地政学・戦略・権力構造の専門家。リアルポリティクで分析する。",
        )

    def analyze(self, topic: str, context: Dict) -> Dict:
        """戦略的視点から分析する"""
        tags = context.get("tags", [])
        base_prob = context.get("base_probability", 50)
        actors = context.get("actors", [])
        dynamics = context.get("dynamics", [])

        # 地政学的力学を特定
        geo_analysis = self._analyze_geopolitical_dynamics(tags, dynamics)

        # アクター利益分析
        actor_analysis = self._analyze_actor_interests(actors, tags)

        # 確率調整（戦略家は+5バイアス = やや強気）
        adjusted_prob = base_prob

        if geo_analysis:
            dyn_name = geo_analysis["dynamic"]
            dyn_data = GEOPOLITICAL_DYNAMICS[dyn_name]
            if "escalation_probability" in dyn_data:
                # 対立系: エスカレーション確率を重視
                adjusted_prob = round(
                    adjusted_prob * 0.6 + dyn_data["escalation_probability"] * 100 * 0.4
                )
            elif "conflict_probability" in dyn_data:
                adjusted_prob = round(
                    adjusted_prob * 0.7 + dyn_data["conflict_probability"] * 100 * 0.3
                )

        # 戦略家バイアス（+5: やや強気・リスク許容）
        adjusted_prob = max(5, min(95, adjusted_prob + 5))

        # アクター分析で修正
        if actor_analysis:
            if actor_analysis["consensus"] == "ALIGNED":
                adjusted_prob = min(95, adjusted_prob + 5)
            elif actor_analysis["consensus"] == "OPPOSED":
                adjusted_prob = max(5, adjusted_prob - 8)

        confidence = 0.75 if geo_analysis else 0.55

        geo_text = f"力学: {geo_analysis['dynamic']}" if geo_analysis else "地政学的力学: 特定不可"
        actor_text = f"アクター合意: {actor_analysis['consensus']}" if actor_analysis else "アクター分析: データ不足"

        analysis = (
            f"戦略分析: {geo_text}。{actor_text}。"
            f"リアルポリティク評価: {adjusted_prob}%。"
            f"国家利益ベクトルは{'収束' if adjusted_prob > 55 else '分散'}している。"
        )

        result = self._format_analysis_result(
            analysis=analysis,
            probability=adjusted_prob,
            confidence=confidence,
            key_claims=[geo_text, actor_text, f"戦略的確率: {adjusted_prob}%"],
            fact_type="ASSUMED",
        )

        self.remember_analysis(topic, analysis, tags, importance=0.8)
        return result

    def _analyze_geopolitical_dynamics(
        self, tags: List[str], dynamics: List[str]
    ) -> Optional[Dict]:
        """タグ・力学から地政学的パターンを特定する"""
        for dyn_name in GEOPOLITICAL_DYNAMICS:
            if dyn_name in tags or dyn_name in dynamics:
                return {"dynamic": dyn_name, "data": GEOPOLITICAL_DYNAMICS[dyn_name]}

        # タグから間接的に特定
        if "地政学・安全保障" in tags:
            if "対立の螺旋" in tags:
                return {"dynamic": "対立の螺旋", "data": GEOPOLITICAL_DYNAMICS["対立の螺旋"]}
            return {"dynamic": "覇権移行", "data": GEOPOLITICAL_DYNAMICS["覇権移行"]}

        return None

    def _analyze_actor_interests(self, actors: List[str], tags: List[str]) -> Optional[Dict]:
        """アクターの利益構造を分析する"""
        if not actors and "地政学・安全保障" not in tags:
            return None

        # 簡易分析: アクター数で合意可能性を推定
        if len(actors) <= 2:
            consensus = "ALIGNED"  # 少数なら交渉可能
        elif len(actors) <= 4:
            consensus = "MIXED"
        else:
            consensus = "OPPOSED"  # 多数アクターは利益が分散

        return {
            "actor_count": len(actors),
            "consensus": consensus,
            "note": f"{len(actors)}アクター間の利益調整",
        }

    def get_strategic_scenarios(self, topic: str, tags: List[str]) -> Dict:
        """戦略的シナリオ（3つ）を生成する"""
        memories = self.get_relevant_memories(tags)
        geo_analysis = self._analyze_geopolitical_dynamics(tags, [])

        base_driver = geo_analysis["dynamic"] if geo_analysis else "不確実性"

        return {
            "topic": topic,
            "strategic_driver": base_driver,
            "scenarios": {
                "hawk": {
                    "name": "タカ派シナリオ",
                    "description": f"{base_driver}がエスカレートし、強硬手段が優勢になる",
                    "probability": 0.35,
                },
                "dove": {
                    "name": "ハト派シナリオ",
                    "description": "外交交渉が機能し、合意に至る",
                    "probability": 0.30,
                },
                "status_quo": {
                    "name": "現状維持シナリオ",
                    "description": "決定的な動きはなく、膠着状態が続く",
                    "probability": 0.35,
                },
            },
            "past_patterns_used": len(memories),
        }
