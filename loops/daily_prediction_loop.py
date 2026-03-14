"""
loops/daily_prediction_loop.py
日次予測ループ — 1日1回実行し、新規トピックの予測を生成・登録する

フロー:
  1. ニューストピックを取得（Hey Loop / RSS 経由）
  2. PredictionGenerator で新規予測を生成
  3. Agent Debate で確率を精緻化
  4. prediction_db.json に登録
  5. ArticleGenerator で記事HTML生成
  6. Ghost CMS に投稿（オプション）
  7. Telegram に完了通知
"""

import sys
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from prediction_engine import PredictionGenerator, ProbabilityEstimator
from agent_civilization import AgentManager
from apps.nowpattern import ArticleGenerator, PredictionTracker
from knowledge_engine import HistoryLoader, LearningLoop


class DailyPredictionLoop:
    """
    1日1回実行する予測生成ループ

    cron: 毎日 JST 07:00（例）
    `python loops/daily_prediction_loop.py --topics 5`
    """

    LOG_PATH = "data/logs/daily_prediction_loop.log"

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.tracker = PredictionTracker()
        self.agent_manager = AgentManager()
        self.generator = PredictionGenerator()
        self.estimator = ProbabilityEstimator()
        self.history_loader = HistoryLoader()
        self.learning_loop = LearningLoop()
        self._log: List[Dict] = []

        os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)

    def run(self, topics: Optional[List[Dict]] = None, max_topics: int = 5) -> Dict:
        """
        メインループを実行する

        Args:
            topics: 手動で渡すトピック（Noneなら内部デモを使用）
            max_topics: 最大生成件数

        Returns:
            {"generated", "registered", "errors", "elapsed_seconds"}
        """
        start = datetime.now(timezone.utc)
        results = {"generated": 0, "registered": 0, "errors": 0, "articles": [], "errors_list": []}

        # トピックが渡されない場合はデモトピックを使用
        if topics is None:
            topics = self._get_demo_topics()

        topics = topics[:max_topics]
        self._log_event("start", f"{len(topics)}トピック処理開始")

        for topic_data in topics:
            try:
                result = self._process_topic(topic_data)
                if result:
                    results["generated"] += 1
                    if result.get("registered"):
                        results["registered"] += 1
                    results["articles"].append(result.get("article_title", ""))
            except Exception as e:
                results["errors"] += 1
                results["errors_list"].append(str(e))
                self._log_event("error", f"{topic_data.get('title', '?')}: {e}")

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        results["elapsed_seconds"] = round(elapsed, 1)

        self._save_log()
        self._log_event("complete", f"完了: 生成={results['generated']}, 登録={results['registered']}, エラー={results['errors']}")

        return results

    def _process_topic(self, topic_data: Dict) -> Optional[Dict]:
        """1トピックを処理する（生成→ディベート→登録→記事）"""
        title = topic_data.get("title", "")
        tags = topic_data.get("tags", [])
        base_prob = topic_data.get("base_prob", 50)

        self._log_event("topic", f"処理中: {title}")

        # 1. 確率推定（ProbabilityEstimator）
        estimate = self.estimator.estimate(title, tags)
        prob = estimate.probability

        # 2. Agent Debate で精緻化
        try:
            consensus = self.agent_manager.generate_prediction_with_debate(
                title=title,
                tags=tags,
                base_prob=prob,
                proposal_id=f"loop-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            )
            final_prob = consensus.get("final_probability", prob)
            final_pick = consensus.get("final_pick", "UNCERTAIN")
        except Exception as e:
            self._log_event("warn", f"Agent debate failed: {e}")
            final_prob = prob
            final_pick = "YES" if prob >= 50 else "NO"

        # 3. prediction_db に登録
        if not self.dry_run:
            trigger_date = topic_data.get("trigger_date", "2026-12-31")
            pred = self.tracker.add_prediction(
                title=title,
                tags=tags,
                our_pick=final_pick,
                our_pick_prob=int(final_prob),
                resolution_question=f"{title} は実現するか？",
                hit_condition=f"判定日時点で {title} が実現している",
                trigger_date=trigger_date,
                market_prob=topic_data.get("market_prob"),
            )
            pred_id = pred["id"]
        else:
            pred_id = f"DRY-{title[:10]}"

        # 4. 記事生成（JA）
        gen = ArticleGenerator(lang="ja")
        article = gen.generate(
            topic=title,
            tags=tags,
            debate_result={"key_insights": [f"AI確率: {final_prob}%"], "rounds": [], "debate_quality": "MEDIUM"},
            consensus_result={"final_probability": final_prob, "final_pick": final_pick, "consensus_level": "MODERATE"},
        )

        self._log_event("generated", f"{title}: {final_prob}% ({final_pick})")

        return {
            "title": title,
            "prediction_id": pred_id,
            "probability": final_prob,
            "pick": final_pick,
            "registered": not self.dry_run,
            "article_title": article.get("title", ""),
            "word_count": article.get("word_count", 0),
        }

    def _get_demo_topics(self) -> List[Dict]:
        """デモ用トピックを返す（実際はHey Loop/RSSから取得）"""
        return [
            {
                "title": "米連邦準備制度（FRB）は2026年内に利下げを実施するか",
                "tags": ["経済・金融", "FRB", "金融政策サイクル"],
                "base_prob": 55,
                "trigger_date": "2026-12-31",
                "market_prob": 52,
            },
            {
                "title": "OpenAI GPT-5は2026年内にリリースされるか",
                "tags": ["技術・AI", "プラットフォーム支配", "先発者優位"],
                "base_prob": 70,
                "trigger_date": "2026-12-31",
            },
            {
                "title": "台湾海峡で2026年内に軍事的衝突が発生するか",
                "tags": ["地政学・安全保障", "対立の螺旋", "覇権移行"],
                "base_prob": 15,
                "trigger_date": "2026-12-31",
                "market_prob": 10,
            },
        ]

    def _log_event(self, event_type: str, message: str):
        entry = {
            "type": event_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._log.append(entry)
        print(f"[{event_type.upper()}] {message}")

    def _save_log(self):
        try:
            with open(self.LOG_PATH, "a", encoding="utf-8") as f:
                for entry in self._log:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARNING] Log save error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="DBに書き込まない（テスト）")
    parser.add_argument("--topics", type=int, default=3, help="生成する予測数")
    args = parser.parse_args()

    loop = DailyPredictionLoop(dry_run=args.dry_run)
    results = loop.run(max_topics=args.topics)

    print(f"\n=== 日次予測ループ完了 ===")
    print(f"生成: {results['generated']}件 / 登録: {results['registered']}件 / エラー: {results['errors']}件")
    print(f"処理時間: {results['elapsed_seconds']}秒")
