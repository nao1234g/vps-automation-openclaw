#!/usr/bin/env python3
"""
Oracle Guardian gate fix:
Add oracle_deadline / oracle_criteria / oracle_question / oracle_premortem
to the row dict built in build_rows() so _validate_tracker_card() can use them.
"""
import re

FILEPATH = "/opt/shared/scripts/prediction_page_builder.py"

with open(FILEPATH, "r", encoding="utf-8") as f:
    src = f.read()

# Target the exact line just after hit_condition_en in the row dict
OLD = '            "hit_condition_en": pred.get("hit_condition_en", ""),'
NEW = (
    '            "hit_condition_en": pred.get("hit_condition_en", ""),\n'
    '            "oracle_deadline":   pred.get("oracle_deadline", ""),\n'
    '            "oracle_criteria":   pred.get("oracle_criteria", ""),\n'
    '            "oracle_question":   pred.get("oracle_question", ""),\n'
    '            "oracle_premortem":  pred.get("oracle_premortem", ""),'
)

if OLD not in src:
    print("ERROR: target line not found — check the file manually")
    raise SystemExit(1)

count = src.count(OLD)
if count > 1:
    print(f"WARNING: target line found {count} times — patching all occurrences")

patched = src.replace(OLD, NEW, 1)

# Verify idempotency guard
if "oracle_deadline" in src:
    print("INFO: oracle_deadline already present — checking if already patched")
    if '"oracle_deadline":   pred.get("oracle_deadline", ""),' in src:
        print("SKIP: already patched, nothing to do")
        raise SystemExit(0)

with open(FILEPATH, "w", encoding="utf-8") as f:
    f.write(patched)

print(f"PATCHED: oracle fields added to row dict ({count} location(s))")

# Quick sanity check
with open(FILEPATH, "r", encoding="utf-8") as f:
    verify = f.read()

assert '"oracle_deadline":   pred.get("oracle_deadline", ""),' in verify, "Patch verification failed!"
print("VERIFIED: oracle_deadline present in patched file")
