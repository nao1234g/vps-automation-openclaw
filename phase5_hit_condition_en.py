#!/usr/bin/env python3
"""
Phase 5: oracle_criteria → hit_condition_en 完全補完
- EN oracle_criteria (859件) → hit_condition_en に直接コピー
- JA oracle_criteria (193件) → Gemini Flash で英訳
- 既に hit_condition_en がある予測はスキップ
"""
import json
import re
import time
import os
import sys
import shutil
from datetime import datetime

DB_PATH = "/opt/shared/scripts/prediction_db.json"
BATCH_SIZE = 10
SLEEP_BETWEEN_BATCHES = 3.0  # Gemini free tier rate limit対策

def has_cjk(s: str) -> bool:
    return bool(re.search(r'[\u3000-\u9fff\uff00-\uffef]', s))

def translate_batch_gemini(model, items: list) -> dict:
    """
    items: list of (prediction_id, japanese_oracle_criteria)
    returns: dict of prediction_id → english_hit_condition
    """
    if not items:
        return {}

    lines = []
    for pid, criteria in items:
        lines.append(f"[{pid}] {criteria}")

    prompt = (
        "Translate the following Japanese prediction hit conditions to concise English. "
        "Each line starts with [ID] followed by Japanese text. "
        "Return ONLY the translations in the exact same [ID] English text format. "
        "Keep the logical structure (YES/NO conditions) intact.\n\n"
        + "\n".join(lines)
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
    except Exception as e:
        print(f"  API error: {e}")
        return {}

    result = {}
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("[") and "]" in line:
            bracket_end = line.index("]")
            pid = line[1:bracket_end].strip()
            translation = line[bracket_end + 1:].strip()
            if pid and translation:
                result[pid] = translation

    return result

def main():
    # Gemini API セットアップ
    api_key = os.environ.get("GEMINI_API_KEY", "")
    use_gemini = bool(api_key)

    if use_gemini:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            print("Gemini Flash ready")
        except ImportError:
            print("WARNING: google-generativeai not installed. JA translations will be skipped.")
            use_gemini = False
            model = None
    else:
        print("WARNING: GEMINI_API_KEY not set. JA translations will be skipped.")
        model = None

    # バックアップ
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    bak = f"{DB_PATH}.bak-phase5b-{ts}"
    shutil.copy2(DB_PATH, bak)
    print(f"Backup: {bak}")

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    preds = db["predictions"]
    print(f"Total: {len(preds)}")

    # 処理対象を分類
    targets_en = []   # コピーのみ (EN oracle_criteria)
    targets_ja = []   # 翻訳必要 (JA oracle_criteria)

    for p in preds:
        criteria = p.get("oracle_criteria", "").strip()
        if not criteria:
            continue
        if p.get("hit_condition_en", "").strip():
            continue  # 既にある → スキップ

        if has_cjk(criteria):
            targets_ja.append((p["prediction_id"], criteria))
        else:
            targets_en.append((p["prediction_id"], criteria))

    print(f"EN copy targets:    {len(targets_en)}")
    print(f"JA translate targets: {len(targets_ja)}")

    # pred_map for fast lookup
    pred_map = {p["prediction_id"]: p for p in preds}

    # --- Step 1: EN oracle_criteria → hit_condition_en コピー ---
    copied = 0
    for pid, criteria in targets_en:
        pred_map[pid]["hit_condition_en"] = criteria
        copied += 1
    print(f"\nCopied EN: {copied}")

    # 中間保存
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("Saved after EN copy.")

    # --- Step 2: JA oracle_criteria → 翻訳 ---
    translated = 0
    failed = 0

    if targets_ja and use_gemini:
        print(f"\nStarting JA translation ({len(targets_ja)} items, batch={BATCH_SIZE})...")
        total_batches = (len(targets_ja) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(targets_ja), BATCH_SIZE):
            batch = targets_ja[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} items)...", end="", flush=True)

            translations = translate_batch_gemini(model, batch)

            for pid, criteria in batch:
                if pid in translations:
                    pred_map[pid]["hit_condition_en"] = translations[pid]
                    translated += 1
                else:
                    failed += 1

            print(f" +{len(translations)} ok, {len(batch)-len(translations)} miss")

            # バッチごとに保存（再開可能）
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)

            if i + BATCH_SIZE < len(targets_ja):
                time.sleep(SLEEP_BETWEEN_BATCHES)

        print(f"\nJA translated: {translated}/{len(targets_ja)}, failed: {failed}")
    elif targets_ja:
        print(f"\nSkipped JA translation (no Gemini). {len(targets_ja)} items remain untranslated.")

    # 最終保存
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    # 事後確認
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db2 = json.load(f)
    p2 = db2["predictions"]

    has_en = sum(1 for p in p2 if p.get("hit_condition_en", "").strip())
    still_ja_only = sum(1 for p in p2 if p.get("oracle_criteria", "").strip()
                        and not p.get("hit_condition_en", "").strip()
                        and has_cjk(p.get("oracle_criteria", "")))

    print(f"\n=== Phase 5b Complete ===")
    print(f"  hit_condition_en total:    {has_en}/{len(p2)}")
    print(f"  JA-only remaining:         {still_ja_only}")
    print(f"  EN copied:                 {copied}")
    print(f"  JA translated:             {translated}")

if __name__ == "__main__":
    main()
