"""
loops/agent_debate_loop.py
エージェントディベートループ — キューから予測を取得してAgent Civilizationに渡す

フロー:
  1. data/debate_queue.json から「pending」の予測を取得
  2. AgentManager.generate_prediction_with_debate() を実行
  3. ConsensusResult を prediction_db.json の確率として更新
  4. 結果を data/debate_results.json に保存
  5. ArticleGenerator で記事を更新

オンデマンド or 毎時 cron で実行。
"""

import sys
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent_civilization import AgentManager
from apps.nowpattern import ArticleGenerator, PredictionTracker


QUEUE_PATH = "data/debate_queue.json"
RESULTS_PATH = "data/debate_results.json"


class AgentDebateLoop:
    """
    ディベートキューを処理するループ

    キューへの追加:
        from loops.agent_debate_loop import AgentDebateLoop
        loop = AgentDebateLoop()
        loop.enqueue(title, tags, base_prob)

    バッチ実行:
        python loops/agent_debate_loop.py --max 10
    """

    def __init__(self):
        self.manager = AgentManager()
        self.tracker = PredictionTracker()
        self._queue: List[Dict] = []
        self._results: List[Dict] = []
        self._load()

    # ── キュー管理 ──────────────────────────────────────

    def enqueue(self,
                title: str,
                tags: List[str],
                base_prob: int = 50,
                prediction_id: Optional[str] = None) -> str:
        """ディベートキューに追加する"""
        item_id = f"DQ-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self._queue)+1:03d}"
        item = {
            "id": item_id,
            "title": title,
            "tags": tags,
            "base_prob": base_prob,
            "prediction_id": prediction_id,
            "status": "pending",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        }
        self._queue.append(item)
        self._save_queue()
        print(f"[ENQUEUE] {item_id}: {title[:50]}")
        return item_id

    def get_pending(self) -> List[Dict]:
        """未処理のキューアイテムを返す"""
        return [q for q in self._queue if q.get("status") == "pending"]

    def get_queue_stats(self) -> Dict:
        """キュー統計"""
        by_status = {}
        for q in self._queue:
            s = q.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        return {"total": len(self._queue), "by_status": by_status}

    # ── ディベート実行 ──────────────────────────────────────

    def run(self, max_items: int = 10) -> Dict:
        """
        キューからディベートを実行する

        Returns:
            {"processed", "succeeded", "failed", "elapsed_seconds"}
        """
        start = datetime.now(timezone.utc)
        pending = self.get_pending()[:max_items]

        if not pending:
            print("[INFO] ディベートキューが空です")
            return {"processed": 0, "succeeded": 0, "failed": 0, "elapsed_seconds": 0}

        print(f"[INFO] ディベート開始: {len(pending)}件")

        succeeded = 0
        failed = 0

        for item in pending:
            result = self._process_item(item)
            if result.get("success"):
                succeeded += 1
            else:
                failed += 1

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        self._save_results()

        return {
            "processed": len(pending),
            "succeeded": succeeded,
            "failed": failed,
            "elapsed_seconds": round(elapsed, 1),
        }

    def _process_item(self, item: Dict) -> Dict:
        """1件のディベートを処理する"""
        item_id = item["id"]
        title = item["title"]
        tags = item["tags"]
        base_prob = item.get("base_prob", 50)
        pred_id = item.get("prediction_id")

        print(f"[DEBATE] {item_id}: {title[:50]}")

        try:
            # Agent Civilization でディベート
            consensus = self.manager.generate_prediction_with_debate(
                title=title,
                tags=tags,
                base_prob=base_prob,
                proposal_id=item_id,
            )

            final_prob = consensus.get("final_probability", base_prob)
            final_pick = consensus.get("final_pick", "UNCERTAIN")
            quality = consensus.get("consensus_level", "MODERATE")

            # 結果を保存
            result = {
                "item_id": item_id,
                "title": title,
                "tags": tags,
                "base_prob": base_prob,
                "final_prob": final_prob,
                "final_pick": final_pick,
                "consensus_level": quality,
                "prediction_id": pred_id,
                "success": True,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

            # キューのステータス更新
            item["status"] = "completed"
            item["result"] = result
            self._results.append(result)
            self._save_queue()

            print(f"  → {final_pick} {final_prob}% ({quality})")
            return result

        except Exception as e:
            error_result = {
                "item_id": item_id,
                "success": False,
                "error": str(e),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            item["status"] = "failed"
            item["error"] = str(e)
            self._results.append(error_result)
            self._save_queue()
            print(f"  [ERROR] {e}")
            return error_result

    # ── 永続化 ──────────────────────────────────────

    def _load(self):
        os.makedirs("data", exist_ok=True)
        if os.path.exists(QUEUE_PATH):
            try:
                with open(QUEUE_PATH, "r", encoding="utf-8") as f:
                    self._queue = json.load(f)
            except Exception as e:
                print(f"[WARNING] Queue load error: {e}")

        if os.path.exists(RESULTS_PATH):
            try:
                with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                    self._results = json.load(f)
            except Exception as e:
                print(f"[WARNING] Results load error: {e}")

    def _save_queue(self):
        try:
            with open(QUEUE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Queue save error: {e}")

    def _save_results(self):
        try:
            with open(RESULTS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Results save error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=10, help="最大処理件数")
    parser.add_argument("--enqueue-demo", action="store_true", help="デモデータをエンキュー")
    parser.add_argument("--stats", action="store_true", help="キュー統計を表示")
    args = parser.parse_args()

    loop = AgentDebateLoop()

    if args.stats:
        stats = loop.get_queue_stats()
        print(f"キュー統計: {json.dumps(stats, ensure_ascii=False, indent=2)}")
        raise SystemExit(0)

    if args.enqueue_demo:
        loop.enqueue(
            title="米国2026年中間選挙: 共和党が下院を維持するか",
            tags=["政治・選挙", "権力の腐敗", "制度崩壊"],
            base_prob=60,
        )
        loop.enqueue(
            title="日銀は2026年内に再度利上げを実施するか",
            tags=["経済・金融", "金融政策サイクル"],
            base_prob=45,
        )
        print("デモデータをエンキューしました")

    results = loop.run(max_items=args.max)
    print(f"\n処理完了: {results['succeeded']}件成功 / {results['failed']}件失敗 / {results['elapsed_seconds']}秒")
