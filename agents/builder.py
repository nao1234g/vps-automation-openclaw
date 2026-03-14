"""
agents/builder.py
ビルダーエージェント — 実装可能性・技術的実現性の専門家

「美しい戦略も、実装できなければゼロだ。実行の障壁を数えろ。」
"""

import sys
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.base_agent import BaseAgent


# 実装難易度マトリクス
IMPLEMENTATION_BARRIERS = {
    "技術的複雑性": {
        "low": 0.85,    # 既存技術で対応可能
        "medium": 0.60,  # 一部新技術が必要
        "high": 0.35,   # 最先端/未実証技術が必要
    },
    "組織的摩擦": {
        "low": 0.80,    # 単独組織・明確な権限
        "medium": 0.55,  # 複数組織の調整が必要
        "high": 0.30,   # 官僚制・政治的障壁
    },
    "資金調達": {
        "low": 0.90,    # 既存予算内
        "medium": 0.65,  # 追加予算が必要
        "high": 0.40,   # 大規模調達/外部依存
    },
    "時間軸": {
        "short": 0.80,  # 3ヶ月以内
        "medium": 0.65,  # 3〜12ヶ月
        "long": 0.45,   # 1年以上
    },
}

# タグ別の実装難易度推定
TAG_COMPLEXITY = {
    "技術・AI": "medium",
    "経済・金融": "medium",
    "地政学・安全保障": "high",
    "社会・文化": "low",
    "気候・環境": "high",
    "暗号資産": "medium",
    "宇宙・科学": "high",
    "医療・健康": "medium",
}


class BuilderAgent(BaseAgent):
    """
    ビルダーエージェント

    専門:
    - 実装可能性の現実的評価
    - 技術的・組織的障壁の定量化
    - タイムライン現実性チェック
    - リソース要件と実行力の分析
    """

    def __init__(self):
        super().__init__(
            name="builder",
            role="builder",
            description="実装可能性・技術的実現性の専門家。障壁を定量化する。",
        )

    def analyze(self, topic: str, context: Dict) -> Dict:
        """実装可能性の視点から分析する"""
        tags = context.get("tags", [])
        base_prob = context.get("base_probability", 50)
        timeline = context.get("timeline_months", 12)
        actors = context.get("actors", [])

        # 実装障壁スコア計算
        barrier_score = self._calculate_barrier_score(tags, timeline, actors)

        # 確率調整（ビルダーは中立 +0 バイアス、実現可能性で調整）
        # 障壁スコアが高いほど実現確率を下方修正
        feasibility_adjustment = round((barrier_score - 0.60) * 50)  # 0.60が基準
        adjusted_prob = max(5, min(95, base_prob + feasibility_adjustment))

        confidence = 0.70

        # タイムライン分析
        timeline_assessment = self._assess_timeline(timeline)

        analysis = (
            f"実装可能性分析: 実現可能性スコア {barrier_score:.2f}。"
            f"タイムライン評価: {timeline_assessment}。"
            f"実装確率: {adjusted_prob}% "
            f"({'実現可能' if adjusted_prob >= 60 else '困難' if adjusted_prob >= 40 else '非現実的'})。"
        )

        key_claims = [
            f"実現可能性スコア: {barrier_score:.2f}",
            f"タイムライン: {timeline_assessment}",
            f"調整幅: {feasibility_adjustment:+d}%",
        ]

        result = self._format_analysis_result(
            analysis=analysis,
            probability=adjusted_prob,
            confidence=confidence,
            key_claims=key_claims,
            fact_type="SURFACE",
        )

        self.remember_analysis(topic, analysis, tags, importance=0.6)
        return result

    def _calculate_barrier_score(
        self, tags: List[str], timeline_months: int, actors: List[str]
    ) -> float:
        """実装障壁スコアを計算する（0.0〜1.0、高いほど実現しやすい）"""
        scores = []

        # 技術的複雑性
        tech_complexity = "low"
        for tag in tags:
            if tag in TAG_COMPLEXITY:
                complexity = TAG_COMPLEXITY[tag]
                if complexity == "high":
                    tech_complexity = "high"
                    break
                elif complexity == "medium" and tech_complexity == "low":
                    tech_complexity = "medium"
        scores.append(IMPLEMENTATION_BARRIERS["技術的複雑性"][tech_complexity])

        # 組織的摩擦（アクター数で推定）
        if len(actors) <= 1:
            org_friction = "low"
        elif len(actors) <= 3:
            org_friction = "medium"
        else:
            org_friction = "high"
        scores.append(IMPLEMENTATION_BARRIERS["組織的摩擦"][org_friction])

        # 資金調達（タグで推定）
        if any(t in tags for t in ["宇宙・科学", "軍事", "インフラ"]):
            funding = "high"
        elif any(t in tags for t in ["技術・AI", "経済・金融"]):
            funding = "medium"
        else:
            funding = "low"
        scores.append(IMPLEMENTATION_BARRIERS["資金調達"][funding])

        # 時間軸
        if timeline_months <= 3:
            time_band = "short"
        elif timeline_months <= 12:
            time_band = "medium"
        else:
            time_band = "long"
        scores.append(IMPLEMENTATION_BARRIERS["時間軸"][time_band])

        return round(sum(scores) / len(scores), 3)

    def _assess_timeline(self, timeline_months: int) -> str:
        """タイムライン評価テキストを生成する"""
        if timeline_months <= 3:
            return f"非常に短期（{timeline_months}ヶ月） — 実行圧が高い"
        elif timeline_months <= 6:
            return f"短期（{timeline_months}ヶ月） — 達成可能"
        elif timeline_months <= 12:
            return f"中期（{timeline_months}ヶ月） — 標準的"
        elif timeline_months <= 24:
            return f"長期（{timeline_months}ヶ月） — 多くの変数リスク"
        else:
            return f"超長期（{timeline_months}ヶ月） — 予測困難"

    def estimate_resources(self, topic: str, tags: List[str], timeline_months: int) -> Dict:
        """リソース要件を推定する"""
        tech_tag_count = sum(1 for t in tags if t in TAG_COMPLEXITY and TAG_COMPLEXITY[t] != "low")

        return {
            "topic": topic,
            "estimated_team_size": max(2, tech_tag_count * 3),
            "timeline_months": timeline_months,
            "complexity_tags": [t for t in tags if t in TAG_COMPLEXITY],
            "critical_dependencies": [
                f"{t}の専門知識" for t in tags if TAG_COMPLEXITY.get(t) == "high"
            ],
            "risk_factors": [
                "タイムライン圧縮リスク" if timeline_months <= 6 else None,
                "組織間調整リスク" if len(tags) > 3 else None,
            ],
        }
