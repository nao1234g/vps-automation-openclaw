"""
agents/base_agent.py
エージェント基底クラス — 全6エージェントが継承する共通インターフェース

各エージェントは analyze() をオーバーライドして専門分析を実装する。
共通機能（メモリ・ファクトチェック・メッセージング）はここで提供。
"""

import sys
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent_civilization.agent_memory import AgentMemory
from agent_civilization.agent_protocol import AgentProtocol, AgentMessage, Claim


class BaseAgent(ABC):
    """
    エージェント基底クラス

    サブクラスは analyze() を必ず実装すること。
    """

    def __init__(self, name: str, role: str, description: str):
        self.name = name
        self.role = role
        self.description = description
        self.memory = AgentMemory(name)
        self._message_queue: List[AgentMessage] = []

    @abstractmethod
    def analyze(self, topic: str, context: Dict) -> Dict:
        """
        専門分析を実行する（サブクラスで実装）

        Args:
            topic: 分析トピック
            context: タグ、確率、ニュースデータ等のコンテキスト

        Returns:
            {
              "analysis": str,        # 分析テキスト
              "probability": int,     # 予測確率（0〜100）
              "confidence": float,    # 確信度（0.0〜1.0）
              "key_claims": List[str],# 主要な主張
              "fact_type": str,       # 使用したファクトのタイプ
            }
        """

    def receive_message(self, message: AgentMessage):
        """メッセージを受信してキューに追加する"""
        is_valid, errors = AgentProtocol.validate_message(message)
        if not is_valid:
            print(f"[{self.name}] メッセージ検証失敗: {errors}")
            return
        self._message_queue.append(message)

    def get_relevant_memories(self, tags: List[str], limit: int = 5) -> List[str]:
        """タグに関連する過去の記憶を取得する"""
        items = self.memory.recall(tags=tags, limit=limit)
        return [item.content for item in items]

    def remember_analysis(self, topic: str, analysis: str,
                           tags: List[str], importance: float = 0.6):
        """分析結果を記憶に保存する"""
        content = f"分析「{topic[:40]}」: {analysis[:100]}"
        self.memory.remember("analysis", content, tags=tags, importance=importance)

    def get_status(self) -> Dict:
        """エージェントの状態を返す"""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "message_queue_size": len(self._message_queue),
            "expertise": self.memory.get_expertise_summary(),
        }

    def _format_analysis_result(self, analysis: str, probability: int,
                                  confidence: float, key_claims: List[str],
                                  fact_type: str = "SURFACE") -> Dict:
        """分析結果を標準フォーマットに変換する"""
        return {
            "agent": self.name,
            "role": self.role,
            "analysis": analysis,
            "probability": max(5, min(95, probability)),
            "confidence": max(0.0, min(1.0, confidence)),
            "key_claims": key_claims,
            "fact_type": fact_type,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
