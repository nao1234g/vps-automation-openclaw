"""
decision_engine/strategy_engine.py
戦略エンジン — PVQE フレームワークで戦略的優先順位を決定する

Geneen原則: 「終わりから始めて、そこへ到達するためにできる限りのことをする」
柳井原則: 「逆算経営 — ゴールを先に宣言してから実行計画を立てる」

このエンジンはNowpatternの「Oracle化」というゴールから逆算し、
今週・今日すべきアクションをランク付けする。
"""

import sys
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class StrategicAction:
    """戦略的アクション"""
    id: str
    title: str
    category: str               # "flywheel" / "moat" / "monetize" / "quality" / "growth"
    pvqe_score: float           # P×V×Q×E 合成スコア（高いほど優先）
    impact: str                 # "HIGH" / "MEDIUM" / "LOW"
    effort: str                 # "LOW" / "MEDIUM" / "HIGH"（低いほど効率的）
    reversible: bool = True     # False = Type 1 判断（要確認）
    deadline: Optional[str] = None
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def roi_score(self) -> float:
        """ROI = Impact / Effort の数値スコア"""
        impact_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        effort_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        return impact_map.get(self.impact, 1) / effort_map.get(self.effort, 2)


# Nowpatternの戦略的ゴール（NORTH_STAR.mdから）
STRATEGIC_GOALS = {
    "oracle": {
        "title": "Oracle化 — 世界No.1予測プラットフォーム",
        "metrics": ["brier_grade", "moat_strength", "prediction_count"],
        "weight": 0.40,
    },
    "monetize": {
        "title": "月収 $10,000 達成（Phase 2〜3）",
        "metrics": ["subscriber_count", "api_users", "revenue_usd"],
        "weight": 0.25,
    },
    "audience": {
        "title": "月間読者 10万人",
        "metrics": ["monthly_visitors", "reader_votes", "x_followers"],
        "weight": 0.20,
    },
    "content": {
        "title": "200記事/日 品質維持",
        "metrics": ["daily_articles", "avg_brier", "reader_engagement"],
        "weight": 0.15,
    },
}


class StrategyEngine:
    """
    Nowpatternの戦略的優先順位を決定するエンジン

    毎朝 06:00 JST に Board Meeting から呼ばれ、
    「今日最もROIが高いアクション」を提示する。
    """

    ACTIONS_PATH = "data/strategic_actions.json"

    def __init__(self):
        self._actions: List[StrategicAction] = []
        self._load()

    # ── アクション管理 ──────────────────────────────────────

    def add_action(self,
                   title: str,
                   category: str,
                   impact: str = "MEDIUM",
                   effort: str = "MEDIUM",
                   description: str = "",
                   reversible: bool = True,
                   deadline: Optional[str] = None) -> StrategicAction:
        """戦略的アクションを追加する"""
        action_id = f"SA-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self._actions)+1:03d}"

        # PVQE スコア計算
        pvqe = self._calculate_pvqe(category, impact, effort)

        action = StrategicAction(
            id=action_id,
            title=title,
            category=category,
            pvqe_score=pvqe,
            impact=impact,
            effort=effort,
            reversible=reversible,
            deadline=deadline,
            description=description,
        )

        self._actions.append(action)
        self._save()
        return action

    def get_top_priorities(self, limit: int = 5) -> List[StrategicAction]:
        """ROI順にトップN件のアクションを返す"""
        pending = [a for a in self._actions if not hasattr(a, 'completed')]
        return sorted(pending, key=lambda a: a.pvqe_score, reverse=True)[:limit]

    def get_by_category(self, category: str) -> List[StrategicAction]:
        """カテゴリ別アクションを返す"""
        return [a for a in self._actions if a.category == category]

    def evaluate_current_state(self, metrics: Dict) -> Dict:
        """
        現在の指標から戦略的状態を評価する

        Args:
            metrics: {"brier_grade", "moat_strength", "daily_articles", ...}

        Returns:
            {"phase", "bottleneck", "recommended_focus", "pvqe_assessment"}
        """
        brier = metrics.get("brier_grade", "N/A")
        moat = metrics.get("moat_strength", "SEED")
        articles = metrics.get("daily_articles", 0)
        hit_rate = metrics.get("hit_rate", 0)

        # 現在フェーズを判定
        if moat in ("SEED", "EARLY"):
            phase = "PHASE_1_FOUNDATION"
            bottleneck = "予測トラックレコードが不足 — 毎日の予測登録を最優先"
            focus = "flywheel"
        elif moat in ("BUILDING", "STRONG"):
            phase = "PHASE_2_GROWTH"
            bottleneck = "読者獲得とエンゲージメントが成長制約"
            focus = "audience"
        else:
            phase = "PHASE_3_MONETIZE"
            bottleneck = "収益化モデルの実装"
            focus = "monetize"

        # P（判断精度）評価
        p_score = {"EXCEPTIONAL": 1.0, "EXCELLENT": 0.9, "GOOD": 0.8,
                   "DECENT": 0.7, "AVERAGE": 0.5, "POOR": 0.3, "N/A": 0.5}.get(brier, 0.5)

        # Q（行動量）評価
        q_score = min(1.0, articles / 200)  # 200記事/日が満点

        # V（改善速度）評価 = hit_rate
        v_score = hit_rate

        pvqe = round(p_score * v_score * q_score, 3)

        return {
            "phase": phase,
            "bottleneck": bottleneck,
            "recommended_focus": focus,
            "pvqe_assessment": {
                "P": round(p_score, 2),
                "V": round(v_score, 2),
                "Q": round(q_score, 2),
                "composite": pvqe,
            },
            "metrics_snapshot": metrics,
        }

    def generate_weekly_agenda(self, metrics: Dict) -> Dict:
        """
        週次ボードミーティング用アジェンダを生成する

        Returns:
            {"this_week_focus", "top_actions", "state_assessment", "risk_flags"}
        """
        state = self.evaluate_current_state(metrics)
        top_actions = self.get_top_priorities(limit=5)

        # 自動デフォルトアクションを追加（常に存在すべきもの）
        default_actions = self._get_default_actions(state["phase"])

        # リスクフラグ
        risk_flags = []
        if metrics.get("avg_brier", 1.0) > 0.25:
            risk_flags.append("⚠️ Brier Score POOR — 予測精度が危機的")
        if metrics.get("daily_articles", 0) < 50:
            risk_flags.append("⚠️ 記事数不足 — コンテンツパイプラインを確認")
        if metrics.get("hit_rate", 0) < 0.4:
            risk_flags.append("⚠️ 的中率40%未満 — エージェントディベートのレビューが必要")

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "this_week_focus": state["recommended_focus"],
            "state_assessment": state,
            "top_actions": [a.to_dict() for a in top_actions],
            "default_actions": default_actions,
            "risk_flags": risk_flags,
        }

    def _calculate_pvqe(self, category: str, impact: str, effort: str) -> float:
        """PVQE スコアを計算する"""
        # カテゴリ別のゴール重み
        category_weights = {
            "flywheel": 0.40,   # Oracle化に直結
            "moat": 0.35,       # トラックレコード構築
            "monetize": 0.25,   # 収益
            "quality": 0.20,    # 品質維持
            "growth": 0.20,     # 読者獲得
        }

        base = category_weights.get(category, 0.20)
        impact_mult = {"HIGH": 1.5, "MEDIUM": 1.0, "LOW": 0.5}.get(impact, 1.0)
        effort_div = {"LOW": 0.8, "MEDIUM": 1.0, "HIGH": 1.5}.get(effort, 1.0)

        return round(base * impact_mult / effort_div, 3)

    def _get_default_actions(self, phase: str) -> List[Dict]:
        """フェーズ別のデフォルト週次アクション"""
        if phase == "PHASE_1_FOUNDATION":
            return [
                {"action": "prediction_db に5件以上追加", "category": "flywheel"},
                {"action": "LearningLoop で解決済み予測を学習", "category": "flywheel"},
                {"action": "記事200本/日を維持", "category": "quality"},
            ]
        elif phase == "PHASE_2_GROWTH":
            return [
                {"action": "X投稿パフォーマンス分析", "category": "growth"},
                {"action": "読者投票ウィジェットの改善", "category": "moat"},
                {"action": "Ghost Members招待ページ作成", "category": "monetize"},
            ]
        else:
            return [
                {"action": "公開API v1 設計", "category": "monetize"},
                {"action": "Superforecaster称号システム設計", "category": "moat"},
                {"action": "B2B予測レポート商品設計", "category": "monetize"},
            ]

    def _load(self):
        if not os.path.exists(self.ACTIONS_PATH):
            return
        try:
            with open(self.ACTIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._actions = [StrategicAction(**d) for d in data]
        except Exception as e:
            print(f"[WARNING] StrategyEngine load error: {e}")

    def _save(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.ACTIONS_PATH, "w", encoding="utf-8") as f:
                json.dump([a.to_dict() for a in self._actions], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] StrategyEngine save error: {e}")


if __name__ == "__main__":
    engine = StrategyEngine()

    # デモアクション追加
    engine.add_action(
        title="prediction_db に毎日5件追加するcronを整備",
        category="flywheel",
        impact="HIGH",
        effort="LOW",
        description="daily_prediction_loop.py を VPS cron に登録する",
    )

    # 評価
    demo_metrics = {
        "brier_grade": "GOOD",
        "moat_strength": "BUILDING",
        "daily_articles": 150,
        "hit_rate": 0.62,
        "avg_brier": 0.14,
    }

    agenda = engine.generate_weekly_agenda(demo_metrics)
    print(f"週次アジェンダ生成:")
    print(f"  フォーカス: {agenda['this_week_focus']}")
    print(f"  フェーズ: {agenda['state_assessment']['phase']}")
    print(f"  ボトルネック: {agenda['state_assessment']['bottleneck']}")
    for flag in agenda["risk_flags"]:
        print(f"  {flag}")
