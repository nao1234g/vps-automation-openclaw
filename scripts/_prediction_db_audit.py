#!/usr/bin/env python3
"""prediction_db.json quality audit."""
import json
from collections import Counter, defaultdict

DB = '/opt/shared/scripts/prediction_db.json'
db = json.load(open(DB, encoding='utf-8'))
preds = db['predictions']

total = len(preds)
open_p = [p for p in preds if p.get('status') == 'open']
resolved = [p for p in preds if p.get('brier_score') is not None]
print(f"Total: {total}  Open: {len(open_p)}  Resolved: {len(resolved)}")
print()

issues = defaultdict(list)

# Check 1: missing ghost_url
no_ghost = [p for p in preds if not p.get('ghost_url')]
print(f"[C1] Missing ghost_url: {len(no_ghost)}")
for p in no_ghost[:10]:
    print(f"  {p.get('prediction_id','?')}: {p.get('title','')[:50]}")
print()

# Check 2: hit_miss normalization
hm_vals = Counter(p.get('hit_miss') for p in resolved)
print(f"[C2] hit_miss values in resolved: {dict(hm_vals)}")
bad_hm = [p for p in resolved if p.get('hit_miss') not in ('correct', 'wrong', None)]
print(f"  Non-standard hit_miss values: {len(bad_hm)}")
for p in bad_hm[:5]:
    print(f"  {p.get('prediction_id','?')}: hit_miss={p.get('hit_miss')} pick={p.get('our_pick')} outcome={p.get('outcome')}")
print()

# Check 3: brier_score outliers / wrong calculation
print("[C3] Brier score outlier check:")
hi_brier = [p for p in resolved if p.get('brier_score',0) > 0.5]
print(f"  Predictions with Brier > 0.5 (bad): {len(hi_brier)}")
for p in hi_brier:
    print(f"  {p.get('prediction_id','?')}: pick={p.get('our_pick')} prob={p.get('our_pick_prob')}% outcome={p.get('outcome')} brier={p.get('brier_score'):.4f}")
print()

# Check 4: open predictions missing key fields
print("[C4] Open predictions field completeness:")
fields = ['title', 'our_pick', 'our_pick_prob', 'resolution_question', 'triggers', 'hit_condition']
for f in fields:
    missing = [p for p in open_p if not p.get(f)]
    if missing:
        print(f"  Missing {f}: {len(missing)} predictions")
        for p in missing[:3]:
            print(f"    {p.get('prediction_id','?')}: {p.get('title','')[:40]}")
print()

# Check 5: ghost_url pattern
ghost_urls = [p.get('ghost_url','') for p in preds if p.get('ghost_url')]
bad_urls = [u for u in ghost_urls if 'nowpattern.com' not in u]
print(f"[C5] ghost_url with bad domain: {len(bad_urls)}")
for u in bad_urls[:5]:
    print(f"  {u}")
print()

# Check 6: prediction_id uniqueness
ids = [p.get('prediction_id') for p in preds]
dup_ids = [id_ for id_, cnt in Counter(ids).items() if cnt > 1 and id_]
print(f"[C6] Duplicate prediction_ids: {len(dup_ids)}")
for d in dup_ids[:5]:
    print(f"  {d}")
print()

# Check 7: outcome field in resolved (should be YES/NO for binary)
print("[C7] Outcome values in resolved:")
outcome_vals = Counter(str(p.get('outcome','')).strip() for p in resolved)
print(f"  {dict(outcome_vals)}")
non_binary = [p for p in resolved if str(p.get('outcome','')).upper().strip() not in ('YES','NO')]
print(f"  Non-binary outcomes: {len(non_binary)}")
for p in non_binary[:5]:
    print(f"  {p.get('prediction_id','?')}: outcome={p.get('outcome')} pick={p.get('our_pick')}")
print()

# Summary
print("=== QUALITY SUMMARY ===")
print(f"  C1 Missing ghost_url: {len(no_ghost)}")
print(f"  C2 Non-standard hit_miss: {len(bad_hm)}")
print(f"  C3 Brier > 0.5: {len(hi_brier)}")
print(f"  C4 Open pred missing fields: (see above)")
print(f"  C5 Bad ghost_url domain: {len(bad_urls)}")
print(f"  C6 Duplicate IDs: {len(dup_ids)}")
print(f"  C7 Non-binary outcomes: {len(non_binary)}")
