#!/usr/bin/env python3
"""
Fix binary Brier score calculation bug in prediction_auto_verifier.py
and recalculate ALL affected predictions in prediction_db.json.

BUG:  _actual = 1.0 if outcome == our_pick else 0.0
FIX:  _actual = 1.0 if outcome == "YES" else 0.0

Affected cases (binary NO predictions only — scenarios use different formula):
  Case A: our_pick=NO, outcome=NO (CORRECT) → old _actual=1.0, new _actual=0.0
          brier: (prob-1)^2 ≈ 0.88  →  (prob-0)^2 ≈ 0.004  [MASSIVE improvement]
  Case B: our_pick=NO, outcome=YES (WRONG)  → old _actual=0.0, new _actual=1.0
          brier: (prob-0)^2 ≈ 0.004  →  (prob-1)^2 ≈ 0.88   [corrects hidden failures]
"""
import json, os, copy

VERIFIER = '/opt/shared/scripts/prediction_auto_verifier.py'
DB       = '/opt/shared/scripts/prediction_db.json'

# === PART 1: Fix prediction_auto_verifier.py ===
OLD_FORMULA = '_actual = 1.0 if str(judgment["outcome"]).upper() == str(pred.get("our_pick", "")).upper() else 0.0'
NEW_FORMULA = '_actual = 1.0 if str(judgment["outcome"]).upper() == "YES" else 0.0  # FIXED 2026-03-22: use actual YES/NO, not our_pick match'

print("=== PART 1: prediction_auto_verifier.py ===")
with open(VERIFIER, encoding='utf-8') as f:
    verifier_src = f.read()

if OLD_FORMULA in verifier_src:
    verifier_src = verifier_src.replace(OLD_FORMULA, NEW_FORMULA)
    with open(VERIFIER, 'w', encoding='utf-8') as f:
        f.write(verifier_src)
    print("  [FIXED] binary Brier formula patched in prediction_auto_verifier.py")
elif NEW_FORMULA in verifier_src:
    print("  [SKIP] already fixed (new formula present)")
else:
    # Try to find the line with a more flexible search
    import re
    pattern = r'_actual\s*=\s*1\.0\s+if\s+str\(judgment\[.outcome.\]\)\.upper\(\)\s*==\s*str\(pred\.get\(.our_pick'
    if re.search(pattern, verifier_src):
        print("  [WARN] formula found but different format — manual check needed")
    else:
        print("  [ERROR] formula marker NOT FOUND in prediction_auto_verifier.py")
        print("  Searching for 'our_pick' near 'brier'...")
        for i, line in enumerate(verifier_src.split('\n')):
            if 'our_pick' in line and '_actual' in line:
                print(f"    Line {i+1}: {line.strip()}")

# === PART 2: Recalculate affected predictions ===
print("\n=== PART 2: prediction_db.json recalculation ===")

with open(DB, encoding='utf-8') as f:
    db = json.load(f)

predictions = db.get('predictions', [])

# Compute old average before changes
old_briers_all = [p['brier_score'] for p in predictions if p.get('brier_score') is not None]
old_avg = sum(old_briers_all) / len(old_briers_all) if old_briers_all else 0.0

case_a_changed = []  # NO pick, NO outcome (correct) — brier goes DOWN
case_b_changed = []  # NO pick, YES outcome (wrong)   — brier goes UP
skipped_no_brier    = 0
skipped_scenarios   = 0
skipped_not_no      = 0
warnings            = []

for pred in predictions:
    our_pick = str(pred.get('our_pick', '')).upper().strip()
    outcome  = str(pred.get('outcome',   '')).upper().strip()

    if our_pick != 'NO':
        skipped_not_no += 1
        continue

    if pred.get('brier_score') is None:
        skipped_no_brier += 1
        continue

    # Scenario-based predictions use a different multi-class formula — NOT affected
    if pred.get('scenarios') and len(pred['scenarios']) > 0:
        skipped_scenarios += 1
        continue

    pid        = pred.get('prediction_id', '?')
    prob_pct   = pred.get('our_pick_prob') or 0
    _prob      = float(prob_pct) / 100.0
    old_brier  = pred['brier_score']

    if outcome == 'NO':
        # Case A: correct NO prediction, formula gave _actual=1.0 (wrong)
        expected_old = round((_prob - 1.0) ** 2, 4)
        new_brier    = round(_prob ** 2, 4)

        if abs(old_brier - expected_old) < 0.02:  # tolerance for float rounding
            pred['brier_score'] = new_brier
            case_a_changed.append({
                'id': pid, 'prob%': prob_pct, 'outcome': 'NO',
                'old': old_brier, 'new': new_brier,
                'delta': round(new_brier - old_brier, 4)
            })
        else:
            warnings.append(f"  [WARN] {pid}: our_pick=NO outcome=NO prob={prob_pct}% old_brier={old_brier} (expected {expected_old} from bug formula) — SKIP")

    elif outcome == 'YES':
        # Case B: wrong NO prediction, formula gave _actual=0.0 (wrong)
        expected_old = round(_prob ** 2, 4)
        new_brier    = round((_prob - 1.0) ** 2, 4)

        if abs(old_brier - expected_old) < 0.02:
            pred['brier_score'] = new_brier
            case_b_changed.append({
                'id': pid, 'prob%': prob_pct, 'outcome': 'YES',
                'old': old_brier, 'new': new_brier,
                'delta': round(new_brier - old_brier, 4)
            })
        else:
            warnings.append(f"  [WARN] {pid}: our_pick=NO outcome=YES prob={prob_pct}% old_brier={old_brier} (expected {expected_old} from bug formula) — SKIP")

all_changed = case_a_changed + case_b_changed
if all_changed:
    with open(DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"  [SAVED] prediction_db.json updated ({len(all_changed)} predictions changed)")
else:
    print("  [SKIP] no predictions needed updating")

# === PART 3: Report ===
print("\n=== CASE A: Correct NO picks (brier goes DOWN) ===")
for c in sorted(case_a_changed, key=lambda x: x['delta']):
    print(f"  {c['id']}: prob={c['prob%']}%  {c['old']:.4f} → {c['new']:.4f}  ({c['delta']:+.4f})")

print(f"\n=== CASE B: Wrong NO picks (brier goes UP) ===")
for c in sorted(case_b_changed, key=lambda x: -x['delta']):
    print(f"  {c['id']}: prob={c['prob%']}%  {c['old']:.4f} → {c['new']:.4f}  ({c['delta']:+.4f})")

if warnings:
    print("\n=== WARNINGS ===")
    for w in warnings:
        print(w)

print(f"\n=== SUMMARY ===")
print(f"  Total resolved predictions:     {len(old_briers_all)}")
print(f"  Case A (correct NO, fixed↓):    {len(case_a_changed)}")
print(f"  Case B (wrong NO, fixed↑):      {len(case_b_changed)}")
print(f"  Skipped (YES pick):             {skipped_not_no}")
print(f"  Skipped (no brier yet):         {skipped_no_brier}")
print(f"  Skipped (has scenarios):        {skipped_scenarios}")

# Recompute new average
new_briers_all = [p['brier_score'] for p in predictions if p.get('brier_score') is not None]
new_avg = sum(new_briers_all) / len(new_briers_all) if new_briers_all else 0.0

print(f"\n  OLD avg Brier: {old_avg:.4f}")
print(f"  NEW avg Brier: {new_avg:.4f}")
print(f"  Improvement:   {old_avg - new_avg:.4f}  ({(old_avg-new_avg)/old_avg*100:.1f}%)")

# Breakdown by pick
yes_briers = [p['brier_score'] for p in predictions if p.get('brier_score') is not None and str(p.get('our_pick','')).upper()=='YES']
no_briers  = [p['brier_score'] for p in predictions if p.get('brier_score') is not None and str(p.get('our_pick','')).upper()=='NO']
print(f"\n  YES picks ({len(yes_briers)}): avg Brier = {sum(yes_briers)/len(yes_briers):.4f}" if yes_briers else "  YES picks: none")
print(f"  NO  picks ({len(no_briers)}):  avg Brier = {sum(no_briers)/len(no_briers):.4f}" if no_briers else "  NO picks: none")
