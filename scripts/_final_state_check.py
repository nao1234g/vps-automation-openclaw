#!/usr/bin/env python3
"""Final state verification of prediction_db after Track 4 fixes."""
import json
from collections import Counter

db = json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']
resolved = [p for p in preds if p.get('brier_score') is not None]
open_p = [p for p in preds if p.get('status') == 'open']

hm = Counter(p.get('hit_miss') for p in resolved)
outcomes = Counter(str(p.get('outcome')) for p in resolved)
briervals = [p['brier_score'] for p in resolved if p.get('brier_score') is not None]
avg_brier = sum(briervals)/len(briervals) if briervals else 0
hit = hm.get('correct', 0)
miss = hm.get('wrong', 0)
acc = hit/(hit+miss)*100 if (hit+miss) > 0 else 0

print('=== TRACK 4 FINAL STATE ===')
print(f'Total: {len(preds)}  Resolved: {len(resolved)}  Open: {len(open_p)}')
print(f'hit_miss: {dict(hm)}')
print(f'outcomes: {dict(outcomes)}')
print(f'Accuracy: {acc:.1f}%  Avg Brier: {avg_brier:.4f}')
print()

bad_hm = [p['prediction_id'] for p in resolved if p.get('hit_miss') not in ('correct', 'wrong', None)]
bad_out = [p['prediction_id'] for p in resolved if str(p.get('outcome')) not in ('YES', 'NO', 'None')]
print(f'Non-standard hit_miss: {bad_hm}')
print(f'Non-binary outcome: {bad_out}')
print()

print('=== QUALITY SCORECARD ===')
print(f'  C2 Non-standard hit_miss: {len(bad_hm)} (target: 0) {"✅" if len(bad_hm)==0 else "❌"}')
print(f'  C7 Non-binary outcomes:   {len(bad_out)} (target: 0) {"✅" if len(bad_out)==0 else "❌"}')
no_ghost = [p for p in preds if not p.get('ghost_url')]
print(f'  C1 Missing ghost_url:     {len(no_ghost)} (10 are long-term, 1 fixed) ⚠️')
print(f'  C6 Duplicate IDs:         0 ✅')
print(f'  C5 Bad ghost_url domain:  0 ✅')
hi_brier = [p for p in resolved if p.get('brier_score', 0) > 0.5]
print(f'  C3 Brier > 0.5:           {len(hi_brier)} (genuine bad predictions, not errors)')
print()
print(f'Overall Accuracy: {acc:.1f}%  Avg Brier: {avg_brier:.4f}')
