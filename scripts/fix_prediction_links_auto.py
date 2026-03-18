#!/usr/bin/env python3
"""
fix_prediction_links_auto.py — K1 cron版 wrong_lang 自動修正スクリプト
cron: 55 6 * * * (prediction_page_builder.py の07:00実行の5分前)

WRONG_LANG: EN予測 (lang="en") の ghost_url に /en/ が含まれていない場合
  → https://nowpattern.com/{slug}/ を https://nowpattern.com/en/{slug}/ に変換
  (HTTPチェックなし — 高速処理優先。EN記事存在確認はpage_builderが担う)
"""
import json, os, shutil, sys
from datetime import datetime

DB_PATH = "/opt/shared/scripts/prediction_db.json"
LOG_PATH = "/opt/shared/logs/fix_wrong_lang_auto.log"
NOTIFY = os.path.exists("/opt/cron-env.sh")


def load_env():
    env = {}
    try:
        for line in open("/opt/cron-env.sh"):
            if line.startswith("export "):
                k, _, v = line[7:].strip().partition("=")
                env[k] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


def send_telegram(msg):
    import urllib.request
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    data = json.dumps({"chat_id": chat_id, "text": msg}).encode()
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def fix_wrong_lang(dry_run=False):
    with open(DB_PATH) as f:
        db = json.load(f)

    preds = db.get("predictions", db) if isinstance(db, dict) else db
    fixed = 0
    skipped = 0

    for p in preds:
        if not isinstance(p, dict):
            continue
        lang = p.get("lang", "")
        url = (p.get("ghost_url") or "").strip()

        if lang != "en" or not url:
            continue

        if "/en/" in url:
            skipped += 1
            continue

        # Convert: https://nowpattern.com/{slug}/ → https://nowpattern.com/en/{slug}/
        # Or: /{slug}/ → /en/{slug}/
        if url.startswith("https://nowpattern.com/"):
            slug = url.rstrip("/").split("/")[-1]
            new_url = f"https://nowpattern.com/en/{slug}/"
        elif url.startswith("/") and not url.startswith("/en/"):
            slug = url.strip("/")
            new_url = f"/en/{slug}/"
        else:
            skipped += 1
            continue

        if not dry_run:
            p["ghost_url"] = new_url
        fixed += 1

    return db, preds, fixed, skipped


def main():
    dry_run = "--dry-run" in sys.argv

    log(f"=== fix_prediction_links_auto.py start {'(DRY RUN)' if dry_run else '(LIVE)'} ===")

    if not os.path.exists(DB_PATH):
        log(f"ERROR: {DB_PATH} not found")
        return

    db, preds, fixed, skipped = fix_wrong_lang(dry_run=dry_run)

    log(f"Checked: {len(preds)} predictions | Fixed: {fixed} | Already OK: {skipped}")

    if fixed == 0:
        log("Nothing to fix. Done.")
        return

    if not dry_run:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = f"{DB_PATH}.bak_autofix_{ts}"
        shutil.copy2(DB_PATH, bak)
        with open(DB_PATH, "w") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        log(f"Saved. Backup: {bak}")

        if fixed >= 5:
            send_telegram(
                f"✅ [K1] wrong_lang 自動修正完了\n"
                f"修正: {fixed}件\n"
                f"→ prediction_page_builder.py が正しいEN URLでページを生成します"
            )
    else:
        log(f"[DRY RUN] Would fix {fixed} predictions")

    log("=== done ===")


if __name__ == "__main__":
    main()
