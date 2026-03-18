#!/usr/bin/env python3
"""K2: prediction_page_builder.py の Brier Score セクションに世界水準ベンチマーク比較を追加"""
import sys, shutil
from datetime import datetime

PATH = "/opt/shared/scripts/prediction_page_builder.py"

with open(PATH) as f:
    content = f.read()

# Already patched check
if "bench_super" in content:
    print("Already patched. Nothing to do.")
    sys.exit(0)

# --- Patch 1: JA branch — add bench labels ---
OLD1 = '        brier_note_bad = "（改善余地あり）"\n        # Comparison bar removed — market accuracy reference not needed\n    else:'
NEW1 = '        brier_note_bad = "（改善余地あり）"\n        bench_super = "スーパー予測者"\n        bench_gjo = "一般予測者"\n        # Comparison bar removed — market accuracy reference not needed\n    else:'

if OLD1 not in content:
    print(f"ERROR: JA label target not found")
    sys.exit(1)
content = content.replace(OLD1, NEW1, 1)

# --- Patch 2: EN branch — add bench labels ---
OLD2 = '        brier_note_bad = "(room for improvement)"\n        # Comparison bar removed — market accuracy reference not needed'
NEW2 = '        brier_note_bad = "(room for improvement)"\n        bench_super = "Superforecaster"\n        bench_gjo = "GJO avg"\n        # Comparison bar removed — market accuracy reference not needed'

if OLD2 not in content:
    print(f"ERROR: EN label target not found")
    sys.exit(1)
content = content.replace(OLD2, NEW2, 1)

# --- Patch 3: Replace Brier div section ---
OLD3 = (
    '                \'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #eee;\'\n'
    '                \'display:flex;align-items:center;gap:8px">\'\n'
    '                f\'<span style="font-size:0.75em;color:#888;letter-spacing:.06em;text-transform:uppercase">\'\n'
    '                f\'{brier_label}</span>\'\n'
    '                f\'<strong style="font-size:1.4em;font-weight:700;color:\'\n'
    '                + ("#16a34a" if mean_brier < 0.15 else ("#f59e0b" if mean_brier < 0.25 else "#dc2626"))\n'
    '                + f\'\">{mean_brier:.3f}</strong>\'\n'
    '                f\'<span style="font-size:0.78em;color:#aaa">\'\n'
    '                + (brier_note_good if mean_brier < 0.15 else (brier_note_ok if mean_brier < 0.25 else brier_note_bad))\n'
    '                + \'</span>\'\n'
    '                \'</div>\''
)

NEW3 = (
    '                \'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #eee">\'\n'
    '                \'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">\'\n'
    '                f\'<span style="font-size:0.75em;color:#888;letter-spacing:.06em;text-transform:uppercase">\'\n'
    '                f\'{brier_label}</span>\'\n'
    '                f\'<strong style="font-size:1.4em;font-weight:700;color:\'\n'
    '                + ("#16a34a" if mean_brier < 0.15 else ("#f59e0b" if mean_brier < 0.25 else "#dc2626"))\n'
    '                + f\'\">{mean_brier:.3f}</strong>\'\n'
    '                f\'<span style="font-size:0.78em;color:#aaa">\'\n'
    '                + (brier_note_good if mean_brier < 0.15 else (brier_note_ok if mean_brier < 0.25 else brier_note_bad))\n'
    '                + \'</span>\'\n'
    '                \'</div>\'\n'
    '                \'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;font-size:0.72em;margin-top:4px">\'\n'
    '                \'<div style="text-align:center;padding:5px 2px;background:#f0fdf4;border-radius:6px">\'\n'
    '                \'<div style="color:#16a34a;font-weight:700;font-size:1.1em">0.081</div>\'\n'
    '                f\'<div style="color:#888;margin-top:2px">{bench_super}</div>\'\n'
    '                \'</div>\'\n'
    '                \'<div style="text-align:center;padding:5px 2px;background:#eff6ff;border-radius:6px">\'\n'
    '                \'<div style="color:#2563eb;font-weight:700;font-size:1.1em">0.101</div>\'\n'
    '                \'<div style="color:#888;margin-top:2px">GPT-4.5</div>\'\n'
    '                \'</div>\'\n'
    '                \'<div style="text-align:center;padding:5px 2px;background:#f9fafb;border-radius:6px">\'\n'
    '                \'<div style="color:#6b7280;font-weight:700;font-size:1.1em">0.225</div>\'\n'
    '                f\'<div style="color:#888;margin-top:2px">{bench_gjo}</div>\'\n'
    '                \'</div>\'\n'
    '                \'</div>\'\n'
    '                \'</div>\''
)

if OLD3 not in content:
    print("ERROR: Brier div target not found")
    print("Looking for literal...")
    # Try to find partial match
    partial = '<div style="margin-top:10px;padding-top:10px;border-top:1px solid #eee;'
    idx = content.find(partial)
    if idx >= 0:
        print(f"Partial found at char {idx}")
        print(repr(content[idx:idx+300]))
    sys.exit(1)

content = content.replace(OLD3, NEW3, 1)

# Save
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
bak = f"{PATH}.bak_k2_{ts}"
shutil.copy2(PATH, bak)
with open(PATH, "w") as f:
    f.write(content)
print(f"Patched successfully: {PATH}")
print(f"Backup: {bak}")
print("Added: Brier benchmark comparison (Superforecaster 0.081 / GPT-4.5 0.101 / GJO avg 0.225)")
