#!/usr/bin/env python3
"""
Oracle Guardian gate fix (pass 2):
Patch the MAIN row dict in build_rows() to include oracle fields.
The main row dict is identified by having:
  - "hit_condition_en": pred.get("hit_condition_en", ""),
  - followed by "polymarket": pm_match,
"""

FILEPATH = "/opt/shared/scripts/prediction_page_builder.py"

with open(FILEPATH, "r", encoding="utf-8") as f:
    src = f.read()

# Target the main row dict - uniquely identified by "polymarket" following hit_condition_en
# (the simplified row dict doesn't have "polymarket")
OLD = (
    '            "hit_condition_en": pred.get("hit_condition_en", ""),\n'
    '            "polymarket": pm_match,'
)
NEW = (
    '            "hit_condition_en": pred.get("hit_condition_en", ""),\n'
    '            "oracle_deadline":   pred.get("oracle_deadline", ""),\n'
    '            "oracle_criteria":   pred.get("oracle_criteria", ""),\n'
    '            "oracle_question":   pred.get("oracle_question", ""),\n'
    '            "oracle_premortem":  pred.get("oracle_premortem", ""),\n'
    '            "polymarket": pm_match,'
)

if OLD not in src:
    # Try alternative spacing
    OLD_ALT = (
        '            "hit_condition_en": pred.get("hit_condition_en", ""),\n'
        '            "polymarket":'
    )
    if OLD_ALT not in src:
        print("ERROR: target pattern not found — checking manually")
        # Find context
        idx = src.find('"hit_condition_en": pred.get("hit_condition_en", ""),')
        if idx != -1:
            print(f"Found hit_condition_en at char {idx}")
            print("Context after:")
            print(repr(src[idx:idx+200]))
        raise SystemExit(1)
    else:
        print("Found alt pattern")
        OLD = OLD_ALT
        NEW = (
            '            "hit_condition_en": pred.get("hit_condition_en", ""),\n'
            '            "oracle_deadline":   pred.get("oracle_deadline", ""),\n'
            '            "oracle_criteria":   pred.get("oracle_criteria", ""),\n'
            '            "oracle_question":   pred.get("oracle_question", ""),\n'
            '            "oracle_premortem":  pred.get("oracle_premortem", ""),\n'
            '            "polymarket":'
        )

# Check if already patched
if '"oracle_deadline":   pred.get("oracle_deadline", ""),\n            "polymarket"' in src:
    print("SKIP: main row dict already patched")
    raise SystemExit(0)

count = src.count(OLD)
print(f"Found target pattern {count} time(s)")

patched = src.replace(OLD, NEW, 1)

with open(FILEPATH, "w", encoding="utf-8") as f:
    f.write(patched)

print("PATCHED: oracle fields added to main row dict")

# Verify
with open(FILEPATH, "r", encoding="utf-8") as f:
    verify = f.read()

# Count oracle_deadline occurrences in row dict context
import re
matches = re.findall(r'"oracle_deadline":\s+pred\.get', verify)
print(f"oracle_deadline in pred.get() form: {len(matches)} occurrences")

# Show context
idx = verify.find('"oracle_deadline":   pred.get("oracle_deadline", ""),\n            "polymarket"')
if idx == -1:
    idx = verify.find('"oracle_deadline":   pred.get("oracle_deadline", "")')
if idx != -1:
    print("Context around patch:")
    # Find start of context
    start = max(0, idx - 100)
    print(repr(verify[start:idx+150]))
    print("VERIFIED OK")
else:
    print("WARNING: could not verify patch location")
