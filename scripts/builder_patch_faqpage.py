#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch prediction_page_builder.py:
  1. Insert _build_faqpage_ld() before _update_dataset_in_head()
  2. Replace _update_dataset_in_head() body to always inject both Dataset + FAQPage

Uses line-number based patching for reliability.
"""
import shutil, subprocess, sys

BUILDER = '/opt/shared/scripts/prediction_page_builder.py'

with open(BUILDER, 'r', encoding='utf-8') as f:
    lines = f.readlines()

total = len(lines)
print(f"Loaded {total} lines from {BUILDER}")

# ---- Locate key lines ----
idx_update_def = next((i for i, l in enumerate(lines) if 'def _update_dataset_in_head(' in l), None)
idx_head_get   = next((i for i, l in enumerate(lines) if i > (idx_update_def or 0) and 'head = p.get("codeinjection_head")' in l), None)
idx_print_done = next((i for i, l in enumerate(lines) if i > (idx_update_def or 0) and '[Dataset] Updated codeinjection_head' in l), None)

if idx_update_def is None:
    print("ERROR: def _update_dataset_in_head not found"); sys.exit(1)
if idx_head_get is None:
    print("ERROR: head = p.get line not found"); sys.exit(1)
if idx_print_done is None:
    print("ERROR: print([Dataset] Updated...) line not found"); sys.exit(1)

print(f"def _update_dataset_in_head at line {idx_update_def+1}")
print(f"Body start at line {idx_head_get+1}")
print(f"Body end at line {idx_print_done+1}")

# Check if already patched
if '"FAQPage"' in ''.join(lines[idx_update_def:idx_print_done+2]):
    print("Already patched. Exiting.")
    sys.exit(0)

# ---- New body for _update_dataset_in_head ----
NEW_BODY_LINES = [
    '    head = p.get("codeinjection_head") or ""\n',
    '    # Remove existing Dataset AND FAQPage blocks (block-aware finditer, re-inject both)\n',
    '    _ld_blocks = list(_re.finditer(\n',
    "        r'<script[^>]*application/ld\\+json[^>]*>[\\s\\S]*?</script>',\n",
    '        head, _re.IGNORECASE,\n',
    '    ))\n',
    '    head_clean = head\n',
    '    for _m in reversed(_ld_blocks):\n',
    '        if \'\"Dataset\"\' in _m.group() or \'\"FAQPage\"\' in _m.group():\n',
    '            head_clean = head_clean[:_m.start()] + head_clean[_m.end():]\n',
    '    head_clean = head_clean.strip()\n',
    '    dataset_block = _build_dataset_ld(stats, lang)\n',
    '    faqpage_block = _build_faqpage_ld(lang)\n',
    '    new_head = (head_clean + chr(10) + dataset_block + chr(10) + faqpage_block\n',
    '                if head_clean else dataset_block + chr(10) + faqpage_block)\n',
    '    payload = {"pages": [{"codeinjection_head": new_head, "updated_at": updated_at}]}\n',
    '    ghost_request("PUT", "/pages/" + page_id + "/", api_key, payload)\n',
    '    print("[Dataset+FAQPage] Updated codeinjection_head for slug=" + slug + " (" + lang + ")")\n',
]

# ---- _build_faqpage_ld function to insert ----
FAQPAGE_FUNC_TEXT = (
'\n'
'def _build_faqpage_ld(lang="ja"):\n'
'    """Generate FAQPage JSON-LD for /predictions/ pages (REQ-008)."""\n'
'    if lang == "en":\n'
'        return (\n'
'            \'<script type="application/ld+json">\\n\'\n'
'            \'{\\n\'\n'
'            \'  "@context": "https://schema.org",\\n\'\n'
'            \'  "@type": "FAQPage",\\n\'\n'
'            \'  "mainEntity": [\\n\'\n'
'            \'    {\\n\'\n'
'            \'      "@type": "Question",\\n\'\n'
'            \'      "name": "How are Nowpattern predictions verified?",\\n\'\n'
'            \'      "acceptedAnswer": {"@type": "Answer",\\n\'\n'
'            \'        "text": "Nowpattern predictions are automatically verified by prediction_auto_verifier.py. After the resolution date passes, AI and news search are combined to judge hit or miss, and accuracy is calculated using Brier Score."}\\n\'\n'
'            \'    },\\n\'\n'
'            \'    {\\n\'\n'
'            \'      "@type": "Question",\\n\'\n'
'            \'      "name": "What is a Brier Score?",\\n\'\n'
'            \'      "acceptedAnswer": {"@type": "Answer",\\n\'\n'
'            \'        "text": "The Brier Score measures prediction accuracy. The closer to 0, the higher the accuracy. 0.00-0.10 is Excellent, 0.10-0.20 is Good."}\\n\'\n'
'            \'    },\\n\'\n'
'            \'    {\\n\'\n'
'            \'      "@type": "Question",\\n\'\n'
'            \'      "name": "How can I participate in predictions?",\\n\'\n'
'            \'      "acceptedAnswer": {"@type": "Answer",\\n\'\n'
'            \'        "text": "Use the vote button on each prediction card to select optimistic, base, or pessimistic scenario and submit your probability. No account registration required."}\\n\'\n'
'            \'    },\\n\'\n'
'            \'    {\\n\'\n'
'            \'      "@type": "Question",\\n\'\n'
'            \'      "name": "Where can I check past prediction results?",\\n\'\n'
'            \'      "acceptedAnswer": {"@type": "Answer",\\n\'\n'
'            \'        "text": "See the Resolved Predictions section on this page for all judged predictions including hit/miss and Brier Score."}\\n\'\n'
'            \'    }\\n\'\n'
'            \'  ]\\n\'\n'
'            \'}\\n\'\n'
'            \'</script>\'\n'
'        )\n'
'    else:\n'
'        return (\n'
'            \'<script type="application/ld+json">\\n\'\n'
'            \'{\\n\'\n'
'            \'  "@context": "https://schema.org",\\n\'\n'
'            \'  "@type": "FAQPage",\\n\'\n'
'            \'  "mainEntity": [\\n\'\n'
'            \'    {\\n\'\n'
'            \'      "@type": "Question",\\n\'\n'
'            u\'      "name": "Nowpattern\\u306e\\u4e88\\u6e2c\\u306f\\u3069\\u306e\\u3088\\u3046\\u306b\\u691c\\u8a3c\\u3055\\u308c\\u307e\\u3059\\u304b\\uff1f",\\n\'\n'
'            \'      "acceptedAnswer": {"@type": "Answer",\\n\'\n'
'            u\'        "text": "Nowpattern\\u306e\\u4e88\\u6e2c\\u306fprediction_auto_verifier.py\\u306b\\u3088\\u3063\\u3066\\u81ea\\u52d5\\u7684\\u306b\\u691c\\u8a3c\\u3055\\u308c\\u307e\\u3059\\u3002\\u5224\\u5b9a\\u65e5\\u304c\\u904e\\u304e\\u305f\\u4e88\\u6e2c\\u306f\\u3001AI\\u3068\\u30cb\\u30e5\\u30fc\\u30b9\\u691c\\u7d22\\u3092\\u7d44\\u307f\\u5408\\u308f\\u305b\\u3066\\u7684\\u4e2d\\u30fb\\u5916\\u308c\\u3092\\u81ea\\u52d5\\u5224\\u5b9a\\u3057\\u3001Brier Score\\u3067\\u7cbe\\u5ea6\\u3092\\u8a08\\u7b97\\u3057\\u307e\\u3059\\u3002"}\\n\'\n'
'            \'    },\\n\'\n'
'            \'    {\\n\'\n'
'            \'      "@type": "Question",\\n\'\n'
'            u\'      "name": "Brier Score\\u3068\\u306f\\u4f55\\u3067\\u3059\\u304b\\uff1f",\\n\'\n'
'            \'      "acceptedAnswer": {"@type": "Answer",\\n\'\n'
'            u\'        "text": "Brier Score\\u306f\\u4e88\\u6e2c\\u7cbe\\u5ea6\\u3092\\u6e2c\\u308b\\u6307\\u6a130\\u306b\\u8fd1\\u3044\\u307b\\u3069\\u7cbe\\u5ea6\\u304c\\u9ad8\\u3044\\u3002Nowpattern\\u3067\\u306f\\u5168\\u4e88\\u6e2c\\u306e\\u5e73\\u5747Brier Score\\u3092\\u516c\\u958b\\u30020.00-0.10\\u304c\\u512a\\u79c0\\u30010.10-0.20\\u304c\\u826f\\u597d\\u3002"}\\n\'\n'
'            \'    },\\n\'\n'
'            \'    {\\n\'\n'
'            \'      "@type": "Question",\\n\'\n'
'            u\'      "name": "\\u4e88\\u6e2c\\u306b\\u53c2\\u52a0\\u3059\\u308b\\u306b\\u306f\\u3069\\u3046\\u3059\\u308c\\u3070\\u3044\\u3044\\u3067\\u3059\\u304b\\uff1f",\\n\'\n'
'            \'      "acceptedAnswer": {"@type": "Answer",\\n\'\n'
'            u\'        "text": "\\u5404\\u4e88\\u6e2c\\u30ab\\u30fc\\u30c9\\u306e\\u6295\\u7968\\u30dc\\u30bf\\u30f3\\u304b\\u3089\\u3001\\u697d\\u89b3\\u30fb\\u57fa\\u672c\\u30fb\\u60b2\\u89b3\\u30b7\\u30ca\\u30ea\\u30aa\\u306e\\u3044\\u305a\\u308c\\u304b\\u3092\\u9078\\u3093\\u3067\\u78ba\\u7387\\u3092\\u6295\\u7968\\u3067\\u304d\\u307e\\u3059\\u3002\\u30a2\\u30ab\\u30a6\\u30f3\\u30c8\\u767b\\u9332\\u4e0d\\u8981\\u3067\\u3001\\u533f\\u540d\\u306e\\u307e\\u307e\\u53c2\\u52a0\\u53ef\\u80fd\\u3002"}\\n\'\n'
'            \'    },\\n\'\n'
'            \'    {\\n\'\n'
'            \'      "@type": "Question",\\n\'\n'
'            u\'      "name": "\\u904e\\u53bb\\u306e\\u4e88\\u6e2c\\u7d50\\u679c\\u306f\\u3069\\u3053\\u3067\\u78ba\\u8a8d\\u3067\\u304d\\u307e\\u3059\\u304b\\uff1f",\\n\'\n'
'            \'      "acceptedAnswer": {"@type": "Answer",\\n\'\n'
'            u\'        "text": "\\u3053\\u306e\\u30da\\u30fc\\u30b8\\u306e\\u300c\\u89e3\\u6c7a\\u6e08\\u307f\\u4e88\\u6e2c\\u300d\\u30bb\\u30af\\u30b7\\u30e7\\u30f3\\u3067\\u3001\\u5224\\u5b9a\\u6e08\\u307f\\u306e\\u5168\\u4e88\\u6e2c\\uff08\\u7684\\u4e2d\\u30fb\\u5916\\u308c\\u30fbBrier Score\\uff09\\u3092\\u78ba\\u8a8d\\u3067\\u304d\\u307e\\u3059\\u3002"}\\n\'\n'
'            \'    }\\n\'\n'
'            \'  ]\\n\'\n'
'            \'}\\n\'\n'
'            \'</script>\'\n'
'        )\n'
'\n'
)
FAQPAGE_FUNC_LINES = [l + '\n' for l in FAQPAGE_FUNC_TEXT.split('\n')]
# Remove extra trailing newline from split
if FAQPAGE_FUNC_LINES and FAQPAGE_FUNC_LINES[-1] == '\n':
    FAQPAGE_FUNC_LINES = FAQPAGE_FUNC_LINES[:-1]

# ---- Apply patches ----
# Step 1: Replace body lines
new_lines = lines[:idx_head_get] + NEW_BODY_LINES + lines[idx_print_done+1:]
print(f"Replaced body: {idx_print_done - idx_head_get + 1} old lines → {len(NEW_BODY_LINES)} new lines")

# Step 2: Insert function (idx_update_def still valid; inserted lines are after it)
new_lines = new_lines[:idx_update_def] + FAQPAGE_FUNC_LINES + new_lines[idx_update_def:]
print(f"Inserted _build_faqpage_ld: {len(FAQPAGE_FUNC_LINES)} lines at position {idx_update_def}")

# ---- Backup and write ----
shutil.copy2(BUILDER, BUILDER + '.bak-20260329-faqfix')
with open(BUILDER, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print(f"Written {len(new_lines)} lines. Backup: .bak-20260329-faqfix")

# ---- Syntax check ----
result = subprocess.run(['python3', '-m', 'py_compile', BUILDER], capture_output=True, text=True)
if result.returncode != 0:
    print(f"SYNTAX ERROR:\n{result.stderr}")
    shutil.copy2(BUILDER + '.bak-20260329-faqfix', BUILDER)
    print("RESTORED backup")
    sys.exit(1)
print("Syntax check: PASSED")

# ---- Verify patch ----
with open(BUILDER, 'r', encoding='utf-8') as f:
    verify = f.read()

for label, text in [
    ('_build_faqpage_ld defined', 'def _build_faqpage_ld('),
    ('"FAQPage" in _update_dataset', '"FAQPage"'),
    ('block-aware finditer', 'finditer('),
    ('faqpage_block assignment', 'faqpage_block = _build_faqpage_ld(lang)'),
    ('Dataset+FAQPage print', '[Dataset+FAQPage] Updated'),
]:
    ok = text in verify
    print(f"  {'OK' if ok else 'FAIL'}: {label}")

print("\nDONE.")
