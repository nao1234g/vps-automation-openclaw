#!/usr/bin/env python3
"""K4: x_swarm_dispatcher.py の generate_redteam_content() を
YES-派/NO-派フォーマットに更新

IMPLEMENTATION_REF.md (formerly content-rules.md) Section 4 準拠:
  「予測は70%でYES — しかし30%のNOシナリオはこうだ」
  Poll: YES / NO / まだわからない / 分析を読む
"""
import sys, shutil, datetime

PATH = "/opt/shared/scripts/x_swarm_dispatcher.py"

with open(PATH) as f:
    content = f.read()

# Already patched check
if "YES-派/NO-派" in content:
    print("K4 redteam template already patched. Nothing to do.")
    sys.exit(0)

# ─── Patch 1: generate_redteam_content() を置換 ───
OLD1 = '''def generate_redteam_content(item):
    """RED-TEAM型: 2視点の討論スレッド + Poll"""
    title = item.get("article_title", "")[:50]
    scenarios = item.get("scenarios", {})
    optimistic = scenarios.get("optimistic", {})
    pessimistic = scenarios.get("pessimistic", {})

    opt_text = optimistic.get("description", "楽観シナリオ")[:200]
    pes_text = pessimistic.get("description", "悲観シナリオ")[:200]
    opt_prob = optimistic.get("probability", "?")
    pes_prob = pessimistic.get("probability", "?")

    tweets = [
        f"⚡ {title}\\n\\n2つのシナリオで考える 🧵",
        f"📈 楽観シナリオ（{opt_prob}%）:\\n{opt_text}",
        f"📉 悲観シナリオ（{pes_prob}%）:\\n{pes_text}",
    ]

    poll = {
        "options": [
            f"楽観 ({opt_prob}%)",
            f"悲観 ({pes_prob}%)",
            "どちらでもない",
            "分析を読む",
        ],
        "duration_minutes": 1440,
    }

    return {"thread": tweets, "poll_on_last": poll, "cat": item.get("cat", "")}'''

NEW1 = '''def generate_redteam_content(item):
    """RED-TEAM型: YES-派/NO-派の討論スレッド + Poll

    IMPLEMENTATION_REF.md (formerly content-rules.md) Section 4 準拠:
    「予測は70%でYES — しかし30%のNOシナリオはこうだ」
    Poll: YES / NO / まだわからない / 分析を読む
    """
    title = item.get("article_title", item.get("text", ""))[:50]
    prediction = item.get("prediction") or {}
    our_pick = str(prediction.get("our_pick") or "YES").upper()
    our_pick_prob = int(prediction.get("our_pick_prob") or 70)
    counter_pick = "NO" if our_pick == "YES" else "YES"
    counter_prob = 100 - our_pick_prob

    # シナリオテキスト取得（scenarios はリスト: [楽観, 基本, 悲観]）
    scenarios = prediction.get("scenarios") or []
    if isinstance(scenarios, list) and len(scenarios) >= 2:
        if our_pick == "YES":
            pick_scen = scenarios[0]    # 楽観 = YES寄り
            counter_scen = scenarios[-1]  # 悲観 = NO寄り
        else:
            pick_scen = scenarios[-1]   # 悲観 = NO寄り
            counter_scen = scenarios[0]  # 楽観 = YES寄り
        pick_text = (pick_scen.get("content") or "")[:180]
        counter_text = (counter_scen.get("content") or "")[:180]
    else:
        pick_text = "この予測が実現する可能性が高い"
        counter_text = "しかし、逆シナリオも十分あり得る"

    resolution = (prediction.get("resolution_question") or title)[:60]

    tweets = [
        f"🔮 {resolution}\\n\\n予測は{our_pick_prob}%で{our_pick} — しかし{counter_prob}%の反論もある 🧵",
        f"✅ {our_pick}派（{our_pick_prob}%）:\\n{pick_text}",
        f"❌ {counter_pick}派（{counter_prob}%）:\\n{counter_text}\\n\\nあなたはどちら？ ↓",
    ]

    poll = {
        "options": ["YES", "NO", "まだわからない", "分析を読む"],
        "duration_minutes": 1440,
    }

    return {"thread": tweets, "poll_on_last": poll, "cat": item.get("cat", "")}'''

if OLD1 not in content:
    print("ERROR: target function not found")
    idx = content.find("def generate_redteam_content")
    if idx >= 0:
        print(repr(content[idx:idx+300]))
    sys.exit(1)

content = content.replace(OLD1, NEW1, 1)
print("Patch 1 applied: generate_redteam_content() → YES-派/NO-派")

# ─── Patch 2: poll_text を更新 ───
OLD2 = '                poll_text = "あなたはどちらのシナリオ？"'
NEW2 = '                poll_text = "あなたはどちら？"'

if OLD2 not in content:
    print("WARNING: poll_text target not found (may already be updated)")
else:
    content = content.replace(OLD2, NEW2, 1)
    print("Patch 2 applied: poll_text → 'あなたはどちら？'")

# Save
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = f"{PATH}.bak_k4_{ts}"
shutil.copy2(PATH, bak)
with open(PATH, "w") as f:
    f.write(content)
print(f"Saved: {PATH}")
print(f"Backup: {bak}")
print("K4 complete: RED-TEAM template → YES-派/NO-派 + Poll (YES/NO/まだわからない/分析を読む)")
