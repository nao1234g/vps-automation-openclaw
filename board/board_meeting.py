"""
board/board_meeting.py
経営ボードミーティング — 全エンジンを統合した週次/日次意思決定

Geneen原則: 「終わりから始めて、そこへ到達するためにできる限りのことをする」
柳井原則: 「正しい経営とは成果を出すこと」

このモジュールは毎朝 06:00 JST にcronから呼ばれ、
Nowpatternの「今日の経営判断」を生成してNaotoのTelegramに送る。
"""

import sys
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from decision_engine.strategy_engine import StrategyEngine
from decision_engine.capital_engine import CapitalEngine
from decision_engine.execution_planner import ExecutionPlanner, TaskOwner


BOARD_LOG_PATH = "data/board_meeting_log.json"
MAX_LOG_ENTRIES = 90  # 90日分


class BoardMeeting:
    """
    経営ボードミーティング

    毎朝 06:00 JST に実行され、以下を生成する:
    1. 現在の戦略フェーズと主要ボトルネック
    2. 今日ROI最大の3アクション
    3. 予算サマリー（承認待ち項目含む）
    4. リスクフラグ（Brier/記事数/的中率）
    5. NEO-ONE/TWO/GPTへのタスク割り当て
    6. Telegram報告テキスト（Naoto向け）
    """

    def __init__(self):
        self.strategy_engine = StrategyEngine()
        self.capital_engine = CapitalEngine()
        self.planner = ExecutionPlanner()
        self._log: List[Dict] = []
        self._load_log()

    def run_daily(self, metrics: Optional[Dict] = None, dry_run: bool = False) -> Dict:
        """
        日次ボードミーティングを実行する

        Args:
            metrics: 現在の指標（省略時はデフォルト値を使用）
            dry_run: True = Telegram通知を送らない

        Returns:
            完全なボードミーティング報告書
        """
        if metrics is None:
            metrics = self._load_latest_metrics()

        print(f"[BOARD] 日次ボードミーティング開始 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

        # 1. 戦略状態評価
        state = self.strategy_engine.evaluate_current_state(metrics)

        # 2. トップアクション
        top_actions = self.strategy_engine.get_top_priorities(limit=3)

        # 3. 実行プラン生成（新規アクションがあれば）
        new_plans = []
        for action in top_actions:
            if not dry_run:
                plan = self.planner.create_plan(
                    action_id=action.id,
                    action_title=action.title,
                    category=action.category,
                    impact=action.impact,
                )
                new_plans.append(plan.id)

        # 4. 今日のタスク割り当て
        owner_assignments = self.planner.generate_owner_assignments()

        # 5. 予算サマリー
        budget_summary = self.capital_engine.get_budget_summary()

        # 6. リスクフラグ
        risk_flags = self._assess_risks(metrics)

        # 7. PVQE評価
        pvqe = state.get("pvqe_assessment", {})

        # 8. ボードレポート生成
        report = {
            "meeting_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "phase": state["phase"],
            "bottleneck": state["bottleneck"],
            "pvqe": pvqe,
            "top_actions": [a.to_dict() for a in top_actions],
            "new_plans": new_plans,
            "owner_assignments": {
                k: len(v) for k, v in owner_assignments.items() if v
            },
            "budget_summary": budget_summary,
            "risk_flags": risk_flags,
            "metrics_snapshot": metrics,
        }

        # 9. ログに記録
        self._log.append(report)
        if len(self._log) > MAX_LOG_ENTRIES:
            self._log = self._log[-MAX_LOG_ENTRIES:]
        self._save_log()

        # 10. Telegramレポートテキスト生成
        telegram_text = self._generate_telegram_report(report)
        report["telegram_text"] = telegram_text

        if not dry_run:
            self._send_telegram(telegram_text)

        self._print_summary(report)
        return report

    def run_weekly(self, metrics: Optional[Dict] = None) -> Dict:
        """
        週次ボードミーティング（毎週月曜 06:00 JST）

        日次より詳細な分析を実施する。
        """
        if metrics is None:
            metrics = self._load_latest_metrics()

        print(f"[BOARD] 週次ボードミーティング開始")

        # 週次アジェンダ生成（StrategyEngineの高度機能を使用）
        agenda = self.strategy_engine.generate_weekly_agenda(metrics)

        # 月間予算配分
        allocation = self.capital_engine.generate_monthly_allocation()

        # 週次ブリーフィング（全オーナー）
        briefing = self.planner.generate_daily_briefing()

        weekly_report = {
            "type": "weekly",
            "meeting_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agenda": agenda,
            "budget_allocation": allocation,
            "briefing": briefing,
        }

        telegram_text = self._generate_weekly_telegram(weekly_report)
        weekly_report["telegram_text"] = telegram_text

        self._send_telegram(telegram_text)
        return weekly_report

    def get_meeting_history(self, last_n: int = 7) -> List[Dict]:
        """過去N日分のボードミーティング記録を返す"""
        return self._log[-last_n:]

    def get_todays_briefing_text(self) -> str:
        """今日のブリーフィングテキストを返す（Telegram用）"""
        if not self._log:
            return "ボードミーティング記録がありません。`run_daily()`を実行してください。"
        return self._log[-1].get("telegram_text", "")

    # ── レポート生成 ─────────────────────────────────────────

    def _generate_telegram_report(self, report: Dict) -> str:
        """Naoto向けTelegramメッセージを生成する"""
        date = report["meeting_date"]
        phase = report["phase"].replace("PHASE_", "Phase ").replace("_", " ")
        bottleneck = report["bottleneck"]

        pvqe = report.get("pvqe", {})
        p = pvqe.get("P", 0)
        v = pvqe.get("V", 0)
        q = pvqe.get("Q", 0)
        composite = pvqe.get("composite", 0)

        # リスクフラグ
        risks = report.get("risk_flags", [])
        risk_text = "\n".join(f"  {r}" for r in risks) if risks else "  ✅ 重大リスクなし"

        # トップアクション
        actions = report.get("top_actions", [])
        action_lines = []
        for i, a in enumerate(actions[:3], 1):
            action_lines.append(f"  {i}. [{a.get('impact', '?')}] {a.get('title', '?')[:50]}")
        action_text = "\n".join(action_lines) or "  （なし）"

        # 予算
        budget = report.get("budget_summary", {})
        pending = budget.get("pending_projects", 0)
        budget_line = f"承認待ち: {pending}件" if pending > 0 else "承認待ちなし"

        lines = [
            f"📋 *Nowpattern 日次ボード — {date}*",
            "",
            f"🎯 *フェーズ*: {phase}",
            f"⚠️ *ボトルネック*: {bottleneck}",
            "",
            f"📊 *PVQEスコア*",
            f"  P(精度)={p:.2f} | V(速度)={v:.2f} | Q(量)={q:.2f}",
            f"  合成スコア: {composite:.3f}",
            "",
            f"🚀 *今日のトップアクション*:",
            action_text,
            "",
            f"⚡ *リスクフラグ*:",
            risk_text,
            "",
            f"💰 *予算*: {budget_line}",
            "",
            f"→ 詳細: `data/board_meeting_log.json`",
        ]
        return "\n".join(lines)

    def _generate_weekly_telegram(self, report: Dict) -> str:
        """週次Telegram報告を生成する"""
        date = report["meeting_date"]
        agenda = report.get("agenda", {})
        allocation = report.get("budget_allocation", {})

        phase = agenda.get("state_assessment", {}).get("phase", "N/A")
        focus = agenda.get("this_week_focus", "N/A")

        risk_flags = agenda.get("risk_flags", [])
        risk_text = "\n".join(f"  {r}" for r in risk_flags) if risk_flags else "  ✅ 重大リスクなし"

        default_actions = agenda.get("default_actions", [])
        action_lines = [f"  • {a['action']}" for a in default_actions]

        unallocated = allocation.get("unallocated_usd", 0)
        warnings = allocation.get("warnings", [])

        lines = [
            f"🗓️ *Nowpattern 週次ボード — {date}*",
            "",
            f"フェーズ: `{phase}`",
            f"今週フォーカス: `{focus}`",
            "",
            f"📌 *デフォルトアクション*:",
            *action_lines,
            "",
            f"⚡ *リスクフラグ*:",
            risk_text,
            "",
            f"💰 *予算残り*: ${unallocated:.0f}/月（裁量）",
            *[f"  {w}" for w in warnings],
        ]
        return "\n".join(lines)

    # ── リスク評価 ────────────────────────────────────────────

    def _assess_risks(self, metrics: Dict) -> List[str]:
        """現在の指標からリスクフラグを生成する"""
        flags = []

        avg_brier = metrics.get("avg_brier", 1.0)
        daily_articles = metrics.get("daily_articles", 0)
        hit_rate = metrics.get("hit_rate", 0)
        moat = metrics.get("moat_strength", "SEED")

        if avg_brier > 0.25:
            flags.append(f"⚠️ Brier Score危機: {avg_brier:.3f} > 0.25 — 予測精度が低すぎる")
        elif avg_brier > 0.20:
            flags.append(f"⚠️ Brier Score注意: {avg_brier:.3f} — 改善が必要")

        if daily_articles < 50:
            flags.append(f"⚠️ 記事数不足: {daily_articles}本/日 < 50本 — パイプライン確認")
        elif daily_articles < 150:
            flags.append(f"📉 記事数低調: {daily_articles}本/日（目標200本）")

        if hit_rate < 0.4:
            flags.append(f"⚠️ 的中率低下: {hit_rate*100:.0f}% < 40% — エージェントディベート見直し")

        if moat in ("SEED",):
            flags.append(f"📍 Moat初期段階: {moat} — 予測トラックレコード積み上げが最優先")

        return flags

    # ── Telegram送信 ─────────────────────────────────────────

    def _send_telegram(self, text: str):
        """Telegram Bot APIでNaotoに送信する"""
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

        if not bot_token or not chat_id:
            print("[BOARD] TELEGRAM_BOT_TOKEN/CHAT_IDが未設定 — 送信スキップ")
            return

        try:
            import urllib.request
            data = json.dumps({
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }).encode()

            req = urllib.request.Request(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                resp = json.loads(r.read())
                if resp.get("ok"):
                    print("[BOARD] Telegram送信完了")
                else:
                    print(f"[BOARD] Telegram送信失敗: {resp}")
        except Exception as e:
            print(f"[BOARD] Telegram送信エラー: {e}")

    # ── データ読み込み ─────────────────────────────────────────

    def _load_latest_metrics(self) -> Dict:
        """
        最新の指標を読み込む

        prediction_db.json + SHARED_STATE.md から取得する。
        ファイルが存在しない場合はデフォルト値を返す。
        """
        metrics = {
            "brier_grade": "N/A",
            "moat_strength": "SEED",
            "daily_articles": 0,
            "hit_rate": 0.0,
            "avg_brier": 0.5,
        }

        # prediction_db.json から取得
        prediction_db_paths = [
            "data/prediction_db.json",
            "/opt/shared/prediction_db.json",
        ]
        for path in prediction_db_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        db = json.load(f)
                    predictions = db if isinstance(db, list) else db.get("predictions", [])
                    resolved = [p for p in predictions if p.get("status") == "resolved"]
                    if resolved:
                        brier_scores = [p.get("brier_score", 0.5) for p in resolved if "brier_score" in p]
                        hits = [p for p in resolved if p.get("result") == p.get("our_pick")]
                        if brier_scores:
                            avg = sum(brier_scores) / len(brier_scores)
                            metrics["avg_brier"] = round(avg, 4)
                            metrics["hit_rate"] = round(len(hits) / len(resolved), 3) if resolved else 0
                    metrics["total_predictions"] = len(predictions)
                    metrics["resolved_predictions"] = len(resolved)
                except Exception as e:
                    print(f"[BOARD] prediction_db読み込みエラー: {e}")
                break

        # SHARED_STATE から記事数取得（VPS上のみ有効）
        shared_state_path = "/opt/shared/SHARED_STATE.md"
        if os.path.exists(shared_state_path):
            try:
                with open(shared_state_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # "Total articles | 166" の行を抽出
                for line in content.split("\n"):
                    if "Total articles" in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            num = parts[-1].strip()
                            if num.isdigit():
                                metrics["daily_articles"] = int(num)
                        break
            except Exception:
                pass

        return metrics

    def _print_summary(self, report: Dict):
        print(f"\n=== ボードミーティング完了 ===")
        print(f"フェーズ: {report['phase']}")
        print(f"ボトルネック: {report['bottleneck']}")
        pvqe = report.get("pvqe", {})
        print(f"PVQE合成: {pvqe.get('composite', 0):.3f}")
        print(f"リスクフラグ: {len(report['risk_flags'])}件")
        for flag in report["risk_flags"]:
            print(f"  {flag}")

    def _load_log(self):
        if os.path.exists(BOARD_LOG_PATH):
            try:
                with open(BOARD_LOG_PATH, "r", encoding="utf-8") as f:
                    self._log = json.load(f)
            except Exception as e:
                print(f"[WARNING] Board log load error: {e}")

    def _save_log(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(BOARD_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Board log save error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly", action="store_true", help="週次ボードミーティング")
    parser.add_argument("--dry-run", action="store_true", help="Telegram通知なし")
    parser.add_argument("--history", action="store_true", help="過去7日の記録を表示")
    args = parser.parse_args()

    board = BoardMeeting()

    if args.history:
        history = board.get_meeting_history()
        for entry in history:
            print(f"{entry['meeting_date']}: Phase={entry['phase']} | Risks={len(entry['risk_flags'])}")
        raise SystemExit(0)

    if args.weekly:
        result = board.run_weekly()
    else:
        result = board.run_daily(dry_run=args.dry_run)

    print(f"\nボードレポート生成完了。")
    print(f"Telegramテキスト ({len(result.get('telegram_text', ''))}文字):")
    print(result.get("telegram_text", ""))
