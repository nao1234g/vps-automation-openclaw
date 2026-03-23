#!/usr/bin/env python3
"""ensemble_batch_stats.py - called at end of run_ensemble_batch.sh to show statistics"""
import sys, re

LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "/opt/shared/logs/ensemble_batch.log"

try:
    with open(LOG_FILE) as f:
        lines = f.readlines()
except Exception as e:
    sys.stderr.write("  [stats] log read error: %s\n" % e)
    sys.exit(0)

recent = lines[-600:]

# Parse DB updates (deduplicated by prediction_id)
db_pattern = re.compile(r'\[DB.{0,10}\]\s+(NP-\d+-\d+):\s+(\d+)%\s+->\s+(\d+)%')
updates = []
seen = set()
for line in recent:
    m = db_pattern.search(line)
    if m:
        pid, b, a = m.group(1), int(m.group(2)), int(m.group(3))
        if pid not in seen:
            seen.add(pid)
            updates.append((pid, b, a))

if not updates:
    sys.stdout.write("  [BATCH_STATS] no DB update entries found\n")
    sys.stdout.flush()
    sys.exit(0)

# Count calibration rule applications (Extremizing != Calibration in same line)
calib_applied = 0
for line in recent:
    ext_m = re.search(r'Extremizing\S+:\s+(\d+)%', line)
    cal_m = re.search(r'Calibration\S+:\s+(\d+)%', line)
    if ext_m and cal_m and ext_m.group(1) != cal_m.group(1):
        calib_applied += 1

changed = [(pid, b, a, a - b) for pid, b, a in updates if b != a]
unchanged = [pid for pid, b, a in updates if b == a]

sys.stdout.write("  [BATCH_STATS] processed=%d changed=%d unchanged=%d calib_applied=%d\n" % (
    len(updates), len(changed), len(unchanged), calib_applied))

if changed:
    deltas = [abs(d) for _, _, _, d in changed]
    avg_delta = sum(deltas) / len(deltas)
    top = sorted(changed, key=lambda x: abs(x[3]), reverse=True)[:5]
    sys.stdout.write("  [BATCH_STATS] avg_delta=%.1fpp\n" % avg_delta)
    for pid, b, a, d in top:
        sign = "+" if d > 0 else ""
        sys.stdout.write("    %s: %d%% -> %d%% (%s%dpp)\n" % (pid, b, a, sign, d))
sys.stdout.flush()
