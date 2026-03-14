#!/usr/bin/env python3
"""
agent_orchestrator.py
AI Civilization OS — エージェントオーケストレーター

VPS上の3エージェント（NEO-ONE / NEO-TWO / NEO-GPT）と
ローカルエージェント（local-claude）の役割分担・タスク割り当てを管理する。

設計原則:
  Geneen原則: 「管理者は管理する。実行が全て。」
  柳井原則: 「チームを作る力 — 個人の能力をチームで実現する」

エージェント役割:
  NEO-ONE  (@claude_brain_nn_bot) → CTO・戦略・記事執筆（Opus 4.6）
  NEO-TWO  (@neo_two_nn2026_bot)  → 補助・並列タスク（Opus 4.6）
  NEO-GPT  (OpenAI Codex CLI)     → バックアップ・技術タスク
  local    (Claude Code Windows)  → ローカルファイル編集・git操作

使用方法:
  python agent_orchestrator.py --status        # 全エージェントの状態確認
  python agent_orchestrator.py --assign        # タスクを最適エージェントに割り当て
  python agent_orchestrator.py --dry-run       # 書き込みなし検証
  python agent_orchestrator.py --report        # 割り当て履歴レポート
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ==============================
# Agent Definitions
# ==============================
AGENTS: Dict[str, Dict] = {
    "neo-one": {
        "name": "NEO-ONE",
        "bot": "@claude_brain_nn_bot",
        "model": "claude-opus-4-6",
        "location": "vps",
        "service": "neo-telegram.service",
        "work_dir": "/opt/claude-code-telegram/",
        "specialties": [
            "article_writing",    # 記事執筆（JP）
            "strategy",           # 戦略立案
            "prediction_gen",     # 予測生成
            "code_review",        # コードレビュー
        ],
        "daily_capacity": 100,    # 1日あたりの最大タスク数（記事換算）
    },
    "neo-two": {
        "name": "NEO-TWO",
        "bot": "@neo_two_nn2026_bot",
        "model": "claude-opus-4-6",
        "location": "vps",
        "service": "neo2-telegram.service",
        "work_dir": "/opt/claude-code-telegram-neo2/",
        "specialties": [
            "article_writing",    # 記事執筆（JP/EN）
            "translation",        # JP→EN翻訳
            "parallel_tasks",     # 並列タスク処理
            "qa_review",          # 記事品質チェック
        ],
        "daily_capacity": 100,
    },
    "neo-gpt": {
        "name": "NEO-GPT",
        "bot": None,
        "model": "openai-codex",
        "location": "vps",
        "service": "neo3-telegram.service",
        "work_dir": "/opt/neo3-codex/",
        "specialties": [
            "code_generation",    # コード生成
            "technical_debug",    # 技術デバッグ
            "backup_writing",     # NEO-ONE/TWO障害時のバックアップ
        ],
        "daily_capacity": 50,
    },
    "local": {
        "name": "local-claude",
        "bot": None,
        "model": "claude-sonnet-4-6",
        "location": "local",
        "service": None,
        "work_dir": "c:/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/",
        "specialties": [
            "local_file_edit",    # ローカルファイル編集
            "git_operations",     # git commit/push
            "claude_md_update",   # CLAUDE.md更新
            "config_change",      # 設定変更
        ],
        "daily_capacity": 200,
    },
}

ASSIGNMENT_LOG_PATH = "data/agent_assignments.json"
MAX_LOG_ENTRIES = 500


# ==============================
# TaskType → Agent Routing
# ==============================
TASK_ROUTING: Dict[str, List[str]] = {
    # タスクタイプ → 優先エージェントリスト（先頭が最優先）
    "article_jp":        ["neo-one", "neo-two"],
    "article_en":        ["neo-two", "neo-one"],       # EN翻訳はNEO-TWOが得意
    "prediction_gen":    ["neo-one", "neo-two"],
    "strategy":          ["neo-one"],
    "code_task":         ["local", "neo-gpt"],
    "git_operation":     ["local"],
    "translation":       ["neo-two"],
    "qa_review":         ["neo-two", "neo-one"],
    "config_change":     ["local"],
    "technical_debug":   ["neo-gpt", "local"],
    "board_meeting":     ["neo-one"],
    "evolution_loop":    ["neo-one"],
}


# ==============================
# AgentOrchestrator
# ==============================
class AgentOrchestrator:
    """
    エージェントオーケストレーター

    - タスクタイプに応じて最適エージェントを選択
    - 日次キャパシティ追跡（over-allocation防止）
    - 割り当て履歴をJSONで永続化
    - VPS上のサービス状態チェック（SSH経由）
    """

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self._log: List[Dict] = []
        self._load_log()
        # 本日の使用量を初期化
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._today_usage: Dict[str, int] = self._get_today_usage(today)

    # --------------------------
    # Public API
    # --------------------------
    def assign_task(self, task_type: str, task_description: str,
                    preferred_agent: Optional[str] = None) -> Dict:
        """
        タスクを最適エージェントに割り当てる

        Returns:
            {"agent": "neo-one", "task_type": "article_jp", "assigned": True}
        """
        agent_id = preferred_agent or self._select_agent(task_type)

        if agent_id is None:
            return {
                "assigned": False,
                "task_type": task_type,
                "reason": f"No available agent for task_type={task_type}",
            }

        agent = AGENTS[agent_id]
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "agent_name": agent["name"],
            "task_type": task_type,
            "description": task_description[:200],
        }

        if not self.dry_run:
            self._log.append(entry)
            self._today_usage[agent_id] = self._today_usage.get(agent_id, 0) + 1
            self._save_log()

        print(f"  → Assigned to {agent['name']}: [{task_type}] {task_description[:60]}")
        return {"assigned": True, "agent": agent_id, **entry}

    def assign_article_batch(self, jp_count: int, en_count: int) -> Dict:
        """
        記事バッチをNEO-ONE / NEO-TWOに分配する

        JP100 + EN100 = 200本/日 の標準割り当て
        """
        assignments = {"jp": [], "en": [], "total": 0}

        # JP記事 → NEO-ONEに優先、残りをNEO-TWOに
        neo_one_cap = max(0, AGENTS["neo-one"]["daily_capacity"] - self._today_usage.get("neo-one", 0))
        neo_two_cap = max(0, AGENTS["neo-two"]["daily_capacity"] - self._today_usage.get("neo-two", 0))

        jp_for_one = min(jp_count, neo_one_cap // 2)  # JPの半分をNEO-ONEに
        jp_for_two = jp_count - jp_for_one

        for i in range(jp_for_one):
            result = self.assign_task("article_jp", f"JP記事 #{i+1}", preferred_agent="neo-one")
            assignments["jp"].append(result)
        for i in range(jp_for_two):
            result = self.assign_task("article_jp", f"JP記事 #{jp_for_one+i+1}", preferred_agent="neo-two")
            assignments["jp"].append(result)

        # EN記事 → NEO-TWO（翻訳得意）
        for i in range(en_count):
            result = self.assign_task("article_en", f"EN記事 #{i+1}", preferred_agent="neo-two")
            assignments["en"].append(result)

        assignments["total"] = len(assignments["jp"]) + len(assignments["en"])
        return assignments

    def get_status(self) -> Dict:
        """全エージェントの状態を返す"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        status = {}
        for agent_id, agent in AGENTS.items():
            used = self._today_usage.get(agent_id, 0)
            cap = agent["daily_capacity"]
            status[agent_id] = {
                "name": agent["name"],
                "model": agent["model"],
                "location": agent["location"],
                "today_used": used,
                "today_capacity": cap,
                "utilization_pct": round(used / cap * 100, 1) if cap > 0 else 0,
                "specialties": agent["specialties"],
            }
        return {
            "date": today,
            "agents": status,
            "total_assignments_today": sum(self._today_usage.values()),
        }

    def get_report(self, days: int = 7) -> Dict:
        """直近N日の割り当てレポートを返す"""
        from collections import Counter
        counts: Counter = Counter()
        agent_counts: Counter = Counter()
        for entry in self._log[-days * 50:]:  # 近似
            counts[entry.get("task_type", "unknown")] += 1
            agent_counts[entry.get("agent_id", "unknown")] += 1
        return {
            "total_assignments": len(self._log),
            "by_task_type": dict(counts.most_common(10)),
            "by_agent": dict(agent_counts.most_common()),
        }

    # --------------------------
    # Agent Selection
    # --------------------------
    def _select_agent(self, task_type: str) -> Optional[str]:
        """タスクタイプに最適なエージェントを選択（キャパシティ考慮）"""
        candidates = TASK_ROUTING.get(task_type, [])
        if not candidates:
            # デフォルト: neo-one
            candidates = ["neo-one", "neo-two"]

        for agent_id in candidates:
            used = self._today_usage.get(agent_id, 0)
            cap = AGENTS[agent_id]["daily_capacity"]
            if used < cap:
                return agent_id

        return None  # 全エージェントがキャパシティオーバー

    # --------------------------
    # Persistence
    # --------------------------
    def _load_log(self):
        if os.path.exists(ASSIGNMENT_LOG_PATH):
            try:
                with open(ASSIGNMENT_LOG_PATH, encoding="utf-8") as f:
                    self._log = json.load(f)
            except Exception:
                self._log = []
        else:
            self._log = []

    def _save_log(self):
        if self.dry_run:
            return
        os.makedirs("data", exist_ok=True)
        # 最新 MAX_LOG_ENTRIES を保持
        self._log = self._log[-MAX_LOG_ENTRIES:]
        with open(ASSIGNMENT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._log, f, ensure_ascii=False, indent=2)

    def _get_today_usage(self, today_str: str) -> Dict[str, int]:
        """本日の使用量を集計"""
        usage: Dict[str, int] = {}
        for entry in self._log:
            if entry.get("ts", "").startswith(today_str):
                agent_id = entry.get("agent_id", "unknown")
                usage[agent_id] = usage.get(agent_id, 0) + 1
        return usage


# ==============================
# CLI
# ==============================
def main():
    parser = argparse.ArgumentParser(description="AI Civilization OS Agent Orchestrator")
    parser.add_argument("--status",  action="store_true", help="全エージェントの状態表示")
    parser.add_argument("--assign",  action="store_true", help="本日の記事バッチを割り当て")
    parser.add_argument("--report",  action="store_true", help="割り当て履歴レポート")
    parser.add_argument("--dry-run", action="store_true", help="書き込みなし検証")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    args = parser.parse_args()

    orch = AgentOrchestrator(dry_run=args.dry_run, verbose=args.verbose)

    if args.status:
        status = orch.get_status()
        print(f"\n[Agent Status — {status['date']}]")
        print(f"Total assignments today: {status['total_assignments_today']}\n")
        print(f"{'Agent':<20} {'Model':<22} {'Location':<8} {'Used/Cap':>10} {'Util':>7}")
        print("-" * 75)
        for agent_id, info in status["agents"].items():
            bar = "█" * int(info["utilization_pct"] / 10)
            print(f"{info['name']:<20} {info['model']:<22} {info['location']:<8} "
                  f"{info['today_used']:>4}/{info['today_capacity']:<4} "
                  f"{info['utilization_pct']:>5.1f}% {bar}")
        return

    if args.assign:
        print("[Assigning daily article batch: JP100 + EN100]")
        result = orch.assign_article_batch(jp_count=100, en_count=100)
        print(f"\nAssigned: JP={len(result['jp'])}, EN={len(result['en'])}, Total={result['total']}")
        return

    if args.report:
        report = orch.get_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # デフォルト: status を表示
    status = orch.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
