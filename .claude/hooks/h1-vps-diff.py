#!/usr/bin/env python3
"""H1: VPS差分検知 - 前回セッションと現在のVPS状態を比較して変更を表示"""
import json, re, sys


def extract_metrics(text):
    m = {}
    for label in ["Total articles", "Japanese (lang-ja)", "English (lang-en)", "Total tags"]:
        r = re.search(r'\|\s*' + re.escape(label) + r'\s*\|\s*(\d+)', text)
        if r:
            m[label] = int(r.group(1))
    r = re.search(r'Active:\s*(\d+)', text)
    if r:
        m["Cron jobs"] = int(r.group(1))
    # Service statuses
    for svc in ["ghost-nowpattern", "neo-telegram", "neo2-telegram"]:
        r = re.search(r'\|\s*[^|]*' + re.escape(svc) + r'[^|]*\|\s*(\w+)\s*\|', text)
        if r:
            m["svc:" + svc] = r.group(1)
    return m


if len(sys.argv) < 3:
    sys.exit(0)

try:
    snap = json.load(open(sys.argv[1], encoding="utf-8"))
    prev_content = snap.get("content", "")
    curr_content = open(sys.argv[2], encoding="utf-8").read()
    prev_ts = snap.get("timestamp", "不明")[:16].replace("T", " ")
except Exception:
    sys.exit(0)

prev = extract_metrics(prev_content)
curr = extract_metrics(curr_content)

LABELS = {
    "Total articles": "記事総数",
    "Japanese (lang-ja)": "JP記事",
    "English (lang-en)": "EN記事",
    "Total tags": "タグ数",
    "Cron jobs": "cronジョブ",
}

changes = []
for key, curr_val in sorted(curr.items()):
    prev_val = prev.get(key)
    if prev_val is None or prev_val == curr_val:
        continue
    if key.startswith("svc:"):
        svc = key[4:]
        icon = "✅" if curr_val.lower() == "ok" else "❌"
        changes.append(f"  {icon} {svc}: {prev_val} → {curr_val}")
    elif isinstance(curr_val, int):
        label = LABELS.get(key, key)
        diff = curr_val - prev_val
        sign = "+" if diff >= 0 else ""
        changes.append(f"  {label}: {prev_val} → {curr_val} ({sign}{diff})")

if changes:
    print(f"前回セッション ({prev_ts}) からの変更:")
    for c in changes:
        print(c)
else:
    print(f"前回セッション ({prev_ts}) から変更なし")
