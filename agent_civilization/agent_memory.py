"""
agent_civilization/agent_memory.py
エージェントメモリ — 各エージェントの個別記憶と経験蓄積

各エージェントは固有の専門知識・過去の判断・学習履歴を持つ。
このメモリがエージェントを「単なるLLM呼び出し」から「経験を持つ専門家」に変える。
"""

import sys
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class MemoryItem:
    """単一の記憶アイテム"""
    item_id: str
    agent_name: str
    memory_type: str           # "analysis" / "debate_win" / "debate_loss" / "prediction_hit" / "prediction_miss"
    content: str
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5    # 0.0〜1.0（重要度）
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recall_count: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


class AgentMemory:
    """
    エージェント個別メモリストレージ

    各エージェントはこれを1つ持つ。
    重要度 × 想起頻度 で記憶の「強さ」を管理する。
    """

    MEMORY_BASE_PATH = "data/agent_memories"
    MAX_ITEMS_PER_AGENT = 1000

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.memory_path = os.path.join(
            self.MEMORY_BASE_PATH, f"{agent_name}_memory.json"
        )
        self._items: Dict[str, MemoryItem] = {}
        self._load()

    # ── 書き込み ──────────────────────────────────────

    def remember(self, memory_type: str, content: str,
                 tags: List[str] = None, importance: float = 0.5) -> MemoryItem:
        """新しい記憶を追加する"""
        item_id = f"{self.agent_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:18]}"
        item = MemoryItem(
            item_id=item_id,
            agent_name=self.agent_name,
            memory_type=memory_type,
            content=content,
            tags=tags or [],
            importance=importance,
        )
        self._items[item_id] = item

        # 上限を超えたら重要度の低いものを削除
        if len(self._items) > self.MAX_ITEMS_PER_AGENT:
            self._prune()

        self._save()
        return item

    def record_prediction_result(self, prediction_id: str,
                                  result: str, brier_score: float,
                                  tags: List[str] = None):
        """予測結果を記憶する"""
        importance = 0.9 if result == "HIT" else 0.7
        content = f"予測 [{prediction_id}] → {result} (Brier={brier_score:.3f})"
        memory_type = "prediction_hit" if result == "HIT" else "prediction_miss"
        self.remember(memory_type, content, tags=tags, importance=importance)

    def record_debate_outcome(self, topic: str, outcome: str, reasoning: str):
        """議論の結果を記憶する"""
        importance = 0.8
        memory_type = "debate_win" if outcome == "WIN" else "debate_loss"
        content = f"議論「{topic}」→ {outcome}: {reasoning[:100]}"
        self.remember(memory_type, content, importance=importance)

    # ── 読み取り ──────────────────────────────────────

    def recall(self, query: str = None, memory_type: str = None,
               tags: List[str] = None, limit: int = 5) -> List[MemoryItem]:
        """
        記憶を想起する

        重要度×想起頻度でスコアリングし、関連性の高い記憶を返す。
        """
        items = list(self._items.values())

        if memory_type:
            items = [i for i in items if i.memory_type == memory_type]

        if tags:
            items = [i for i in items if any(t in i.tags for t in tags)]

        if query:
            q = query.lower()
            items = [i for i in items if q in i.content.lower()]

        # スコア = 重要度 × (1 + recall_count × 0.1)（想起するほど強化）
        items.sort(key=lambda i: i.importance * (1 + i.recall_count * 0.1), reverse=True)

        results = items[:limit]
        # 想起カウントをインクリメント
        for item in results:
            self._items[item.item_id].recall_count += 1
        if results:
            self._save()

        return results

    def get_expertise_summary(self) -> Dict:
        """このエージェントの専門性サマリー"""
        items = list(self._items.values())
        if not items:
            return {"expertise": "未蓄積", "top_tags": [], "total_memories": 0}

        # タグ頻度
        tag_freq: Dict[str, int] = {}
        for item in items:
            for tag in item.tags:
                tag_freq[tag] = tag_freq.get(tag, 0) + 1

        top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:5]

        # 予測精度
        hits = sum(1 for i in items if i.memory_type == "prediction_hit")
        misses = sum(1 for i in items if i.memory_type == "prediction_miss")
        total_preds = hits + misses

        return {
            "agent": self.agent_name,
            "total_memories": len(items),
            "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
            "prediction_hit_rate": round(hits / total_preds, 3) if total_preds > 0 else None,
            "prediction_total": total_preds,
            "debate_wins": sum(1 for i in items if i.memory_type == "debate_win"),
            "debate_losses": sum(1 for i in items if i.memory_type == "debate_loss"),
        }

    # ── プライベート ──────────────────────────────────────

    def _prune(self):
        """重要度の低いアイテムを削除する（上限管理）"""
        items = sorted(self._items.values(),
                       key=lambda i: i.importance * (1 + i.recall_count * 0.1))
        to_remove = len(self._items) - self.MAX_ITEMS_PER_AGENT + 100
        for item in items[:to_remove]:
            del self._items[item.item_id]

    def _load(self):
        if not os.path.exists(self.memory_path):
            return
        try:
            with open(self.memory_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item_id, data in raw.items():
                self._items[item_id] = MemoryItem(**data)
        except Exception as e:
            print(f"[WARNING] AgentMemory({self.agent_name}) load error: {e}")

    def _save(self):
        os.makedirs(self.MEMORY_BASE_PATH, exist_ok=True)
        try:
            data = {iid: item.to_dict() for iid, item in self._items.items()}
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] AgentMemory({self.agent_name}) save error: {e}")


if __name__ == "__main__":
    mem = AgentMemory("historian")
    mem.remember(
        "analysis",
        "1930年代の保護主義の螺旋: スムート・ホーリー関税法 → 世界貿易60%縮小",
        tags=["経済・貿易", "対立の螺旋"],
        importance=0.9,
    )
    mem.record_prediction_result("2026-03-01-001", "HIT", 0.14,
                                  tags=["経済・金融", "対立の螺旋"])

    memories = mem.recall(tags=["対立の螺旋"])
    for m in memories:
        print(f"[{m.memory_type}] {m.content[:60]}")

    print("\n専門性サマリー:", json.dumps(mem.get_expertise_summary(), ensure_ascii=False, indent=2))
