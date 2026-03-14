"""
prediction_engine/scenario_generator.py
3シナリオ生成エンジン — Nowpattern Deep Pattern v6.0 準拠

楽観 / 基本 / 悲観 の3シナリオを構造化データとして生成する。
確率の合計は必ず100%になる。
"""

import sys
from typing import Dict, List, Optional
from dataclasses import dataclass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class Scenario:
    name: str            # "楽観" / "基本" / "悲観"
    name_en: str         # "optimistic" / "base" / "pessimistic"
    probability: int     # 5〜90 (合計100)
    description: str
    trigger: str         # このシナリオが実現する条件
    timeline: str        # いつ頃


@dataclass
class ScenarioSet:
    title: str
    title_en: str
    optimistic: Scenario
    base: Scenario
    pessimistic: Scenario

    def validate(self) -> bool:
        total = self.optimistic.probability + self.base.probability + self.pessimistic.probability
        return total == 100

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "title_en": self.title_en,
            "scenarios": {
                "optimistic": {
                    "name": self.optimistic.name,
                    "probability": self.optimistic.probability,
                    "description": self.optimistic.description,
                    "trigger": self.optimistic.trigger,
                    "timeline": self.optimistic.timeline,
                },
                "base": {
                    "name": self.base.name,
                    "probability": self.base.probability,
                    "description": self.base.description,
                    "trigger": self.base.trigger,
                    "timeline": self.base.timeline,
                },
                "pessimistic": {
                    "name": self.pessimistic.name,
                    "probability": self.pessimistic.probability,
                    "description": self.pessimistic.description,
                    "trigger": self.pessimistic.trigger,
                    "timeline": self.pessimistic.timeline,
                },
            },
            "total_probability": self.optimistic.probability + self.base.probability + self.pessimistic.probability,
            "valid": self.validate(),
        }

    def to_article_html(self) -> str:
        """Deep Pattern v6.0 セクション5「次のシナリオ」用HTML"""
        o = self.optimistic
        b = self.base
        p = self.pessimistic
        return f"""<div class="np-scenarios">
<h3>🔮 次のシナリオ</h3>
<div class="scenario optimistic">
  <strong>楽観シナリオ ({o.probability}%)</strong><br>
  {o.description}<br>
  <em>トリガー: {o.trigger} / 時期: {o.timeline}</em>
</div>
<div class="scenario base">
  <strong>基本シナリオ ({b.probability}%)</strong><br>
  {b.description}<br>
  <em>トリガー: {b.trigger} / 時期: {b.timeline}</em>
</div>
<div class="scenario pessimistic">
  <strong>悲観シナリオ ({p.probability}%)</strong><br>
  {p.description}<br>
  <em>トリガー: {p.trigger} / 時期: {p.timeline}</em>
</div>
</div>"""


class ScenarioGenerator:
    """
    3シナリオ生成エンジン

    原則: 確率は必ず5〜90%の範囲。合計100%。
    Nowpatternの予測はこの構造で表現される。
    """

    # プリセット: よくある地政学・経済シナリオのテンプレート
    TEMPLATES = {
        "geopolitical_escalation": ScenarioSet(
            title="地政学的緊張の展開",
            title_en="Geopolitical Tension Development",
            optimistic=Scenario("楽観", "optimistic", 25,
                "外交交渉が進み、緊張が緩和される",
                "水面下の交渉チャンネルが活性化",
                "3〜6ヶ月"),
            base=Scenario("基本", "base", 55,
                "現状維持。緊張は続くが制御された状態",
                "双方が明確なエスカレーションを避ける",
                "6〜12ヶ月"),
            pessimistic=Scenario("悲観", "pessimistic", 20,
                "偶発的衝突またはリスクの誤算で事態が悪化",
                "国内政治の圧力または誤算",
                "3ヶ月以内"),
        ),
        "fed_rate_decision": ScenarioSet(
            title="米連邦準備制度の金利決定",
            title_en="Federal Reserve Rate Decision",
            optimistic=Scenario("楽観", "optimistic", 30,
                "インフレ鎮静化を受け、利下げサイクル開始",
                "CPI 3ヶ月連続での目標値接近",
                "2〜4ヶ月"),
            base=Scenario("基本", "base", 50,
                "データ依存の姿勢を維持し、様子見継続",
                "経済指標が混在シグナルを出し続ける",
                "6ヶ月"),
            pessimistic=Scenario("悲観", "pessimistic", 20,
                "インフレ再燃を受け、利上げ再開または高金利長期化",
                "エネルギー価格急騰またはサプライチェーン混乱",
                "3〜6ヶ月"),
        ),
        "ai_regulation": ScenarioSet(
            title="AI規制の展開",
            title_en="AI Regulation Development",
            optimistic=Scenario("楽観", "optimistic", 35,
                "業界主導の自主規制が成立し、政府規制が軽量化",
                "大手テック企業が統一安全基準を採択",
                "6〜12ヶ月"),
            base=Scenario("基本", "base", 45,
                "断片的な規制が各国で進み、パッチワーク状態",
                "EUのAI法が施行され、他国が追随開始",
                "12〜18ヶ月"),
            pessimistic=Scenario("悲観", "pessimistic", 20,
                "厳格な規制がイノベーションを阻害し、AIリーダーシップが分散",
                "重大AIインシデントの発生",
                "6〜12ヶ月"),
        ),
    }

    def from_template(self, template_key: str) -> Optional[ScenarioSet]:
        """プリセットテンプレートから生成"""
        return self.TEMPLATES.get(template_key)

    def create(self, title: str, title_en: str,
               optimistic_prob: int, base_prob: int, pessimistic_prob: int,
               opt_desc: str, base_desc: str, pess_desc: str,
               opt_trigger: str = "", base_trigger: str = "", pess_trigger: str = "",
               opt_timeline: str = "", base_timeline: str = "", pess_timeline: str = "") -> ScenarioSet:
        """カスタムシナリオセットを生成"""
        assert optimistic_prob + base_prob + pessimistic_prob == 100, \
            f"確率の合計が100%になっていません: {optimistic_prob + base_prob + pessimistic_prob}%"

        return ScenarioSet(
            title=title,
            title_en=title_en,
            optimistic=Scenario("楽観", "optimistic", optimistic_prob, opt_desc, opt_trigger, opt_timeline),
            base=Scenario("基本", "base", base_prob, base_desc, base_trigger, base_timeline),
            pessimistic=Scenario("悲観", "pessimistic", pessimistic_prob, pess_desc, pess_trigger, pess_timeline),
        )

    def list_templates(self) -> List[str]:
        return list(self.TEMPLATES.keys())


if __name__ == "__main__":
    gen = ScenarioGenerator()

    # テンプレート使用例
    scenario = gen.from_template("ai_regulation")
    if scenario:
        import json
        print(json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2))
        print()
        print(scenario.to_article_html())
