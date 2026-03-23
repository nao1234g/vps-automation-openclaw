#!/usr/bin/env python3
"""Fix prediction_db.json quality issues:
  C2: 'incorrect' -> 'wrong' normalization (6 records)
  C7: scenario-based outcomes -> YES/NO + Brier recalc (8 records)
"""
import json, shutil, os
from datetime import datetime

DB = '/opt/shared/scripts/prediction_db.json'
BACKUP = f'/opt/shared/scripts/prediction_db.json.bak.{datetime.now().strftime("%Y%m%d_%H%M%S")}'

DRY_RUN = '--apply' not in __import__('sys').argv
if DRY_RUN:
    print('DRY-RUN mode. Pass --apply to execute.')
else:
    shutil.copy2(DB, BACKUP)
    print(f'[BACKUP] {BACKUP}')

db = json.load(open(DB, encoding='utf-8'))
preds = db['predictions']

c2_fixed = 0
c7_fixed = 0
brier_recalc = 0

def calc_brier(our_pick, our_pick_prob, outcome_yn):
    """Standard binary Brier score. outcome_yn: 'YES'->1.0, 'NO'->0.0"""
    if our_pick == 'YES':
        p_yes = our_pick_prob / 100.0
    else:
        p_yes = 1.0 - our_pick_prob / 100.0
    outcome_val = 1.0 if outcome_yn == 'YES' else 0.0
    return round((p_yes - outcome_val) ** 2, 4)

for p in preds:
    pid = p.get('prediction_id', '?')
    changed = False

    # C2: normalize hit_miss 'incorrect' -> 'wrong'
    if p.get('hit_miss') == 'incorrect':
        print(f'[C2] {pid}: hit_miss incorrect -> wrong')
        if not DRY_RUN:
            p['hit_miss'] = 'wrong'
        c2_fixed += 1
        changed = True

    # C7: convert scenario-based outcomes to YES/NO
    outcome = p.get('outcome', '')
    if outcome not in ('YES', 'NO', None, '') and p.get('brier_score') is not None:
        hm = p.get('hit_miss', '')
        pick = p.get('our_pick', '')
        prob = p.get('our_pick_prob')

        # Determine binary outcome from hit_miss
        if hm in ('correct',):
            new_outcome = pick  # correct prediction -> outcome matches pick
        elif hm in ('incorrect', 'wrong'):
            new_outcome = 'NO' if pick == 'YES' else 'YES'
        else:
            print(f'[C7-SKIP] {pid}: hit_miss={hm} unknown, cannot infer')
            continue

        old_brier = p.get('brier_score')
        new_brier = calc_brier(pick, prob, new_outcome) if prob is not None else old_brier

        print(f'[C7] {pid}: outcome={outcome} -> {new_outcome}  hit_miss={hm}')
        print(f'      pick={pick} prob={prob}%  brier: {old_brier} -> {new_brier}')

        if not DRY_RUN:
            p['outcome'] = new_outcome
            p['brier_score'] = new_brier

        c7_fixed += 1
        brier_recalc += 1
        changed = True

    # Special case: outcome=None but brier and hit_miss already set
    if p.get('outcome') is None and p.get('brier_score') is not None and p.get('hit_miss') in ('correct', 'wrong'):
        pick = p.get('our_pick', '')
        hm = p.get('hit_miss')
        if hm == 'correct':
            new_outcome = pick
        else:
            new_outcome = 'NO' if pick == 'YES' else 'YES'
        prob = p.get('our_pick_prob')
        new_brier = calc_brier(pick, prob, new_outcome) if prob is not None else p.get('brier_score')
        print(f'[C7-NULL] {pid}: outcome=None -> {new_outcome}  brier: {p.get("brier_score")} -> {new_brier}')
        if not DRY_RUN:
            p['outcome'] = new_outcome
            p['brier_score'] = new_brier
        c7_fixed += 1
        brier_recalc += 1

if not DRY_RUN:
    with open(DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f'\n[SAVED] {DB}')

print(f'\n=== SUMMARY ===')
print(f'  C2 hit_miss fixed: {c2_fixed}')
print(f'  C7 outcome fixed:  {c7_fixed}')
print(f'  Brier recalculated: {brier_recalc}')
print(f'\nRun with --apply to execute' if DRY_RUN else 'Done.')
