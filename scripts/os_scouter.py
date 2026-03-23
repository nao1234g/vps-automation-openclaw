#!/usr/bin/env python3
"""
Naoto Intelligence OS Scouter
7軸スコア計算 (0-7) + confidence A-E + evidence + trend + frontier_gap

Axes:
  1. Learning Ingestion  — 学習取り込み量
  2. Retention/Memory    — 記憶・保存率
  3. Reflection/ECC      — 反省・エラー訂正
  4. Execution/Autonomy  — 実行・自律性
  5. World Knowledge     — 世界知識の鮮度
  6. Frontier Gap        — フロンティアギャップ
  7. SMNA                — 同じミスゼロ

Usage:
  python os_scouter.py [--json] [--save]
  --json: JSON形式で出力
  --save: scouter_history.json に追記保存
"""

import json
import os
import sys
import re
import subprocess
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path

# ---- パス設定 ----
_IS_VPS = Path("/opt/shared").exists()
_SCRIPT_DIR = Path(__file__).parent

if _IS_VPS:
    _BASE = Path("/opt/shared")
    _SCRIPTS = _BASE / "scripts"
    _LOGS = _BASE / "logs"
    _TASK_LOG = _BASE / "task-log"
    _DATA = _SCRIPTS  # VPS: data files live alongside scripts
else:
    _BASE = _SCRIPT_DIR.parent
    _SCRIPTS = _SCRIPT_DIR
    _LOGS = _BASE / "data"
    _TASK_LOG = _BASE / "data" / "task-log"
    _DATA = _BASE / "data"

SCOUTER_HISTORY_PATH = _DATA / "scouter_history.json"
MISTAKE_REGISTRY_PATH = _DATA / "mistake_registry.json"
AGENT_WISDOM_PATH = _BASE / "AGENT_WISDOM.md"
EVOLUTION_LOG_PATH = _LOGS / "evolution_log.json"
MISTAKE_PATTERNS_PATH = _BASE / "mistake_patterns.json"
PENDING_APPROVALS_PATH = _DATA / "pending_approvals.json"
KNOWN_MISTAKES_PATH = _BASE.parent / "docs" / "KNOWN_MISTAKES.md" if not _IS_VPS else _BASE / "KNOWN_MISTAKES.md"


def _days_since(path: Path) -> int:
    """ファイルの最終更新から何日経過したか"""
    if not path.exists():
        return 9999
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - mtime).days


def _count_task_logs(days: int = 7) -> int:
    """直近N日間のtask-logファイル数"""
    if not _TASK_LOG.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    count = 0
    for f in _TASK_LOG.rglob("*.md"):
        if datetime.fromtimestamp(f.stat().st_mtime) >= cutoff:
            count += 1
    return count


def _get_cron_count() -> int:
    """cron ジョブ総数（VPS専用）"""
    if not _IS_VPS:
        return -1
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=5
        )
        lines = [l for l in result.stdout.splitlines() if l.strip() and not l.startswith("#")]
        return len(lines)
    except Exception:
        return -1


def _get_services_status() -> dict:
    """VPSサービスの稼働状況（VPS専用）"""
    services = {
        "neo-telegram": False,
        "neo2-telegram": False,
        "neo3-telegram": False,
        "ghost-nowpattern": False,
    }
    if not _IS_VPS:
        return services
    for svc in list(services.keys()):
        try:
            r = subprocess.run(
                ["systemctl", "is-active", f"{svc}.service"],
                capture_output=True, text=True, timeout=5
            )
            services[svc] = r.stdout.strip() == "active"
        except Exception:
            pass
    return services


def _load_mistake_registry() -> list:
    """mistake_registry.json を読み込む"""
    if not MISTAKE_REGISTRY_PATH.exists():
        return []
    try:
        data = json.loads(MISTAKE_REGISTRY_PATH.read_text(encoding="utf-8"))
        return data.get("mistakes", [])
    except Exception:
        return []


def _load_evolution_log() -> list:
    """evolution_log.json を読み込む"""
    if not EVOLUTION_LOG_PATH.exists():
        return []
    try:
        data = json.loads(EVOLUTION_LOG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return data.get("entries", [])
    except Exception:
        return []


def _get_agent_wisdom_stats() -> dict:
    """AGENT_WISDOM.md の統計"""
    if not AGENT_WISDOM_PATH.exists():
        return {"exists": False, "lines": 0, "days_since_update": 9999}
    lines = len(AGENT_WISDOM_PATH.read_text(encoding="utf-8").splitlines())
    return {
        "exists": True,
        "lines": lines,
        "days_since_update": _days_since(AGENT_WISDOM_PATH),
    }


def _level_from_score(score: float, max_score: float = 7.0) -> int:
    """スコアをレベル 0-7 に変換"""
    return max(0, min(7, round(score * 7 / max_score)))


def _confidence_from_evidence_count(n: int) -> str:
    if n >= 6: return "A"
    if n >= 4: return "B"
    if n >= 3: return "C"
    if n >= 2: return "D"
    return "E"


# ============================================================
# 7軸スコア計算
# ============================================================

def score_learning_ingestion() -> dict:
    """Axis 1: Learning Ingestion — 学習取り込み量"""
    evidence = []
    score = 0.0

    # task-log活動量（7日間）
    task_logs_7d = _count_task_logs(7)
    task_logs_30d = _count_task_logs(30)
    evidence.append(f"Task logs (7d): {task_logs_7d} files")
    evidence.append(f"Task logs (30d): {task_logs_30d} files")
    if task_logs_7d >= 10:
        score += 2.5
    elif task_logs_7d >= 5:
        score += 1.5
    elif task_logs_7d >= 1:
        score += 0.8

    # AGENT_WISDOM.md の規模
    aw = _get_agent_wisdom_stats()
    if aw["exists"]:
        evidence.append(f"AGENT_WISDOM.md: {aw['lines']} lines, updated {aw['days_since_update']}d ago")
        if aw["lines"] >= 200:
            score += 2.0
        elif aw["lines"] >= 100:
            score += 1.5
        elif aw["lines"] >= 50:
            score += 1.0
    else:
        evidence.append("AGENT_WISDOM.md: not found")

    # Evolution log 存在
    evo = _load_evolution_log()
    evidence.append(f"Evolution log entries: {len(evo)}")
    if len(evo) >= 5:
        score += 1.5
    elif len(evo) >= 1:
        score += 0.8

    # ChromaDB（VPS専用）
    chromadb_active = False
    if _IS_VPS:
        try:
            r = subprocess.run(
                ["python3", "-c",
                 "import chromadb; c=chromadb.PersistentClient('/opt/shared/memory/chroma'); "
                 "cols=c.list_collections(); print(len(cols))"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                n_cols = int(r.stdout.strip() or "0")
                chromadb_active = True
                evidence.append(f"ChromaDB collections: {n_cols}")
                score += 1.0
        except Exception:
            pass
    if not chromadb_active:
        evidence.append("ChromaDB: unavailable (not checked)")

    level = max(0, min(7, round(score)))
    return {
        "axis": "Learning Ingestion",
        "axis_ja": "学習取り込み",
        "level": level,
        "confidence": _confidence_from_evidence_count(len(evidence)),
        "evidence": evidence,
        "trend": "improving" if task_logs_7d >= 5 else "stable",
        "metrics": {
            "task_logs_7d": task_logs_7d,
            "task_logs_30d": task_logs_30d,
            "agent_wisdom_lines": aw.get("lines", 0),
            "evolution_entries": len(evo),
            "chromadb_active": chromadb_active,
        }
    }


def score_retention_memory() -> dict:
    """Axis 2: Retention/Memory — 記憶・保存率"""
    evidence = []
    score = 0.0

    # AGENT_WISDOM.md
    aw = _get_agent_wisdom_stats()
    days_aw = aw.get("days_since_update", 9999)
    if aw["exists"]:
        evidence.append(f"AGENT_WISDOM.md: {aw['lines']} lines, {days_aw}d old")
        if days_aw <= 7:
            score += 2.0
        elif days_aw <= 14:
            score += 1.5
        elif days_aw <= 30:
            score += 1.0
        else:
            score += 0.3
    else:
        evidence.append("AGENT_WISDOM.md: missing — memory loss risk")

    # evolution_log.json
    evo = _load_evolution_log()
    evidence.append(f"Evolution log: {len(evo)} entries")
    if len(evo) >= 10:
        score += 2.0
    elif len(evo) >= 5:
        score += 1.5
    elif len(evo) >= 1:
        score += 0.8

    # scouter_history.json（自己追跡）
    if SCOUTER_HISTORY_PATH.exists():
        try:
            hist = json.loads(SCOUTER_HISTORY_PATH.read_text(encoding="utf-8"))
            n_os = len(hist.get("os", []))
            n_smna = len(hist.get("smna", []))
            evidence.append(f"Scouter history: OS={n_os}, SMNA={n_smna} entries")
            if n_os + n_smna >= 10:
                score += 1.5
            elif n_os + n_smna >= 3:
                score += 1.0
            else:
                score += 0.5
        except Exception:
            evidence.append("Scouter history: parse error")
    else:
        evidence.append("Scouter history: not yet started (first run)")
        score += 0.3  # 初回はペナルティなし

    # mistake_registry.json 存在
    mistakes = _load_mistake_registry()
    evidence.append(f"Mistake registry: {len(mistakes)} entries")
    if len(mistakes) >= 15:
        score += 1.5
    elif len(mistakes) >= 5:
        score += 1.0
    elif len(mistakes) >= 1:
        score += 0.5

    level = max(0, min(7, round(score)))
    return {
        "axis": "Retention/Memory",
        "axis_ja": "記憶・保存",
        "level": level,
        "confidence": _confidence_from_evidence_count(len(evidence)),
        "evidence": evidence,
        "trend": "improving" if days_aw <= 7 else ("stable" if days_aw <= 14 else "degrading"),
        "metrics": {
            "agent_wisdom_days_old": days_aw,
            "evolution_entries": len(evo),
            "mistake_registry_count": len(mistakes),
        }
    }


def score_reflection_ecc() -> dict:
    """Axis 3: Reflection/ECC — 反省・エラー訂正"""
    evidence = []

    mistakes = _load_mistake_registry()
    if not mistakes:
        return {
            "axis": "Reflection/ECC",
            "axis_ja": "反省・エラー訂正",
            "level": 1,
            "confidence": "E",
            "evidence": ["mistake_registry.json: not found"],
            "trend": "stable",
            "metrics": {}
        }

    total = len(mistakes)
    prevented = sum(1 for m in mistakes if m.get("status") == "prevented")
    active = sum(1 for m in mistakes if m.get("status") == "active")
    recurred = sum(1 for m in mistakes if m.get("recurrence_count", 1) > 1)

    prevention_rate = prevented / total if total > 0 else 0
    recurrence_rate = recurred / total if total > 0 else 0
    guarded = sum(1 for m in mistakes if m.get("linked_guard"))
    guard_coverage = guarded / total if total > 0 else 0
    tested = sum(1 for m in mistakes if m.get("linked_test"))
    test_coverage = tested / total if total > 0 else 0

    evidence.append(f"Mistakes documented: {total}")
    evidence.append(f"Prevention rate: {prevention_rate:.1%} ({prevented}/{total})")
    evidence.append(f"Guard coverage: {guard_coverage:.1%} ({guarded}/{total})")
    evidence.append(f"Test coverage: {test_coverage:.1%} ({tested}/{total})")
    evidence.append(f"Active (unresolved): {active}")
    if recurred > 0:
        evidence.append(f"Recurred mistakes: {recurred} ({recurrence_rate:.1%})")

    # mistake_patterns.json ガード数
    guard_count = 0
    if MISTAKE_PATTERNS_PATH.exists():
        try:
            patterns = json.loads(MISTAKE_PATTERNS_PATH.read_text(encoding="utf-8"))
            guard_count = len(patterns) if isinstance(patterns, list) else len(patterns.get("patterns", []))
            evidence.append(f"mistake_patterns.json guards: {guard_count}")
        except Exception:
            evidence.append("mistake_patterns.json: parse error")
    else:
        evidence.append("mistake_patterns.json: not found (VPS guard gap)")

    # スコア計算
    raw = (
        prevention_rate * 3.5
        + guard_coverage * 1.0
        + test_coverage * 1.0
        + (guard_count / max(total, 1)) * 1.0
        - recurrence_rate * 2.5
    )
    level = max(0, min(7, round(raw)))

    trend = "improving" if prevention_rate >= 0.7 and recurrence_rate < 0.1 else (
        "degrading" if recurrence_rate > 0.3 else "stable"
    )

    return {
        "axis": "Reflection/ECC",
        "axis_ja": "反省・エラー訂正",
        "level": level,
        "confidence": _confidence_from_evidence_count(len(evidence)),
        "evidence": evidence,
        "trend": trend,
        "metrics": {
            "total_mistakes": total,
            "prevention_rate": round(prevention_rate, 4),
            "guard_coverage": round(guard_coverage, 4),
            "test_coverage": round(test_coverage, 4),
            "recurrence_rate": round(recurrence_rate, 4),
            "active_mistakes": active,
            "guard_count": guard_count,
        }
    }


def score_execution_autonomy() -> dict:
    """Axis 4: Execution/Autonomy — 実行・自律性"""
    evidence = []
    score = 0.0

    # cron ジョブ数
    cron_count = _get_cron_count()
    if cron_count >= 0:
        evidence.append(f"Cron jobs: {cron_count}")
        if cron_count >= 50:
            score += 2.5
        elif cron_count >= 30:
            score += 2.0
        elif cron_count >= 10:
            score += 1.5
        elif cron_count >= 1:
            score += 0.8
    else:
        evidence.append("Cron jobs: not checked (local mode)")
        score += 1.0  # ローカルでもある程度のスコア

    # サービス稼働状況
    services = _get_services_status()
    if _IS_VPS:
        active_svcs = sum(1 for v in services.values() if v)
        total_svcs = len(services)
        evidence.append(f"Services active: {active_svcs}/{total_svcs}")
        for svc, ok in services.items():
            evidence.append(f"  {svc}: {'✅' if ok else '❌'}")
        score += (active_svcs / total_svcs) * 2.5
    else:
        evidence.append("Services: not checked (local mode)")
        score += 1.5

    # task-log 活動量（自律実行の証拠）
    task_logs_7d = _count_task_logs(7)
    evidence.append(f"Task logs (7d): {task_logs_7d}")
    if task_logs_7d >= 10:
        score += 2.0
    elif task_logs_7d >= 5:
        score += 1.5
    elif task_logs_7d >= 1:
        score += 0.8

    level = max(0, min(7, round(score)))
    active_svcs = sum(1 for v in services.values() if v) if _IS_VPS else -1

    return {
        "axis": "Execution/Autonomy",
        "axis_ja": "実行・自律性",
        "level": level,
        "confidence": "B" if _IS_VPS else "D",
        "evidence": evidence,
        "trend": "stable",
        "metrics": {
            "cron_count": cron_count,
            "services_active": active_svcs,
            "task_logs_7d": task_logs_7d,
        }
    }


def score_world_freshness() -> dict:
    """Axis 5: World Knowledge Freshness — 世界知識の鮮度"""
    evidence = []
    score = 0.0

    # AGENT_WISDOM.md の鮮度
    aw = _get_agent_wisdom_stats()
    days_aw = aw.get("days_since_update", 9999)
    evidence.append(f"AGENT_WISDOM.md: {days_aw}d since update")
    if days_aw <= 3:
        score += 3.0
    elif days_aw <= 7:
        score += 2.5
    elif days_aw <= 14:
        score += 1.5
    elif days_aw <= 30:
        score += 0.8
    else:
        score += 0.2

    # evolution_log 最新エントリ日付
    evo = _load_evolution_log()
    if evo:
        # エントリが辞書の場合、timestampフィールドを探す
        last_ts = None
        for entry in reversed(evo):
            if isinstance(entry, dict):
                ts = entry.get("timestamp") or entry.get("ts") or entry.get("date")
                if ts:
                    last_ts = ts
                    break
        if last_ts:
            try:
                last_dt = datetime.fromisoformat(last_ts[:19])
                days_evo = (datetime.now() - last_dt).days
                evidence.append(f"Evolution log latest: {days_evo}d ago")
                if days_evo <= 7:
                    score += 1.5
                elif days_evo <= 14:
                    score += 1.0
                elif days_evo <= 30:
                    score += 0.5
            except Exception:
                evidence.append("Evolution log: timestamp parse error")
        else:
            evidence.append(f"Evolution log: {len(evo)} entries (no timestamp)")
            score += 0.5
    else:
        evidence.append("Evolution log: empty")

    # Google Search Console データ（VPS専用）
    gsc_path = Path("/opt/shared/data/gsc_intelligence.json") if _IS_VPS else None
    if gsc_path and gsc_path.exists():
        days_gsc = _days_since(gsc_path)
        evidence.append(f"GSC intelligence: {days_gsc}d old")
        if days_gsc <= 7:
            score += 1.5
        elif days_gsc <= 14:
            score += 1.0
        else:
            score += 0.3
    else:
        evidence.append("GSC intelligence: not available")
        score += 0.3

    # model_intel_bot 実行証拠（pending_approvals に model_intel 系があるか）
    model_intel_found = False
    if PENDING_APPROVALS_PATH.exists():
        try:
            approvals = json.loads(PENDING_APPROVALS_PATH.read_text(encoding="utf-8"))
            if isinstance(approvals, list):
                model_intel_items = [a for a in approvals if "model" in str(a).lower() or "sota" in str(a).lower()]
            else:
                model_intel_items = [a for k, v in approvals.items()
                                     for a in (v if isinstance(v, list) else [v])
                                     if "model" in str(a).lower()]
            if model_intel_items:
                model_intel_found = True
                evidence.append(f"Model intel proposals: {len(model_intel_items)} found")
                score += 0.5
        except Exception:
            pass
    if not model_intel_found:
        evidence.append("Model intel: no recent proposals found")

    level = max(0, min(7, round(score)))
    return {
        "axis": "World Knowledge Freshness",
        "axis_ja": "世界知識の鮮度",
        "level": level,
        "confidence": _confidence_from_evidence_count(len(evidence)),
        "evidence": evidence,
        "trend": "improving" if days_aw <= 7 else ("degrading" if days_aw > 30 else "stable"),
        "metrics": {
            "agent_wisdom_days_old": days_aw,
            "evolution_entries": len(evo),
            "model_intel_found": model_intel_found,
        }
    }


def score_frontier_gap() -> dict:
    """Axis 6: Frontier Gap — フロンティアギャップ（低いほど良い）"""
    evidence = []
    gap_score = 0.0  # 0=最先端、7=最遅れ

    # pending_approvals から未実装の改善提案数
    pending_count = 0
    if PENDING_APPROVALS_PATH.exists():
        try:
            approvals = json.loads(PENDING_APPROVALS_PATH.read_text(encoding="utf-8"))
            if isinstance(approvals, list):
                pending_count = sum(1 for a in approvals if isinstance(a, dict) and a.get("status") == "pending")
            evidence.append(f"Pending approvals: {pending_count}")
            # 保留が多いほどギャップが大きい
            if pending_count >= 10:
                gap_score += 3.0
            elif pending_count >= 5:
                gap_score += 2.0
            elif pending_count >= 1:
                gap_score += 1.0
        except Exception:
            evidence.append("Pending approvals: parse error")
    else:
        evidence.append("Pending approvals: file not found")

    # AGENT_WISDOM に「Frontier」「SOTA」「最新」記述があるか
    sota_mentions = 0
    if AGENT_WISDOM_PATH.exists():
        content = AGENT_WISDOM_PATH.read_text(encoding="utf-8")
        sota_mentions = len(re.findall(r"(frontier|sota|最新|最先端|model.*intel)", content, re.IGNORECASE))
        evidence.append(f"SOTA mentions in AGENT_WISDOM: {sota_mentions}")
        if sota_mentions >= 5:
            gap_score -= 1.5  # SOTA情報が多い = ギャップ小
        elif sota_mentions >= 2:
            gap_score -= 0.8

    # KNOWN_MISTAKES.md に「古い情報」パターンがあるか
    outdated_count = 0
    if KNOWN_MISTAKES_PATH.exists():
        km_content = KNOWN_MISTAKES_PATH.read_text(encoding="utf-8")
        outdated_count = len(re.findall(r"(古い情報|outdated|廃止|deprecated)", km_content, re.IGNORECASE))
        if outdated_count > 0:
            evidence.append(f"Outdated pattern warnings: {outdated_count}")
            gap_score += 0.5

    # evolution_loop が稼働中か（自己進化 = フロンティアギャップ縮小）
    evo = _load_evolution_log()
    if len(evo) >= 3:
        evidence.append(f"Self-evolution active: {len(evo)} cycles")
        gap_score -= 1.5
    elif len(evo) >= 1:
        evidence.append(f"Self-evolution started: {len(evo)} cycles")
        gap_score -= 0.8
    else:
        evidence.append("Self-evolution: not yet active")
        gap_score += 1.5

    # フロンティアギャップは低いほど良い。レベルはギャップの逆数
    gap_score = max(0.0, gap_score)
    level = max(0, min(7, 7 - round(gap_score)))

    return {
        "axis": "Frontier Gap",
        "axis_ja": "フロンティアギャップ",
        "level": level,
        "confidence": _confidence_from_evidence_count(len(evidence)),
        "evidence": evidence,
        "trend": "improving" if len(evo) >= 3 else "stable",
        "frontier_gap": round(gap_score, 2),
        "metrics": {
            "pending_approvals": pending_count,
            "sota_mentions": sota_mentions,
            "evolution_cycles": len(evo),
        }
    }


def score_smna() -> dict:
    """Axis 7: SMNA — 同じミスゼロ (mistake_registry.py の結果を再利用)"""
    mistakes = _load_mistake_registry()
    if not mistakes:
        return {
            "axis": "SMNA",
            "axis_ja": "同じミスゼロ",
            "level": 0,
            "confidence": "E",
            "evidence": ["mistake_registry.json: not found"],
            "trend": "stable",
            "metrics": {}
        }

    total = len(mistakes)
    prevented = sum(1 for m in mistakes if m.get("status") == "prevented")
    recurred = sum(1 for m in mistakes if m.get("recurrence_count", 1) > 1)
    guarded = sum(1 for m in mistakes if m.get("linked_guard"))
    tested = sum(1 for m in mistakes if m.get("linked_test"))
    active = sum(1 for m in mistakes if m.get("status") == "active")

    prevention_rate = prevented / total
    recurrence_rate = recurred / total
    guard_coverage = guarded / total
    test_coverage = tested / total

    severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    severity_score = sum(severity_weights.get(m.get("severity", "medium"), 2) for m in mistakes)
    max_severity = total * 4
    severity_ratio = severity_score / max_severity if max_severity > 0 else 0

    raw = (
        prevention_rate * 4.0
        + guard_coverage * 1.0
        + test_coverage * 1.0
        + (1 - severity_ratio) * 1.0
        - recurrence_rate * 3.0
    )
    level = max(0, min(7, round(raw)))

    evidence = [
        f"Total mistakes: {total}",
        f"Prevention rate: {prevention_rate:.1%} ({prevented}/{total})",
        f"Guard coverage: {guard_coverage:.1%} ({guarded}/{total})",
        f"Test coverage: {test_coverage:.1%} ({tested}/{total})",
        f"Recurrence rate: {recurrence_rate:.1%} ({recurred}/{total})",
        f"Active (open): {active}",
    ]
    if total >= 15:
        confidence = "A"
    elif total >= 10:
        confidence = "B"
    elif total >= 5:
        confidence = "C"
    elif total >= 3:
        confidence = "D"
    else:
        confidence = "E"

    return {
        "axis": "SMNA",
        "axis_ja": "同じミスゼロ",
        "level": level,
        "confidence": confidence,
        "evidence": evidence,
        "trend": "improving" if prevention_rate >= 0.7 else ("degrading" if recurrence_rate > 0.2 else "stable"),
        "metrics": {
            "total_mistakes": total,
            "prevention_rate": round(prevention_rate, 4),
            "guard_coverage": round(guard_coverage, 4),
            "test_coverage": round(test_coverage, 4),
            "recurrence_rate": round(recurrence_rate, 4),
            "active": active,
        }
    }


# ============================================================
# 集約スコア計算
# ============================================================

def calc_os_scouter() -> dict:
    """7軸を計算して総合OSスコアを返す"""
    axes = [
        score_learning_ingestion(),
        score_retention_memory(),
        score_reflection_ecc(),
        score_execution_autonomy(),
        score_world_freshness(),
        score_frontier_gap(),
        score_smna(),
    ]

    total_level = sum(a["level"] for a in axes)
    avg_level = total_level / len(axes)

    # 総合スコア: 平均レベル（0-7）
    overall_level = round(avg_level, 2)

    # 信頼度: 最も低い軸のconfidenceを採用
    conf_order = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
    weakest_conf = min(axes, key=lambda a: conf_order.get(a["confidence"], 0))["confidence"]

    # クリティカル問題（level <= 2 の軸）
    critical_axes = [a for a in axes if a["level"] <= 2]

    # フロンティアギャップ（Axis 6から）
    frontier_gap = next((a.get("frontier_gap", 0) for a in axes if a["axis"] == "Frontier Gap"), 0)

    return {
        "scouter": "Naoto Intelligence OS Scouter",
        "timestamp": datetime.now().isoformat(),
        "overall_level": overall_level,
        "overall_confidence": weakest_conf,
        "axes": axes,
        "critical_axes": [{"axis": a["axis"], "level": a["level"]} for a in critical_axes],
        "frontier_gap": frontier_gap,
        "environment": "vps" if _IS_VPS else "local",
    }


def save_history(result: dict):
    """scouter_history.json に追記保存"""
    if SCOUTER_HISTORY_PATH.exists():
        history = json.loads(SCOUTER_HISTORY_PATH.read_text(encoding="utf-8"))
    else:
        history = {"smna": [], "os": [], "nowpattern": []}

    history.setdefault("os", []).append({
        "timestamp": result["timestamp"],
        "overall_level": result["overall_level"],
        "axes": {a["axis"]: a["level"] for a in result["axes"]},
        "frontier_gap": result["frontier_gap"],
    })
    # 最新52件保持
    history["os"] = history["os"][-52:]

    SCOUTER_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCOUTER_HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def print_report(result: dict):
    """人間可読レポートを出力"""
    print("=" * 65)
    print("🔭  NAOTO INTELLIGENCE OS SCOUTER")
    print("=" * 65)
    print(f"Overall Level: {result['overall_level']:.1f}/7 | "
          f"Confidence: {result['overall_confidence']} | "
          f"Env: {result['environment']}")
    print(f"Frontier Gap: {result['frontier_gap']:.2f}")
    print()
    print(f"{'Axis':<30} {'Level':>5} {'Conf':>5} {'Trend':<12}")
    print("-" * 65)
    for ax in result["axes"]:
        trend_sym = "↑" if ax["trend"] == "improving" else ("↓" if ax["trend"] == "degrading" else "→")
        bar = "█" * ax["level"] + "░" * (7 - ax["level"])
        print(f"{ax['axis']:<30} {ax['level']:>5}/7  {ax['confidence']:>4}  {trend_sym} [{bar}]")

    if result["critical_axes"]:
        print()
        print("🚨 Critical Axes (level ≤ 2):")
        for ca in result["critical_axes"]:
            print(f"  ⚠️  {ca['axis']}: Lv{ca['level']}/7")

    print()
    print("📋 Evidence per axis:")
    for ax in result["axes"]:
        print(f"\n  [{ax['axis']}] Lv{ax['level']} ({ax['confidence']})")
        for ev in ax["evidence"][:4]:  # 最大4件表示
            print(f"    • {ev}")

    print()
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Naoto Intelligence OS Scouter")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--save", action="store_true", help="scouter_history.jsonに保存")
    args = parser.parse_args()

    result = calc_os_scouter()

    if args.save:
        save_history(result)
        if not args.json:
            print(f"[Saved to {SCOUTER_HISTORY_PATH}]")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)
        print(f"\n[OS Scouter: {result['overall_level']:.1f}/7 | "
              f"Confidence: {result['overall_confidence']} | "
              f"Frontier Gap: {result['frontier_gap']:.2f}]")


if __name__ == "__main__":
    main()
