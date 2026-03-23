#!/usr/bin/env python3
"""
Same Mistake Never Again (SMNA) Engine
mistake_registry.json を読み込み、防止率・再発率・ガードカバレッジを計算する。

Usage:
  python mistake_registry.py [--json] [--update-last-seen M001]
  --json: JSON形式で出力
  --update-last-seen MISTAKE_ID: last_seen を今日に更新しrecurrence_count++

Output: SMNA Score (0-7) + 各メトリクス
"""
import json
import sys
import os
import argparse
from datetime import date, datetime
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / 'data' / 'mistake_registry.json'
SCOUTER_HISTORY_PATH = Path(__file__).parent.parent / 'data' / 'scouter_history.json'


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Registry not found: {REGISTRY_PATH}")
    return json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))


def save_registry(registry: dict):
    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def calc_smna_score(mistakes: list) -> dict:
    """SMNA スコアを計算する（0-7 スケール）"""
    if not mistakes:
        return {"level": 0, "confidence": "E", "evidence": []}

    total = len(mistakes)
    prevented = sum(1 for m in mistakes if m.get('status') == 'prevented')
    active = sum(1 for m in mistakes if m.get('status') == 'active')
    monitoring = sum(1 for m in mistakes if m.get('status') == 'monitoring')

    # 再発件数（recurrence_count > 1）
    recurred = sum(1 for m in mistakes if m.get('recurrence_count', 1) > 1)
    recurrence_rate = recurred / total if total > 0 else 0.0

    # 防止率
    prevention_rate = prevented / total if total > 0 else 0.0

    # ガードカバレッジ（linked_guard が non-null の割合）
    guarded = sum(1 for m in mistakes if m.get('linked_guard'))
    guard_coverage = guarded / total if total > 0 else 0.0

    # テストカバレッジ（linked_test が non-null の割合）
    tested = sum(1 for m in mistakes if m.get('linked_test'))
    test_coverage = tested / total if total > 0 else 0.0

    # 深刻度スコア（critical=4, high=3, medium=2, low=1）
    severity_weights = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
    severity_score = sum(
        severity_weights.get(m.get('severity', 'medium'), 2)
        for m in mistakes
    )
    max_severity = total * 4
    severity_ratio = severity_score / max_severity if max_severity > 0 else 0

    # SMNA レベル計算（0-7）
    # 基本: prevention_rate * 5 + guard_coverage * 1 + test_coverage * 1
    # ペナルティ: recurrence_rate * -3
    raw_score = (
        prevention_rate * 4.0
        + guard_coverage * 1.0
        + test_coverage * 1.0
        + (1 - severity_ratio) * 1.0  # 深刻度が低いほど加点
        - recurrence_rate * 3.0
    )
    level = max(0, min(7, round(raw_score)))

    # 信頼度（証拠数から）
    evidence_count = total
    if evidence_count >= 15:
        confidence = "A"
    elif evidence_count >= 10:
        confidence = "B"
    elif evidence_count >= 5:
        confidence = "C"
    elif evidence_count >= 3:
        confidence = "D"
    else:
        confidence = "E"

    evidence = [
        f"Total mistakes documented: {total}",
        f"Prevention rate: {prevention_rate:.1%} ({prevented}/{total})",
        f"Guard coverage: {guard_coverage:.1%} ({guarded}/{total})",
        f"Test coverage: {test_coverage:.1%} ({tested}/{total})",
        f"Recurrence rate: {recurrence_rate:.1%} ({recurred}/{total})",
        f"Active (unresolved): {active}",
        f"Critical/High severity: {sum(1 for m in mistakes if m.get('severity') in ('critical','high'))}",
    ]

    # アクティブな問題リスト（fixが必要）
    critical_active = [
        m for m in mistakes
        if m.get('status') == 'active' and m.get('severity') in ('critical', 'high')
    ]

    return {
        "level": level,
        "confidence": confidence,
        "evidence": evidence,
        "metrics": {
            "total_mistakes": total,
            "prevented": prevented,
            "active": active,
            "monitoring": monitoring,
            "recurred": recurred,
            "prevention_rate": round(prevention_rate, 4),
            "guard_coverage": round(guard_coverage, 4),
            "test_coverage": round(test_coverage, 4),
            "recurrence_rate": round(recurrence_rate, 4),
        },
        "critical_active": [
            {"id": m["mistake_id"], "title": m["title"]}
            for m in critical_active
        ]
    }


def detect_fingerprint_match(text: str, mistakes: list) -> list:
    """テキスト内にmistakeのfingerprintパターンが含まれるか検索"""
    import re
    matches = []
    for m in mistakes:
        pattern = m.get('fingerprint', '')
        if not pattern:
            continue
        try:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append({
                    "mistake_id": m["mistake_id"],
                    "title": m["title"],
                    "severity": m["severity"],
                    "status": m["status"]
                })
        except re.error:
            pass
    return matches


def update_last_seen(registry: dict, mistake_id: str) -> bool:
    """指定したmistake_idのlast_seenを今日に更新し、recurrence_count++"""
    today = date.today().isoformat()
    for m in registry['mistakes']:
        if m['mistake_id'] == mistake_id:
            old_count = m.get('recurrence_count', 1)
            m['last_seen'] = today
            m['recurrence_count'] = old_count + 1
            m['status'] = 'active'  # 再発したのでactiveに戻す
            return True
    return False


def print_report(score_data: dict, json_mode: bool = False):
    """スコアレポートを出力"""
    if json_mode:
        print(json.dumps(score_data, ensure_ascii=False, indent=2))
        return

    level = score_data['level']
    conf = score_data['confidence']
    metrics = score_data['metrics']

    level_labels = {
        0: "Lv0: 未計測",
        1: "Lv1: 記録開始",
        2: "Lv2: パターン識別中",
        3: "Lv3: 防止策あり",
        4: "Lv4: 大部分防止済み",
        5: "Lv5: 高度な防止",
        6: "Lv6: ほぼ完全防止",
        7: "Lv7: 同じミスゼロ（世界水準）",
    }

    print("=" * 60)
    print("🛡️  SAME MISTAKE NEVER AGAIN (SMNA) ENGINE")
    print("=" * 60)
    print(f"Level: {level}/7 — {level_labels.get(level, '')}")
    print(f"Confidence: {conf}")
    print()
    print("📊 Metrics:")
    print(f"  Total mistakes documented: {metrics['total_mistakes']}")
    print(f"  Prevention rate:  {metrics['prevention_rate']:.1%} ({metrics['prevented']}/{metrics['total_mistakes']})")
    print(f"  Guard coverage:   {metrics['guard_coverage']:.1%}")
    print(f"  Test coverage:    {metrics['test_coverage']:.1%}")
    print(f"  Recurrence rate:  {metrics['recurrence_rate']:.1%}")
    print(f"  Active (open):    {metrics['active']}")
    print()
    print("📋 Evidence:")
    for e in score_data['evidence']:
        print(f"  • {e}")

    if score_data.get('critical_active'):
        print()
        print("🚨 Critical/High severity (not yet prevented):")
        for item in score_data['critical_active']:
            print(f"  [{item['id']}] {item['title']}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='SMNA Engine — Same Mistake Never Again')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--update-last-seen', metavar='MISTAKE_ID', help='Mark mistake as recurred')
    parser.add_argument('--check', metavar='TEXT', help='Check text against fingerprints')
    parser.add_argument('--list', action='store_true', help='List all mistakes')
    args = parser.parse_args()

    registry = load_registry()
    mistakes = registry['mistakes']

    if args.update_last_seen:
        if update_last_seen(registry, args.update_last_seen):
            save_registry(registry)
            print(f"Updated {args.update_last_seen}: last_seen={date.today().isoformat()}, recurrence++")
        else:
            print(f"Mistake ID not found: {args.update_last_seen}", file=sys.stderr)
            sys.exit(1)
        return

    if args.check:
        matches = detect_fingerprint_match(args.check, mistakes)
        if matches:
            print(f"⚠️  FINGERPRINT MATCHES ({len(matches)}):")
            for m in matches:
                print(f"  [{m['mistake_id']}] {m['title']} (severity: {m['severity']}, status: {m['status']})")
        else:
            print("✅ No known mistake patterns detected")
        return

    if args.list:
        print(f"{'ID':<8} {'Severity':<10} {'Status':<12} {'Recur':<8} {'Title'}")
        print("-" * 80)
        for m in mistakes:
            print(f"{m['mistake_id']:<8} {m.get('severity','?'):<10} {m.get('status','?'):<12} {m.get('recurrence_count',1):<8} {m['title'][:50]}")
        return

    # デフォルト: スコア計算
    score_data = calc_smna_score(mistakes)
    score_data['timestamp'] = datetime.now().isoformat()
    score_data['registry_version'] = registry.get('version', '1.0')

    # 履歴に追記
    history_path = SCOUTER_HISTORY_PATH
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding='utf-8'))
    else:
        history = {"smna": [], "os": [], "nowpattern": []}

    history.setdefault("smna", []).append({
        "timestamp": score_data['timestamp'],
        "level": score_data['level'],
        "metrics": score_data['metrics']
    })
    # 最新52件のみ保持
    history["smna"] = history["smna"][-52:]
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')

    print_report(score_data, json_mode=args.json)

    if not args.json:
        print(f"\n[SMNA Score: {score_data['level']}/7 | Confidence: {score_data['confidence']}]")


if __name__ == '__main__':
    main()
