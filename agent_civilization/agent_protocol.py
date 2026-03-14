"""
agent_civilization/agent_protocol.py
エージェント間通信プロトコル — 標準メッセージフォーマットと型定義

全エージェントはこのプロトコルで通信する。
型安全なメッセージングでエージェント間の誤解を防ぐ。
"""

import sys
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class MessageType(Enum):
    """メッセージタイプ"""
    ANALYSIS_REQUEST = "analysis_request"     # 分析依頼
    ANALYSIS_RESPONSE = "analysis_response"   # 分析結果
    DEBATE_CLAIM = "debate_claim"             # 議論での主張
    DEBATE_REBUTTAL = "debate_rebuttal"       # 反論
    CONSENSUS_VOTE = "consensus_vote"         # 合意投票
    PREDICTION_PROPOSAL = "prediction_proposal"  # 予測提案
    FACT_CHECK = "fact_check"                 # ファクトチェック依頼
    FACT_CHECK_RESULT = "fact_check_result"   # ファクトチェック結果
    LEARNING_SIGNAL = "learning_signal"       # 学習シグナル
    ALERT = "alert"                           # 警告・異常通知


@dataclass
class Claim:
    """エージェントの主張"""
    content: str
    confidence: float           # 0.0〜1.0
    fact_type: str              # UNSHAKEABLE / SURFACE / ASSUMED / REPORTED
    evidence_ids: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


@dataclass
class AgentMessage:
    """エージェント間メッセージ"""
    message_id: str
    sender: str                 # エージェント名
    receiver: str               # エージェント名（"ALL" = ブロードキャスト）
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None   # リクエスト-レスポンス紐付け

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["message_type"] = self.message_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentMessage":
        data["message_type"] = MessageType(data["message_type"])
        return cls(**data)


class AgentProtocol:
    """
    エージェント間通信プロトコル

    メッセージの生成・検証・ルーティングを管理する。
    """

    @staticmethod
    def create_analysis_request(sender: str, receiver: str,
                                 topic: str, context: Dict,
                                 tags: List[str] = None) -> AgentMessage:
        """分析依頼メッセージを生成する"""
        return AgentMessage(
            message_id=AgentProtocol._generate_id(),
            sender=sender,
            receiver=receiver,
            message_type=MessageType.ANALYSIS_REQUEST,
            payload={
                "topic": topic,
                "context": context,
                "tags": tags or [],
            }
        )

    @staticmethod
    def create_analysis_response(sender: str, receiver: str,
                                  correlation_id: str,
                                  analysis: str,
                                  claims: List[Claim],
                                  confidence: float) -> AgentMessage:
        """分析結果メッセージを生成する"""
        return AgentMessage(
            message_id=AgentProtocol._generate_id(),
            sender=sender,
            receiver=receiver,
            message_type=MessageType.ANALYSIS_RESPONSE,
            correlation_id=correlation_id,
            payload={
                "analysis": analysis,
                "claims": [asdict(c) for c in claims],
                "overall_confidence": confidence,
            }
        )

    @staticmethod
    def create_debate_claim(sender: str, topic: str,
                             position: str, reasoning: str,
                             confidence: float,
                             evidence_ids: List[str] = None) -> AgentMessage:
        """議論での主張メッセージを生成する"""
        return AgentMessage(
            message_id=AgentProtocol._generate_id(),
            sender=sender,
            receiver="ALL",
            message_type=MessageType.DEBATE_CLAIM,
            payload={
                "topic": topic,
                "position": position,
                "reasoning": reasoning,
                "confidence": confidence,
                "evidence_ids": evidence_ids or [],
            }
        )

    @staticmethod
    def create_consensus_vote(sender: str, proposal_id: str,
                               vote: str,  # "YES" / "NO" / "ABSTAIN"
                               reasoning: str,
                               confidence: float) -> AgentMessage:
        """合意投票メッセージを生成する"""
        return AgentMessage(
            message_id=AgentProtocol._generate_id(),
            sender=sender,
            receiver="consensus_engine",
            message_type=MessageType.CONSENSUS_VOTE,
            payload={
                "proposal_id": proposal_id,
                "vote": vote,
                "reasoning": reasoning,
                "confidence": confidence,
            }
        )

    @staticmethod
    def create_prediction_proposal(sender: str,
                                    title: str,
                                    our_pick: str,
                                    probability: int,
                                    reasoning: str,
                                    tags: List[str],
                                    resolution_date: str) -> AgentMessage:
        """予測提案メッセージを生成する"""
        return AgentMessage(
            message_id=AgentProtocol._generate_id(),
            sender=sender,
            receiver="ALL",
            message_type=MessageType.PREDICTION_PROPOSAL,
            payload={
                "title": title,
                "our_pick": our_pick,
                "probability": probability,
                "reasoning": reasoning,
                "tags": tags,
                "resolution_date": resolution_date,
            }
        )

    @staticmethod
    def validate_message(message: AgentMessage) -> tuple:
        """
        メッセージの検証

        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []

        # Wishful fact チェック（ANALYSIS_RESPONSE の場合）
        if message.message_type == MessageType.ANALYSIS_RESPONSE:
            claims = message.payload.get("claims", [])
            for claim in claims:
                if claim.get("fact_type") == "WISHFUL":
                    errors.append(f"WISHFUL fact が含まれています: {claim.get('content', '')[:50]}")

        # 信頼度チェック
        confidence = message.payload.get("overall_confidence",
                                          message.payload.get("confidence", 0.5))
        if not (0.0 <= confidence <= 1.0):
            errors.append(f"信頼度が範囲外: {confidence}")

        return len(errors) == 0, errors

    @staticmethod
    def _generate_id() -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:18]
        return f"MSG-{ts}"


if __name__ == "__main__":
    # デモ
    msg = AgentProtocol.create_analysis_request(
        sender="strategist",
        receiver="historian",
        topic="米中貿易摩擦の行方",
        context={"tags": ["経済・貿易", "対立の螺旋"], "probability": 62},
    )
    print(json.dumps(msg.to_dict(), ensure_ascii=False, indent=2))

    is_valid, errors = AgentProtocol.validate_message(msg)
    print(f"\n検証: {'OK' if is_valid else 'NG'} {errors}")
