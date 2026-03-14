"""
agent_civilization/debate_engine.py
議論エンジン — 6エージェントが予測について議論し、最良の判断を導く

「良い議論は良い予測を生む」

エージェントはそれぞれの専門的視点から主張し合い、
Wishful facts を排除した Unshakeable facts だけで
合意に達するまで議論する。
"""

import sys
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent_civilization.agent_protocol import AgentProtocol, AgentMessage, MessageType


@dataclass
class DebatePosition:
    """議論における1エージェントの立場"""
    agent: str
    position: str          # "BULLISH" / "BEARISH" / "NEUTRAL" / YES / NO
    probability: int       # 予測確率（0〜100）
    reasoning: str
    key_claims: List[str] = field(default_factory=list)
    confidence: float = 0.7


@dataclass
class DebateRound:
    """議論の1ラウンド"""
    round_number: int
    positions: List[DebatePosition] = field(default_factory=list)
    rebuttal: Optional[str] = None


@dataclass
class DebateResult:
    """議論の最終結果"""
    topic: str
    rounds: List[DebateRound]
    consensus_probability: int
    consensus_pick: str
    majority_position: str
    dissent_agents: List[str]       # 少数意見のエージェント
    key_insights: List[str]
    debate_quality: str             # HIGH / MEDIUM / LOW
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "rounds": len(self.rounds),
            "consensus_probability": self.consensus_probability,
            "consensus_pick": self.consensus_pick,
            "majority_position": self.majority_position,
            "dissent_agents": self.dissent_agents,
            "key_insights": self.key_insights,
            "debate_quality": self.debate_quality,
            "completed_at": self.completed_at,
        }


class DebateEngine:
    """
    マルチエージェント議論エンジン

    原則:
    1. 各エージェントは独立した視点から主張する
    2. 反論は Unshakeable facts でのみ行う
    3. 最終確率は単純平均ではなく信頼度加重平均
    4. 全員が同意した場合のみ HIGH quality
    """

    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds

    def run_debate(self, topic: str, agent_positions: List[DebatePosition]) -> DebateResult:
        """
        エージェント議論を実行する

        Args:
            topic: 議論トピック
            agent_positions: 各エージェントの初期立場

        Returns:
            DebateResult
        """
        if not agent_positions:
            raise ValueError("議論には最低1エージェントが必要です")

        rounds = [DebateRound(round_number=1, positions=agent_positions)]

        # 最大3ラウンドの議論
        for round_num in range(2, self.max_rounds + 1):
            if self._is_consensus(agent_positions):
                break
            # 簡略化: 2ラウンド目以降は確率を収束させる
            agent_positions = self._converge_positions(agent_positions)
            rounds.append(DebateRound(round_number=round_num, positions=agent_positions))

        return self._synthesize_result(topic, rounds, agent_positions)

    def create_position_from_context(self, agent_name: str, agent_role: str,
                                      topic: str, tags: List[str],
                                      base_probability: int) -> DebatePosition:
        """
        エージェントの役割・タグから初期立場を生成する

        実際の実装ではLLMを呼ぶが、ここでは役割ベースのルールで生成する。
        """
        # 役割ごとの確率バイアス
        ROLE_BIASES = {
            "historian": 0,        # 歴史的ベースレートに忠実
            "scientist": -3,       # やや保守的（証拠重視）
            "economist": +2,       # やや楽観的（市場効率を信頼）
            "strategist": +5,      # やや強気（地政学リスクを重視）
            "builder": 0,          # 中立（実装の可否で判断）
            "auditor": -5,         # やや悲観的（リスク重視）
        }

        bias = ROLE_BIASES.get(agent_role, 0)
        adjusted_prob = max(5, min(95, base_probability + bias))

        # 立場テキスト
        if adjusted_prob >= 65:
            position = "BULLISH"
        elif adjusted_prob <= 35:
            position = "BEARISH"
        else:
            position = "NEUTRAL"

        # 役割ベースの理由
        ROLE_REASONING = {
            "historian": f"歴史的ベースレートに基づき {adjusted_prob}% と推定。類似事例では同様のパターンが繰り返された。",
            "scientist": f"データ的根拠から {adjusted_prob}% と推定。証拠が不十分な領域は保守的に評価。",
            "economist": f"市場価格と経済指標から {adjusted_prob}% と推定。効率的市場仮説を加味。",
            "strategist": f"地政学的力学から {adjusted_prob}% と推定。アクターの利益構造を分析。",
            "builder": f"実装難度・実現可能性から {adjusted_prob}% と推定。",
            "auditor": f"リスク分析から {adjusted_prob}% と推定。ダウンサイドリスクを優先考慮。",
        }

        return DebatePosition(
            agent=agent_name,
            position=position,
            probability=adjusted_prob,
            reasoning=ROLE_REASONING.get(agent_role, f"{adjusted_prob}% と推定"),
            key_claims=[f"{agent_role}視点: {topic} について {adjusted_prob}% の確率"],
            confidence=0.7,
        )

    # ── プライベートメソッド ──────────────────────────────────────

    def _is_consensus(self, positions: List[DebatePosition]) -> bool:
        """全エージェントが合意しているか（確率差が10%以内）"""
        probs = [p.probability for p in positions]
        return max(probs) - min(probs) <= 10

    def _converge_positions(self, positions: List[DebatePosition]) -> List[DebatePosition]:
        """
        各ラウンドで確率を収束させる（他のエージェントの意見を聞いて更新）

        簡略実装: 平均に向けて20%収束
        """
        avg_prob = sum(p.probability for p in positions) / len(positions)
        new_positions = []
        for pos in positions:
            # 平均に向けて20%引き寄せる（ベイズ更新の簡略版）
            new_prob = round(pos.probability * 0.8 + avg_prob * 0.2)
            new_prob = max(5, min(95, new_prob))
            new_positions.append(DebatePosition(
                agent=pos.agent,
                position=pos.position,
                probability=new_prob,
                reasoning=pos.reasoning + f" (更新: {pos.probability}→{new_prob}%)",
                key_claims=pos.key_claims,
                confidence=min(0.95, pos.confidence + 0.05),
            ))
        return new_positions

    def _synthesize_result(self, topic: str, rounds: List[DebateRound],
                            final_positions: List[DebatePosition]) -> DebateResult:
        """議論結果を合成する"""
        # 信頼度加重平均で最終確率を計算
        total_weight = sum(p.confidence for p in final_positions)
        consensus_prob = round(
            sum(p.probability * p.confidence for p in final_positions) / total_weight
        )

        # 多数派の立場
        bullish = sum(1 for p in final_positions if p.position == "BULLISH")
        bearish = sum(1 for p in final_positions if p.position == "BEARISH")
        neutral = sum(1 for p in final_positions if p.position == "NEUTRAL")

        if bullish > bearish and bullish > neutral:
            majority_position = "BULLISH"
        elif bearish > bullish and bearish > neutral:
            majority_position = "BEARISH"
        else:
            majority_position = "NEUTRAL"

        consensus_pick = "YES" if consensus_prob >= 50 else "NO"

        # 少数意見
        dissent_agents = [
            p.agent for p in final_positions
            if abs(p.probability - consensus_prob) > 15
        ]

        # インサイト集約
        key_insights = []
        for p in final_positions[:3]:
            key_insights.append(f"{p.agent}: {p.reasoning[:80]}")

        # 議論品質
        if self._is_consensus(final_positions):
            quality = "HIGH"
        elif max(p.probability for p in final_positions) - \
             min(p.probability for p in final_positions) <= 25:
            quality = "MEDIUM"
        else:
            quality = "LOW"

        return DebateResult(
            topic=topic,
            rounds=rounds,
            consensus_probability=consensus_prob,
            consensus_pick=consensus_pick,
            majority_position=majority_position,
            dissent_agents=dissent_agents,
            key_insights=key_insights,
            debate_quality=quality,
        )


if __name__ == "__main__":
    engine = DebateEngine()

    # デモ: 米中関税戦争の議論
    topic = "2026年内に追加関税が発動されるか？"
    base_prob = 60

    positions = [
        engine.create_position_from_context("historian", "historian", topic,
                                             ["経済・貿易", "対立の螺旋"], base_prob),
        engine.create_position_from_context("economist", "economist", topic,
                                             ["経済・貿易"], base_prob),
        engine.create_position_from_context("strategist", "strategist", topic,
                                             ["地政学・安全保障"], base_prob),
        engine.create_position_from_context("auditor", "auditor", topic, [], base_prob),
    ]

    result = engine.run_debate(topic, positions)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
