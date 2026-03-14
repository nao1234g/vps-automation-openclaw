#!/usr/bin/env python3
"""
system_scheduler.py
AI Civilization OS — システムスケジューラー

cronの代わりに Python 内でタスクをスケジュール管理する。
VPS の crontab が死んでもこのスケジューラーが生き残る最後の砦。

設計原則:
  - configs/system.yaml の cron セクションを読んで実行タイミングを判定
  - 各タスクは run_due_tasks() 呼び出し時に「期限切れか否か」を判定
  - 実行履歴を data/scheduler_state.json に保存（再起動後も続行可）
  - dry_run=True の場合は書き込みせず検証のみ

使用方法:
  python system_scheduler.py               # 期限切れタスクを実行
  python system_scheduler.py --list        # スケジュール一覧
  python system_scheduler.py --force board # 強制実行（期限無視）
  python system_scheduler.py --dry-run     # 実行内容を表示するだけ
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ==============================
# Task Registry
# ==============================
# タスク定義: name → {interval_hours, description, runner_fn_name}
TASK_REGISTRY: Dict[str, Dict] = {
    "board_daily": {
        "interval_hours": 24,
        "description": "毎日の経営ボードミーティング（ROI判断・タスク割り当て）",
        "runner": "run_board_daily",
        "priority": 1,
    },
    "knowledge_update": {
        "interval_hours": 24,
        "description": "知識ストアへの日次更新（Hey Loop結果を取り込む）",
        "runner": "run_knowledge_update",
        "priority": 2,
    },
    "article_pipeline": {
        "interval_hours": 24,
        "description": "記事生成パイプライン（JP100 + EN100 = 200本/日）",
        "runner": "run_article_pipeline",
        "priority": 3,
    },
    "knowledge_ingestion": {
        "interval_hours": 6,
        "description": "知識インジェスション（6時間ごと: RSS/Redditを取り込む）",
        "runner": "run_knowledge_ingestion",
        "priority": 4,
    },
    "evolution_loop": {
        "interval_hours": 168,  # 7日
        "description": "週次自己進化ループ（Brier分析 → AGENT_WISDOMを自己更新）",
        "runner": "run_evolution_loop",
        "priority": 5,
    },
    "prediction_page_build": {
        "interval_hours": 24,
        "description": "予測ページビルド（/predictions/ を毎日再生成）",
        "runner": "run_prediction_page_build",
        "priority": 6,
    },
}

STATE_PATH = "data/scheduler_state.json"


# ==============================
# SystemScheduler
# ==============================
class SystemScheduler:
    """
    AI Civilization OS タスクスケジューラー

    期限切れタスクを検出して実行し、実行履歴を管理する。
    VPS cron からは `python system_scheduler.py` を呼ぶだけでよい。
    """

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self._state: Dict = self._load_state()

    # --------------------------
    # Public API
    # --------------------------
    def run_due_tasks(self) -> Dict:
        """期限切れのタスクをすべて実行する"""
        now = datetime.now(timezone.utc)
        due = self._get_due_tasks(now)

        if not due:
            print("[Scheduler] No tasks due. All up to date.")
            return {"ran": 0, "skipped": len(TASK_REGISTRY), "tasks": []}

        print(f"[Scheduler] {len(due)} task(s) due to run")
        results = []

        for task_name in sorted(due, key=lambda n: TASK_REGISTRY[n]["priority"]):
            result = self._run_task(task_name, now)
            results.append(result)

        self._save_state()
        ran = sum(1 for r in results if r.get("status") == "ok")
        failed = sum(1 for r in results if r.get("status") == "error")
        skipped = len(TASK_REGISTRY) - len(due)

        summary = {
            "ran": ran,
            "failed": failed,
            "skipped": skipped,
            "tasks": results,
        }
        print(f"[Scheduler] Complete — ran={ran}, failed={failed}, skipped={skipped}")
        return summary

    def force_run(self, task_name: str) -> Dict:
        """指定タスクを期限無視で強制実行"""
        if task_name not in TASK_REGISTRY:
            print(f"Unknown task: {task_name}. Available: {list(TASK_REGISTRY)}")
            return {"status": "error", "task": task_name, "error": "not found"}
        now = datetime.now(timezone.utc)
        result = self._run_task(task_name, now, force=True)
        self._save_state()
        return result

    def list_tasks(self) -> List[Dict]:
        """タスク一覧と次回実行時刻を返す"""
        now = datetime.now(timezone.utc)
        rows = []
        for name, cfg in TASK_REGISTRY.items():
            last_run = self._get_last_run(name)
            if last_run:
                next_run = last_run + timedelta(hours=cfg["interval_hours"])
                due = now >= next_run
                next_run_str = next_run.strftime("%Y-%m-%d %H:%M UTC")
            else:
                due = True
                next_run_str = "OVERDUE (never run)"
            rows.append({
                "name": name,
                "description": cfg["description"],
                "interval_h": cfg["interval_hours"],
                "last_run": last_run.isoformat() if last_run else "never",
                "next_run": next_run_str,
                "due": due,
            })
        return rows

    # --------------------------
    # Task Runners
    # --------------------------
    def run_board_daily(self) -> Dict:
        try:
            from board.board_meeting import BoardMeeting
            board = BoardMeeting()
            result = board.run_daily(dry_run=self.dry_run)
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_knowledge_update(self) -> Dict:
        try:
            from loops.knowledge_update_loop import KnowledgeUpdateLoop
            loop = KnowledgeUpdateLoop(dry_run=self.dry_run)
            result = loop.run()
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_article_pipeline(self) -> Dict:
        try:
            from article_pipeline import ArticlePipeline
            pipeline = ArticlePipeline(dry_run=self.dry_run)
            result = pipeline.run_daily()
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_knowledge_ingestion(self) -> Dict:
        try:
            from knowledge_ingestion import KnowledgeIngestion
            ingestion = KnowledgeIngestion(dry_run=self.dry_run)
            result = ingestion.ingest_latest()
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_evolution_loop(self) -> Dict:
        try:
            from loops.evolution_loop import EvolutionLoop
            loop = EvolutionLoop(dry_run=self.dry_run)
            result = loop.run()
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_prediction_page_build(self) -> Dict:
        """VPS上の prediction_page_builder.py を呼び出す（VPS専用タスク）"""
        vps_script = "/opt/shared/scripts/prediction_page_builder.py"
        if not os.path.exists(vps_script):
            # ローカル環境では dry-run 扱い
            if self.dry_run or not os.path.exists("/opt"):
                return {"status": "ok", "note": "VPS only task — skipped on local"}
        try:
            import subprocess
            cmd = ["python3", vps_script, "--lang", "ja"]
            if self.dry_run:
                cmd.append("--dry-run")
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return {
                "status": "ok" if r.returncode == 0 else "error",
                "returncode": r.returncode,
                "stdout": r.stdout[-500:] if r.stdout else "",
                "stderr": r.stderr[-200:] if r.stderr else "",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # --------------------------
    # Internal
    # --------------------------
    def _get_due_tasks(self, now: datetime) -> List[str]:
        due = []
        for name, cfg in TASK_REGISTRY.items():
            last_run = self._get_last_run(name)
            if last_run is None:
                due.append(name)
            else:
                next_run = last_run + timedelta(hours=cfg["interval_hours"])
                if now >= next_run:
                    due.append(name)
        return due

    def _run_task(self, task_name: str, now: datetime, force: bool = False) -> Dict:
        cfg = TASK_REGISTRY[task_name]
        runner_fn_name = cfg["runner"]

        if self.dry_run and not force:
            print(f"  [DRY-RUN] Would run: {task_name}")
            return {"task": task_name, "status": "dry-run"}

        print(f"  → Running: {task_name} ({cfg['description']})")

        runner = getattr(self, runner_fn_name, None)
        if runner is None:
            return {"task": task_name, "status": "error", "error": f"No runner: {runner_fn_name}"}

        try:
            result = runner()
            status = result.get("status", "ok")
            self._state.setdefault("last_runs", {})[task_name] = now.isoformat()
            print(f"    {'✓' if status == 'ok' else '✗'} {task_name}: {status}")
            return {"task": task_name, "status": status, "result": result}
        except Exception as e:
            print(f"    ✗ {task_name}: ERROR — {e}")
            return {"task": task_name, "status": "error", "error": str(e)}

    def _get_last_run(self, task_name: str) -> Optional[datetime]:
        last_str = self._state.get("last_runs", {}).get(task_name)
        if last_str is None:
            return None
        try:
            return datetime.fromisoformat(last_str)
        except Exception:
            return None

    def _load_state(self) -> Dict:
        if os.path.exists(STATE_PATH):
            try:
                with open(STATE_PATH, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_runs": {}}

    def _save_state(self):
        if self.dry_run:
            return
        os.makedirs("data", exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)


# ==============================
# CLI
# ==============================
def main():
    parser = argparse.ArgumentParser(description="AI Civilization OS Scheduler")
    parser.add_argument("--list",    action="store_true", help="タスク一覧を表示")
    parser.add_argument("--force",   default=None, metavar="TASK", help="タスクを強制実行")
    parser.add_argument("--dry-run", action="store_true", help="書き込みなしで検証")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    args = parser.parse_args()

    scheduler = SystemScheduler(dry_run=args.dry_run, verbose=args.verbose)

    if args.list:
        rows = scheduler.list_tasks()
        print(f"\n{'Task':<30} {'Interval':>10} {'Last Run':<22} {'Next Run':<22} {'Due'}")
        print("-" * 95)
        for r in rows:
            due_str = "⚡ DUE" if r["due"] else "—"
            last = r["last_run"][:19] if r["last_run"] != "never" else "never"
            print(f"{r['name']:<30} {r['interval_h']:>9}h  {last:<22} {r['next_run']:<22} {due_str}")
        return

    if args.force:
        result = scheduler.force_run(args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    result = scheduler.run_due_tasks()
    if args.verbose:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
