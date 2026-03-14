"""agent_civilization — AI Civilization OS のエージェント層

6つの専門エージェントが協調して予測・分析・意思決定を行う。

エージェント:
  - historian: 歴史パターン専門家
  - scientist: データ分析・検証専門家
  - economist: 経済・金融専門家
  - strategist: 戦略・地政学専門家
  - builder: 実装・構築専門家
  - auditor: 品質・検証専門家
"""
from agent_civilization.agent_manager import AgentManager
from agent_civilization.agent_protocol import AgentProtocol, AgentMessage, MessageType
from agent_civilization.debate_engine import DebateEngine
from agent_civilization.consensus_engine import ConsensusEngine
from agent_civilization.agent_memory import AgentMemory

__all__ = [
    "AgentManager",
    "AgentProtocol", "AgentMessage", "MessageType",
    "DebateEngine",
    "ConsensusEngine",
    "AgentMemory",
]
