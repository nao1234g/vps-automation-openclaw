"""
loops/evolution_loop.py
自己進化ループ — Brier Score → Gemini分析 → AGENT_WISDOM更新

NORTH_STAR.md の「Self-Evolving Architecture」を実装する。

フロー（毎週日曜 JST 09:00）:
  1. prediction_db.json から解決済み予測を取得
  2. LearningLoop.analyze_miss_patterns() でパターン分析
  3. LearningLoop.generate_weight_report() で重み調整案を生成
  4. 「次回精度向上のための指示事項」を自動生成
  5. AGENT_WISDOM.md の「## 自己学習ログ」に追記
  6. evolution_log.json に監査証跡を記録
  7. Telegram で Naoto に変更通知

制約:
  - NORTH_STAR.md / CLAUDE.md への書き込みは禁止
  - prediction_db.json のデータ変更は禁止
  - AGENT_WISDOM.md の「## 自己学習ログ」セクションへの追記のみ許可
"""

import sys
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from knowledge_engine import LearningLoop
from apps.nowpattern import PredictionTracker


EVOLUTION_LOG_PATH = "data/evolution_log.json"
AGENT_WISDOM_LOCAL = "data/agent_wisdom_updates.json"  # ローカル蓄積（VPS AGENT_WISDOM.mdには別途同期）


class EvolutionLoop:
    """
    週次自己進化ループ

    Brier Scoreの歴史から「なぜ外れたか」を分析し、
    全エージェントが次回から使える知識を AGENT_WISDOM に書き込む。

    これが「3年積み上げたトラックレコード = モート」の第2の理由:
    単に記録するだけでなく、それを使って自ら賢くなる。
    """

    MAX_EVOLUTION_LOG_ENTRIES = 52  # 52週 = 1年分

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.tracker = PredictionTracker()
        self.learning_loop = LearningLoop()
        self._evolution_log: List[Dict] = []
        self._load_log()

    def run(self, dry_run: Optional[bool] = None) -> Dict:
        """
        週次進化ループを実行する

        Args:
            dry_run: True = AGENT_WISDOMに書き込まない

        Returns:
            {"evolved", "insights_generated", "weight_recommendations", "wisdom_update"}
        """
        if dry_run is None:
            dry_run = self.dry_run
        print("[EVOLUTION] 週次自己進化ループ開始...")

        # 1. データ収集
        resolved = self.tracker.get_resolved_predictions()
        tracker_stats = self.tracker.get_stats()

        if len(resolved) < 2:
            print("[EVOLUTION] 解決済み予測が少なすぎます（最低2件必要）")
            return {"evolved": False, "reason": "insufficient_data"}

        # 2. パターン分析
        miss_patterns = self.learning_loop.analyze_miss_patterns()
        weight_report = self.learning_loop.generate_weight_report()
        loop_summary = self.learning_loop.get_learning_summary()

        # 3. 進化インサイトを生成
        wisdom_update = self._generate_wisdom_update(
            resolved, miss_patterns, weight_report, tracker_stats, loop_summary
        )

        # 4. AGENT_WISDOM更新（ローカルJSONに蓄積）
        if not dry_run:
            self._append_to_wisdom(wisdom_update)

        # 5. 進化ログに記録
        log_entry = {
            "evolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_count": len(resolved),
            "miss_count": miss_patterns["miss_count"],
            "avg_brier": tracker_stats["avg_brier"],
            "brier_grade": tracker_stats["brier_grade"],
            "moat_strength": tracker_stats["moat_strength"],
            "weight_recommendations": weight_report.get("recommendations", [])[:3],
            "wisdom_update": wisdom_update[:200] + "..." if len(wisdom_update) > 200 else wisdom_update,
        }

        self._evolution_log.append(log_entry)

        # ローテーション（52週）
        if len(self._evolution_log) > self.MAX_EVOLUTION_LOG_ENTRIES:
            self._evolution_log = self._evolution_log[-self.MAX_EVOLUTION_LOG_ENTRIES:]

        self._save_log()

        result = {
            "evolved": True,
            "insights_generated": len(wisdom_update.split("\n")),
            "weight_recommendations": len(weight_report.get("recommendations", [])),
            "wisdom_update": wisdom_update,
            "stats": {
                "brier_grade": tracker_stats["brier_grade"],
                "moat_strength": tracker_stats["moat_strength"],
                "hit_rate": tracker_stats["hit_rate"],
            },
        }

        self._print_summary(result)
        return result

    def _generate_wisdom_update(self,
                                 resolved: List[Dict],
                                 miss_patterns: Dict,
                                 weight_report: Dict,
                                 tracker_stats: Dict,
                                 loop_summary: Dict) -> str:
        """
        AGENT_WISDOM.md に追記する学習インサイトを生成する

        これは「AIが自分のプロンプトを最適化する」DSPy原理の実装。
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        brier_grade = tracker_stats.get("brier_grade", "N/A")
        hit_rate = tracker_stats.get("hit_rate", 0)
        moat = tracker_stats.get("moat_strength", "SEED")

        lines = [
            f"## 自己学習ログ — {now_str}",
            "",
            f"### 予測精度サマリー",
            f"- Brier評価: {brier_grade} / 的中率: {hit_rate*100:.1f}% / Moat: {moat}",
            "",
        ]

        # ミスパターン分析
        if miss_patterns["miss_count"] > 0:
            lines.append("### 外れパターン（次回改善点）")
            top_tags = miss_patterns.get("top_miss_tags", [])
            if top_tags:
                tag_str = " / ".join(f"{t[0]}({t[1]}件)" for t in top_tags[:3])
                lines.append(f"- 外れが多いタグ: {tag_str}")
            if miss_patterns.get("overconfidence_count", 0) > 0:
                lines.append(
                    f"- 過信による外れ: {miss_patterns['overconfidence_count']}件 "
                    f"→ 次回は75%以上の予測に対してAuditorのレビューを必須化"
                )
            lines.append("")

        # 重み調整推奨
        recs = weight_report.get("recommendations", [])
        if recs:
            lines.append("### 力学タグ重み調整推奨")
            for rec in recs[:5]:
                lines.append(f"- {rec}")
            lines.append("")

        # 次回のための指示事項（DSPy原理）
        lines.append("### 次回予測精度向上のための指示")

        if brier_grade in ("POOR", "AVERAGE"):
            lines.append("- 証拠品質がSURFACE以下の予測は確率を±10%以内に制限する")
            lines.append("- Polymarket確率との乖離が20%超の場合、Market Agentのレビューを必須化")
        elif brier_grade in ("GOOD", "EXCELLENT", "EXCEPTIONAL"):
            lines.append("- 現在の予測プロセスは機能している。継続する")
            lines.append("- 次のフロンティア: 予測判定期間の最適化（短期 vs 長期精度比較）")

        # 過信が多い場合
        if miss_patterns.get("overconfidence_count", 0) >= 3:
            lines.append("- 【重要】過信バイアス検出: 全確率を5%下方修正することを推奨")

        # 低確率的中が多い場合
        if miss_patterns.get("underconfidence_count", 0) >= 3:
            lines.append("- 【重要】過小評価バイアス検出: 一見低確率のトリガーイベントを再評価")

        return "\n".join(lines)

    def _append_to_wisdom(self, update: str):
        """ローカルJSONに蓄積（VPS AGENT_WISDOM.mdへは別途同期）"""
        os.makedirs("data", exist_ok=True)
        try:
            existing = []
            if os.path.exists(AGENT_WISDOM_LOCAL):
                with open(AGENT_WISDOM_LOCAL, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "update": update,
            })

            # 最新52件を保持
            if len(existing) > 52:
                existing = existing[-52:]

            with open(AGENT_WISDOM_LOCAL, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            print(f"[EVOLUTION] AGENT_WISDOM 更新: {len(update)}文字")
        except Exception as e:
            print(f"[WARNING] Wisdom append error: {e}")

    def get_evolution_history(self, last_n: int = 10) -> List[Dict]:
        """進化履歴を返す"""
        return self._evolution_log[-last_n:]

    def get_latest_wisdom(self) -> Optional[str]:
        """最新の自己学習インサイトを返す"""
        if os.path.exists(AGENT_WISDOM_LOCAL):
            try:
                with open(AGENT_WISDOM_LOCAL, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                if entries:
                    return entries[-1]["update"]
            except Exception:
                pass
        return None

    def _print_summary(self, result: Dict):
        print(f"\n=== 自己進化完了 ===")
        print(f"インサイト生成: {result['insights_generated']}件")
        print(f"重み調整推奨: {result['weight_recommendations']}件")
        print(f"Brier評価: {result['stats']['brier_grade']}")
        print(f"Moat強度: {result['stats']['moat_strength']}")

    def _load_log(self):
        if os.path.exists(EVOLUTION_LOG_PATH):
            try:
                with open(EVOLUTION_LOG_PATH, "r", encoding="utf-8") as f:
                    self._evolution_log = json.load(f)
            except Exception as e:
                print(f"[WARNING] Evolution log load error: {e}")

    def _save_log(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(EVOLUTION_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._evolution_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Evolution log save error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="AGENT_WISDOMに書き込まない")
    parser.add_argument("--history", action="store_true", help="進化履歴を表示")
    parser.add_argument("--wisdom", action="store_true", help="最新の知恵を表示")
    args = parser.parse_args()

    loop = EvolutionLoop()

    if args.history:
        history = loop.get_evolution_history()
        for entry in history:
            print(f"{entry['evolved_at']}: Brier={entry.get('brier_grade', 'N/A')}, Moat={entry.get('moat_strength', 'N/A')}")
        raise SystemExit(0)

    if args.wisdom:
        wisdom = loop.get_latest_wisdom()
        print(wisdom or "（学習ログなし）")
        raise SystemExit(0)

    result = loop.run(dry_run=args.dry_run)
    if result.get("evolved"):
        print(f"\n進化完了。Brier={result['stats']['brier_grade']}, Moat={result['stats']['moat_strength']}")
