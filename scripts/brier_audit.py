#!/usr/bin/env python3
"""
Brier Score Daily Audit
metrics整合性チェック + YES/NOテスト + daily cron用
2026-03-22 Track 4 追加
"""
import json
import sys
from pathlib import Path

_IS_VPS = Path('/opt/shared').exists()
if _IS_VPS:
    DB_PATH = Path('/opt/shared/scripts/prediction_db.json')
else:
    DB_PATH = Path(__file__).parent / 'prediction_db.json'

def calc_brier_score(our_pick_prob, outcome):
    p = our_pick_prob / 100.0
    return round((p - outcome) ** 2, 4)

def run_unit_tests():
    tests = [
        (70, 1, 0.09,  'YES予測70% -> 的中: BS=0.09'),
        (70, 0, 0.49,  'YES予測70% -> 外れ: BS=0.49'),
        (30, 0, 0.09,  'NO予測prob=30 -> 的中: BS=0.09'),
        (30, 1, 0.49,  'NO予測prob=30 -> 外れ: BS=0.49'),
        (50, 1, 0.25,  '確率50% -> 的中: BS=0.25'),
        (50, 0, 0.25,  '確率50% -> 外れ: BS=0.25'),
        (10, 0, 0.01,  '低確率 -> 的中: BS=0.01'),
        (90, 1, 0.01,  '高確率 -> 的中: BS=0.01'),
    ]
    print('=== Brier Score Unit Tests ===')
    all_pass = True
    for prob, outcome, expected, desc in tests:
        actual = calc_brier_score(prob, outcome)
        passed = abs(actual - expected) < 0.001
        status = 'PASS' if passed else 'FAIL'
        if not passed:
            all_pass = False
        print(f'  [{status}] {desc}')
        if not passed:
            print(f'       Expected {expected}, Got {actual}')
    return all_pass

def audit_db():
    db = json.load(open(DB_PATH, encoding='utf-8'))
    preds = db['predictions']
    total = len(preds)
    resolved = [p for p in preds if p.get('status') == 'resolved']
    active = [p for p in preds if p.get('status') == 'active']
    open_ = [p for p in preds if p.get('status') == 'open']
    resolving = [p for p in preds if p.get('status') == 'resolving']
    scored = [p for p in resolved if p.get('brier_score') is not None]
    avg_brier = sum(p['brier_score'] for p in scored) / len(scored) if scored else None

    uuid_urls = [p for p in preds if '/p/' in p.get('ghost_url','')]
    missing_urls = [p for p in preds if not p.get('ghost_url','') and p.get('status') != 'resolved']
    invalid_prob = [p for p in preds if not (0 <= p.get('our_pick_prob', 50) <= 100)]

    print('\n=== Prediction DB Audit ===')
    print(f'Total: {total}')
    print(f'  active:    {len(active)}')
    print(f'  open:      {len(open_)}')
    print(f'  resolving: {len(resolving)}')
    print(f'  resolved:  {len(resolved)}')
    print(f'  scored:    {len(scored)}')
    if avg_brier is not None:
        grade = 'EXCELLENT' if avg_brier <= 0.15 else 'GOOD' if avg_brier <= 0.20 else 'OK' if avg_brier <= 0.25 else 'BAD'
        print(f'  avg Brier: {avg_brier:.4f} ({grade})')
    print(f'\n  UUID ghost_url:   {len(uuid_urls)} (SHOULD BE 0)')
    print(f'  ghost_url missing: {len(missing_urls)}')
    print(f'  invalid prob:     {len(invalid_prob)}')

    issues = []
    if uuid_urls:
        issues.append(f'UUID ghost_url {len(uuid_urls)}')
    if len(missing_urls) > 10:
        issues.append(f'ghost_url missing {len(missing_urls)}')
    if invalid_prob:
        issues.append(f'invalid prob {len(invalid_prob)}')
    if avg_brier and avg_brier > 0.25:
        issues.append(f'Brier BAD {avg_brier:.4f}')

    if issues:
        print(f'\nISSUES: {issues}')
        return False
    else:
        print('\nAll checks passed')
        return True

if __name__ == '__main__':
    tests_ok = run_unit_tests()
    audit_ok = audit_db()
    if tests_ok and audit_ok:
        print('\nBRIER AUDIT: ALL PASS')
        sys.exit(0)
    else:
        print('\nBRIER AUDIT: ISSUES FOUND')
        sys.exit(1)
