"""knowledge_engine — AI Civilization OS の Knowledge Layer

役割:
- 歴史的パターンを蓄積・検索する
- 力学ナレッジグラフを管理する
- 予測の学習ループを回す
"""
from knowledge_engine.knowledge_store import KnowledgeStore, KnowledgeEntry
from knowledge_engine.knowledge_graph import KnowledgeGraph
from knowledge_engine.history_loader import HistoryLoader
from knowledge_engine.civilization_patterns import CivilizationPatterns
from knowledge_engine.learning_loop import LearningLoop

__all__ = [
    "KnowledgeStore", "KnowledgeEntry",
    "KnowledgeGraph",
    "HistoryLoader",
    "CivilizationPatterns",
    "LearningLoop",
]
