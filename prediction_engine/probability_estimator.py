"""
prediction_engine/probability_estimator.py
確率推定エンジン — ベースレートとパターンマッチングで確率を導出する

Nowpatternの予測は「なんとなく」ではなく
歴史的ベースレートと力学パターンから算出された確率を持つ。
"""

import sys
from typing import Dict, List, Optional
from dataclasses import dataclass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# 歴史的ベースレート（過去の類似事象から算出）
HISTORICAL_BASE_RATES = {
    # 地政学
    "geopolitical_escalation_to_conflict": 0.15,
    "sanctions_lead_to_policy_change": 0.25,
    "ceasefire_holds_1year": 0.45,
    "election_incumbent_wins": 0.55,
    "regime_change_after_protest": 0.20,

    # 経済・金融
    "fed_rate_cut_after_cpi_drop": 0.70,
    "recession_after_yield_inversion": 0.65,
    "currency_crisis_after_debt_surge": 0.30,
    "tech_bubble_burst_within_2year": 0.35,

    # テクノロジー
    "ai_regulation_passes_within_1year": 0.40,
    "tech_monopoly_broken_up": 0.10,
    "new_ai_model_surpasses_sota": 0.85,  # ほぼ毎年起きる

    # 暗号資産
    "btc_halving_price_increase": 0.75,
    "crypto_exchange_bankruptcy": 0.20,
    "country_bans_crypto": 0.25,
}

# 力学タグ別の確率修正係数
DYNAMICS_MULTIPLIERS = {
    "プラットフォーム支配": 1.15,    # 独占傾向があると確率を上げる
    "規制の捕獲": 0.90,            # 規制回避が多い
    "対立の螺旋": 1.25,            # エスカレーションしやすい
    "同盟の亀裂": 1.10,
    "制度の劣化": 1.20,
    "危機便乗": 1.30,              # 危機時は変化が起きやすい
    "後発逆転": 0.85,              # 逆転は稀
    "勝者総取り": 1.10,
    "伝染の連鎖": 1.35,            # 伝染は広がりやすい
    "正統性の空白": 1.40,          # 権力真空は急変を生む
}


@dataclass
class ProbabilityEstimate:
    """確率推定結果"""
    base_rate: float          # 歴史的ベースレート
    adjusted_probability: float  # 力学修正後の確率
    confidence: str           # HIGH / MEDIUM / LOW
    reasoning: str
    dynamics_applied: List[str]


class ProbabilityEstimator:
    """
    ベースレート + 力学パターンから確率を推定する

    Superforecaster原則:
    1. まず歴史的ベースレートを調べる（外側視点）
    2. 次に今回固有の要因で修正する（内側視点）
    3. 確率は5%〜95%の範囲に収める
    """

    def estimate(self, event_type: str, dynamics: List[str] = None,
                 manual_base_rate: float = None) -> ProbabilityEstimate:
        """
        確率を推定する

        Args:
            event_type: HISTORICAL_BASE_RATES のキー
            dynamics: 適用する力学タグのリスト
            manual_base_rate: ベースレートを手動指定する場合
        """
        dynamics = dynamics or []

        # Step 1: ベースレートを取得
        base_rate = manual_base_rate or HISTORICAL_BASE_RATES.get(event_type, 0.50)

        # Step 2: 力学タグで修正
        adjusted = base_rate
        applied_dynamics = []
        for dyn in dynamics:
            if dyn in DYNAMICS_MULTIPLIERS:
                multiplier = DYNAMICS_MULTIPLIERS[dyn]
                adjusted = min(0.95, max(0.05, adjusted * multiplier))
                applied_dynamics.append(f"{dyn} (x{multiplier})")

        # Step 3: 確率を5〜95%にクランプ
        adjusted = round(min(0.95, max(0.05, adjusted)), 2)

        # 信頼度を決定
        if manual_base_rate is None and event_type not in HISTORICAL_BASE_RATES:
            confidence = "LOW"
            reasoning = f"歴史的ベースレートが見つかりません。デフォルト50%から調整"
        elif len(dynamics) >= 2:
            confidence = "MEDIUM"
            reasoning = f"ベースレート {base_rate*100:.0f}% + {len(dynamics)}つの力学で調整"
        else:
            confidence = "HIGH" if event_type in HISTORICAL_BASE_RATES else "MEDIUM"
            reasoning = f"歴史的ベースレート: {base_rate*100:.0f}%"

        return ProbabilityEstimate(
            base_rate=base_rate,
            adjusted_probability=adjusted,
            confidence=confidence,
            reasoning=reasoning,
            dynamics_applied=applied_dynamics,
        )

    def calibrate_from_market(self, our_estimate: float,
                               market_probability: float) -> Dict:
        """
        市場確率（Polymarket等）と自分の推定を比較して最終値を出す

        市場と大きく乖離する場合は「エッジがある」か「間違い」のどちらか
        """
        delta = abs(our_estimate - market_probability)

        if delta < 0.05:
            verdict = "CONSENSUS"    # 市場と一致
            final = (our_estimate + market_probability) / 2
        elif delta < 0.15:
            verdict = "SLIGHT_EDGE"  # わずかな見解の差
            final = our_estimate     # 自分の推定を優先
        else:
            verdict = "STRONG_EDGE"  # 市場と大きく異なる
            # 独自の根拠があれば維持、なければ市場に近づける
            final = our_estimate

        return {
            "our_estimate": our_estimate,
            "market_probability": market_probability,
            "delta": round(delta, 4),
            "verdict": verdict,
            "final_recommendation": round(final, 2),
            "note": "STRONG_EDGEの場合は根拠を必ず確認してください" if verdict == "STRONG_EDGE" else "",
        }

    def available_event_types(self) -> List[str]:
        return list(HISTORICAL_BASE_RATES.keys())


if __name__ == "__main__":
    est = ProbabilityEstimator()

    # 例: 米中貿易関税強化の確率
    result = est.estimate(
        event_type="sanctions_lead_to_policy_change",
        dynamics=["対立の螺旋", "経路依存"],
    )
    print(f"確率推定: {result.adjusted_probability*100:.0f}%")
    print(f"信頼度: {result.confidence}")
    print(f"理由: {result.reasoning}")
    print(f"力学適用: {result.dynamics_applied}")

    # 市場との比較
    cal = est.calibrate_from_market(0.35, 0.48)
    print(f"\n市場との比較: {cal['verdict']} (delta={cal['delta']})")
