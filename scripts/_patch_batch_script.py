#!/usr/bin/env python3
"""Patch run_ensemble_batch.sh to add stats call"""

target = '/opt/shared/scripts/run_ensemble_batch.sh'

with open(target) as f:
    content = f.read()

marker = 'log "=== ensemble_batch DONE:'
stats_line = 'python3 /opt/shared/scripts/ensemble_batch_stats.py "$LOG_FILE" | tee -a "$LOG_FILE"\n'

if stats_line in content:
    print('already present, no change needed')
elif marker not in content:
    print('ERROR: marker not found in script')
else:
    content = content.replace(marker, stats_line + marker)
    with open(target, 'w') as f:
        f.write(content)
    print('OK: stats call inserted before DONE log')
