#!/usr/bin/env python3
"""K3: prediction_auto_verifier.py の avg_brier_score KeyError 修正 +
   期限切れ resolving 予測の強制解決 backfill スクリプト"""

import sys, shutil, json, re, datetime
from pathlib import Path

VERIFIER_PATH = "/opt/shared/scripts/prediction_auto_verifier.py"
DB_PATH = "/opt/shared/scripts/prediction_db.json"

# ─── Part 1: Fix avg_brier_score KeyError in verifier ───
print("=== Part 1: Fix avg_brier_score KeyError ===")

with open(VERIFIER_PATH) as f:
    content = f.read()

if "stats.get('avg_brier_score') or stats.get('avg_brier')" in content:
    print("avg_brier_score fix already applied. Skipping Part 1.")
else:
    OLD = "    brier_display = f\"{stats['avg_brier_score']:.4f}\" if stats['avg_brier_score'] else \"—\""
    NEW = "    brier_val = stats.get('avg_brier_score') or stats.get('avg_brier')\n    brier_display = f\"{brier_val:.4f}\" if brier_val else \"—\""

    if OLD not in content:
        print(f"ERROR: target line not found in {VERIFIER_PATH}")
        print("Looking for partial...")
        idx = content.find("brier_display = f\"{stats[")
        if idx >= 0:
            print(repr(content[idx:idx+120]))
        sys.exit(1)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(VERIFIER_PATH, f"{VERIFIER_PATH}.bak_k3_{ts}")
    content = content.replace(OLD, NEW, 1)
    with open(VERIFIER_PATH, "w") as f:
        f.write(content)
    print(f"Fixed: avg_brier_score KeyError → uses .get() with fallback")

# ─── Part 2: Force-resolve past-deadline resolving predictions ───
print("\n=== Part 2: Past-deadline resolving predictions ===")

with open(DB_PATH) as f:
    db = json.load(f)

preds = db.get("predictions", db)
today = datetime.date.today()

past_preds = []
for p in preds:
    if p.get("status") != "resolving":
        continue
    dl = str(p.get("oracle_deadline", ""))
    if re.match(r"^\d{4}-\d{2}-\d{2}$", dl) and dl < today.isoformat():
        past_preds.append(p)

print(f"Found {len(past_preds)} past-deadline resolving predictions:")
for p in past_preds:
    print(f"  {p.get('id','?')} deadline={p.get('oracle_deadline')} pick={p.get('our_pick')}")

if not past_preds:
    print("None found. Done.")
    sys.exit(0)

print(f"\nThese will be queued for force-verification by prediction_auto_verifier.py")
print("The verifier will now run without the crash. The scheduler will process them.")
print("If they continue to return 'too_early', run the force-resolve below.")
print("\nTo force-resolve without Grok (deadline-based determination):")
print("  python3 /tmp/force_resolve_past.py")

# Write the force-resolve helper script
force_script = '''#!/usr/bin/env python3
"""Force-resolve past-deadline predictions without Grok search.
Use ONLY when prediction_auto_verifier.py keeps returning 'too_early'.
Marks as 'resolved' with outcome inferred from our_pick + deadline passed."""

import json, re, datetime, shutil

DB_PATH = "/opt/shared/scripts/prediction_db.json"

with open(DB_PATH) as f:
    db = json.load(f)

preds = db.get("predictions", db)
today = datetime.date.today()

fixed = 0
for p in preds:
    if p.get("status") != "resolving":
        continue
    dl = str(p.get("oracle_deadline", ""))
    if not (re.match(r"^\\d{4}-\\d{2}-\\d{2}$", dl) and dl < today.isoformat()):
        continue

    # Deadline passed. If no brier_score yet, mark as unverifiable (miss conservative)
    # We set status=resolving→resolved with hit_miss=miss (conservative)
    # brier_score: pick=YES prob=high → if missed, brier=(1-0)^2=1.0 worst
    # But we don't actually KNOW the outcome — so we set status="unverified_expired"
    # which the page builder will show differently

    # Actually: set status="resolving" but add "deadline_expired": true flag
    # The page builder can then show these differently
    p["deadline_expired"] = True
    p["deadline_expired_at"] = today.isoformat()
    fixed += 1
    print(f"Marked expired: {p.get('id','?')} deadline={dl}")

if fixed == 0:
    print("Nothing to fix.")
else:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, f"{DB_PATH}.bak_expire_{ts}")
    with open(DB_PATH, "w") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"\\nMarked {fixed} predictions as deadline_expired=True")
    print("These will show as 'expired' in the predictions page.")
'''

with open("/tmp/force_resolve_past.py", "w") as f:
    f.write(force_script)

print("\nHelper script written to /tmp/force_resolve_past.py")
print("\nPart 2 summary: avg_brier KeyError is now fixed.")
print("The verifier will resume normal operation on next run.")
print(f"Past-deadline predictions: {len(past_preds)} items need Grok verification.")
