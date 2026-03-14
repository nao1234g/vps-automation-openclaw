"""
prediction_engine/prediction_generator.py
予測生成エンジン — ニュースから構造化された予測を生成する

Deep Pattern v6.0 フォーマットに準拠した予測を
probability_estimator + scenario_generator と連携して生成する。
"""

import sys
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from prediction_engine.scenario_generator import ScenarioGenerator
from prediction_engine.probability_estimator import ProbabilityEstimator
from prediction_engine.prediction_registry import PredictionRegistry


class PredictionGenerator:
    """
    予測生成エンジン

    入力: ニュース記事のメタデータ（タイトル、タグ、力学）
    出力: prediction_db.json に追加可能な構造化予測

    このクラスがNowpatternの「予測オラクル」機能の中核。
    """

    def __init__(self):
        self.scenario_gen = ScenarioGenerator()
        self.prob_est = ProbabilityEstimator()
        self.registry = PredictionRegistry()

    def generate_from_article(self,
                               article_title: str,
                               article_slug: str,
                               genre_tags: List[str],
                               dynamics_tags: List[str],
                               event_type: str = None,
                               our_pick: str = "YES",
                               manual_prob: int = None,
                               resolution_question_ja: str = None,
                               resolution_question_en: str = None,
                               hit_condition_ja: str = None,
                               resolution_date: str = None,
                               market_probability: int = None) -> Dict:
        """
        記事から予測を生成する

        Args:
            article_title: 記事タイトル
            article_slug: Ghost CMS スラッグ
            genre_tags: ジャンルタグ（例: ["地政学・安全保障"]）
            dynamics_tags: 力学タグ（例: ["対立の螺旋", "経路依存"]）
            event_type: 確率推定用イベントタイプ
            our_pick: "YES" / "NO" / 具体的予測
            manual_prob: 手動指定確率（0〜100）。Noneなら自動推定
            resolution_question_ja: 判定質問（日本語）
            resolution_question_en: 判定質問（英語）
            hit_condition_ja: 的中条件（日本語）
            resolution_date: 判定日（YYYY-MM-DD）
            market_probability: Polymarket等の市場確率（0〜100）
        """
        # 確率推定
        if manual_prob is not None:
            probability = manual_prob
        else:
            estimate = self.prob_est.estimate(
                event_type=event_type or "unknown",
                dynamics=dynamics_tags,
            )
            probability = int(estimate.adjusted_probability * 100)

        # 市場確率との調整
        market_consensus = None
        if market_probability is not None:
            cal = self.prob_est.calibrate_from_market(
                probability / 100, market_probability / 100
            )
            market_consensus = {
                "probability": market_probability,
                "source": "Polymarket",
                "delta": cal["delta"],
                "verdict": cal["verdict"],
            }

        # 予測ID生成
        pred_id = self.registry.generate_prediction_id()

        prediction = {
            "id": pred_id,
            "title": article_title,
            "article_slug": article_slug,
            "article_url": f"https://nowpattern.com/{article_slug}/",
            "our_pick": our_pick,
            "our_pick_prob": probability,
            "resolution_question": resolution_question_ja or f"{article_title} — この予測は的中するか？",
            "resolution_question_en": resolution_question_en or "",
            "hit_condition": hit_condition_ja or f"{our_pick} が {resolution_date or '判定日'} までに実現する",
            "resolution_date": resolution_date,
            "tags": genre_tags + dynamics_tags,
            "dynamics": dynamics_tags,
            "genre": genre_tags,
            "market_consensus": market_consensus,
            "triggers": [{"date": resolution_date, "description": hit_condition_ja}] if resolution_date else [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
            "result": None,
            "brier_score": None,
            "generated_by": "prediction_generator.py v1.0",
        }

        return prediction

    def generate_oracle_statement(self, prediction: Dict) -> str:
        """
        ORACLE STATEMENT ボックスを生成する（記事末尾に挿入）
        content-rules.md のフォーマットに準拠
        """
        market = prediction.get("market_consensus") or {}
        market_prob = market.get("probability", "未取得")
        market_question = "Polymarket" if market.get("probability") else "データなし"

        triggers = prediction.get("triggers", [])
        resolution_date = triggers[0]["date"] if triggers else prediction.get("resolution_date", "未定")

        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ORACLE STATEMENT — この予測の追跡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
判定質問: {prediction.get('resolution_question', '?')}
Nowpatternの予測: {prediction.get('our_pick', '?')} — {prediction.get('our_pick_prob', '?')}%確率
市場の予測（{market_question}）: {market_prob}%
判定日: {resolution_date}
的中条件: {prediction.get('hit_condition', '?')}
↳ 予測一覧: nowpattern.com/predictions/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    def batch_generate(self, articles: List[Dict]) -> List[Dict]:
        """複数記事から一括予測生成"""
        predictions = []
        for article in articles:
            try:
                pred = self.generate_from_article(**article)
                predictions.append(pred)
            except Exception as e:
                print(f"[WARNING] 予測生成失敗 {article.get('article_slug', '?')}: {e}")
        return predictions


if __name__ == "__main__":
    gen = PredictionGenerator()

    # デモ
    pred = gen.generate_from_article(
        article_title="米中関税戦争：2026年の分岐点",
        article_slug="us-china-tariff-2026",
        genre_tags=["経済・貿易", "地政学・安全保障"],
        dynamics_tags=["対立の螺旋", "経路依存"],
        event_type="sanctions_lead_to_policy_change",
        our_pick="YES",
        resolution_question_ja="2026年内に米中が新たな関税引き上げを実施するか？",
        hit_condition_ja="2026年12月31日までに追加関税が発動される",
        resolution_date="2026-12-31",
        market_probability=55,
    )

    print(json.dumps(pred, ensure_ascii=False, indent=2))
    print()
    print(gen.generate_oracle_statement(pred))
