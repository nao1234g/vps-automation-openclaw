"""
knowledge_engine/history_loader.py
歴史データローダー — 過去の予測・記事・解決データをナレッジに変換する

prediction_db.json → KnowledgeStore + KnowledgeGraph に一括インポートする。
新規記事が公開されるたびに呼ばれ、ナレッジを最新状態に保つ。
"""

import sys
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from knowledge_engine.knowledge_store import KnowledgeStore
from knowledge_engine.knowledge_graph import KnowledgeGraph


class HistoryLoader:
    """
    歴史データローダー

    データソース:
      1. prediction_db.json — 予測・解決済みデータ
      2. Ghost記事メタデータ（オプション）
    """

    PREDICTION_DB_PATH = "data/prediction_db.json"

    def __init__(self,
                 store: KnowledgeStore = None,
                 graph: KnowledgeGraph = None,
                 prediction_db_path: str = None):
        self.store = store or KnowledgeStore()
        self.graph = graph or KnowledgeGraph()
        self.prediction_db_path = prediction_db_path or self.PREDICTION_DB_PATH

    def load_prediction_db(self, verbose: bool = True) -> Dict:
        """
        prediction_db.json を読み込み、KnowledgeStore + KnowledgeGraph を更新する

        Returns:
            {"loaded": N, "resolved": N, "errors": N}
        """
        if not os.path.exists(self.prediction_db_path):
            print(f"[SKIP] prediction_db が見つかりません: {self.prediction_db_path}")
            return {"loaded": 0, "resolved": 0, "errors": 0}

        with open(self.prediction_db_path, "r", encoding="utf-8") as f:
            db = json.load(f)

        predictions = db if isinstance(db, list) else db.get("predictions", [])
        loaded = resolved = errors = 0

        for pred in predictions:
            try:
                pred_id = pred.get("id", "")
                tags = pred.get("tags", [])
                title = pred.get("title", "")
                prob = pred.get("our_pick_prob", 50)
                created = pred.get("created_at", "")
                is_resolved = pred.get("resolved", False)
                result = pred.get("result")
                brier = pred.get("brier_score")

                # KnowledgeStore に Unshakeable fact として登録
                # （タイトル + 確率 + タグは検証済みデータ）
                self.store.add(
                    content=f"予測 [{pred_id}]: 「{title}」 確率={prob}% タグ={','.join(tags[:3])}",
                    fact_type="UNSHAKEABLE" if is_resolved else "SURFACE",
                    source=f"prediction_db.json/{pred_id}",
                    tags=tags,
                    confidence=0.95 if is_resolved else 0.7,
                )

                # KnowledgeGraph を更新
                self.graph.update_from_prediction(pred_id, tags)

                # 解決済みなら精度情報を反映
                if is_resolved and result and brier is not None:
                    self.graph.resolve_edge(pred_id, tags, result, brier)
                    resolved += 1

                loaded += 1

            except Exception as e:
                errors += 1
                if verbose:
                    print(f"[ERROR] {pred.get('id', '?')}: {e}")

        if verbose:
            print(f"[HistoryLoader] ロード完了: {loaded}件 (解決済み={resolved}, エラー={errors})")

        return {"loaded": loaded, "resolved": resolved, "errors": errors}

    def load_article_knowledge(self, articles: List[Dict]) -> int:
        """
        Ghost記事リストからナレッジを抽出してストアに追加する

        Args:
            articles: [{"slug": "...", "title": "...", "tags": [...], "published_at": "..."}]
        Returns:
            追加したエントリー数
        """
        added = 0
        for article in articles:
            slug = article.get("slug", "?")
            title = article.get("title", "")
            tags = [t.get("slug", t) if isinstance(t, dict) else t for t in article.get("tags", [])]

            entry = self.store.add(
                content=f"記事: 「{title}」 slug={slug}",
                fact_type="SURFACE",
                source=f"ghost_cms/{slug}",
                tags=tags,
                confidence=0.8,
            )
            if entry:
                added += 1
        return added

    def full_rebuild(self, verbose: bool = True) -> Dict:
        """
        全データソースから完全再構築する
        """
        if verbose:
            print("[HistoryLoader] 完全再構築開始...")

        result = self.load_prediction_db(verbose=verbose)

        if verbose:
            store_stats = self.store.stats()
            graph_summary = self.graph.graph_summary()
            print(f"[HistoryLoader] KnowledgeStore: {store_stats['total_entries']}件")
            print(f"[HistoryLoader] KnowledgeGraph: ノード={graph_summary['node_count']} エッジ={graph_summary['edge_count']}")

        return {
            "prediction_db": result,
            "store_stats": self.store.stats(),
            "graph_summary": self.graph.graph_summary(),
        }


if __name__ == "__main__":
    loader = HistoryLoader()

    # prediction_db がない場合はデモデータで代替
    demo_db_path = "data/prediction_db.json"
    if not os.path.exists(demo_db_path):
        os.makedirs("data", exist_ok=True)
        demo = [
            {
                "id": "2026-03-01-001",
                "title": "米中関税戦争：2026年の分岐点",
                "our_pick": "YES",
                "our_pick_prob": 62,
                "tags": ["経済・金融", "地政学・安全保障", "対立の螺旋"],
                "resolved": True,
                "result": "HIT",
                "brier_score": 0.14,
                "created_at": "2026-03-01T10:00:00+00:00",
            },
            {
                "id": "2026-03-05-001",
                "title": "イラン政変：正統性の空白が生む権力再編",
                "our_pick": "YES",
                "our_pick_prob": 75,
                "tags": ["地政学・安全保障", "正統性の空白", "制度の劣化"],
                "resolved": True,
                "result": "HIT",
                "brier_score": 0.06,
                "created_at": "2026-03-05T10:00:00+00:00",
            },
            {
                "id": "2026-03-10-001",
                "title": "BTC半減期後の価格動向",
                "our_pick": "YES",
                "our_pick_prob": 70,
                "tags": ["暗号資産", "伝染の連鎖"],
                "resolved": False,
                "result": None,
                "brier_score": None,
                "created_at": "2026-03-10T10:00:00+00:00",
            },
        ]
        with open(demo_db_path, "w", encoding="utf-8") as f:
            json.dump(demo, f, ensure_ascii=False, indent=2)
        print("[Demo] prediction_db.json を作成しました")

    result = loader.full_rebuild()
    print(json.dumps(result["store_stats"]["by_fact_type"], ensure_ascii=False))
