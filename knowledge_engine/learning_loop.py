"""
knowledge_engine/learning_loop.py
学習ループ — 予測解決 → ナレッジ更新 → 次の予測精度向上

「予測が外れた理由」を分析してナレッジに書き戻し、
次回同じパターンが出たときの精度を上げる。

これがNowpatternの「Intelligence Flywheel」の中核。
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


class LearningLoop:
    """
    予測解決 → ナレッジ学習ループ

    フロー:
      1. 予測が解決される（prediction_auto_verifier.py が呼ぶ）
      2. process_resolved_prediction() で学習
      3. KnowledgeGraph を更新（力学タグの精度を蓄積）
      4. KnowledgeStore に「何が当たった/外れたか」を記録
      5. adjust_dynamics_weights() で確率推定器の係数提案を生成
    """

    LEARNING_LOG_PATH = "data/learning_log.json"
    DYNAMICS_WEIGHTS_PATH = "data/dynamics_weights_adjusted.json"

    def __init__(self,
                 store: KnowledgeStore = None,
                 graph: KnowledgeGraph = None):
        self.store = store or KnowledgeStore()
        self.graph = graph or KnowledgeGraph()
        self._log: List[Dict] = []
        self._adjusted_weights: Dict[str, float] = {}
        self._load()

    # ── メイン学習エントリーポイント ──────────────────────────

    def process_resolved_prediction(self, prediction: Dict) -> Dict:
        """
        解決済み予測を処理し、ナレッジを更新する

        Args:
            prediction: prediction_db.json の1エントリー（resolved=True）

        Returns:
            {"learned": bool, "insight": str, "weight_changes": Dict}
        """
        pred_id = prediction.get("id", "")
        result = prediction.get("result")   # "HIT" / "MISS"
        brier = prediction.get("brier_score")
        tags = prediction.get("tags", [])
        prob = prediction.get("our_pick_prob", 50) / 100
        title = prediction.get("title", "")

        if not result or brier is None:
            return {"learned": False, "insight": "未解決または不完全なデータ", "weight_changes": {}}

        # 1. KnowledgeGraph に精度反映
        self.graph.resolve_edge(pred_id, tags, result, brier)

        # 2. 学習インサイトを生成
        insight = self._generate_insight(result, brier, prob, tags, title)

        # 3. KnowledgeStore に記録
        fact_type = "UNSHAKEABLE"  # 解決済み = 揺るぎない事実
        self.store.add(
            content=f"[解決済み] {title} → {result} (確率={prob*100:.0f}%, Brier={brier:.3f}) | {insight}",
            fact_type=fact_type,
            source=f"prediction_resolved/{pred_id}",
            tags=tags,
            confidence=1.0,  # 解決済みは100%確実
        )

        # 4. 学習ログに追加
        log_entry = {
            "prediction_id": pred_id,
            "result": result,
            "brier_score": brier,
            "our_prob": prob,
            "tags": tags,
            "insight": insight,
            "learned_at": datetime.now(timezone.utc).isoformat(),
        }
        self._log.append(log_entry)

        # 5. 力学タグの重み調整を計算
        weight_changes = self._calculate_weight_changes(tags, result, brier)

        self._save()

        return {
            "learned": True,
            "insight": insight,
            "weight_changes": weight_changes,
        }

    def batch_learn(self, predictions: List[Dict]) -> Dict:
        """複数の解決済み予測を一括学習する"""
        results = {"learned": 0, "skipped": 0, "insights": []}
        for pred in predictions:
            if not pred.get("resolved", False):
                results["skipped"] += 1
                continue
            r = self.process_resolved_prediction(pred)
            if r["learned"]:
                results["learned"] += 1
                results["insights"].append(r["insight"])
            else:
                results["skipped"] += 1
        return results

    # ── 重み調整 ──────────────────────────────────────

    def get_adjusted_weight(self, dynamics_tag: str,
                            default_weight: float) -> float:
        """
        学習済みの力学タグ重みを返す

        ProbabilityEstimator がこれを使って基準確率を修正する。
        """
        return self._adjusted_weights.get(dynamics_tag, default_weight)

    def generate_weight_report(self) -> Dict:
        """
        全力学タグの調整済み重みレポートを生成する

        これを probability_estimator.py の DYNAMICS_MULTIPLIERS に反映することで
        予測精度が向上する。
        """
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "weights": {},
            "recommendations": [],
        }

        for tag, weight in self._adjusted_weights.items():
            stats = self.graph.get_tag_stats(tag)
            if stats:
                original = 1.0  # デフォルト（未調整）
                change = round(weight - original, 3)
                report["weights"][tag] = {
                    "current_weight": weight,
                    "hit_rate": stats["hit_rate"],
                    "avg_brier": stats["avg_brier"],
                    "sample_size": stats["resolved"],
                }
                if abs(change) > 0.05 and stats["resolved"] >= 3:
                    direction = "上昇" if change > 0 else "低下"
                    report["recommendations"].append(
                        f"{tag}: 重みを {original:.2f} → {weight:.2f} に調整を推奨 "
                        f"（的中率={stats['hit_rate']}, N={stats['resolved']}）"
                    )

        return report

    # ── 分析 ──────────────────────────────────────

    def analyze_miss_patterns(self) -> Dict:
        """
        外れた予測のパターンを分析する

        「なぜ外れたか」の共通因子を特定する。
        """
        misses = [e for e in self._log if e["result"] == "MISS"]
        if not misses:
            return {"miss_count": 0, "patterns": []}

        # 外れ予測に多く含まれるタグ
        tag_frequency: Dict[str, int] = {}
        for miss in misses:
            for tag in miss["tags"]:
                tag_frequency[tag] = tag_frequency.get(tag, 0) + 1

        sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)

        # 確率バイアス分析（過信 or 過小評価）
        high_conf_misses = [m for m in misses if m["our_prob"] >= 0.7]
        low_conf_hits = [e for e in self._log if e["result"] == "HIT" and e["our_prob"] <= 0.4]

        return {
            "miss_count": len(misses),
            "top_miss_tags": sorted_tags[:5],
            "overconfidence_count": len(high_conf_misses),  # 高確率なのに外れ
            "underconfidence_count": len(low_conf_hits),    # 低確率なのに当たり
            "avg_miss_brier": round(
                sum(m["brier_score"] for m in misses) / len(misses), 4
            ) if misses else None,
        }

    def get_learning_summary(self) -> Dict:
        """学習状態のサマリー"""
        total = len(self._log)
        hits = sum(1 for e in self._log if e["result"] == "HIT")
        misses = total - hits

        return {
            "total_learned": total,
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / total, 3) if total > 0 else 0,
            "adjusted_weight_count": len(self._adjusted_weights),
            "last_learned": self._log[-1]["learned_at"] if self._log else None,
        }

    # ── プライベートメソッド ──────────────────────────────────────

    def _generate_insight(self, result: str, brier: float,
                          prob: float, tags: List[str], title: str) -> str:
        """予測結果からインサイトを生成する"""
        if result == "HIT":
            if brier <= 0.10:
                return f"高精度的中 (Brier={brier:.3f}) — 力学パターン {tags[:2]} は引き続き信頼できる"
            else:
                return f"的中 (Brier={brier:.3f}) — 確率推定に改善余地あり"
        else:  # MISS
            if prob >= 0.70:
                return f"過信による外れ (確率={prob*100:.0f}%, Brier={brier:.3f}) — {tags[:2]} の基準確率を下げることを検討"
            elif prob <= 0.35:
                return f"低確率予測が外れ (確率={prob*100:.0f}%) — 想定範囲内の外れ"
            else:
                return f"外れ (確率={prob*100:.0f}%, Brier={brier:.3f}) — タグ {tags[:2]} の組み合わせを再検討"

    def _calculate_weight_changes(self, tags: List[str],
                                  result: str, brier: float) -> Dict[str, float]:
        """
        力学タグの重みを調整する

        論理:
        - HIT で Brier < 0.10 → 重みを僅かに増加（良いパターン）
        - MISS で prob >= 0.70 → 重みを減少（過信パターン）
        """
        changes = {}
        adjustment = 0.0

        if result == "HIT" and brier <= 0.10:
            adjustment = +0.02  # 小さく増やす
        elif result == "MISS" and brier >= 0.40:
            adjustment = -0.05  # より大きく減らす
        elif result == "MISS":
            adjustment = -0.02

        for tag in tags:
            current = self._adjusted_weights.get(tag, 1.0)
            # 0.50〜2.00 の範囲に収める
            new_weight = round(max(0.50, min(2.00, current + adjustment)), 3)
            if abs(new_weight - current) > 0.001:
                self._adjusted_weights[tag] = new_weight
                changes[tag] = {"old": current, "new": new_weight}

        return changes

    def _load(self):
        if os.path.exists(self.LEARNING_LOG_PATH):
            try:
                with open(self.LEARNING_LOG_PATH, "r", encoding="utf-8") as f:
                    self._log = json.load(f)
            except Exception as e:
                print(f"[WARNING] LearningLoop log load error: {e}")

        if os.path.exists(self.DYNAMICS_WEIGHTS_PATH):
            try:
                with open(self.DYNAMICS_WEIGHTS_PATH, "r", encoding="utf-8") as f:
                    self._adjusted_weights = json.load(f)
            except Exception as e:
                print(f"[WARNING] LearningLoop weights load error: {e}")

    def _save(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.LEARNING_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._log, f, ensure_ascii=False, indent=2)
            with open(self.DYNAMICS_WEIGHTS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._adjusted_weights, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] LearningLoop save error: {e}")


if __name__ == "__main__":
    loop = LearningLoop()

    # デモ: 解決済み予測から学習
    demo_predictions = [
        {
            "id": "2026-03-01-001",
            "title": "米中関税戦争：2026年の分岐点",
            "our_pick_prob": 62,
            "tags": ["経済・金融", "地政学・安全保障", "対立の螺旋"],
            "resolved": True,
            "result": "HIT",
            "brier_score": 0.14,
        },
        {
            "id": "2026-03-05-001",
            "title": "BTC価格 2026年末$150,000予測",
            "our_pick_prob": 72,
            "tags": ["暗号資産", "伝染の連鎖"],
            "resolved": True,
            "result": "MISS",
            "brier_score": 0.52,
        },
    ]

    result = loop.batch_learn(demo_predictions)
    print(f"学習完了: {result['learned']}件")
    for insight in result["insights"]:
        print(f"  インサイト: {insight}")

    print("\n--- ミスパターン分析 ---")
    miss_analysis = loop.analyze_miss_patterns()
    print(json.dumps(miss_analysis, ensure_ascii=False, indent=2))

    print("\n--- 重みレポート ---")
    weight_report = loop.generate_weight_report()
    for rec in weight_report["recommendations"]:
        print(f"  推奨: {rec}")
