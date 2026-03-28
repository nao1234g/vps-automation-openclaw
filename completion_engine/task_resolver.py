#!/usr/bin/env python3
"""
completion_engine/task_resolver.py
完遂エンジン — Task Resolver

複数の入力ソースから「今回のタスク」を解決する。

優先順位:
  1. explicit_task_input  — 明示された task input
  2. latest_user_message  — 直近のユーザー依頼
  3. active_context       — active_task_id.txt + task_ledger.json
  4. handoff_source       — handoff / docs / logs に残っている未完了タスク

TASK_INPUT が空・プレースホルダーでも、他のソースから安全に特定できれば前進する。
何も解決できない場合のみ blocked を返す。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from completion_engine.schema import Task, TaskSource

# ==============================
# Constants
# ==============================
PROJECT_ROOT = Path(__file__).parent.parent
STATE_DIR    = PROJECT_ROOT / ".claude" / "state"
DATA_DIR     = PROJECT_ROOT / "data"
DOCS_DIR     = PROJECT_ROOT / "docs"

PLACEHOLDER_PATTERNS = [
    r"^\s*\[ここに.*?\]\s*$",
    r"^\s*\[Insert.*?\]\s*$",
    r"^\s*<TASK_INPUT>\s*$",
    r"^\s*</TASK_INPUT>\s*$",
    r"^\s*$",
]

HANDOFF_SOURCES = [
    DATA_DIR / "current_task_checklist.json",
    DATA_DIR / "execution_plans.json",
    DOCS_DIR / "morning_handoff_report.md",
]


# ==============================
# Helpers
# ==============================

def _is_placeholder(text: str) -> bool:
    """テキストがプレースホルダーまたは空かどうかを判定"""
    stripped = text.strip()
    if not stripped:
        return True
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True
    # TASK_INPUTタグを除去した後の中身がプレースホルダーかチェック
    inner = re.sub(r"</?TASK_INPUT>", "", stripped).strip()
    if not inner:
        return True
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, inner, re.IGNORECASE):
            return True
    return False


def _extract_task_input_content(raw: str) -> str:
    """<TASK_INPUT>...</TASK_INPUT> タグの中身を取り出す"""
    m = re.search(r"<TASK_INPUT>(.*?)</TASK_INPUT>", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    return raw.strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_task_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"CE-{ts}"


# ==============================
# Source Resolvers
# ==============================

def _resolve_from_explicit(raw_input: str) -> Optional[str]:
    """Source 1: 明示された task input"""
    content = _extract_task_input_content(raw_input)
    if _is_placeholder(content):
        return None
    return content


def _resolve_from_active_context() -> Optional[str]:
    """Source 3: active_task_id.txt + task_ledger.json から in_progress タスクを取得"""
    active_id_file = STATE_DIR / "active_task_id.txt"
    ledger_file    = STATE_DIR / "task_ledger.json"

    active_id = None
    if active_id_file.exists():
        active_id = active_id_file.read_text(encoding="utf-8").strip()

    if not ledger_file.exists():
        return None

    try:
        ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
        tasks  = ledger.get("tasks", [])

        # active_id が指定されていればそのタスク
        if active_id:
            for t in tasks:
                if t.get("id") == active_id and t.get("status") in ("open", "in_progress"):
                    title    = t.get("title", "")
                    rationale = t.get("rationale", "")
                    return f"[継続タスク: {title}] {rationale}"

        # in_progress のタスクを探す
        for t in tasks:
            if t.get("status") == "in_progress":
                return f"[in_progress タスク: {t.get('title', '')}] {t.get('rationale', '')}"

        # open の最新タスクを探す
        open_tasks = [t for t in tasks if t.get("status") == "open"]
        if open_tasks:
            latest = open_tasks[-1]
            return f"[open タスク: {latest.get('title', '')}] {latest.get('rationale', '')}"

    except (json.JSONDecodeError, KeyError):
        pass

    return None


def _resolve_from_handoff() -> Optional[str]:
    """Source 4: handoff docs / checklist から未完了タスクを取得"""
    # current_task_checklist.json を優先
    checklist = DATA_DIR / "current_task_checklist.json"
    if checklist.exists():
        try:
            data  = json.loads(checklist.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("tasks", [])
            pending = [i for i in items if i.get("status") in ("pending", "in_progress", "open")]
            if pending:
                names = [i.get("name", i.get("title", "")) for i in pending[:3]]
                return f"[チェックリスト未完了] {', '.join(names)}"
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # morning_handoff_report.md
    handoff = DOCS_DIR / "morning_handoff_report.md"
    if handoff.exists():
        text = handoff.read_text(encoding="utf-8")
        # 「次のステップ」「Next Step」セクションを探す
        m = re.search(r"(?:次のステップ|Next Step[s]?)[:\s]+(.+?)(?:\n\n|\Z)", text, re.DOTALL)
        if m:
            return f"[ハンドオフ引継ぎ] {m.group(1).strip()[:300]}"

    return None


# ==============================
# Main Resolver
# ==============================

class TaskResolver:
    """
    複数ソースから今回の task を解決する。

    使い方:
        resolver = TaskResolver(raw_input="...")
        task, blocked_reason = resolver.resolve()
        if blocked_reason:
            print(f"BLOCKED: {blocked_reason}")
        else:
            # task.source で解決元を確認
    """

    def __init__(self, raw_input: str = ""):
        self.raw_input = raw_input

    def resolve(self) -> Tuple[Optional[Task], Optional[str]]:
        """
        Task を解決して返す。
        Returns:
            (Task, None)           — 解決成功
            (None, blocked_reason) — 解決失敗
        """
        # --- Source 1: 明示 task input ---
        explicit = _resolve_from_explicit(self.raw_input)
        if explicit:
            return self._make_task(explicit, TaskSource.EXPLICIT_TASK_INPUT), None

        # --- Source 3: active context (latest_user_message は会話APIなしでは取得不可) ---
        active = _resolve_from_active_context()
        if active:
            return self._make_task(active, TaskSource.ACTIVE_CONTEXT), None

        # --- Source 4: handoff source ---
        handoff = _resolve_from_handoff()
        if handoff:
            return self._make_task(handoff, TaskSource.HANDOFF_SOURCE), None

        # --- 全ソース失敗 → BLOCKED ---
        return None, (
            "concrete task missing — "
            "explicit_task_input is placeholder/empty, "
            "active_context has no in_progress/open tasks, "
            "handoff_source found nothing actionable"
        )

    def _make_task(self, resolved_text: str, source: TaskSource) -> Task:
        title = resolved_text.split("\n")[0][:80]
        return Task(
            id         = _make_task_id(),
            title      = title,
            source     = source.value,
            raw_input  = resolved_text,
            phase      = "resolve_task",
            status     = "open",
            created_at = _now_iso(),
            updated_at = _now_iso(),
        )
