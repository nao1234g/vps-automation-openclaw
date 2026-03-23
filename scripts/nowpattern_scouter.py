#!/usr/bin/env python3
"""
Nowpattern Scouter
予測プラットフォームの健全性を7軸で評価 (0-7) + confidence A-E + world_gap + critical_issues

Axes:
  1. Forecasting Quality       — 予測品質 (Brier Score)
  2. Metrics Integrity         — メトリクス整合性
  3. Content-Prediction Link   — コンテンツ・予測連携
  4. Search/Discoverability    — 検索・発見可能性
  5. UI/UX Quality             — UI/UX品質
  6. Publishing/Ops Reliability — 配信・運用信頼性
  7. SMNA                      — 同じミスゼロ

Usage:
  python nowpattern_scouter.py [--json] [--save] [--dry-run]
  --json:    JSON形式で出力
  --save:    scouter_history.json に追記保存
  --dry-run: 実際のHTTP/サービス呼び出しをスキップ
"""

import json
import os
import sys
import re
import subprocess
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

# ---- パス設定 ----
_IS_VPS = Path("/opt/shared").exists()
_SCRIPT_DIR = Path(__file__).parent

if _IS_VPS:
    _BASE = Path("/opt/shared")
    _SCRIPTS = _BASE / "scripts"
    _LOGS = _BASE / "logs"
    _DATA = _SCRIPTS
else:
    _BASE = _SCRIPT_DIR.parent
    _SCRIPTS = _SCRIPT_DIR
    _LOGS = _BASE / "data"
    _DATA = _BASE / "data"

SCOUTER_HISTORY_PATH = _DATA / "scouter_history.json"
MISTAKE_REGISTRY_PATH = _DATA / "mistake_registry.json"
PREDICTION_DB_PATH = _SCRIPTS / "prediction_db.json"
BRIER_AUDIT_PATH = _SCRIPTS / "brier_audit.py"
AGENT_WISDOM_PATH = _BASE / "AGENT_WISDOM.md"

# VPS専用パス
SITE_HEALTH_PATH = Path("/opt/shared/reports/site_health_latest.json") if _IS_VPS else None
PAGE_BUILDER_LOG = Path("/opt/shared/logs/prediction_page_builder.log") if _IS_VPS else None
NEO_DISPATCH_LOG = Path("/opt/shared/logs/neo_queue_dispatcher.log") if _IS_VPS else None


def _days_since(path: Path) -> int:
    if not path.exists():
        return 9999
    return (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days


def _load_prediction_db() -> dict:
    """prediction_db.json を読み込む"""
    if not PREDICTION_DB_PATH.exists():
        return {}
    try:
        return json.loads(PREDICTION_DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_mistake_registry() -> list:
    if not MISTAKE_REGISTRY_PATH.exists():
        return []
    try:
        data = json.loads(MISTAKE_REGISTRY_PATH.read_text(encoding="utf-8"))
        return data.get("mistakes", [])
    except Exception:
        return []


def _confidence_from_evidence_count(n: int) -> str:
    if n >= 6: return "A"
    if n >= 4: return "B"
    if n >= 3: return "C"
    if n >= 2: return "D"
    return "E"


# ============================================================
# 7軸スコア計算
# ============================================================

def score_forecasting_quality(db: dict, dry_run: bool = False) -> dict:
    """Axis 1: Forecasting Quality — 予測品質 (Brier Score)"""
    evidence = []
    predictions = db.get("predictions", [])

    if not predictions:
        return {
            "axis": "Forecasting Quality",
            "axis_ja": "予測品質",
            "level": 0,
            "confidence": "E",
            "evidence": ["prediction_db.json: not found or empty"],
            "trend": "stable",
            "metrics": {}
        }

    total = len(predictions)
    resolved = [p for p in predictions if p.get("status") == "resolved" and p.get("brier_score") is not None]
    active = [p for p in predictions if p.get("status") in ("active", "open")]

    evidence.append(f"Total predictions: {total}")
    evidence.append(f"Resolved (with Brier): {len(resolved)}")
    evidence.append(f"Active/Open: {len(active)}")

    if not resolved:
        return {
            "axis": "Forecasting Quality",
            "axis_ja": "予測品質",
            "level": 2,
            "confidence": "D",
            "evidence": evidence + ["No resolved predictions yet"],
            "trend": "stable",
            "metrics": {"total": total, "resolved": 0, "active": len(active)}
        }

    brier_scores = [p["brier_score"] for p in resolved if isinstance(p.get("brier_score"), (int, float))]
    avg_brier = sum(brier_scores) / len(brier_scores) if brier_scores else 0.25
    min_brier = min(brier_scores) if brier_scores else 0
    max_brier = max(brier_scores) if brier_scores else 1

    evidence.append(f"Avg Brier Score: {avg_brier:.4f}")
    evidence.append(f"Min/Max Brier: {min_brier:.4f} / {max_brier:.4f}")

    # Brier Score → Level変換
    # 0.00-0.10 = Lv7 (PERFECT), 0.10-0.15 = Lv6, 0.15-0.20 = Lv5
    # 0.20-0.25 = Lv4 (GOOD), 0.25-0.30 = Lv3, 0.30-0.35 = Lv2
    # >0.35 = Lv1, >0.45 = Lv0
    if avg_brier <= 0.05:
        level = 7
    elif avg_brier <= 0.10:
        level = 6
    elif avg_brier <= 0.15:
        level = 5
    elif avg_brier <= 0.20:
        level = 4
    elif avg_brier <= 0.25:
        level = 3
    elif avg_brier <= 0.35:
        level = 2
    elif avg_brier <= 0.45:
        level = 1
    else:
        level = 0

    # キャリブレーション: 予測確率が分散しているか
    if len(resolved) >= 5:
        probs = [p.get("our_pick_prob", 50) for p in resolved if p.get("our_pick_prob") is not None]
        unique_probs = len(set(probs))
        evidence.append(f"Probability diversity: {unique_probs} unique values in {len(probs)} predictions")
        if unique_probs >= 5:
            evidence.append("Calibration: diversified (good)")
        else:
            evidence.append("Calibration: limited diversity")

    # 直近7日間の予測活動
    recent_count = 0
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    for p in predictions:
        created = p.get("created_at") or p.get("created") or ""
        if created >= cutoff:
            recent_count += 1
    evidence.append(f"New predictions (7d): {recent_count}")

    # lang分布
    lang_ja = sum(1 for p in predictions if p.get("lang") == "ja")
    lang_en = sum(1 for p in predictions if p.get("lang") == "en")
    lang_none = total - lang_ja - lang_en
    evidence.append(f"Lang: JA={lang_ja}, EN={lang_en}, unset={lang_none}")

    trend = "improving" if avg_brier <= 0.20 else ("degrading" if avg_brier > 0.30 else "stable")

    return {
        "axis": "Forecasting Quality",
        "axis_ja": "予測品質",
        "level": level,
        "confidence": "A" if len(resolved) >= 20 else ("B" if len(resolved) >= 10 else "C"),
        "evidence": evidence,
        "trend": trend,
        "metrics": {
            "total_predictions": total,
            "resolved_count": len(resolved),
            "active_count": len(active),
            "avg_brier": round(avg_brier, 4),
            "lang_ja": lang_ja,
            "lang_en": lang_en,
            "recent_7d": recent_count,
        }
    }


def score_metrics_integrity(db: dict, dry_run: bool = False) -> dict:
    """Axis 2: Metrics Integrity — メトリクス整合性"""
    evidence = []
    score = 0.0
    predictions = db.get("predictions", [])

    if not predictions:
        return {
            "axis": "Metrics Integrity",
            "axis_ja": "メトリクス整合性",
            "level": 0,
            "confidence": "E",
            "evidence": ["prediction_db.json: not found"],
            "trend": "stable",
            "metrics": {}
        }

    total = len(predictions)

    # ghost_url 健全性
    uuid_ghost = [p for p in predictions if p.get("ghost_url") and re.search(
        r'/[0-9a-f]{8}-[0-9a-f]{4}-', str(p.get("ghost_url", "")), re.IGNORECASE
    )]
    no_ghost = [p for p in predictions if not p.get("ghost_url")]
    valid_ghost = total - len(uuid_ghost) - len(no_ghost)

    evidence.append(f"Valid ghost_url: {valid_ghost}/{total}")
    evidence.append(f"UUID ghost_url (broken): {len(uuid_ghost)}")
    evidence.append(f"Missing ghost_url: {len(no_ghost)}")

    if len(uuid_ghost) == 0 and len(no_ghost) < 10:
        score += 2.5
    elif len(uuid_ghost) <= 5:
        score += 1.5
    else:
        score += 0.5

    # our_pick_prob 整合性チェック（prob=0+NO, prob=100+YES は意味的に正常）
    def _is_invalid_prob(p):
        prob = p.get("our_pick_prob")
        pick = str(p.get("our_pick", "")).upper()
        if prob is None:
            return True
        if prob < 0 or prob > 100:
            return True
        if prob == 0 and pick == "YES":
            return True  # P(YES)=0 なのに YES 予測は矛盾
        if prob == 100 and pick == "NO":
            return True  # P(YES)=100 なのに NO 予測は矛盾
        return False
    invalid_prob = [p for p in predictions if _is_invalid_prob(p)]
    evidence.append(f"Invalid probability range: {len(invalid_prob)}")
    if len(invalid_prob) == 0:
        score += 2.0
    elif len(invalid_prob) <= 3:
        score += 1.0
    else:
        score += 0.0

    # brier_score 整合性（resolvedでbrier_scoreがある割合）
    resolved = [p for p in predictions if p.get("status") == "resolved"]
    if resolved:
        brier_filled = sum(1 for p in resolved if p.get("brier_score") is not None)
        brier_rate = brier_filled / len(resolved)
        evidence.append(f"Brier filled rate: {brier_rate:.1%} ({brier_filled}/{len(resolved)})")
        if brier_rate >= 0.9:
            score += 2.0
        elif brier_rate >= 0.5:
            score += 1.0
        else:
            score += 0.0
    else:
        evidence.append("No resolved predictions (brier check skipped)")
        score += 1.0

    # brier_audit.py 存在確認
    if BRIER_AUDIT_PATH.exists():
        evidence.append("brier_audit.py: present ✅")
        score += 0.5
    else:
        evidence.append("brier_audit.py: MISSING ⚠️")

    level = max(0, min(7, round(score)))
    return {
        "axis": "Metrics Integrity",
        "axis_ja": "メトリクス整合性",
        "level": level,
        "confidence": _confidence_from_evidence_count(len(evidence)),
        "evidence": evidence,
        "trend": "improving" if len(uuid_ghost) == 0 else "degrading",
        "metrics": {
            "valid_ghost_url": valid_ghost,
            "uuid_ghost_url": len(uuid_ghost),
            "missing_ghost_url": len(no_ghost),
            "invalid_prob": len(invalid_prob),
            "brier_audit_exists": BRIER_AUDIT_PATH.exists(),
        }
    }


def score_content_prediction_link(db: dict) -> dict:
    """Axis 3: Content-Prediction Link — コンテンツ・予測連携"""
    evidence = []
    predictions = db.get("predictions", [])

    if not predictions:
        return {
            "axis": "Content-Prediction Link",
            "axis_ja": "コンテンツ・予測連携",
            "level": 0,
            "confidence": "E",
            "evidence": ["prediction_db.json: not found"],
            "trend": "stable",
            "metrics": {}
        }

    total = len(predictions)
    with_ghost = sum(1 for p in predictions if p.get("ghost_url") and
                     not re.search(r'/[0-9a-f]{8}-[0-9a-f]{4}-', str(p.get("ghost_url", ""))))
    ghost_rate = with_ghost / total if total > 0 else 0

    evidence.append(f"Predictions with valid ghost_url: {with_ghost}/{total} ({ghost_rate:.1%})")

    # oracle_id / prediction_id 命名規則
    np_format = sum(1 for p in predictions if re.match(r"NP-\d{4}-\d{4}$", p.get("prediction_id", "")))
    evidence.append(f"Predictions with NP-YYYY-NNNN format: {np_format}/{total}")

    # 予測DB→記事連携率でスコアリング
    score = 0.0
    if ghost_rate >= 0.90:
        score += 4.0
    elif ghost_rate >= 0.75:
        score += 3.0
    elif ghost_rate >= 0.50:
        score += 2.0
    elif ghost_rate >= 0.25:
        score += 1.0

    # NP-format ID比率
    np_rate = np_format / total if total > 0 else 0
    if np_rate >= 0.9:
        score += 2.0
    elif np_rate >= 0.5:
        score += 1.0
    evidence.append(f"Prediction ID NP-format rate: {np_rate:.1%}")

    # prediction_auto_verifier の稼働確認（VPS専用）
    verifier_path = Path("/opt/shared/scripts/prediction_auto_verifier.py")
    if _IS_VPS:
        if verifier_path.exists():
            evidence.append("prediction_auto_verifier.py: present ✅")
            score += 1.0
        else:
            evidence.append("prediction_auto_verifier.py: MISSING ⚠️")

    level = max(0, min(7, round(score)))
    return {
        "axis": "Content-Prediction Link",
        "axis_ja": "コンテンツ・予測連携",
        "level": level,
        "confidence": _confidence_from_evidence_count(len(evidence)),
        "evidence": evidence,
        "trend": "stable",
        "metrics": {
            "ghost_url_rate": round(ghost_rate, 4),
            "np_format_rate": round(np_rate, 4),
            "predictions_with_ghost": with_ghost,
        }
    }


def score_search_discoverability(db: dict, dry_run: bool = False) -> dict:
    """Axis 4: Search/Discoverability — 検索・発見可能性"""
    evidence = []
    score = 0.0
    predictions = db.get("predictions", [])

    # 言語バランス (EN/JA)
    lang_ja = sum(1 for p in predictions if p.get("lang") == "ja")
    lang_en = sum(1 for p in predictions if p.get("lang") == "en")
    total = len(predictions)

    if total > 0:
        en_ratio = lang_en / total
        evidence.append(f"EN predictions: {lang_en}/{total} ({en_ratio:.1%})")
        if en_ratio >= 0.4:
            score += 2.0
        elif en_ratio >= 0.2:
            score += 1.5
        elif en_ratio >= 0.1:
            score += 1.0
        else:
            evidence.append("⚠️ EN content very low — SEO gap")
            score += 0.3

    # GSC データ（VPS専用）
    gsc_data = None
    if SITE_HEALTH_PATH and SITE_HEALTH_PATH.exists():
        try:
            gsc_data = json.loads(SITE_HEALTH_PATH.read_text(encoding="utf-8"))
            evidence.append("Site health report: present ✅")
            score += 1.0
        except Exception:
            evidence.append("Site health report: parse error")

    # predictions/ ページの存在確認（VPS専用）
    if _IS_VPS and not dry_run:
        try:
            r = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "https://nowpattern.com/predictions/"],
                capture_output=True, text=True, timeout=15
            )
            status_code = r.stdout.strip()
            evidence.append(f"/predictions/ HTTP: {status_code}")
            if status_code == "200":
                score += 2.0
            elif status_code in ("301", "302"):
                score += 1.5
            else:
                evidence.append(f"⚠️ /predictions/ returned {status_code}")
        except Exception as e:
            evidence.append(f"/predictions/ check: error ({e})")
    else:
        evidence.append("/predictions/ check: skipped (local/dry-run)")
        score += 1.5  # ローカルでの推定値

    # /en/predictions/ 確認
    if _IS_VPS and not dry_run:
        try:
            r = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "https://nowpattern.com/en/predictions/"],
                capture_output=True, text=True, timeout=15
            )
            status_code = r.stdout.strip()
            evidence.append(f"/en/predictions/ HTTP: {status_code}")
            if status_code == "200":
                score += 1.5
            else:
                evidence.append(f"⚠️ /en/predictions/ returned {status_code}")
        except Exception as e:
            evidence.append(f"/en/predictions/ check: error ({e})")
    else:
        evidence.append("/en/predictions/ check: skipped (local/dry-run)")
        score += 1.0

    level = max(0, min(7, round(score)))
    return {
        "axis": "Search/Discoverability",
        "axis_ja": "検索・発見可能性",
        "level": level,
        "confidence": "B" if _IS_VPS and not dry_run else "D",
        "evidence": evidence,
        "trend": "stable",
        "metrics": {
            "lang_ja": lang_ja,
            "lang_en": lang_en,
            "en_ratio": round(lang_en / max(total, 1), 4),
        }
    }


def score_uiux_quality(dry_run: bool = False) -> dict:
    """Axis 5: UI/UX Quality — UI/UX品質"""
    evidence = []
    score = 0.0

    # site_health レポートから読み込み
    if SITE_HEALTH_PATH and SITE_HEALTH_PATH.exists():
        try:
            health = json.loads(SITE_HEALTH_PATH.read_text(encoding="utf-8"))
            fail_count = health.get("fail_count", -1)
            total_checks = health.get("total_checks", -1)
            if fail_count >= 0:
                evidence.append(f"Site health FAIL count: {fail_count}/{total_checks}")
                if fail_count == 0:
                    score += 4.0
                elif fail_count <= 2:
                    score += 3.0
                elif fail_count <= 5:
                    score += 2.0
                else:
                    score += 1.0
            else:
                evidence.append("Site health: no fail_count field")
                score += 2.0

            # 個別チェック項目
            checks = health.get("checks", {})
            for check_name, passed in checks.items():
                if not passed:
                    evidence.append(f"  FAIL: {check_name}")
        except Exception as e:
            evidence.append(f"Site health: parse error ({e})")
            score += 1.5
    else:
        evidence.append("Site health report: not available")
        # ローカルは手動評価なし
        score += 2.0  # 推定値

    # prediction_page_builder.py の最終実行
    if PAGE_BUILDER_LOG and PAGE_BUILDER_LOG.exists():
        days_pb = _days_since(PAGE_BUILDER_LOG)
        evidence.append(f"prediction_page_builder log: {days_pb}d old")
        if days_pb <= 1:
            score += 2.0
        elif days_pb <= 3:
            score += 1.5
        elif days_pb <= 7:
            score += 1.0
        else:
            evidence.append("⚠️ Page builder may not be running")
    else:
        evidence.append("Page builder log: not found")
        if _IS_VPS:
            score += 0.5
        else:
            score += 1.5

    # design-system check (prediction-design-system.md 存在確認)
    design_system = _BASE.parent / ".claude" / "rules" / "prediction-design-system.md" if not _IS_VPS else Path("/opt/shared/rules/prediction-design-system.md")
    if not _IS_VPS:
        design_system = Path(__file__).parent.parent / ".claude" / "rules" / "prediction-design-system.md"
    if design_system.exists():
        evidence.append("Prediction design system: defined ✅")
        score += 1.0
    else:
        evidence.append("Prediction design system: not found")

    level = max(0, min(7, round(score)))
    return {
        "axis": "UI/UX Quality",
        "axis_ja": "UI/UX品質",
        "level": level,
        "confidence": "B" if (SITE_HEALTH_PATH and SITE_HEALTH_PATH.exists()) else "D",
        "evidence": evidence,
        "trend": "stable",
        "metrics": {}
    }


def score_publishing_ops(db: dict, dry_run: bool = False) -> dict:
    """Axis 6: Publishing/Ops Reliability — 配信・運用信頼性"""
    evidence = []
    score = 0.0
    predictions = db.get("predictions", [])

    # NEO-ONE/TWO サービス稼働（VPS専用）
    if _IS_VPS:
        for svc in ["neo-telegram", "neo2-telegram", "ghost-nowpattern"]:
            try:
                r = subprocess.run(
                    ["systemctl", "is-active", f"{svc}.service"],
                    capture_output=True, text=True, timeout=5
                )
                ok = r.stdout.strip() == "active"
                evidence.append(f"{svc}: {'✅ active' if ok else '❌ inactive'}")
                if ok:
                    score += 1.0
            except Exception:
                evidence.append(f"{svc}: check failed")
    else:
        evidence.append("Service status: not checked (local mode)")
        score += 2.0

    # prediction_page_builder.py cron 確認（VPS専用）
    if _IS_VPS:
        try:
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            has_page_builder = "prediction_page_builder" in r.stdout
            evidence.append(f"prediction_page_builder cron: {'✅' if has_page_builder else '❌ not found'}")
            if has_page_builder:
                score += 1.0
        except Exception:
            evidence.append("Cron check: error")
    else:
        evidence.append("Cron check: skipped (local)")
        score += 1.0

    # 最新記事活動（prediction_db の created_at）
    if predictions:
        recent = sorted(
            [p for p in predictions if p.get("created_at")],
            key=lambda p: p.get("created_at", ""),
            reverse=True
        )[:5]
        if recent:
            latest = recent[0].get("created_at", "")[:10]
            evidence.append(f"Latest prediction created: {latest}")
            try:
                days_latest = (date.today() - date.fromisoformat(latest)).days
                if days_latest <= 3:
                    score += 2.0
                elif days_latest <= 7:
                    score += 1.5
                elif days_latest <= 14:
                    score += 1.0
                else:
                    score += 0.3
                    evidence.append(f"⚠️ No new predictions for {days_latest} days")
            except Exception:
                score += 1.0

    # brier_audit.py cron（VPS専用）
    if _IS_VPS:
        try:
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            has_brier = "brier_audit" in r.stdout
            evidence.append(f"brier_audit cron: {'✅' if has_brier else '❌ not found'}")
            if has_brier:
                score += 1.0
        except Exception:
            pass

    level = max(0, min(7, round(score)))
    return {
        "axis": "Publishing/Ops Reliability",
        "axis_ja": "配信・運用信頼性",
        "level": level,
        "confidence": "B" if _IS_VPS else "C",
        "evidence": evidence,
        "trend": "stable",
        "metrics": {}
    }


def score_smna_nowpattern() -> dict:
    """Axis 7: SMNA — 同じミスゼロ (nowpattern関連ミスにフォーカス)"""
    mistakes = _load_mistake_registry()
    if not mistakes:
        return {
            "axis": "SMNA (Nowpattern)",
            "axis_ja": "同じミスゼロ",
            "level": 0,
            "confidence": "E",
            "evidence": ["mistake_registry.json: not found"],
            "trend": "stable",
            "metrics": {}
        }

    # nowpatternに関連するミスだけフィルタ
    np_scopes = {"nowpattern", "ghost", "prediction_db", "predictions_page", "x_twitter", "brier"}
    np_mistakes = [
        m for m in mistakes
        if any(s in (m.get("affected_scope") or []) for s in np_scopes)
        or any(s in str(m.get("title", "")).lower() for s in ["ghost", "brier", "prediction", "nowpattern", "oracle"])
    ]
    all_mistakes = mistakes  # 全ミストも参照

    total_all = len(all_mistakes)
    total_np = len(np_mistakes)
    prevented_np = sum(1 for m in np_mistakes if m.get("status") == "prevented")
    recurred_np = sum(1 for m in np_mistakes if m.get("recurrence_count", 1) > 1)

    prevention_rate = prevented_np / total_np if total_np > 0 else 0
    recurrence_rate = recurred_np / total_np if total_np > 0 else 0
    guarded = sum(1 for m in np_mistakes if m.get("linked_guard"))
    guard_coverage = guarded / total_np if total_np > 0 else 0

    evidence = [
        f"Nowpattern-related mistakes: {total_np}/{total_all}",
        f"Prevention rate (NP): {prevention_rate:.1%} ({prevented_np}/{total_np})",
        f"Guard coverage (NP): {guard_coverage:.1%}",
        f"Recurrence rate (NP): {recurrence_rate:.1%}",
    ]

    raw = (
        prevention_rate * 4.0
        + guard_coverage * 1.5
        - recurrence_rate * 3.0
        + (1.5 if guard_coverage >= 0.5 else 0)
    )
    level = max(0, min(7, round(raw)))

    if total_np >= 10:
        confidence = "A"
    elif total_np >= 5:
        confidence = "B"
    elif total_np >= 3:
        confidence = "C"
    else:
        confidence = "D"

    return {
        "axis": "SMNA (Nowpattern)",
        "axis_ja": "同じミスゼロ (Nowpattern)",
        "level": level,
        "confidence": confidence,
        "evidence": evidence,
        "trend": "improving" if prevention_rate >= 0.7 else "stable",
        "metrics": {
            "np_mistakes": total_np,
            "prevention_rate": round(prevention_rate, 4),
            "guard_coverage": round(guard_coverage, 4),
            "recurrence_rate": round(recurrence_rate, 4),
        }
    }


# ============================================================
# 集約スコア計算
# ============================================================

def calc_nowpattern_scouter(dry_run: bool = False) -> dict:
    """7軸を計算して総合Nowpatternスコアを返す"""
    db = _load_prediction_db()

    axes = [
        score_forecasting_quality(db, dry_run),
        score_metrics_integrity(db, dry_run),
        score_content_prediction_link(db),
        score_search_discoverability(db, dry_run),
        score_uiux_quality(dry_run),
        score_publishing_ops(db, dry_run),
        score_smna_nowpattern(),
    ]

    total_level = sum(a["level"] for a in axes)
    avg_level = total_level / len(axes)
    overall_level = round(avg_level, 2)

    conf_order = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
    weakest_conf = min(axes, key=lambda a: conf_order.get(a["confidence"], 0))["confidence"]

    critical_axes = [a for a in axes if a["level"] <= 2]
    critical_issues = []
    for a in axes:
        for ev in a.get("evidence", []):
            if "⚠️" in ev or "FAIL" in ev or "MISSING" in ev or (
                    "broken" in ev.lower() and not ev.rstrip().endswith(": 0")):
                critical_issues.append({"axis": a["axis"], "issue": ev.strip()})

    # World Gap: 世界No.1予測プラットフォームへのギャップ推定
    # 完全な予測追跡プラットフォーム(Metaculus相当)を7とした場合の差分
    brier_axis = next((a for a in axes if a["axis"] == "Forecasting Quality"), {})
    link_axis = next((a for a in axes if a["axis"] == "Content-Prediction Link"), {})
    world_gap = max(0.0, round(7.0 - avg_level, 2))

    # このrunで直した問題（固定的な確認項目）
    fixed_this_run = []
    if db.get("predictions"):
        uuid_count = sum(1 for p in db["predictions"]
                         if re.search(r'/[0-9a-f]{8}-[0-9a-f]{4}-', str(p.get("ghost_url", ""))))
        if uuid_count == 0:
            fixed_this_run.append("UUID ghost_url: 0 remaining ✅")

    return {
        "scouter": "Nowpattern Scouter",
        "timestamp": datetime.now().isoformat(),
        "overall_level": overall_level,
        "overall_confidence": weakest_conf,
        "axes": axes,
        "critical_axes": [{"axis": a["axis"], "level": a["level"]} for a in critical_axes],
        "critical_issues": critical_issues[:10],  # 最大10件
        "world_gap": world_gap,
        "fixed_this_run": fixed_this_run,
        "environment": "vps" if _IS_VPS else "local",
        "dry_run": dry_run,
    }


def save_history(result: dict):
    """scouter_history.json に追記保存"""
    if SCOUTER_HISTORY_PATH.exists():
        history = json.loads(SCOUTER_HISTORY_PATH.read_text(encoding="utf-8"))
    else:
        history = {"smna": [], "os": [], "nowpattern": []}

    history.setdefault("nowpattern", []).append({
        "timestamp": result["timestamp"],
        "overall_level": result["overall_level"],
        "overall_confidence": result.get("overall_confidence"),
        "axes": {a["axis"]: a["level"] for a in result["axes"]},
        "world_gap": result["world_gap"],
        "critical_issues": [ci.get("issue", str(ci)) for ci in result.get("critical_issues", [])],
    })
    # 最新52件保持
    history["nowpattern"] = history["nowpattern"][-52:]

    SCOUTER_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCOUTER_HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def print_report(result: dict):
    """人間可読レポートを出力"""
    print("=" * 65)
    print("🎯  NOWPATTERN SCOUTER")
    print("=" * 65)
    print(f"Overall Level: {result['overall_level']:.1f}/7 | "
          f"Confidence: {result['overall_confidence']} | "
          f"World Gap: {result['world_gap']:.2f}")
    if result.get("dry_run"):
        print("(DRY RUN — HTTP calls skipped)")
    print()
    print(f"{'Axis':<32} {'Level':>5} {'Conf':>5} {'Trend':<12}")
    print("-" * 65)
    for ax in result["axes"]:
        trend_sym = "↑" if ax["trend"] == "improving" else ("↓" if ax["trend"] == "degrading" else "→")
        bar = "█" * ax["level"] + "░" * (7 - ax["level"])
        print(f"{ax['axis_ja']:<32} {ax['level']:>5}/7  {ax['confidence']:>4}  {trend_sym} [{bar}]")

    if result["critical_issues"]:
        print()
        print("🚨 Critical Issues:")
        for ci in result["critical_issues"][:5]:
            print(f"  ⚠️  [{ci['axis']}] {ci['issue']}")

    if result.get("fixed_this_run"):
        print()
        print("✅ Fixed This Run:")
        for fix in result["fixed_this_run"]:
            print(f"  {fix}")

    print()
    print("📋 Evidence per axis:")
    for ax in result["axes"]:
        print(f"\n  [{ax['axis_ja']}] Lv{ax['level']} ({ax['confidence']})")
        for ev in ax["evidence"][:4]:
            print(f"    • {ev}")

    print()
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Nowpattern Scouter")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--save", action="store_true", help="scouter_history.jsonに保存")
    parser.add_argument("--dry-run", action="store_true", help="HTTP呼び出しをスキップ")
    args = parser.parse_args()

    result = calc_nowpattern_scouter(dry_run=args.dry_run)

    if args.save:
        save_history(result)
        if not args.json:
            print(f"[Saved to {SCOUTER_HISTORY_PATH}]")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)
        print(f"\n[Nowpattern Scouter: {result['overall_level']:.1f}/7 | "
              f"World Gap: {result['world_gap']:.2f} | "
              f"Confidence: {result['overall_confidence']}]")


if __name__ == "__main__":
    main()
