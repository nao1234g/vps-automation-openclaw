"""
agent_civilization/agent_manager.py
エージェントマネージャー — 6エージェントの生成・管理・タスク配分

6エージェント（historian / scientist / economist / strategist / builder / auditor）を
一元管理し、予測生成・議論・合意のオーケストレーションを行う。
"""

import sys
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent_civilization.agent_memory import AgentMemory
from agent_civilization.debate_engine import DebateEngine, DebatePosition
from agent_civilization.consensus_engine import ConsensusEngine
from agent_civilization.agent_protocol import AgentProtocol


# エージェント定義
AGENT_DEFINITIONS = {
    "historian": {
        "name": "historian",
        "role": "historian",
        "description": "歴史的パターン・類似事例の専門家。3000年の歴史データから力学を読む。",
        "specialties": ["地政学・安全保障", "経済・貿易", "政治・選挙"],
        "bias": "historical_precedent",
    },
    "scientist": {
        "name": "scientist",
        "role": "scientist",
        "description": "データ分析・統計・証拠検証の専門家。Wishful factsをブロックする番犬。",
        "specialties": ["テクノロジー・AI", "経済・金融"],
        "bias": "evidence_based",
    },
    "economist": {
        "name": "economist",
        "role": "economist",
        "description": "経済・金融・市場の専門家。Polymarket確率との乖離を分析する。",
        "specialties": ["経済・金融", "経済・貿易", "暗号資産"],
        "bias": "market_efficiency",
    },
    "strategist": {
        "name": "strategist",
        "role": "strategist",
        "description": "地政学・国際関係・権力構造の専門家。アクターの利益構造を分析する。",
        "specialties": ["地政学・安全保障", "政治・選挙"],
        "bias": "realpolitik",
    },
    "builder": {
        "name": "builder",
        "role": "builder",
        "description": "実装・構築・実現可能性の専門家。「これは本当に起きうるか」を問う。",
        "specialties": ["テクノロジー・AI", "経済・貿易"],
        "bias": "feasibility",
    },
    "auditor": {
        "name": "auditor",
        "role": "auditor",
        "description": "品質・リスク・ダウンサイドの専門家。過剰な楽観論に常に反論する。",
        "specialties": [],  # 全ジャンル対応
        "bias": "risk_focused",
    },
}


class AgentManager:
    """
    6エージェントのオーケストレーター

    使い方:
      manager = AgentManager()
      result = manager.generate_prediction_with_debate(
          title="米中追加関税", tags=["経済・貿易", "対立の螺旋"], base_prob=60
      )
    """

    def __init__(self):
        self.agents = AGENT_DEFINITIONS.copy()
        self.memories: Dict[str, AgentMemory] = {
            name: AgentMemory(name) for name in self.agents
        }
        self.debate_engine = DebateEngine()
        self.consensus_engine = ConsensusEngine()

    def generate_prediction_with_debate(self,
                                          title: str,
                                          tags: List[str],
                                          base_prob: int,
                                          proposal_id: str = None) -> Dict:
        """
        6エージェントの議論を経て予測を生成する

        Args:
            title: 予測タイトル
            tags: 力学・ジャンルタグ
            base_prob: ProbabilityEstimator による基準確率
            proposal_id: 予測ID（Noneなら自動生成）

        Returns:
            {
              "debate_result": DebateResult.to_dict(),
              "consensus": ConsensusResult.to_dict(),
              "final_probability": int,
              "final_pick": str,
            }
        """
        if not proposal_id:
            proposal_id = f"DEBATE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # 1. 関連エージェントを選択（specialtiesがtagsに含まれるもの優先）
        relevant_agents = self._select_agents(tags)

        # 2. 各エージェントの初期立場を生成
        positions: List[DebatePosition] = []
        for agent_name in relevant_agents:
            agent_def = self.agents[agent_name]
            pos = self.debate_engine.create_position_from_context(
                agent_name=agent_name,
                agent_role=agent_def["role"],
                topic=title,
                tags=tags,
                base_probability=base_prob,
            )
            positions.append(pos)

        # 3. 議論を実行
        debate_result = self.debate_engine.run_debate(title, positions)

        # 4. 合意を計算
        agent_prob_list = [
            {
                "agent": p.agent,
                "prob": p.probability,
                "confidence": p.confidence,
                "reasoning": p.reasoning,
            }
            for p in debate_result.rounds[-1].positions
        ]
        consensus = self.consensus_engine.calculate_from_debate(
            proposal_id=proposal_id,
            proposal_title=title,
            agent_name_prob_list=agent_prob_list,
        )

        # 5. エージェントメモリに記録
        for agent_name in relevant_agents:
            self.memories[agent_name].remember(
                "analysis",
                f"予測議論参加: 「{title}」 → {consensus.final_pick} ({consensus.final_probability}%)",
                tags=tags,
                importance=0.7,
            )

        return {
            "debate_result": debate_result.to_dict(),
            "consensus": consensus.to_dict(),
            "final_probability": consensus.final_probability,
            "final_pick": consensus.final_pick,
            "consensus_level": consensus.consensus_level,
            "participating_agents": relevant_agents,
        }

    def record_prediction_resolution(self, prediction_id: str,
                                       result: str, brier_score: float,
                                       tags: List[str]):
        """予測解決を全エージェントのメモリに記録する"""
        for agent_name, memory in self.memories.items():
            memory.record_prediction_result(prediction_id, result, brier_score, tags)

    def get_agent_expertise_report(self) -> Dict:
        """全エージェントの専門性レポートを生成する"""
        return {
            name: memory.get_expertise_summary()
            for name, memory in self.memories.items()
        }

    def _select_agents(self, tags: List[str]) -> List[str]:
        """
        タグに関連するエージェントを選択する

        必ずauditを含む（品質管理のため）。
        関連エージェントが少ない場合は全エージェント参加。
        """
        selected = set()

        for agent_name, agent_def in self.agents.items():
            specialties = agent_def.get("specialties", [])
            if not specialties:  # specialtiesが空 = 全ジャンル対応（auditor）
                selected.add(agent_name)
                continue
            if any(t in specialties for t in tags):
                selected.add(agent_name)

        # 最低4エージェント確保
        if len(selected) < 4:
            selected = set(self.agents.keys())

        # auditor は常に参加
        selected.add("auditor")

        return list(selected)


if __name__ == "__main__":
    manager = AgentManager()

    # デモ: 米中関税戦争の議論
    result = manager.generate_prediction_with_debate(
        title="2026年内に追加関税が発動されるか？",
        tags=["経済・貿易", "地政学・安全保障", "対立の螺旋"],
        base_prob=60,
    )

    print(f"\n=== 議論結果 ===")
    print(f"最終確率: {result['final_probability']}%")
    print(f"最終予測: {result['final_pick']}")
    print(f"合意レベル: {result['consensus_level']}")
    print(f"参加エージェント: {result['participating_agents']}")
    print(f"\nインサイト:")
    for insight in result["debate_result"]["key_insights"]:
        print(f"  - {insight}")
