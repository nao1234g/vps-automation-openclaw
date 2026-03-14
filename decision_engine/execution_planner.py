"""
decision_engine/execution_planner.py
実行プランナー — 戦略的アクションをタスクシーケンスに変換する

柳井原則: 「実行が伴っていなければ意味がない」
Geneen原則: 「肝心なのは行うことである」

戦略はツールではない。実行のための準備に過ぎない。
"""

import sys
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskOwner(str, Enum):
    NEO_ONE = "NEO-ONE"
    NEO_TWO = "NEO-TWO"
    NEO_GPT = "NEO-GPT"
    LOCAL_CLAUDE = "local-claude"
    CRON = "cron"
    HUMAN = "human"  # Naoto


@dataclass
class ExecutionTask:
    """実行可能なタスク単位"""
    id: str
    title: str
    description: str
    action_id: str              # 元のStrategicAction.id
    owner: str                   # TaskOwner
    status: str = TaskStatus.PENDING
    priority: int = 2            # 1=最高 / 2=高 / 3=中 / 4=低
    estimated_minutes: int = 30
    depends_on: List[str] = field(default_factory=list)  # task idのリスト
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def is_blocked(self) -> bool:
        return self.status == TaskStatus.BLOCKED

    @property
    def is_ready(self) -> bool:
        """依存タスクが全て完了しているかを確認（depends_onが空か）"""
        return len(self.depends_on) == 0 and self.status == TaskStatus.PENDING


@dataclass
class ExecutionPlan:
    """実行計画（複数タスクのシーケンス）"""
    id: str
    title: str
    action_id: str
    tasks: List[ExecutionTask] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d

    @property
    def completion_rate(self) -> float:
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)

    @property
    def is_complete(self) -> bool:
        return all(t.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED) for t in self.tasks)

    @property
    def next_tasks(self) -> List[ExecutionTask]:
        """次に実行すべきタスク（依存なし・pending）を返す"""
        # 完了済みタスクIDのセット
        done_ids = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        ready = []
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            if all(dep in done_ids for dep in task.depends_on):
                ready.append(task)
        return sorted(ready, key=lambda t: t.priority)


# アクションカテゴリ → タスクテンプレートのマッピング
CATEGORY_TASK_TEMPLATES = {
    "flywheel": [
        {
            "title_prefix": "予測DB登録",
            "description_template": "{action_title}のための予測エントリをprediction_db.jsonに追加する",
            "owner": TaskOwner.NEO_ONE,
            "estimated_minutes": 20,
            "priority": 1,
        },
        {
            "title_prefix": "記事生成",
            "description_template": "{action_title}の力学分析記事を執筆しGhostに公開する",
            "owner": TaskOwner.NEO_ONE,
            "estimated_minutes": 45,
            "priority": 1,
            "depends_on_prev": True,
        },
        {
            "title_prefix": "X配信",
            "description_template": "公開した記事をX投稿用にフォーマットしてキューに追加する",
            "owner": TaskOwner.CRON,
            "estimated_minutes": 5,
            "priority": 2,
            "depends_on_prev": True,
        },
    ],
    "moat": [
        {
            "title_prefix": "予測検証",
            "description_template": "prediction_auto_verifier.pyを実行し解決済み予測のBrier Scoreを更新する",
            "owner": TaskOwner.NEO_ONE,
            "estimated_minutes": 15,
            "priority": 1,
        },
        {
            "title_prefix": "トラックレコード更新",
            "description_template": "/predictions/ページをprediction_page_builder.pyで再ビルドする",
            "owner": TaskOwner.CRON,
            "estimated_minutes": 10,
            "priority": 2,
            "depends_on_prev": True,
        },
    ],
    "quality": [
        {
            "title_prefix": "品質チェック",
            "description_template": "article_validator.pyで全記事の品質を検証する",
            "owner": TaskOwner.LOCAL_CLAUDE,
            "estimated_minutes": 10,
            "priority": 2,
        },
        {
            "title_prefix": "修正対応",
            "description_template": "FAILした記事の修正をNEO-TWOに委譲する",
            "owner": TaskOwner.NEO_TWO,
            "estimated_minutes": 30,
            "priority": 2,
            "depends_on_prev": True,
        },
    ],
    "growth": [
        {
            "title_prefix": "X分析",
            "description_template": "x-algorithm-monitor.pyで投稿パフォーマンスを分析する",
            "owner": TaskOwner.CRON,
            "estimated_minutes": 10,
            "priority": 3,
        },
        {
            "title_prefix": "戦術調整",
            "description_template": "analytics結果に基づいてX投稿戦術を調整する",
            "owner": TaskOwner.LOCAL_CLAUDE,
            "estimated_minutes": 20,
            "priority": 3,
            "depends_on_prev": True,
        },
    ],
    "monetize": [
        {
            "title_prefix": "収益化設計",
            "description_template": "{action_title}の具体的な実装仕様を設計する",
            "owner": TaskOwner.LOCAL_CLAUDE,
            "estimated_minutes": 60,
            "priority": 2,
        },
        {
            "title_prefix": "実装",
            "description_template": "設計に基づいて収益化機能を実装する",
            "owner": TaskOwner.NEO_ONE,
            "estimated_minutes": 120,
            "priority": 2,
            "depends_on_prev": True,
        },
        {
            "title_prefix": "承認確認",
            "description_template": "Naotoに実装内容を報告し承認を得る",
            "owner": TaskOwner.HUMAN,
            "estimated_minutes": 30,
            "priority": 1,
            "depends_on_prev": True,
        },
    ],
}


class ExecutionPlanner:
    """
    実行プランナー

    StrategyEngine から StrategicAction を受け取り、
    オーナー別・依存関係付きのタスクシーケンスに変換する。
    """

    PLANS_PATH = "data/execution_plans.json"
    TASK_LOG_PATH = "data/task_execution_log.json"

    def __init__(self):
        self._plans: List[ExecutionPlan] = []
        self._task_log: List[Dict] = []
        self._load()

    # ── プラン生成 ────────────────────────────────────────────

    def create_plan(self, action_id: str, action_title: str,
                    category: str, impact: str = "MEDIUM",
                    due_date: Optional[str] = None) -> ExecutionPlan:
        """
        StrategicAction からExecutionPlanを生成する

        Args:
            action_id: StrategicAction.id
            action_title: アクションタイトル
            category: flywheel / moat / quality / growth / monetize
            impact: HIGH / MEDIUM / LOW
            due_date: ISO形式の期限

        Returns:
            ExecutionPlan（タスク付き）
        """
        plan_id = f"EP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self._plans)+1:03d}"

        templates = CATEGORY_TASK_TEMPLATES.get(category, CATEGORY_TASK_TEMPLATES["quality"])

        tasks = []
        prev_task_id: Optional[str] = None
        priority_base = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(impact, 2)

        for i, tmpl in enumerate(templates):
            task_id = f"{plan_id}-T{i+1:02d}"
            title = f"{tmpl['title_prefix']}: {action_title[:50]}"
            description = tmpl.get("description_template", "").format(
                action_title=action_title
            )

            # 依存関係（前のタスクが必要か）
            depends_on = []
            if tmpl.get("depends_on_prev") and prev_task_id:
                depends_on.append(prev_task_id)

            task = ExecutionTask(
                id=task_id,
                title=title,
                description=description,
                action_id=action_id,
                owner=tmpl.get("owner", TaskOwner.LOCAL_CLAUDE),
                priority=tmpl.get("priority", priority_base),
                estimated_minutes=tmpl.get("estimated_minutes", 30),
                depends_on=depends_on,
                due_date=due_date,
            )
            tasks.append(task)
            prev_task_id = task_id

        plan = ExecutionPlan(
            id=plan_id,
            title=f"実行計画: {action_title[:60]}",
            action_id=action_id,
            tasks=tasks,
        )

        self._plans.append(plan)
        self._save()

        return plan

    def get_active_plans(self) -> List[ExecutionPlan]:
        """未完了のプランを返す"""
        return [p for p in self._plans if not p.is_complete]

    def get_next_tasks(self, owner: Optional[str] = None, limit: int = 10) -> List[ExecutionTask]:
        """
        次に実行すべきタスクを返す

        Args:
            owner: フィルタするオーナー（Noneなら全員）
            limit: 最大件数

        Returns:
            priority順にソートしたタスクリスト
        """
        all_next = []
        for plan in self.get_active_plans():
            for task in plan.next_tasks:
                if owner is None or task.owner == owner:
                    all_next.append(task)

        return sorted(all_next, key=lambda t: (t.priority, t.created_at))[:limit]

    def complete_task(self, task_id: str, result: str = "") -> bool:
        """タスクを完了としてマークする"""
        for plan in self._plans:
            for task in plan.tasks:
                if task.id == task_id:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now(timezone.utc).isoformat()
                    task.result = result

                    # プラン完了チェック
                    if plan.is_complete:
                        plan.completed_at = datetime.now(timezone.utc).isoformat()

                    # 依存解除: 他タスクの depends_on からこのIDを削除
                    self._resolve_dependencies(task_id, plan)

                    # ログ記録
                    self._log_completion(task, plan.title)
                    self._save()
                    return True
        return False

    def generate_daily_briefing(self, owner: Optional[str] = None) -> Dict:
        """
        デイリーブリーフィング — 今日やること

        Returns:
            {"today_tasks", "blocked_tasks", "overdue_tasks", "completion_rate"}
        """
        today = datetime.now(timezone.utc).date().isoformat()
        next_tasks = self.get_next_tasks(owner=owner, limit=20)

        today_tasks = []
        overdue_tasks = []

        for task in next_tasks:
            if task.due_date and task.due_date < today:
                overdue_tasks.append(task.to_dict())
            else:
                today_tasks.append(task.to_dict())

        # ブロック中タスク
        blocked = []
        for plan in self.get_active_plans():
            for task in plan.tasks:
                if task.status == TaskStatus.BLOCKED:
                    blocked.append(task.to_dict())

        # 全体完了率
        all_tasks = [t for p in self._plans for t in p.tasks]
        completed_count = sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED)
        completion_rate = completed_count / len(all_tasks) if all_tasks else 0.0

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "owner_filter": owner,
            "today_tasks": today_tasks[:5],
            "blocked_tasks": blocked,
            "overdue_tasks": overdue_tasks,
            "completion_rate": round(completion_rate, 2),
            "total_tasks": len(all_tasks),
            "completed_tasks": completed_count,
        }

    def generate_owner_assignments(self) -> Dict[str, List[Dict]]:
        """全オーナー別のタスク割り当てを返す"""
        result: Dict[str, List[Dict]] = {owner.value: [] for owner in TaskOwner}
        for task in self.get_next_tasks(limit=50):
            owner = task.owner
            if owner in result:
                result[owner].append(task.to_dict())
            else:
                result[owner] = [task.to_dict()]
        return result

    # ── 内部処理 ──────────────────────────────────────────────

    def _resolve_dependencies(self, completed_task_id: str, plan: ExecutionPlan):
        """完了タスクへの依存を解除する（depends_onリストから削除）"""
        for task in plan.tasks:
            if completed_task_id in task.depends_on:
                task.depends_on.remove(completed_task_id)
                if task.status == TaskStatus.BLOCKED:
                    task.status = TaskStatus.PENDING

    def _log_completion(self, task: ExecutionTask, plan_title: str):
        self._task_log.append({
            "task_id": task.id,
            "plan_title": plan_title,
            "owner": task.owner,
            "completed_at": task.completed_at,
            "result": task.result,
        })
        # 最新500件のみ保持
        if len(self._task_log) > 500:
            self._task_log = self._task_log[-500:]

    def _load(self):
        if os.path.exists(self.PLANS_PATH):
            try:
                with open(self.PLANS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for plan_data in data:
                    tasks = [ExecutionTask(**t) for t in plan_data.pop("tasks", [])]
                    plan = ExecutionPlan(**plan_data, tasks=tasks)
                    self._plans.append(plan)
            except Exception as e:
                print(f"[WARNING] ExecutionPlanner load error: {e}")

        if os.path.exists(self.TASK_LOG_PATH):
            try:
                with open(self.TASK_LOG_PATH, "r", encoding="utf-8") as f:
                    self._task_log = json.load(f)
            except Exception:
                pass

    def _save(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.PLANS_PATH, "w", encoding="utf-8") as f:
                json.dump([p.to_dict() for p in self._plans], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] ExecutionPlanner save error: {e}")

        try:
            with open(self.TASK_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._task_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] ExecutionPlanner log save error: {e}")


if __name__ == "__main__":
    planner = ExecutionPlanner()

    # デモ: prediction_dbに5件追加するプランを作成
    plan = planner.create_plan(
        action_id="SA-20260314-001",
        action_title="prediction_db に毎日5件追加するcronを整備",
        category="flywheel",
        impact="HIGH",
        due_date=(datetime.now(timezone.utc) + timedelta(days=3)).date().isoformat(),
    )

    print(f"プラン生成: {plan.title}")
    print(f"タスク数: {len(plan.tasks)}")
    for task in plan.tasks:
        deps = f" (依存: {task.depends_on})" if task.depends_on else ""
        print(f"  [{task.priority}] {task.title} → {task.owner}{deps}")

    # ブリーフィング
    briefing = planner.generate_daily_briefing()
    print(f"\nデイリーブリーフィング:")
    print(f"  今日のタスク: {len(briefing['today_tasks'])}件")
    print(f"  完了率: {briefing['completion_rate']*100:.0f}%")
