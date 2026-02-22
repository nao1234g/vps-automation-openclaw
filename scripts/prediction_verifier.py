#!/usr/bin/env python3
"""
prediction_verifier.py — 予測検証ループ（フライホイールの回転軸）

毎日1回実行: 未判定の予測を自動チェックし、判定提案をTelegram通知する。

フロー:
  1. prediction_db.json から未判定（open）の予測を取得
  2. トリガー日が過ぎた予測を特定
  3. 各予測について、Gemini でニュース検索 + シナリオ照合
  4. 判定提案（どのシナリオが実現したか + 根拠）を生成
  5. Telegram通知（オーナーが確認 → 承認/却下）
  6. --auto-judge: オーナー承認なしでAI判定を自動適用（オプション）

cron: 0 6 * * * source /opt/cron-env.sh && python3 /opt/shared/scripts/prediction_verifier.py
      → 毎日 JST 15:00 に実行

使い方:
  python3 prediction_verifier.py                    # 通常実行（提案のみ）
  python3 prediction_verifier.py --auto-judge       # AI判定を自動適用
  python3 prediction_verifier.py --dry-run          # 分析のみ（通知なし）
  python3 prediction_verifier.py --check-all        # 期限関係なく全open予測をチェック
"""

import json
import os
import sys
import argparse
import subprocess
import re
from datetime import datetime, timezone, timedelta

PREDICTION_DB = "/opt/shared/scripts/prediction_db.json"
TELEGRAM_SCRIPT = "/opt/shared/scripts/send-telegram-message.py"
SCRIPTS_DIR = "/opt/shared/scripts"

# 判定プロンプト
VERIFICATION_PROMPT = """あなたはニュース分析の専門家です。
以下の予測記事について、現時点でどのシナリオが実現しているか（または実現に向かっているか）を判定してください。

【予測記事の情報】
- 予測ID: {prediction_id}
- タイトル: {title}
- 公開日: {published_at}
- 力学タグ: {dynamics_tags}

【3つのシナリオ】
{scenarios_text}

【注目トリガー】
{triggers_text}

【判定指示】
Google検索を使って、上記のトリガーイベントや関連ニュースの最新状況を調べてください。
その上で、以下のJSON形式で判定結果を返してください:

{{
  "verdict": "楽観シナリオ" | "基本シナリオ" | "悲観シナリオ" | "判定不可",
  "confidence": "high" | "medium" | "low",
  "evidence": [
    {{
      "event": "実際に起きた出来事",
      "date": "YYYY-MM-DD（判明している場合）",
      "source": "ニュースソース名",
      "relevance": "この出来事がシナリオ判定にどう関係するか"
    }}
  ],
  "reasoning": "判定理由の要約（3-5文）",
  "status": "resolved" | "still_open",
  "next_check_date": "YYYY-MM-DD（まだ判定できない場合、次にチェックすべき日付）"
}}

注意:
- "判定不可"はトリガーイベントがまだ発生していない場合に使用
- "still_open"はまだ最終判定できない場合（予測の時間軸がまだ先の場合）
- confidence="high"は明確なエビデンスがある場合のみ
- 確証がなければ無理に判定せず "判定不可" + "still_open" を返す
"""


def load_db():
    if os.path.exists(PREDICTION_DB):
        with open(PREDICTION_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"predictions": [], "stats": {}}


def save_db(db):
    # stats再計算
    preds = db["predictions"]
    resolved = [p for p in preds if p["status"] == "resolved"]
    brier_scores = [p["brier_score"] for p in resolved if p.get("brier_score") is not None]
    db["stats"] = {
        "total": len(preds),
        "resolved": len(resolved),
        "open": len(preds) - len(resolved),
        "avg_brier_score": round(sum(brier_scores) / len(brier_scores), 4) if brier_scores else None,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    with open(PREDICTION_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_open_predictions(db):
    """未判定の予測を取得"""
    return [p for p in db["predictions"] if p["status"] == "open"]


def is_trigger_overdue(trigger_date_str):
    """トリガー日が過ぎているかチェック"""
    now = datetime.now(timezone.utc)
    # 様々な日付形式に対応
    formats = ["%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(trigger_date_str, fmt).replace(tzinfo=timezone.utc)
            return dt < now
        except ValueError:
            continue
    # "2026年Q4" "2026年上半期" などの曖昧な日付
    match = re.search(r"(\d{4})年?(Q[1-4]|上半期|下半期)", trigger_date_str)
    if match:
        year = int(match.group(1))
        period = match.group(2)
        quarter_end = {
            "Q1": datetime(year, 3, 31, tzinfo=timezone.utc),
            "Q2": datetime(year, 6, 30, tzinfo=timezone.utc),
            "上半期": datetime(year, 6, 30, tzinfo=timezone.utc),
            "Q3": datetime(year, 9, 30, tzinfo=timezone.utc),
            "Q4": datetime(year, 12, 31, tzinfo=timezone.utc),
            "下半期": datetime(year, 12, 31, tzinfo=timezone.utc),
        }
        end = quarter_end.get(period)
        if end and end < now:
            return True
    return False


def has_any_overdue_trigger(prediction):
    """予測に期限切れのトリガーがあるかチェック"""
    for trigger in prediction.get("triggers", []):
        if is_trigger_overdue(trigger.get("date", "")):
            return True
    return False


def get_overdue_triggers(prediction):
    """期限切れトリガーのリストを返す"""
    overdue = []
    for trigger in prediction.get("triggers", []):
        if is_trigger_overdue(trigger.get("date", "")):
            overdue.append(trigger)
    return overdue


def verify_with_gemini(prediction):
    """Gemini 2.5 Proで予測をニュースと照合して判定提案"""
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("  ERROR: GEMINI_API_KEY / GOOGLE_API_KEY が設定されていません")
        return None

    # シナリオテキスト構築
    scenarios_text = ""
    for s in prediction.get("scenarios", []):
        label = s.get("label", "")
        prob = s.get("probability", 0)
        content = s.get("content", "")
        action = s.get("action", "")
        scenarios_text += f"\n{label}（確率: {prob*100:.0f}%）:\n  内容: {content}\n  示唆: {action}\n"

    # トリガーテキスト構築
    triggers_text = ""
    for t in prediction.get("triggers", []):
        overdue_mark = " ← 【期限超過】" if is_trigger_overdue(t.get("date", "")) else ""
        triggers_text += f"- {t.get('name', '')}: {t.get('date', '')}{overdue_mark}\n"

    prompt = VERIFICATION_PROMPT.format(
        prediction_id=prediction["prediction_id"],
        title=prediction.get("article_title", ""),
        published_at=prediction.get("published_at", ""),
        dynamics_tags=prediction.get("dynamics_tags", ""),
        scenarios_text=scenarios_text,
        triggers_text=triggers_text,
    )

    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=api_key)

        # Google Searchグラウンディングで最新ニュースを検索
        from google.genai.types import Tool as GenaiTool, GoogleSearch
        google_search_tool = GenaiTool(google_search=GoogleSearch())

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"tools": [google_search_tool]},
        )

        text = response.text
        # JSON抽出
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
    except Exception as e:
        print(f"  Gemini検証失敗: {e}")
        return None


def calculate_brier_score(scenarios, outcome_label):
    """Brier Scoreを計算"""
    score = 0.0
    for s in scenarios:
        # ラベルの部分一致（「楽観シナリオ」と「楽観」の両方に対応）
        actual = 1.0 if outcome_label in s["label"] or s["label"] in outcome_label else 0.0
        predicted = s["probability"]
        score += (predicted - actual) ** 2
    return round(score / len(scenarios), 4) if scenarios else None


def apply_judgment(db, prediction_id, outcome, note):
    """予測にAI判定を適用"""
    for p in db["predictions"]:
        if p["prediction_id"] == prediction_id:
            p["status"] = "resolved"
            p["outcome"] = outcome
            p["resolved_at"] = datetime.now(timezone.utc).isoformat()
            p["brier_score"] = calculate_brier_score(p["scenarios"], outcome)
            p["resolution_note"] = note
            return p["brier_score"]
    return None


def send_telegram(message):
    """Telegram通知"""
    try:
        if os.path.exists(TELEGRAM_SCRIPT):
            subprocess.run(
                ["python3", TELEGRAM_SCRIPT, message],
                capture_output=True, text=True, timeout=15
            )
    except Exception:
        pass


def run_verifier(auto_judge=False, dry_run=False, check_all=False):
    """メイン検証ループ"""
    print("🔄 Prediction Verifier 起動")
    print(f"   モード: {'自動判定' if auto_judge else '提案のみ'}")
    print(f"   対象: {'全open予測' if check_all else '期限切れトリガーのある予測'}")

    db = load_db()
    open_preds = get_open_predictions(db)

    if not open_preds:
        print("  未判定の予測はありません。")
        return

    print(f"   未判定予測: {len(open_preds)}件")

    # チェック対象を選定
    if check_all:
        targets = open_preds
    else:
        # トリガー日超過 OR 公開から30日以上経過した予測
        targets = []
        for p in open_preds:
            if has_any_overdue_trigger(p):
                targets.append(p)
            else:
                # 30日以上経過チェック
                try:
                    pub_dt = datetime.fromisoformat(p.get("published_at", ""))
                    if (datetime.now(timezone.utc) - pub_dt).days >= 30:
                        targets.append(p)
                except Exception:
                    pass

    if not targets:
        print("  チェック対象の予測はありません（全トリガーが未到来）。")
        # トリガー日超過がなくても、サマリーは通知
        if not dry_run:
            summary = f"📊 予測検証デイリーレポート\n"
            summary += f"未判定: {len(open_preds)}件\n"
            summary += f"本日チェック対象: 0件（全トリガー未到来）\n"
            next_triggers = []
            for p in open_preds:
                for t in p.get("triggers", []):
                    next_triggers.append(f"  {t.get('date', '?')}: {t.get('name', '')[:30]}")
            if next_triggers:
                summary += f"\n次のトリガー:\n" + "\n".join(next_triggers[:5])
            send_telegram(summary)
        return

    print(f"\n  チェック対象: {len(targets)}件")

    # Geminiで検証
    results = []
    for p in targets:
        print(f"\n  📌 {p['prediction_id']}: {p['article_title'][:50]}...")
        overdue = get_overdue_triggers(p)
        if overdue:
            for t in overdue:
                print(f"     ⏰ 期限切れ: {t['name']} ({t['date']})")

        verdict = verify_with_gemini(p)
        if verdict:
            print(f"     判定: {verdict.get('verdict', '?')} (確信度: {verdict.get('confidence', '?')})")
            print(f"     状態: {verdict.get('status', '?')}")
            print(f"     理由: {verdict.get('reasoning', '')[:100]}...")
            results.append({"prediction": p, "verdict": verdict})

            # 自動判定モード
            if auto_judge and verdict.get("status") == "resolved" and verdict.get("confidence") in ("high", "medium"):
                outcome = verdict["verdict"]
                note = f"[AI自動判定] {verdict.get('reasoning', '')}"
                brier = apply_judgment(db, p["prediction_id"], outcome, note)
                print(f"     ✅ 自動判定適用: {outcome} (Brier: {brier})")
        else:
            print(f"     ❌ 検証失敗")

    # DB保存（auto_judgeの場合のみ変更あり）
    if auto_judge and not dry_run:
        save_db(db)

    # Telegram通知
    if not dry_run and results:
        msg = f"📊 予測検証デイリーレポート\n"
        msg += f"チェック: {len(targets)}件 | 判定提案: {len(results)}件\n\n"

        for r in results:
            p = r["prediction"]
            v = r["verdict"]
            msg += f"{'✅' if v.get('status') == 'resolved' else '🔄'} {p['prediction_id']}\n"
            msg += f"  {p['article_title'][:40]}...\n"
            msg += f"  判定: {v.get('verdict', '?')} ({v.get('confidence', '?')})\n"
            if v.get("evidence"):
                for e in v["evidence"][:2]:
                    msg += f"  📰 {e.get('event', '')[:60]}\n"
            if auto_judge and v.get("status") == "resolved":
                brier = None
                for pred in db["predictions"]:
                    if pred["prediction_id"] == p["prediction_id"] and pred.get("brier_score") is not None:
                        brier = pred["brier_score"]
                if brier is not None:
                    msg += f"  Brier Score: {brier}\n"
            msg += "\n"

        # 統計
        stats = db.get("stats", {})
        if stats.get("avg_brier_score") is not None:
            msg += f"📈 累計精度: Brier {stats['avg_brier_score']} "
            if stats['avg_brier_score'] < 0.15:
                msg += "(Superforecaster級 🏆)\n"
            elif stats['avg_brier_score'] < 0.20:
                msg += "(優秀)\n"
            elif stats['avg_brier_score'] < 0.25:
                msg += "(平均以上)\n"
            else:
                msg += "(改善余地あり)\n"
            msg += f"   判定済: {stats.get('resolved', 0)} / 未判定: {stats.get('open', 0)}\n"

        if not auto_judge:
            msg += "\n💡 判定を適用するには:\n"
            msg += "python3 prediction_tracker.py judge NP-XXXX --outcome '基本シナリオ'\n"

        send_telegram(msg)
        print(f"\n  📱 Telegram通知送信完了")

    # サマリー
    print(f"\n=== Prediction Verifier 完了 ===")
    print(f"  チェック: {len(targets)}件")
    print(f"  判定提案: {len(results)}件")
    resolved_count = sum(1 for r in results if r["verdict"].get("status") == "resolved")
    print(f"  判定可能: {resolved_count}件")
    if auto_judge:
        print(f"  自動適用: {resolved_count}件")


def main():
    parser = argparse.ArgumentParser(description="Prediction Verifier — 予測検証ループ")
    parser.add_argument("--auto-judge", action="store_true", help="AI判定を自動適用")
    parser.add_argument("--dry-run", action="store_true", help="分析のみ（通知・更新なし）")
    parser.add_argument("--check-all", action="store_true", help="期限関係なく全open予測をチェック")
    args = parser.parse_args()

    run_verifier(
        auto_judge=args.auto_judge,
        dry_run=args.dry_run,
        check_all=args.check_all,
    )


if __name__ == "__main__":
    main()
