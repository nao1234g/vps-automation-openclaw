"""
knowledge_engine/civilization_patterns.py
文明パターンライブラリ — 歴史が繰り返す力学パターンのカタログ

「歴史は繰り返さないが、韻を踏む」— マーク・トウェイン

このモジュールは:
1. 過去の類似事例（Historical Parallels）を提供する
2. 力学タグから関連パターンを検索する
3. Deep Pattern v6.0 の「パターンの歴史」セクションの素材を生成する
"""

import sys
from typing import Dict, List, Optional
from dataclasses import dataclass, field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class HistoricalParallel:
    """歴史的類似事例"""
    period: str           # 例: "1930年代"
    event: str            # 例: "世界大恐慌後の保護主義の波"
    outcome: str          # 例: "関税戦争が世界貿易を60%縮小させた"
    dynamics: List[str]   # 適用される力学タグ
    brier_lesson: str     # 予測精度への教訓
    similarity_score: float = 0.7  # 現在の状況との類似度（0〜1）


@dataclass
class CivilizationPattern:
    """文明パターン"""
    pattern_id: str
    name: str
    name_en: str
    description: str
    dynamics_triggers: List[str]   # このパターンが発動する力学タグ
    genre_triggers: List[str]      # 関連ジャンルタグ
    historical_parallels: List[HistoricalParallel] = field(default_factory=list)
    base_probability: float = 0.50  # このパターンが継続する基準確率
    resolution_timeframe: str = "6〜12ヶ月"


# ── パターンカタログ ──────────────────────────────────────

PATTERNS: List[CivilizationPattern] = [

    CivilizationPattern(
        pattern_id="CP-001",
        name="帝国の過剰拡張",
        name_en="Imperial Overextension",
        description="支配的勢力が複数の前線を同時に維持しようとして資源を消耗し、覇権が傾く。",
        dynamics_triggers=["対立の螺旋", "同盟の亀裂", "制度の劣化"],
        genre_triggers=["地政学・安全保障"],
        historical_parallels=[
            HistoricalParallel(
                period="1914〜1918年",
                event="第一次世界大戦：多正面作戦とオーストリア帝国の崩壊",
                outcome="4帝国が崩壊（ロシア・オスマン・オーストリア・ドイツ）",
                dynamics=["対立の螺旋", "同盟の亀裂"],
                brier_lesson="多正面作戦が始まったら崩壊確率は急上昇する",
                similarity_score=0.85,
            ),
            HistoricalParallel(
                period="1970〜1980年代",
                event="ソ連のアフガニスタン侵攻と経済崩壊",
                outcome="冷戦終結・ソ連解体（1991年）",
                dynamics=["対立の螺旋", "制度の劣化"],
                brier_lesson="軍事コストが経済成長を上回り始めると10年以内に崩壊",
                similarity_score=0.75,
            ),
        ],
        base_probability=0.35,
        resolution_timeframe="5〜15年",
    ),

    CivilizationPattern(
        pattern_id="CP-002",
        name="保護主義の螺旋",
        name_en="Protectionist Spiral",
        description="関税・制裁の応酬が連鎖し、世界貿易を縮小させながら各国が孤立化する。",
        dynamics_triggers=["対立の螺旋", "経路依存", "伝染の連鎖"],
        genre_triggers=["経済・貿易", "地政学・安全保障"],
        historical_parallels=[
            HistoricalParallel(
                period="1930年代",
                event="スムート・ホーリー関税法 → 報復関税の連鎖",
                outcome="世界貿易が5年で66%縮小。大恐慌が長期化",
                dynamics=["対立の螺旋", "伝染の連鎖"],
                brier_lesson="最初の報復関税から24ヶ月以内に第2国も追随する確率は72%",
                similarity_score=0.80,
            ),
        ],
        base_probability=0.45,
        resolution_timeframe="2〜5年",
    ),

    CivilizationPattern(
        pattern_id="CP-003",
        name="技術的断絶",
        name_en="Technological Discontinuity",
        description="新技術が既存産業の雇用・収益モデルを急速に破壊し、社会的適応コストが急増する。",
        dynamics_triggers=["プラットフォーム支配", "勝者総取り", "後発逆転"],
        genre_triggers=["テクノロジー・AI", "経済・貿易"],
        historical_parallels=[
            HistoricalParallel(
                period="1980〜1990年代",
                event="パソコン革命：IBMの失墜とWindowsの台頭",
                outcome="IBMのPC部門が20年後に売却（Lenovo）。Microsoftが独占",
                dynamics=["勝者総取り", "プラットフォーム支配"],
                brier_lesson="プラットフォーム戦争の勝者は最初の5年で決まる確率が高い",
                similarity_score=0.70,
            ),
            HistoricalParallel(
                period="2007〜2012年",
                event="スマートフォン革命：ノキア・ブラックベリーの崩壊",
                outcome="iPhone発売から5年でノキアのシェアが60%→5%",
                dynamics=["勝者総取り", "後発逆転"],
                brier_lesson="S字カーブの変曲点を超えた新技術は既存勢力に3年以内に打撃",
                similarity_score=0.80,
            ),
        ],
        base_probability=0.55,
        resolution_timeframe="3〜7年",
    ),

    CivilizationPattern(
        pattern_id="CP-004",
        name="通貨危機の伝染",
        name_en="Currency Crisis Contagion",
        description="1国の通貨危機が近隣国・新興市場全体に波及し、連鎖的な資本逃避が起きる。",
        dynamics_triggers=["伝染の連鎖", "正統性の空白", "危機便乗"],
        genre_triggers=["経済・金融", "地政学・安全保障"],
        historical_parallels=[
            HistoricalParallel(
                period="1997〜1998年",
                event="アジア通貨危機：タイバーツ切り下げから連鎖崩壊",
                outcome="タイ→マレーシア→インドネシア→韓国→ロシア→ブラジルへと波及",
                dynamics=["伝染の連鎖", "危機便乗"],
                brier_lesson="最初の通貨危機から90日以内に隣国も危機に入る確率は58%",
                similarity_score=0.85,
            ),
        ],
        base_probability=0.40,
        resolution_timeframe="12〜36ヶ月",
    ),

    CivilizationPattern(
        pattern_id="CP-005",
        name="正統性の崩壊と権力再編",
        name_en="Legitimacy Collapse and Power Reconfiguration",
        description="政権・制度の正統性が失われ、権力の真空が生じ、急速な政治再編が起きる。",
        dynamics_triggers=["正統性の空白", "制度の劣化", "危機便乗"],
        genre_triggers=["地政学・安全保障", "政治・選挙"],
        historical_parallels=[
            HistoricalParallel(
                period="1979年",
                event="イラン・イスラム革命：パフラヴィー朝の崩壊",
                outcome="42年以上続くイスラム共和制が樹立",
                dynamics=["正統性の空白", "危機便乗"],
                brier_lesson="民衆デモが6ヶ月以上続いた政権が1年以内に倒れる確率は45%",
                similarity_score=0.75,
            ),
            HistoricalParallel(
                period="2010〜2012年",
                event="アラブの春：チュニジア→エジプト→リビア→シリアへの波及",
                outcome="チュニジアは民主化、リビア・シリアは内戦状態に",
                dynamics=["正統性の空白", "伝染の連鎖"],
                brier_lesson="隣国での政変後6ヶ月は伝染リスクが最も高い",
                similarity_score=0.80,
            ),
        ],
        base_probability=0.30,
        resolution_timeframe="1〜3年",
    ),

    CivilizationPattern(
        pattern_id="CP-006",
        name="AI覇権競争",
        name_en="AI Hegemony Race",
        description="AI技術の優位性を巡る国家・企業間の競争が安全保障・経済・規制を同時に変容させる。",
        dynamics_triggers=["プラットフォーム支配", "規制の捕獲", "勝者総取り"],
        genre_triggers=["テクノロジー・AI", "地政学・安全保障"],
        historical_parallels=[
            HistoricalParallel(
                period="1940〜1950年代",
                event="核兵器開発競争：マンハッタン計画 → ソ連核実験",
                outcome="米ソ核均衡が半世紀続く冷戦構造を形成",
                dynamics=["対立の螺旋", "勝者総取り"],
                brier_lesson="覇権技術の独占は平均12年で崩れる（後発国のキャッチアップ）",
                similarity_score=0.65,
            ),
        ],
        base_probability=0.60,
        resolution_timeframe="5〜10年",
    ),
]


class CivilizationPatterns:
    """
    文明パターンライブラリへのインターフェース

    力学タグ・ジャンルタグから関連パターンを検索し、
    Deep Pattern v6.0「パターンの歴史」セクションの素材を生成する。
    """

    def __init__(self):
        self._patterns = {p.pattern_id: p for p in PATTERNS}

    def search_by_dynamics(self, dynamics: List[str], limit: int = 3) -> List[CivilizationPattern]:
        """
        力学タグから関連パターンを検索する

        スコア = 一致した力学タグの数
        """
        scored = []
        for pattern in self._patterns.values():
            overlap = sum(1 for d in dynamics if d in pattern.dynamics_triggers)
            if overlap > 0:
                scored.append((overlap, pattern))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def search_by_genre(self, genre_tags: List[str], limit: int = 3) -> List[CivilizationPattern]:
        """ジャンルタグから関連パターンを検索する"""
        scored = []
        for pattern in self._patterns.values():
            overlap = sum(1 for g in genre_tags if g in pattern.genre_triggers)
            if overlap > 0:
                scored.append((overlap, pattern))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def get_parallels_html(self, dynamics: List[str], genre_tags: List[str],
                           max_parallels: int = 2) -> str:
        """
        Deep Pattern v6.0「パターンの歴史」セクション用HTMLを生成する

        content-rules.md セクション4「パターンの歴史」準拠
        """
        patterns = self.search_by_dynamics(dynamics, limit=2) or \
                   self.search_by_genre(genre_tags, limit=2)

        if not patterns:
            return "<p>関連する歴史的パターンは現在データベースに登録されていません。</p>"

        parallels = []
        for pattern in patterns:
            for hp in pattern.historical_parallels[:1]:
                parallels.append({
                    "pattern_name": pattern.name,
                    "period": hp.period,
                    "event": hp.event,
                    "outcome": hp.outcome,
                    "lesson": hp.brier_lesson,
                })
                if len(parallels) >= max_parallels:
                    break
            if len(parallels) >= max_parallels:
                break

        html_parts = ['<div class="np-pattern-history">']
        for i, p in enumerate(parallels, 1):
            html_parts.append(f"""
<div class="parallel-case">
  <strong>事例{i}（{p['period']}）: {p['event']}</strong><br>
  結果: {p['outcome']}<br>
  <em>パターン「{p['pattern_name']}」より — 教訓: {p['lesson']}</em>
</div>""")
        html_parts.append("</div>")
        return "\n".join(html_parts)

    def get_pattern(self, pattern_id: str) -> Optional[CivilizationPattern]:
        return self._patterns.get(pattern_id)

    def list_all(self) -> List[CivilizationPattern]:
        return list(self._patterns.values())


if __name__ == "__main__":
    cp = CivilizationPatterns()

    # 米中関税戦争の記事に関連するパターンを検索
    dynamics = ["対立の螺旋", "経路依存"]
    genre_tags = ["経済・貿易", "地政学・安全保障"]

    patterns = cp.search_by_dynamics(dynamics)
    print(f"力学タグ {dynamics} に関連するパターン:")
    for p in patterns:
        print(f"  [{p.pattern_id}] {p.name}: 基準確率={p.base_probability*100:.0f}%")

    print("\n--- パターンの歴史セクション ---")
    print(cp.get_parallels_html(dynamics, genre_tags))
