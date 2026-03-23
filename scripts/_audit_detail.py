#!/usr/bin/env python3
"""Deep dive into C7 non-binary outcomes and C4 no-title predictions."""
import json
from collections import Counter

DB = '/opt/shared/scripts/prediction_db.json'
db = json.load(open(DB, encoding='utf-8'))
preds = db['predictions']

# C7: Non-binary outcomes detail
print('=== C7 NON-BINARY OUTCOMES (full detail) ===')
resolved = [p for p in preds if p.get('brier_score') is not None]
non_binary = [p for p in resolved if str(p.get('outcome','')).upper().strip() not in ('YES','NO')]
print(f'Total non-binary: {len(non_binary)}')
for p in non_binary:
    pid = p.get('prediction_id', '?')
    print(f"\n{pid}: pick={p.get('our_pick')} prob={p.get('our_pick_prob')} outcome={p.get('outcome')} hit_miss={p.get('hit_miss')} brier={p.get('brier_score')}")
    print(f"  title: {p.get('title','')[:70]}")
    # Check if outcome maps to a scenario
    o = str(p.get('outcome','')).strip()
    pk = str(p.get('our_pick','')).strip()
    # Determine correct YES/NO mapping
    # Old format: our_pick was scenario name (楽観/基本/悲観)
    # New format: our_pick is YES/NO
    print(f"  our_pick_scenario: {p.get('our_pick_scenario','none')}")
    print(f"  resolution_question: {p.get('resolution_question','')[:60]}")

print()
print('=== C4 NO-TITLE PREDICTIONS ===')
no_title = [p for p in preds if not p.get('title')]
print(f'Total no-title: {len(no_title)}')
for p in no_title[:5]:
    pid = p.get('prediction_id', '?')
    print(f"\n{pid}: status={p.get('status')} our_pick={p.get('our_pick')} brier={p.get('brier_score')}")
    print(f"  Keys present: {[k for k,v in p.items() if v]}")
    # Show any data that IS present
    for k in ['resolution_question', 'ghost_url', 'triggers']:
        v = p.get(k)
        if v:
            print(f"  {k}: {str(v)[:60]}")

print()
print('=== C1 MISSING GHOST_URL: FIRST 11 IDS ===')
no_ghost = [p for p in preds if not p.get('ghost_url')]
for p in no_ghost:
    print(f"  {p.get('prediction_id','?')}: {p.get('title','')[:50]}")
