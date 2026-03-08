#!/usr/bin/env python3
"""
prediction_taxonomy_validator.py
prediction_db.json のジャンル/力学タグが nowpattern_taxonomy.json に準拠しているか検証する。

Usage:
  python3 prediction_taxonomy_validator.py           # 不整合を報告
  python3 prediction_taxonomy_validator.py --fix     # prediction_db.json を自動修正（正規化できるものだけ）
  python3 prediction_taxonomy_validator.py --notify  # Telegram通知を送る
"""

import json
import os
import sys
import urllib.request

PREDICTION_DB  = "/opt/shared/scripts/prediction_db.json"
TAXONOMY_JSON  = "/opt/shared/scripts/nowpattern_taxonomy.json"
CRON_ENV       = "/opt/cron-env.sh"

# --- 環境変数読み込み ---
def load_env():
    env = {}
    try:
        for line in open(CRON_ENV):
            if line.startswith("export "):
                k, _, v = line[7:].strip().partition("=")
                env[k] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env

ENV = load_env()

# --- タクソノミー読み込み ---
def load_taxonomy():
    tx = json.load(open(TAXONOMY_JSON))
    genre_names     = {g["name_ja"] for g in tx["genres"]}
    genre_slugs     = {g["slug"] for g in tx["genres"]}
    dyn_names       = {d["name_ja"] for d in tx["dynamics"]}
    dyn_slugs       = {d["slug"] for d in tx["dynamics"]}
    event_names     = {e["name_ja"] for e in tx["events"]}
    event_slugs     = {e["slug"] for e in tx["events"]}
    genre_name2slug = {g["name_ja"]: g["slug"] for g in tx["genres"]}
    dyn_name2slug   = {d["name_ja"]: d["slug"] for d in tx["dynamics"]}
    return (genre_names, genre_slugs, dyn_names, dyn_slugs,
            event_names, event_slugs, genre_name2slug, dyn_name2slug)

# --- 正規化マップ（予測DBで確認された非正規表記 → 正規name_ja） ---
GENRE_NORMALIZE = {
    "geopolitics":                   "地政学・安全保障",
    "economy":                       "経済・貿易",
    "finance":                       "金融・市場",
    "business":                      "ビジネス・産業",
    "technology":                    "テクノロジー",
    "crypto":                        "暗号資産",
    "energy":                        "エネルギー",
    "environment":                   "環境・気候",
    "governance":                    "ガバナンス・法",
    "society":                       "社会",
    "culture":                       "文化・エンタメ・スポーツ",
    "media":                         "メディア・情報",
    "health":                        "健康・科学",
    "technology / governance & law": "テクノロジー",
    "ai":                            "テクノロジー",
    "tech":                          "テクノロジー",
    "地政学":                        "地政学・安全保障",
    "暗号資産・web3":                "暗号資産",
    "暗号資産・Web3":                "暗号資産",
    "金融":                          "金融・市場",
    "経済":                          "経済・貿易",
    "テック":                        "テクノロジー",
}

# None = タクソノミーに存在しない（手動追加が必要）
DYNAMICS_NORMALIZE = {
    "platform power":            "プラットフォーム支配",
    "regulatory capture":        "規制の捕獲",
    "narrative war":             "物語の覇権",
    "overreach":                 "権力の過伸展",
    "escalation spiral":         "対立の螺旋",
    "alliance strain":           "同盟の亀裂",
    "alliance-strain":           "同盟の亀裂",
    "path dependency":           "経路依存",
    "path-dependency":           "経路依存",
    "backlash":                  "揺り戻し",
    "institutional decay":       "制度の劣化",
    "institutional-decay":       "制度の劣化",
    "coordination failure":      "協調の失敗",
    "coordination-failure":      "協調の失敗",
    "moral hazard":              "モラルハザード",
    "moral-hazard":              "モラルハザード",
    "contagion":                 "伝染の連鎖",
    "shock doctrine":            "危機便乗",
    "tech leapfrog":             "後発逆転",
    "winner takes all":          "勝者総取り",
    "winner-takes-all":          "勝者総取り",
    "legitimacy void":           "正統性の空白",
    "escalation-spiral":         "対立の螺旋",
    "Legitimacy Void":           "正統性の空白",
    "Narrative War":             "物語の覇権",
    "Platform Power":            "プラットフォーム支配",
    "Regulatory Capture":        "規制の捕獲",
    "institutional-fomo":        None,
    "ナラティブ":                "物語の覇権",
    "規制キャプチャー":          "規制の捕獲",
    "伝染カスケード":            "伝染の連鎖",
    "市場ショック":              None,
    "インフレヘッジ":            None,
    "法的迂回の限界":            None,
    "議会との権力再配分":        None,
    "選挙サイクルの時限装置":    None,
    "利益相反の制度化":          None,
}


def normalize_genre(raw, canonical_set):
    """(正規name_ja または raw, 正規化できたか)"""
    s = (raw or "").strip()
    if s in canonical_set:
        return s, True
    mapped = GENRE_NORMALIZE.get(s) or GENRE_NORMALIZE.get(s.lower())
    if mapped and mapped in canonical_set:
        return mapped, True
    return s, False


def normalize_dynamics(raw, canonical_set):
    """(正規name_ja または None, 正規化できたか)"""
    s = (raw or "").strip()
    if s in canonical_set:
        return s, True
    mapped = DYNAMICS_NORMALIZE.get(s) or DYNAMICS_NORMALIZE.get(s.lower())
    if mapped is None and (s in DYNAMICS_NORMALIZE or s.lower() in DYNAMICS_NORMALIZE):
        # 既知の「存在しない」タグ
        return None, False
    if mapped and mapped in canonical_set:
        return mapped, True
    return s, False


def validate():
    (genre_names, genre_slugs, dyn_names, dyn_slugs,
     event_names, event_slugs, g2s, d2s) = load_taxonomy()

    db = json.load(open(PREDICTION_DB))
    predictions = db["predictions"]

    genre_issues  = []   # (pred_id, raw, msg)
    dyn_issues    = []
    fixable_genre = []   # (index, pred_id, old, new)
    fixable_dyn   = []   # (index, pred_id, old_str, new_str)

    for i, p in enumerate(predictions):
        pid = p.get("prediction_id", f"idx-{i}")

        # ジャンルタグ検証
        raw_genre = (p.get("genre_tags") or "").strip()
        if not raw_genre:
            genre_issues.append((pid, "", "genre_tags が空"))
        else:
            norm, ok = normalize_genre(raw_genre, genre_names)
            if not ok:
                genre_issues.append((pid, raw_genre, "タクソノミー外: " + repr(raw_genre)))
            elif norm != raw_genre:
                genre_issues.append((pid, raw_genre, "非正規 " + repr(raw_genre) + " → " + repr(norm)))
                fixable_genre.append((i, pid, raw_genre, norm))

        # 力学タグ検証
        raw_dyn = (p.get("dynamics_tags") or "").strip()
        if not raw_dyn:
            dyn_issues.append((pid, "", "dynamics_tags が空"))
        else:
            parts = [x.strip() for x in raw_dyn.split("×") if x.strip()]
            new_parts = []
            row_changed = False
            row_has_unknown = False
            for part in parts:
                norm, ok = normalize_dynamics(part, dyn_names)
                if norm is None:
                    # 既知の「タクソノミー外」タグ
                    dyn_issues.append((pid, raw_dyn, "タクソノミー外(既知): " + repr(part)))
                    new_parts.append(part)
                    row_has_unknown = True
                elif not ok and norm not in dyn_names:
                    dyn_issues.append((pid, raw_dyn, "タクソノミー外(未知): " + repr(part)))
                    new_parts.append(part)
                    row_has_unknown = True
                elif norm != part:
                    dyn_issues.append((pid, raw_dyn, "非正規 " + repr(part) + " → " + repr(norm)))
                    new_parts.append(norm)
                    row_changed = True
                else:
                    new_parts.append(norm)
            new_dyn_str = " × ".join(new_parts)
            if row_changed and not row_has_unknown and new_dyn_str != raw_dyn:
                fixable_dyn.append((i, pid, raw_dyn, new_dyn_str))

    return (genre_issues, dyn_issues, fixable_genre, fixable_dyn, predictions, db)


def send_telegram(msg):
    bot  = ENV.get("TELEGRAM_BOT_TOKEN", "")
    chat = ENV.get("TELEGRAM_CHAT_ID", "")
    if not bot or not chat:
        return
    data = json.dumps({"chat_id": chat, "text": msg, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot" + bot + "/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print("Telegram error:", e)


def main():
    fix    = "--fix"    in sys.argv
    notify = "--notify" in sys.argv or "--slack" in sys.argv

    genre_issues, dyn_issues, fixable_genre, fixable_dyn, predictions, db = validate()

    total              = len(predictions)
    total_genre_issues = len(genre_issues)
    total_dyn_issues   = len(dyn_issues)

    print("=== prediction_taxonomy_validator ===")
    print("prediction_db:", total, "件")
    print()

    if genre_issues:
        print("[GENRE ISSUES]", len(genre_issues), "件")
        shown = set()
        for pid, raw, msg in genre_issues:
            key = msg
            if key not in shown:
                shown.add(key)
                print("  " + pid + ": " + msg)
    else:
        print("[GENRE] 全件OK — タクソノミー準拠")

    print()

    if dyn_issues:
        print("[DYNAMICS ISSUES]", len(dyn_issues), "件")
        shown = set()
        for pid, raw, msg in dyn_issues:
            key = msg
            if key not in shown:
                shown.add(key)
                print("  " + pid + ": " + msg)
    else:
        print("[DYNAMICS] 全件OK — タクソノミー準拠")

    print()

    if fix:
        n_fixed = len(fixable_genre) + len(fixable_dyn)
        print("[FIX] ジャンル修正:", len(fixable_genre), "件 / 力学修正:", len(fixable_dyn), "件")
        for i, pid, old, new in fixable_genre:
            predictions[i]["genre_tags"] = new
            print("  GENRE:", pid, repr(old), "→", repr(new))
        for i, pid, old, new in fixable_dyn:
            predictions[i]["dynamics_tags"] = new
            print("  DYN:  ", pid, repr(old), "→", repr(new))
        if n_fixed:
            db["predictions"] = predictions
            json.dump(db, open(PREDICTION_DB, "w"), ensure_ascii=False, indent=2)
            print("[SAVED]", PREDICTION_DB, "を更新しました")
        else:
            print("  修正対象なし（自動修正できない非正規タグが残存）")
    else:
        fixable = len(fixable_genre) + len(fixable_dyn)
        if fixable:
            print("[FIX可能]", fixable, "件が --fix で自動修正可能")

    print()
    if total_genre_issues == 0 and total_dyn_issues == 0:
        print("✅ 全件タクソノミー準拠")
    else:
        unknown_dyn = [m for _, _, m in dyn_issues if "既知" in m or "未知" in m]
        print("RESULT: GENRE", total_genre_issues, "件 / DYNAMICS", total_dyn_issues, "件 の不整合")
        print("  → --fix で自動修正可能なものは修正します")
        if unknown_dyn:
            seen = set()
            print("  → タクソノミーに存在しないタグ（手動で taxonomy.json へ追加推奨）:")
            for m in unknown_dyn:
                if m not in seen:
                    seen.add(m)
                    print("    " + m)

    if notify and (total_genre_issues > 0 or total_dyn_issues > 0):
        msg = (
            "⚠️ *prediction_taxonomy_validator*\n"
            "prediction_db: " + str(total) + "件中\n"
            "ジャンル不整合: " + str(total_genre_issues) + "件\n"
            "力学不整合: " + str(total_dyn_issues) + "件\n"
            "→ python3 /opt/shared/scripts/prediction_taxonomy_validator.py --fix"
        )
        send_telegram(msg)

    if total_genre_issues > 0 or total_dyn_issues > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
