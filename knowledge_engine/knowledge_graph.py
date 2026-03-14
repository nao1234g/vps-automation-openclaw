"""
knowledge_engine/knowledge_graph.py
力学ナレッジグラフ — 力学タグ間の関係性・共起パターンを管理する

「対立の螺旋」と「伝染の連鎖」が同時に発動した時の
過去の予測精度はどうだったか？
→ このグラフがその答えを持っている。
"""

import sys
import json
import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class KnowledgeGraph:
    """
    力学ナレッジグラフ

    ノード: 力学タグ / ジャンルタグ / イベントタグ
    エッジ: 共起回数 + 平均Brier Score + 的中率

    使い方:
      1. 記事が公開されるたびに update_from_prediction() を呼ぶ
      2. 予測が解決されたら resolve_edge() で精度を更新する
      3. get_cooccurrence() で特定タグの関係性を調べる
    """

    DEFAULT_PATH = "data/knowledge_graph.json"

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DEFAULT_PATH
        # edges: {(tag_a, tag_b): {"count": N, "hit": M, "brier_sum": X, "predictions": [...]}}
        self._edges: Dict[str, Dict] = {}
        # node metadata: {tag: {"count": N, "avg_brier": X, "hit_rate": X}}
        self._nodes: Dict[str, Dict] = {}
        self._load()

    # ── 更新 ──────────────────────────────────────

    def update_from_prediction(self, prediction_id: str, tags: List[str]):
        """
        新しい予測からグラフを更新する（共起エッジを追加）
        """
        # ノード更新
        for tag in tags:
            if tag not in self._nodes:
                self._nodes[tag] = {"count": 0, "hit": 0, "resolved": 0,
                                     "brier_sum": 0.0, "predictions": []}
            self._nodes[tag]["count"] += 1
            self._nodes[tag]["predictions"].append(prediction_id)

        # エッジ更新（全ペアの共起）
        for i, tag_a in enumerate(tags):
            for tag_b in tags[i+1:]:
                edge_key = self._edge_key(tag_a, tag_b)
                if edge_key not in self._edges:
                    self._edges[edge_key] = {
                        "tags": [tag_a, tag_b],
                        "count": 0,
                        "hit": 0,
                        "resolved": 0,
                        "brier_sum": 0.0,
                        "predictions": [],
                    }
                self._edges[edge_key]["count"] += 1
                self._edges[edge_key]["predictions"].append(prediction_id)

        self._save()

    def resolve_edge(self, prediction_id: str, tags: List[str],
                     result: str, brier_score: float):
        """
        予測解決時にエッジの精度情報を更新する

        Args:
            result: "HIT" / "MISS"
            brier_score: 0.0〜1.0
        """
        is_hit = 1 if result == "HIT" else 0

        # ノード更新
        for tag in tags:
            if tag in self._nodes:
                self._nodes[tag]["resolved"] += 1
                self._nodes[tag]["hit"] += is_hit
                self._nodes[tag]["brier_sum"] += brier_score

        # エッジ更新
        for i, tag_a in enumerate(tags):
            for tag_b in tags[i+1:]:
                edge_key = self._edge_key(tag_a, tag_b)
                if edge_key in self._edges:
                    self._edges[edge_key]["resolved"] += 1
                    self._edges[edge_key]["hit"] += is_hit
                    self._edges[edge_key]["brier_sum"] += brier_score

        self._save()

    # ── クエリ ──────────────────────────────────────

    def get_cooccurrence(self, tag: str, limit: int = 10) -> List[Dict]:
        """
        あるタグと最もよく共起するタグのリストを返す

        Returns:
            [{"tag": "...", "count": N, "hit_rate": X, "avg_brier": X}]
        """
        results = []
        for edge_key, edge in self._edges.items():
            tags = edge["tags"]
            if tag not in tags:
                continue
            partner = tags[1] if tags[0] == tag else tags[0]
            resolved = edge["resolved"]
            hit_rate = round(edge["hit"] / resolved, 3) if resolved > 0 else None
            avg_brier = round(edge["brier_sum"] / resolved, 4) if resolved > 0 else None
            results.append({
                "tag": partner,
                "count": edge["count"],
                "resolved": resolved,
                "hit_rate": hit_rate,
                "avg_brier": avg_brier,
            })

        results.sort(key=lambda r: r["count"], reverse=True)
        return results[:limit]

    def get_strongest_patterns(self, min_resolved: int = 3, limit: int = 10) -> List[Dict]:
        """
        解決済み件数が多く、的中率の高いエッジパターンを返す
        """
        results = []
        for edge_key, edge in self._edges.items():
            resolved = edge["resolved"]
            if resolved < min_resolved:
                continue
            hit_rate = edge["hit"] / resolved
            avg_brier = edge["brier_sum"] / resolved
            results.append({
                "tags": edge["tags"],
                "count": edge["count"],
                "resolved": resolved,
                "hit_rate": round(hit_rate, 3),
                "avg_brier": round(avg_brier, 4),
                "strength": round(hit_rate * resolved, 2),  # 信頼度×件数
            })

        results.sort(key=lambda r: r["strength"], reverse=True)
        return results[:limit]

    def get_tag_stats(self, tag: str) -> Optional[Dict]:
        """単一タグの統計"""
        node = self._nodes.get(tag)
        if not node:
            return None
        resolved = node["resolved"]
        return {
            "tag": tag,
            "total_predictions": node["count"],
            "resolved": resolved,
            "hit_rate": round(node["hit"] / resolved, 3) if resolved > 0 else None,
            "avg_brier": round(node["brier_sum"] / resolved, 4) if resolved > 0 else None,
        }

    def get_all_tags(self) -> List[str]:
        return list(self._nodes.keys())

    def graph_summary(self) -> Dict:
        total_resolved = sum(e["resolved"] for e in self._edges.values())
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "total_resolved_edges": total_resolved,
            "strongest_patterns": self.get_strongest_patterns(min_resolved=1, limit=5),
        }

    # ── ユーティリティ ──────────────────────────────────────

    def _edge_key(self, tag_a: str, tag_b: str) -> str:
        """タグペアの正規化キー（順序不問）"""
        return "::".join(sorted([tag_a, tag_b]))

    def _load(self):
        if not os.path.exists(self.db_path):
            return
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._edges = data.get("edges", {})
            self._nodes = data.get("nodes", {})
        except Exception as e:
            print(f"[WARNING] KnowledgeGraph load error: {e}")

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({"edges": self._edges, "nodes": self._nodes},
                          f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] KnowledgeGraph save error: {e}")


if __name__ == "__main__":
    graph = KnowledgeGraph("data/knowledge_graph.json")

    # デモ: 予測登録
    graph.update_from_prediction("2026-03-14-001", ["地政学・安全保障", "対立の螺旋", "同盟の亀裂"])
    graph.update_from_prediction("2026-03-14-002", ["経済・金融", "対立の螺旋", "制度の劣化"])
    graph.update_from_prediction("2026-03-14-003", ["地政学・安全保障", "対立の螺旋"])

    # 予測解決
    graph.resolve_edge("2026-03-14-001", ["地政学・安全保障", "対立の螺旋", "同盟の亀裂"],
                       result="HIT", brier_score=0.09)

    # クエリ
    cooc = graph.get_cooccurrence("対立の螺旋")
    print("「対立の螺旋」共起タグ:")
    for c in cooc:
        print(f"  {c['tag']}: {c['count']}回 hit_rate={c['hit_rate']}")

    print("\nグラフサマリー:", json.dumps(graph.graph_summary(), ensure_ascii=False, indent=2))
