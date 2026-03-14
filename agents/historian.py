"""
agents/historian.py
歴史家エージェント — 3000年の歴史パターンから力学を読む

「現在のニュースは必ず過去に類似事例がある。
 歴史を知らない者は、同じ過ちを繰り返す。」
"""

import sys
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.base_agent import BaseAgent
from knowledge_engine.civilization_patterns import CivilizationPatterns


class HistorianAgent(BaseAgent):
    """
    歴史家エージェント

    専門:
    - 歴史的類似事例（Historical Parallels）の検索
    - 力学パターンの歴史的ベースレート算出
    - 「これは過去にも起きた」という外側視点の提供
    """

    def __init__(self):
        super().__init__(
            name="historian",
            role="historian",
            description="歴史的パターン・類似事例の専門家。3000年の歴史データから力学を読む。",
        )
        self.patterns = CivilizationPatterns()

    def analyze(self, topic: str, context: Dict) -> Dict:
        """
        歴史的視点から分析する

        - 類似事例を検索
        - 歴史的ベースレートを計算
        - 「前回と何が違うか」を特定
        """
        tags = context.get("tags", [])
        base_prob = context.get("base_probability", 50)

        # 関連する歴史パターンを検索
        related_patterns = self.patterns.search_by_dynamics(tags, limit=2)
        if not related_patterns:
            related_patterns = self.patterns.search_by_genre(
                context.get("genre_tags", []), limit=2
            )

        # 過去の記憶から関連事例を想起
        past_memories = self.get_relevant_memories(tags, limit=3)

        # 分析テキスト生成
        if related_patterns:
            pattern = related_patterns[0]
            parallels = pattern.historical_parallels
            if parallels:
                hp = parallels[0]
                analysis = (
                    f"歴史パターン「{pattern.name}」に該当。"
                    f"類似事例: {hp.period} 「{hp.event}」— {hp.outcome}。"
                    f"教訓: {hp.brier_lesson}"
                )
                # 歴史的ベースレートをベースに確率調整
                hist_prob = round(pattern.base_probability * 100)
                # 現在の確率と歴史的確率の加重平均
                adjusted_prob = round(base_prob * 0.6 + hist_prob * 0.4)
            else:
                analysis = f"歴史パターン「{pattern.name}」に該当するが、詳細事例は未登録。"
                adjusted_prob = base_prob
        else:
            analysis = "明確な歴史的先例は見当たらない。ベースレートから外挿する。"
            adjusted_prob = base_prob

        key_claims = [
            f"歴史的ベースレート: {adjusted_prob}%",
            f"類似パターン: {related_patterns[0].name if related_patterns else '不明'}",
        ]
        if past_memories:
            key_claims.append(f"関連記憶: {past_memories[0][:60]}")

        result = self._format_analysis_result(
            analysis=analysis,
            probability=adjusted_prob,
            confidence=0.80 if related_patterns else 0.50,
            key_claims=key_claims,
            fact_type="UNSHAKEABLE" if related_patterns else "SURFACE",
        )

        self.remember_analysis(topic, analysis, tags, importance=0.7)
        return result

    def get_historical_parallels(self, tags: List[str],
                                   genre_tags: List[str] = None) -> str:
        """
        Deep Pattern v6.0 「パターンの歴史」セクション用HTMLを生成する
        """
        return self.patterns.get_parallels_html(tags, genre_tags or [])
