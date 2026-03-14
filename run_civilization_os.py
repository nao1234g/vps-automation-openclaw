#!/usr/bin/env python3
"""
run_civilization_os.py
AI Civilization OS — エントリーポイント

Naotoの意志: 「Nowpatternを世界No.1の予測プラットフォームにする」
このスクリプトはOSを起動し、全エンジンを統合してフライホイールを回す。

使用方法:
  python run_civilization_os.py              # フルOS起動
  python run_civilization_os.py --dry-run    # 書き込みなしで検証
  python run_civilization_os.py --check      # ヘルスチェックのみ
  python run_civilization_os.py --component board  # 特定コンポーネントのみ

NORTH_STAR: Truth → Prediction → Verification → Track Record → Trust
"""

import sys
import os
import json
import argparse
import traceback
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ==============================
# Boot Banner
# ==============================
BOOT_BANNER = """
╔══════════════════════════════════════════════════════════╗
║          AI CIVILIZATION OS — NOWPATTERN                 ║
║   Truth Engine → Prediction → Trust → Moat              ║
║   Mission: World's No.1 Prediction Platform              ║
╚══════════════════════════════════════════════════════════╝
"""

# ==============================
# Component Imports (遅延 — 起動チェックで個別に検証)
# ==============================
def _import_engines() -> Dict[str, bool]:
    """全エンジンのインポート状態をチェックして返す"""
    results = {}

    checks = [
        ("truth_engine",     "truth_engine.truth_engine",          "TruthEngine"),
        ("prediction_engine","prediction_engine.prediction_registry","PredictionRegistry"),
        ("knowledge_engine", "knowledge_engine.knowledge_store",    "KnowledgeStore"),
        ("decision_engine",  "decision_engine.strategy_engine",     "StrategyEngine"),
        ("capital_engine",   "decision_engine.capital_engine",      "CapitalEngine"),
        ("exec_planner",     "decision_engine.execution_planner",   "ExecutionPlanner"),
        ("board_meeting",    "board.board_meeting",                 "BoardMeeting"),
        ("agent_manager",    "agent_civilization.agent_manager",    "AgentManager"),
    ]

    for name, module_path, class_name in checks:
        try:
            mod = __import__(module_path, fromlist=[class_name])
            getattr(mod, class_name)
            results[name] = True
        except Exception as e:
            results[name] = False
            print(f"  [WARN] {name}: {e}", file=sys.stderr)

    return results


# ==============================
# CivilizationOS Main Class
# ==============================
class CivilizationOS:
    """
    AI Civilization OS メインクラス

    5層アーキテクチャ:
      Layer 1: Truth Engine       (事実の収集・分類・検証)
      Layer 2: Prediction Engine  (予測の生成・記録)
      Layer 3: Knowledge Engine   (知識の蓄積・進化)
      Layer 4: Decision Engine    (意思決定・ROI最大化)
      Layer 5: Agent Civilization (6エージェントの分散知性)
    """

    OS_VERSION = "1.0.0"
    LOG_PATH = "data/os_boot_log.json"

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._boot_log: List[Dict] = []
        self._engines: Dict = {}

    # --------------------------
    # Boot Sequence
    # --------------------------
    def boot(self) -> bool:
        """OSを起動する。失敗した場合は False を返す"""
        print(BOOT_BANNER)
        self._log("BOOT", "OS starting", {"version": self.OS_VERSION, "dry_run": self.dry_run})

        steps = [
            ("1/5 Health Check",       self._step_health_check),
            ("2/5 Engine Init",        self._step_init_engines),
            ("3/5 Config Validation",  self._step_validate_config),
            ("4/5 Data Dir Check",     self._step_check_data_dirs),
            ("5/5 Boot Complete",      self._step_boot_complete),
        ]

        for step_name, step_fn in steps:
            print(f"\n[{step_name}]")
            try:
                ok = step_fn()
                if not ok:
                    self._log("FAIL", step_name, {})
                    print(f"  ✗ FAILED — OS boot aborted at {step_name}")
                    return False
                print(f"  ✓ OK")
            except Exception as e:
                self._log("ERROR", step_name, {"error": str(e)})
                print(f"  ✗ ERROR: {e}")
                if self.verbose:
                    traceback.print_exc()
                return False

        self._save_boot_log()
        print("\n✅ AI Civilization OS — BOOT COMPLETE\n")
        return True

    def _step_health_check(self) -> bool:
        import_results = _import_engines()
        ok_count = sum(1 for v in import_results.values() if v)
        total = len(import_results)
        print(f"  Engines online: {ok_count}/{total}")
        for name, ok in import_results.items():
            status = "✓" if ok else "✗"
            if self.verbose or not ok:
                print(f"    {status} {name}")
        # 必須エンジンが揃っているかチェック
        required = ["truth_engine", "prediction_engine", "decision_engine", "board_meeting"]
        return all(import_results.get(r, False) for r in required)

    def _step_init_engines(self) -> bool:
        try:
            from decision_engine.strategy_engine import StrategyEngine
            from decision_engine.capital_engine import CapitalEngine
            from decision_engine.execution_planner import ExecutionPlanner
            from board.board_meeting import BoardMeeting

            self._engines["strategy"] = StrategyEngine()
            self._engines["capital"] = CapitalEngine()
            self._engines["planner"] = ExecutionPlanner()
            self._engines["board"] = BoardMeeting()
            print(f"  Initialized: {', '.join(self._engines.keys())}")
            return True
        except Exception as e:
            print(f"  Engine init failed: {e}")
            return False

    def _step_validate_config(self) -> bool:
        config_path = "configs/system.yaml"
        if not os.path.exists(config_path):
            print(f"  Missing: {config_path}")
            return False
        try:
            import yaml  # type: ignore
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            required_keys = ["system", "data", "budget", "content", "prediction"]
            missing = [k for k in required_keys if k not in cfg]
            if missing:
                print(f"  Config missing keys: {missing}")
                return False
            print(f"  Config OK: version={cfg['system']['version']}")
            return True
        except ImportError:
            # yaml未インストールでも起動は続行（警告のみ）
            print("  [WARN] PyYAML not installed — config validation skipped")
            return True

    def _step_check_data_dirs(self) -> bool:
        required_dirs = ["data", "data/logs"]
        for d in required_dirs:
            if not os.path.exists(d):
                if not self.dry_run:
                    os.makedirs(d, exist_ok=True)
                    print(f"  Created: {d}/")
                else:
                    print(f"  [DRY-RUN] Would create: {d}/")
        return True

    def _step_boot_complete(self) -> bool:
        self._log("BOOT_COMPLETE", "All systems nominal", {
            "engines_loaded": list(self._engines.keys()),
            "dry_run": self.dry_run,
        })
        return True

    # --------------------------
    # Run Modes
    # --------------------------
    def run_component(self, component: str, **kwargs) -> Optional[Dict]:
        """特定コンポーネントのみ実行"""
        if component == "board":
            return self._run_board(**kwargs)
        elif component == "scheduler":
            return self._run_scheduler(**kwargs)
        elif component == "article":
            return self._run_article_pipeline(**kwargs)
        elif component == "knowledge":
            return self._run_knowledge_ingestion(**kwargs)
        else:
            print(f"Unknown component: {component}")
            print("Available: board, scheduler, article, knowledge")
            return None

    def _run_board(self, **kwargs) -> Dict:
        board: "BoardMeeting" = self._engines.get("board")  # type: ignore
        if not board:
            return {"error": "BoardMeeting not initialized"}
        metrics = kwargs.get("metrics", {})
        result = board.run_daily(metrics=metrics, dry_run=self.dry_run)
        return result

    def _run_scheduler(self, **kwargs) -> Dict:
        try:
            from system_scheduler import SystemScheduler
            scheduler = SystemScheduler(dry_run=self.dry_run)
            return scheduler.run_due_tasks()
        except ImportError:
            return {"error": "system_scheduler.py not found"}

    def _run_article_pipeline(self, **kwargs) -> Dict:
        try:
            from article_pipeline import ArticlePipeline
            pipeline = ArticlePipeline(dry_run=self.dry_run)
            return pipeline.run_daily()
        except ImportError:
            return {"error": "article_pipeline.py not found"}

    def _run_knowledge_ingestion(self, **kwargs) -> Dict:
        try:
            from knowledge_ingestion import KnowledgeIngestion
            ingestion = KnowledgeIngestion(dry_run=self.dry_run)
            return ingestion.ingest_latest()
        except ImportError:
            return {"error": "knowledge_ingestion.py not found"}

    # --------------------------
    # Utilities
    # --------------------------
    def _log(self, level: str, message: str, data: Dict):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "data": data,
        }
        self._boot_log.append(entry)
        if self.verbose:
            print(f"  [{level}] {message}")

    def _save_boot_log(self):
        if self.dry_run:
            return
        os.makedirs("data", exist_ok=True)
        try:
            existing = []
            if os.path.exists(self.LOG_PATH):
                with open(self.LOG_PATH, encoding="utf-8") as f:
                    existing = json.load(f)
        except Exception:
            existing = []
        # 最新200エントリを保持
        combined = existing + self._boot_log
        combined = combined[-200:]
        with open(self.LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)


# ==============================
# CLI Entry Point
# ==============================
def main():
    parser = argparse.ArgumentParser(
        description="AI Civilization OS — Nowpattern Intelligence Flywheel"
    )
    parser.add_argument("--dry-run",   action="store_true", help="書き込みなしで検証")
    parser.add_argument("--check",     action="store_true", help="ヘルスチェックのみ（起動しない）")
    parser.add_argument("--verbose",   action="store_true", help="詳細ログを表示")
    parser.add_argument("--component", default=None,
                        choices=["board", "scheduler", "article", "knowledge"],
                        help="特定コンポーネントのみ実行")
    args = parser.parse_args()

    os_instance = CivilizationOS(dry_run=args.dry_run, verbose=args.verbose)

    # --check: ヘルスチェックのみ
    if args.check:
        print("[Health Check Mode]")
        results = _import_engines()
        ok = sum(1 for v in results.values() if v)
        total = len(results)
        print(f"\nEngines: {ok}/{total} online")
        for name, status in results.items():
            print(f"  {'✓' if status else '✗'} {name}")
        sys.exit(0 if ok == total else 1)

    # Boot
    booted = os_instance.boot()
    if not booted:
        print("❌ Boot failed. Check errors above.")
        sys.exit(1)

    # Component run
    if args.component:
        result = os_instance.run_component(args.component)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    # Full OS run: board + scheduler
    print("[Running full OS cycle]")
    result = os_instance.run_component("board")
    if result:
        status = result.get("status", "unknown")
        print(f"  Board Meeting: {status}")

    print("\n✅ OS cycle complete.")


if __name__ == "__main__":
    main()
