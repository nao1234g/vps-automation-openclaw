#!/usr/bin/env python3
"""Post-fix state check: Brier stats + calibration rules + 4-disconnection status"""
import json

# Load prediction_db
db = json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']

# Stats
resolved = [p for p in preds if p.get('brier_score') is not None]
open_p   = [p for p in preds if p.get('status') == 'open']
total    = len(preds)

yes_p = [p for p in resolved if str(p.get('our_pick','')).upper()=='YES']
no_p  = [p for p in resolved if str(p.get('our_pick','')).upper()=='NO']
hit   = [p for p in resolved if p.get('hit_miss')=='correct']
miss  = [p for p in resolved if p.get('hit_miss')=='wrong']

avg_brier = sum(p['brier_score'] for p in resolved) / len(resolved) if resolved else 0
yes_avg   = sum(p['brier_score'] for p in yes_p) / len(yes_p) if yes_p else 0
no_avg    = sum(p['brier_score'] for p in no_p)  / len(no_p)  if no_p  else 0

print("=== PREDICTION DB STATE (after Brier fix) ===")
print("  Total: %d  Open: %d  Resolved: %d" % (total, len(open_p), len(resolved)))
print("  YES picks: %d  NO picks: %d" % (len(yes_p), len(no_p)))
print("  Hit: %d  Miss: %d  Accuracy: %.1f%%" % (len(hit), len(miss), len(hit)/len(resolved)*100 if resolved else 0))
print("  Avg Brier: %.4f  (YES: %.4f  NO: %.4f)" % (avg_brier, yes_avg, no_avg))
print()

# Worst predictions remaining
print("=== TOP 5 WORST PREDICTIONS (after fix) ===")
for p in sorted(resolved, key=lambda x: -x['brier_score'])[:5]:
    print("  %s: pick=%s prob=%s%% outcome=%s hit=%s brier=%.4f" % (
        p.get('prediction_id','?'), p.get('our_pick','?'), p.get('our_pick_prob','?'),
        p.get('outcome','?'), p.get('hit_miss','?'), p['brier_score']
    ))
print()

# Best predictions
print("=== TOP 5 BEST PREDICTIONS ===")
for p in sorted(resolved, key=lambda x: x['brier_score'])[:5]:
    print("  %s: pick=%s prob=%s%% outcome=%s hit=%s brier=%.4f" % (
        p.get('prediction_id','?'), p.get('our_pick','?'), p.get('our_pick_prob','?'),
        p.get('outcome','?'), p.get('hit_miss','?'), p['brier_score']
    ))
print()

# Calibration rules
print("=== CALIBRATION RULES ===")
cal = json.load(open('/opt/shared/data/calibration_rules.json'))
for r in cal.get('rules', []):
    rid   = r.get('id','?')
    rname = r.get('name','?')
    bf    = r.get('blend_factor','')
    br    = r.get('base_rate','')
    fp    = r.get('floor_probability','')
    cap   = r.get('max_probability','')
    print("  %s [%s]: blend_factor=%s base_rate=%s floor=%s max=%s" % (rid, rname, bf, br, fp, cap))
print("  last_auto_update: %s" % cal.get('meta',{}).get('last_auto_update','N/A'))
print("  status: %s" % cal.get('meta',{}).get('status','N/A'))
print()

# Check 4 disconnections
import os, time
print("=== 4断絶 STATUS CHECK ===")

# A: ensemble cron
import subprocess
cron_out = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
has_ensemble_cron = 'run_ensemble_batch' in cron_out.stdout or 'prediction_ensemble' in cron_out.stdout
print("  断絶A (cron→ensemble):     %s" % ("WORKING" if has_ensemble_cron else "NOT FOUND in crontab"))

# B: evolution_loop calibration
log_path = '/opt/shared/logs/evolution_loop.log'
with open(log_path) as f:
    elog = f.read()
has_calib_log = '[calibration] write_success' in elog
print("  断絶B (evolution→calibration_rules): %s" % ("WORKING (write_success in log)" if has_calib_log else "NOT CONFIRMED"))

# C: genre_tags fix
try:
    import sys
    sys.path.insert(0, '/opt/shared/scripts')
    import prediction_ensemble as pe
    src = open('/opt/shared/scripts/prediction_ensemble.py').read()
    has_genre_fix = 'genre_tags' in src and 'strip()' in src
    print("  断絶C (genre_tags空文字補正): %s" % ("LIKELY FIXED (genre_tags + strip in code)" if has_genre_fix else "CHECK NEEDED"))
except Exception as e:
    print("  断絶C: could not verify — %s" % e)

# D: CR-002/CR-003 applied
src_e = open('/opt/shared/scripts/prediction_ensemble.py').read()
has_cr002 = 'CR-002' in src_e or 'floor_probability' in src_e
print("  断絶D (CR-002/CR-003 in ensemble): %s" % ("APPLIED" if has_cr002 else "NOT FOUND"))
