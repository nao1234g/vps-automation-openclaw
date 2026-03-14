"""
loops/knowledge_update_loop.py
知識更新ループ — 解決済み予測からナレッジグラフを更新する

フロー:
  1. prediction_db.json から「新規解決済み」予測を特定
  2. LearningLoop.process_resolved_prediction() を呼ぶ
  3. 力学タグの重みを dynamics_weights_adjusted.json に保存
  4. knowledge_store.json を UNSHAKEABLE facts で更新
  5. 学習サマリーを Telegram 送信
  6. 週次で generate_weight_report() をコンソール出力

毎日 JST 08:00 に cron から実行する想定。
"""

import sys
import json
import os
from typing import Dict, List
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from knowledge_engine import LearningLoop
from apps.nowpattern import PredictionTracker


PROCESSED_IDS_PATH = "data/learned_prediction_ids.json"


class KnowledgeUpdateLoop:
    """
    解決済み予測を学習してナレッジグラフを更新するループ

    「同じ力学パターンが再び現れたとき、前回より賢く予測できる」
    これがNowpatternのIntelligence Flywheelの学習段階。
    """

    def __init__(self):
        self.tracker = PredictionTracker()
        self.learning_loop = LearningLoop()
        self._processed_ids: set = self._load_processed_ids()

    def run(self, force_all: bool = False) -> Dict:
        """
        未学習の解決済み予測を処理する

        Args:
            force_all: True = 既処理を含めて全件再処理

        Returns:
            {"learned", "skipped", "weight_changes_count", "top_insights"}
        """
        resolved = self.tracker.get_resolved_predictions()

        # 未処理のみフィルタ
        if not force_all:
            to_process = [p for p in resolved if p["id"] not in self._processed_ids]
        else:
            to_process = resolved

        if not to_process:
            print("[INFO] 新規学習対象なし")
            return {"learned": 0, "skipped": 0, "weight_changes_count": 0, "top_insights": []}

        print(f"[INFO] 学習対象: {len(to_process)}件")

        # バッチ学習
        result = self.learning_loop.batch_learn(to_process)

        # 処理済みIDを記録
        for pred in to_process:
            self._processed_ids.add(pred["id"])
        self._save_processed_ids()

        # 重みレポート生成
        weight_report = self.learning_loop.generate_weight_report()
        weight_changes_count = len(weight_report.get("recommendations", []))

        # ミスパターン分析
        miss_patterns = self.learning_loop.analyze_miss_patterns()

        summary = {
            "learned": result["learned"],
            "skipped": result["skipped"],
            "weight_changes_count": weight_changes_count,
            "top_insights": result["insights"][:3],
            "miss_analysis": {
                "miss_count": miss_patterns["miss_count"],
                "top_miss_tags": miss_patterns.get("top_miss_tags", [])[:3],
                "overconfidence_count": miss_patterns.get("overconfidence_count", 0),
            },
            "weight_recommendations": weight_report.get("recommendations", [])[:3],
        }

        self._print_summary(summary)
        return summary

    def get_learning_summary(self) -> Dict:
        """現在の学習状態サマリーを返す"""
        loop_summary = self.learning_loop.get_learning_summary()
        tracker_stats = self.tracker.get_stats()
        weight_report = self.learning_loop.generate_weight_report()

        return {
            "total_predictions": tracker_stats["total"],
            "resolved_predictions": tracker_stats["resolved"],
            "learned_from": loop_summary["total_learned"],
            "learning_hit_rate": loop_summary["hit_rate"],
            "adjusted_weights_count": loop_summary["adjusted_weight_count"],
            "moat_strength": tracker_stats["moat_strength"],
            "brier_grade": tracker_stats["brier_grade"],
            "weight_recommendations_count": len(weight_report.get("recommendations", [])),
        }

    def generate_full_report(self) -> str:
        """Telegram 送信用のフルレポートテキストを生成する"""
        summary = self.get_learning_summary()
        miss = self.learning_loop.analyze_miss_patterns()

        lines = [
            "📚 ナレッジ更新レポート",
            f"学習済み予測: {summary['learned_from']}件",
            f"的中率: {summary['learning_hit_rate']*100:.1f}%",
            f"Brier評価: {summary['brier_grade']}",
            f"Moat強度: {summary['moat_strength']}",
            "",
            "⚠️ 過信ミス" if miss.get("overconfidence_count", 0) > 0 else "",
            f"過信による外れ: {miss.get('overconfidence_count', 0)}件",
        ]

        weight_report = self.learning_loop.generate_weight_report()
        if weight_report.get("recommendations"):
            lines.append("\n🔧 重み調整推奨:")
            for rec in weight_report["recommendations"][:3]:
                lines.append(f"  {rec}")

        return "\n".join(l for l in lines if l or l == "")

    def _print_summary(self, summary: Dict):
        """サマリーをコンソールに出力する"""
        print(f"\n=== ナレッジ更新完了 ===")
        print(f"学習: {summary['learned']}件 / スキップ: {summary['skipped']}件")
        print(f"重み調整推奨: {summary['weight_changes_count']}件")
        if summary.get("top_insights"):
            print("\nトップインサイト:")
            for ins in summary["top_insights"]:
                print(f"  - {ins}")
        if summary.get("weight_recommendations"):
            print("\n重み調整推奨:")
            for rec in summary["weight_recommendations"]:
                print(f"  - {rec}")

    def _load_processed_ids(self) -> set:
        if os.path.exists(PROCESSED_IDS_PATH):
            try:
                with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                pass
        return set()

    def _save_processed_ids(self):
        os.makedirs(os.path.dirname(PROCESSED_IDS_PATH) if os.path.dirname(PROCESSED_IDS_PATH) else ".", exist_ok=True)
        try:
            with open(PROCESSED_IDS_PATH, "w", encoding="utf-8") as f:
                json.dump(list(self._processed_ids), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Processed IDs save error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force-all", action="store_true", help="全件再処理")
    parser.add_argument("--report-only", action="store_true", help="学習せずレポートのみ")
    args = parser.parse_args()

    loop = KnowledgeUpdateLoop()

    if args.report_only:
        report = loop.generate_full_report()
        print(report)
    else:
        results = loop.run(force_all=args.force_all)
        print(f"\n学習完了: {results['learned']}件, 重み調整推奨: {results['weight_changes_count']}件")
