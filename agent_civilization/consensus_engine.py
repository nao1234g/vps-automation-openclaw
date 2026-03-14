"""
agent_civilization/consensus_engine.py
合意エンジン — エージェント投票から最終的な予測判断を導出する

議論後の投票を集計し、Nowpatternの「公式予測」として
prediction_dbに登録できる形式に変換する。
"""

import sys
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent_civilization.agent_protocol import AgentMessage, MessageType


@dataclass
class Vote:
    """エージェントの投票"""
    agent: str
    vote: str              # "YES" / "NO" / "ABSTAIN"
    probability: int       # 0〜100
    reasoning: str
    confidence: float      # 0.0〜1.0（投票の確信度）


@dataclass
class ConsensusResult:
    """合意結果"""
    proposal_id: str
    proposal_title: str
    votes: List[Vote]
    final_pick: str          # "YES" / "NO"
    final_probability: int   # 0〜100（信頼度加重平均）
    consensus_level: str     # "STRONG" / "MODERATE" / "WEAK" / "DIVIDED"
    yes_votes: int
    no_votes: int
    abstain_votes: int
    dissent_notes: List[str]
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return {
            "proposal_id": self.proposal_id,
            "proposal_title": self.proposal_title,
            "final_pick": self.final_pick,
            "final_probability": self.final_probability,
            "consensus_level": self.consensus_level,
            "yes_votes": self.yes_votes,
            "no_votes": self.no_votes,
            "abstain_votes": self.abstain_votes,
            "dissent_notes": self.dissent_notes,
            "decided_at": self.decided_at,
            "vote_breakdown": [
                {"agent": v.agent, "vote": v.vote, "prob": v.probability,
                 "confidence": v.confidence}
                for v in self.votes
            ],
        }

    def to_prediction_dict(self) -> Dict:
        """prediction_db.json 追加用の形式に変換"""
        return {
            "our_pick": self.final_pick,
            "our_pick_prob": self.final_probability,
            "consensus_level": self.consensus_level,
            "agent_vote_summary": f"YES={self.yes_votes}/NO={self.no_votes}/ABSTAIN={self.abstain_votes}",
        }


class ConsensusEngine:
    """
    合意エンジン

    ルール:
    1. 絶対多数（4/6以上）でST RONG合意
    2. 単純多数（3/5以上）でMODERATE合意
    3. 同数またはABSTAIN多数でWEAK / DIVIDED
    4. 信頼度加重平均で最終確率を計算
    """

    def collect_votes(self, proposal_id: str, proposal_title: str,
                       vote_messages: List[AgentMessage]) -> ConsensusResult:
        """
        投票メッセージを収集して合意を計算する

        Args:
            vote_messages: MessageType.CONSENSUS_VOTE のメッセージリスト
        """
        votes = []
        for msg in vote_messages:
            if msg.message_type != MessageType.CONSENSUS_VOTE:
                continue
            if msg.payload.get("proposal_id") != proposal_id:
                continue

            votes.append(Vote(
                agent=msg.sender,
                vote=msg.payload.get("vote", "ABSTAIN"),
                probability=msg.payload.get("probability", 50),
                reasoning=msg.payload.get("reasoning", ""),
                confidence=msg.payload.get("confidence", 0.5),
            ))

        return self._calculate_consensus(proposal_id, proposal_title, votes)

    def calculate_from_debate(self, proposal_id: str, proposal_title: str,
                               agent_name_prob_list: List[Dict]) -> ConsensusResult:
        """
        議論結果（エージェント名 + 確率 + 信頼度のリスト）から合意を計算する

        Args:
            agent_name_prob_list: [{"agent": "historian", "prob": 65, "confidence": 0.8}]
        """
        votes = []
        for entry in agent_name_prob_list:
            prob = entry.get("prob", 50)
            vote_str = "YES" if prob >= 50 else "NO"
            if 45 <= prob <= 55:
                vote_str = "ABSTAIN"

            votes.append(Vote(
                agent=entry.get("agent", "unknown"),
                vote=vote_str,
                probability=prob,
                reasoning=entry.get("reasoning", ""),
                confidence=entry.get("confidence", 0.7),
            ))

        return self._calculate_consensus(proposal_id, proposal_title, votes)

    def _calculate_consensus(self, proposal_id: str, proposal_title: str,
                              votes: List[Vote]) -> ConsensusResult:
        """合意計算のコア"""
        if not votes:
            return ConsensusResult(
                proposal_id=proposal_id,
                proposal_title=proposal_title,
                votes=[],
                final_pick="NO",
                final_probability=50,
                consensus_level="WEAK",
                yes_votes=0, no_votes=0, abstain_votes=0,
                dissent_notes=["投票なし"],
            )

        yes_votes = sum(1 for v in votes if v.vote == "YES")
        no_votes = sum(1 for v in votes if v.vote == "NO")
        abstain_votes = sum(1 for v in votes if v.vote == "ABSTAIN")
        total_decisive = yes_votes + no_votes

        # 信頼度加重平均で最終確率
        total_weight = sum(v.confidence for v in votes if v.vote != "ABSTAIN")
        if total_weight > 0:
            final_prob = round(
                sum(v.probability * v.confidence for v in votes if v.vote != "ABSTAIN")
                / total_weight
            )
        else:
            final_prob = 50

        final_prob = max(5, min(95, final_prob))
        final_pick = "YES" if final_prob >= 50 else "NO"

        # 合意レベル判定
        if total_decisive == 0:
            consensus_level = "DIVIDED"
        elif total_decisive > 0:
            majority = max(yes_votes, no_votes)
            majority_ratio = majority / len(votes)
            if majority_ratio >= 0.8:
                consensus_level = "STRONG"
            elif majority_ratio >= 0.6:
                consensus_level = "MODERATE"
            elif majority_ratio >= 0.5:
                consensus_level = "WEAK"
            else:
                consensus_level = "DIVIDED"
        else:
            consensus_level = "DIVIDED"

        # 少数意見を収集
        dissent_notes = []
        for v in votes:
            if abs(v.probability - final_prob) > 20 and v.vote != "ABSTAIN":
                dissent_notes.append(
                    f"{v.agent}: {v.vote} ({v.probability}%) — {v.reasoning[:60]}"
                )

        return ConsensusResult(
            proposal_id=proposal_id,
            proposal_title=proposal_title,
            votes=votes,
            final_pick=final_pick,
            final_probability=final_prob,
            consensus_level=consensus_level,
            yes_votes=yes_votes,
            no_votes=no_votes,
            abstain_votes=abstain_votes,
            dissent_notes=dissent_notes,
        )


if __name__ == "__main__":
    engine = ConsensusEngine()

    # デモ: 議論後の合意計算
    result = engine.calculate_from_debate(
        proposal_id="2026-03-14-001",
        proposal_title="2026年内に追加関税が発動されるか？",
        agent_name_prob_list=[
            {"agent": "historian",  "prob": 60, "confidence": 0.85, "reasoning": "歴史的パターン一致"},
            {"agent": "economist",  "prob": 62, "confidence": 0.80, "reasoning": "市場シグナル強"},
            {"agent": "strategist", "prob": 68, "confidence": 0.75, "reasoning": "地政学リスク高"},
            {"agent": "scientist",  "prob": 57, "confidence": 0.90, "reasoning": "データ証拠は中程度"},
            {"agent": "builder",    "prob": 59, "confidence": 0.70, "reasoning": "実現可能性は高い"},
            {"agent": "auditor",    "prob": 55, "confidence": 0.85, "reasoning": "リスク要因を保守的に評価"},
        ]
    )

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    print("\n予測DB用:", json.dumps(result.to_prediction_dict(), ensure_ascii=False, indent=2))
