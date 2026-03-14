"""
agents/economist.py
経済学者エージェント — 市場・金融・経済指標の専門家

「市場は集合知。Polymarketが60%なら、反論するには強い根拠が必要。」
"""

import sys
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.base_agent import BaseAgent


# 経済指標とその予測力（歴史的相関）
ECONOMIC_INDICATORS = {
    "yield_curve_inversion": {"recession_probability": 0.65, "timeframe": "12〜24ヶ月"},
    "cpi_rise": {"rate_hike_probability": 0.75, "timeframe": "2〜3ヶ月"},
    "unemployment_rise": {"recession_probability": 0.45, "timeframe": "6〜12ヶ月"},
    "trade_deficit_widening": {"currency_pressure": 0.50, "timeframe": "3〜6ヶ月"},
    "btc_halving": {"price_increase_probability": 0.75, "timeframe": "6〜18ヶ月"},
}


class EconomistAgent(BaseAgent):
    """
    経済学者エージェント

    専門:
    - Polymarket等の市場確率との比較分析
    - 経済指標から確率を推定
    - 効率的市場仮説: 市場と乖離するには強い根拠が必要
    """

    def __init__(self):
        super().__init__(
            name="economist",
            role="economist",
            description="経済・金融・市場の専門家。Polymarket確率との乖離を分析する。",
        )

    def analyze(self, topic: str, context: Dict) -> Dict:
        """経済的視点から分析する"""
        tags = context.get("tags", [])
        base_prob = context.get("base_probability", 50)
        market_prob = context.get("market_probability")
        indicators = context.get("economic_indicators", [])

        # 市場確率との比較
        if market_prob is not None:
            delta = base_prob - market_prob
            if abs(delta) <= 5:
                verdict = "CONSENSUS"
                adjusted_prob = base_prob
                market_analysis = f"市場と一致 ({market_prob}%) — コンセンサス確認"
            elif abs(delta) <= 15:
                verdict = "SLIGHT_EDGE"
                adjusted_prob = round(base_prob * 0.6 + market_prob * 0.4)
                direction = "強気" if delta > 0 else "弱気"
                market_analysis = f"市場より{direction} ({base_prob}% vs {market_prob}%) — 軽度の乖離"
            else:
                verdict = "STRONG_EDGE"
                # 強い乖離の場合は市場に近づける（市場の集合知を尊重）
                adjusted_prob = round(base_prob * 0.5 + market_prob * 0.5)
                direction = "強気" if delta > 0 else "弱気"
                market_analysis = (
                    f"市場より大幅{direction} ({base_prob}% vs {market_prob}%)。"
                    f"強い根拠がない限り市場を尊重し {adjusted_prob}% に調整"
                )
        else:
            adjusted_prob = base_prob
            verdict = "NO_MARKET_DATA"
            market_analysis = "Polymarketデータなし — ベースレートを使用"

        # 経済指標からの追加調整
        indicator_adjustment = self._analyze_indicators(indicators, tags)
        if indicator_adjustment:
            adjusted_prob = max(5, min(95, adjusted_prob + indicator_adjustment["delta"]))

        adjusted_prob = max(5, min(95, adjusted_prob))
        confidence = 0.85 if market_prob is not None else 0.65

        analysis = (
            f"経済分析: {market_analysis}。"
            f"最終確率: {adjusted_prob}% (市場乖離判定: {verdict})。"
        )

        result = self._format_analysis_result(
            analysis=analysis,
            probability=adjusted_prob,
            confidence=confidence,
            key_claims=[market_analysis, f"乖離判定: {verdict}"],
            fact_type="UNSHAKEABLE" if market_prob is not None else "SURFACE",
        )

        self.remember_analysis(topic, analysis, tags, importance=0.7)
        return result

    def _analyze_indicators(self, indicators: List[str], tags: List[str]) -> Optional[Dict]:
        """経済指標タグから確率調整を計算する"""
        # 暗号資産タグがある場合はBTC半減期の影響を確認
        if "暗号資産" in tags and "btc_halving" in indicators:
            ind = ECONOMIC_INDICATORS["btc_halving"]
            return {"delta": +10, "note": f"BTC半減期効果: {ind['timeframe']}で価格上昇確率{ind['price_increase_probability']*100:.0f}%"}

        # 経済・金融タグで景気後退指標
        if "経済・金融" in tags and "yield_curve_inversion" in indicators:
            ind = ECONOMIC_INDICATORS["yield_curve_inversion"]
            return {"delta": +8, "note": f"逆イールド: 景気後退確率{ind['recession_probability']*100:.0f}%"}

        return None
