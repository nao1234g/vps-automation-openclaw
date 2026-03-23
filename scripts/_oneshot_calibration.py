#!/usr/bin/env python3
"""
One-shot test: evolution_loop.update_calibration_rules()
Simulates exactly what main() does, using real resolved predictions.
Logs to evolution_loop.log via the same logger.
"""
import sys, os, json, time

sys.path.insert(0, '/opt/shared/scripts')

# Import evolution_loop (this sets up the logger to write to evolution_loop.log)
import evolution_loop as el

print("[one-shot] Starting calibration one-shot test")
print("[one-shot] LOG FILE: /opt/shared/logs/evolution_loop.log")

# Load all predictions (same as main())
db = json.load(open('/opt/shared/scripts/prediction_db.json', encoding='utf-8'))
predictions = db.get('predictions', [])
resolved = [p for p in predictions if p.get('brier_score') is not None]

print("[one-shot] total=%d resolved=%d" % (len(predictions), len(resolved)))

# Record before mtime
mtime_before = os.path.getmtime('/opt/shared/data/calibration_rules.json')
with open('/opt/shared/data/calibration_rules.json') as f:
    before = json.load(f)
bf_before = next((r.get('blend_factor') for r in before.get('rules', []) if r['id']=='CR-001'), None)
f2_before = next((r.get('floor_probability') for r in before.get('rules', []) if r['id']=='CR-002'), None)
f3_before = next((r.get('floor_probability') for r in before.get('rules', []) if r['id']=='CR-003'), None)
print("[one-shot] BEFORE: CR-001 bf=%s CR-002 f=%s CR-003 f=%s" % (bf_before, f2_before, f3_before))
print("[one-shot] BEFORE mtime: %s" % time.ctime(mtime_before))

# Actually call the function (writes to evolution_loop.log)
result = el.update_calibration_rules(resolved)
print("[one-shot] return_value=%s" % result)

# Record after mtime
mtime_after = os.path.getmtime('/opt/shared/data/calibration_rules.json')
with open('/opt/shared/data/calibration_rules.json') as f:
    after = json.load(f)
bf_after = next((r.get('blend_factor') for r in after.get('rules', []) if r['id']=='CR-001'), None)
f2_after = next((r.get('floor_probability') for r in after.get('rules', []) if r['id']=='CR-002'), None)
f3_after = next((r.get('floor_probability') for r in after.get('rules', []) if r['id']=='CR-003'), None)
last_update = after.get('meta', {}).get('last_auto_update', '')
print("[one-shot] AFTER:  CR-001 bf=%s CR-002 f=%s CR-003 f=%s" % (bf_after, f2_after, f3_after))
print("[one-shot] AFTER mtime: %s" % time.ctime(mtime_after))
print("[one-shot] AFTER last_auto_update: %s" % last_update)

print()
print("=== DIFF ===")
if bf_before != bf_after:
    print("CR-001 blend_factor: %s -> %s  CHANGED" % (bf_before, bf_after))
else:
    print("CR-001 blend_factor: %s -> %s  unchanged" % (bf_before, bf_after))
if f2_before != f2_after:
    print("CR-002 floor:        %s -> %s  CHANGED" % (f2_before, f2_after))
else:
    print("CR-002 floor:        %s -> %s  unchanged" % (f2_before, f2_after))
if f3_before != f3_after:
    print("CR-003 floor:        %s -> %s  CHANGED" % (f3_before, f3_after))
else:
    print("CR-003 floor:        %s -> %s  unchanged" % (f3_before, f3_after))
mtime_changed = mtime_after > mtime_before
print("mtime changed: %s" % mtime_changed)

print()
print("=== LAST 20 LINES OF evolution_loop.log (calibration entries) ===")
import subprocess
result2 = subprocess.run(
    ['grep', '-n', r'\[calibration\]', '/opt/shared/logs/evolution_loop.log'],
    capture_output=True, text=True
)
lines = result2.stdout.strip().split('\n')
for line in lines[-20:]:
    print(line)
