#!/usr/bin/env python3
"""K3 Part 2: find_overdue_predictions() に oracle_deadline フォールバックを追加

9件の past-deadline resolving 予測は triggers[].date が非パース可能テキストのため
verifier に選ばれない。oracle_deadline フィールドで補完する。
"""
import sys, shutil, datetime

PATH = "/opt/shared/scripts/prediction_auto_verifier.py"

with open(PATH) as f:
    content = f.read()

# Already patched check
if "oracle_deadline fallback" in content:
    print("oracle_deadline fallback already applied. Nothing to do.")
    sys.exit(0)

# The original block to find and extend
OLD = """        if earliest_trigger:
            overdue.append({
                "prediction": pred,
                "trigger": earliest_trigger,
                "trigger_date": earliest_date,
            })

    return overdue"""

NEW = """        if earliest_trigger:
            overdue.append({
                "prediction": pred,
                "trigger": earliest_trigger,
                "trigger_date": earliest_date,
            })
        else:
            # oracle_deadline fallback: no parseable trigger, but oracle_deadline is past ISO date
            import re as _re
            dl = str(pred.get("oracle_deadline", ""))
            if _re.match(r'^\d{4}-\d{2}-\d{2}$', dl):
                from datetime import datetime as _dt
                dl_dt = _dt.fromisoformat(dl).replace(tzinfo=timezone.utc)
                if dl_dt < now:
                    overdue.append({
                        "prediction": pred,
                        "trigger": {"date": dl, "name": "oracle_deadline fallback"},
                        "trigger_date": dl_dt,
                    })

    return overdue"""

if OLD not in content:
    print(f"ERROR: target block not found in {PATH}")
    # Show what's around the area
    idx = content.find("if earliest_trigger:")
    if idx >= 0:
        print(repr(content[idx:idx+300]))
    sys.exit(1)

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(PATH, f"{PATH}.bak_k3p2_{ts}")
content = content.replace(OLD, NEW, 1)
with open(PATH, "w") as f:
    f.write(content)
print(f"Patched: {PATH}")
print("Added: oracle_deadline fallback to find_overdue_predictions()")
print(f"Backup: {PATH}.bak_k3p2_{ts}")
