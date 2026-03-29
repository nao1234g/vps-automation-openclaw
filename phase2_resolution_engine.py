#!/usr/bin/env python3
"""
Phase 2: 解決期限・判定エンジン実装
- oracle_deadline テキスト → event_cutoff_at (ISO YYYY-MM-DD)
- evidence_grace_until = event_cutoff_at + 7 days
- final_resolution_at = event_cutoff_at + 14 days
- unresolved_policy 追加 (binary → AUTO_NO_AT_DEADLINE, etc.)
- AWAITING_EVIDENCE かつ期限切れ → status を EXPIRED_UNRESOLVED に更新

バックアップ: prediction_db.json.bak-phase2 に保存
"""
import json
import re
import shutil
from datetime import datetime, timedelta
from collections import Counter

DB_PATH = "/opt/shared/scripts/prediction_db.json"
TODAY = datetime.today().date()

def parse_oracle_deadline(text: str):
    """日本語テキストの日付からISO dateを抽出。できない場合はNone。"""
    if not text:
        return None
    text = text.strip()

    # 既にISO形式 YYYY-MM-DD or YYYY/MM/DD
    m = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).date().isoformat()
        except ValueError:
            pass

    # 日本語: 2026年3月18日（ or 前後 or ─ or 〜X日）
    # 2026年3月18-19日 → 19日を取る（後ろの方が安全な期限）
    m = re.search(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})[-〜～](\d{1,2})日', text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(4))
        try:
            return datetime(y, mo, d).date().isoformat()
        except ValueError:
            pass

    # 2026年3月18日 (単日)
    m = re.search(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日', text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).date().isoformat()
        except ValueError:
            pass

    # 2026年4月 → 月末を使う
    m = re.search(r'(\d{4})年\s*(\d{1,2})月', text)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        # 月末
        if mo == 12:
            end = datetime(y + 1, 1, 1).date() - timedelta(days=1)
        else:
            end = datetime(y, mo + 1, 1).date() - timedelta(days=1)
        return end.isoformat()

    # Q1/Q2/Q3/Q4
    m = re.search(r'(\d{4})年?\s*Q([1-4])', text, re.IGNORECASE)
    if not m:
        m = re.search(r'(\d{4})[年\s]*Q([1-4])', text, re.IGNORECASE)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        q_end = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
        return f"{y}-{q_end[q]}"

    # 2026 H1/H2 (上半期/下半期)
    m = re.search(r'(\d{4}).*(?:H1|上半期|前半)', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)}-06-30"
    m = re.search(r'(\d{4}).*(?:H2|下半期|後半)', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)}-12-31"

    # 年だけ → 年末
    m = re.match(r'(\d{4})年?$', text.strip())
    if m:
        return f"{m.group(1)}-12-31"

    return None  # 解析不能

def derive_unresolved_policy(p: dict) -> str:
    """question_type と oracle_deadline から unresolved_policy を決定"""
    qtype = p.get("question_type", "binary")
    deadline_text = p.get("oracle_deadline", "")

    # 継続監視型
    if qtype in ("continuous", "CONTINUOUS_MONITORING"):
        return "SUCCESSOR_FORECAST_REQUIRED"
    # 条件型
    if qtype in ("conditional", "CONDITIONAL"):
        return "MANUAL_REVIEW"
    # デフォルト: binary → 期限でNO扱い
    return "AUTO_NO_AT_DEADLINE"

def main():
    # バックアップ
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    bak = f"{DB_PATH}.bak-phase2-{ts}"
    shutil.copy2(DB_PATH, bak)
    print(f"Backup: {bak}")

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    preds = db["predictions"]
    print(f"Total: {len(preds)}")

    stats = {
        "event_cutoff_added": 0,
        "event_cutoff_unparseable": 0,
        "grace_added": 0,
        "unresolved_policy_added": 0,
        "expired_updated": 0,
    }
    unparseable_samples = []

    for p in preds:
        # 1. event_cutoff_at
        if not p.get("event_cutoff_at"):
            dl = p.get("oracle_deadline", "")
            iso = parse_oracle_deadline(dl)
            if iso:
                p["event_cutoff_at"] = iso
                stats["event_cutoff_added"] += 1
            else:
                stats["event_cutoff_unparseable"] += 1
                if len(unparseable_samples) < 5:
                    unparseable_samples.append((p.get("prediction_id","?"), dl))

        # 2. evidence_grace_until / final_resolution_at
        cutoff = p.get("event_cutoff_at")
        if cutoff and not p.get("evidence_grace_until"):
            try:
                cutoff_date = datetime.fromisoformat(cutoff).date()
                grace = (cutoff_date + timedelta(days=7)).isoformat()
                final = (cutoff_date + timedelta(days=14)).isoformat()
                p["evidence_grace_until"] = grace
                p["final_resolution_at"] = final
                stats["grace_added"] += 1
            except Exception:
                pass

        # 3. unresolved_policy
        if not p.get("unresolved_policy"):
            p["unresolved_policy"] = derive_unresolved_policy(p)
            stats["unresolved_policy_added"] += 1

        # 4. 期限切れ かつ AWAITING_EVIDENCE → EXPIRED_UNRESOLVED
        if p.get("status") == "AWAITING_EVIDENCE" and p.get("event_cutoff_at"):
            try:
                cutoff_date = datetime.fromisoformat(p["event_cutoff_at"]).date()
                grace_until = p.get("evidence_grace_until", p["event_cutoff_at"])
                grace_date = datetime.fromisoformat(grace_until).date()
                if TODAY > grace_date:
                    p["status"] = "EXPIRED_UNRESOLVED"
                    # verdictもUPDATE
                    if p.get("verdict") == "PENDING":
                        if p.get("unresolved_policy") == "AUTO_NO_AT_DEADLINE":
                            p["verdict"] = "MISS"
                            p["hit_miss"] = "MISS"
                        else:
                            p["verdict"] = "NOT_SCORED"
                    stats["expired_updated"] += 1
            except Exception:
                pass

    # 保存
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("Done!")
    print(f"  event_cutoff_at added:      {stats['event_cutoff_added']}")
    print(f"  event_cutoff_unparseable:   {stats['event_cutoff_unparseable']}")
    print(f"  grace/final_resolution_at:  {stats['grace_added']}")
    print(f"  unresolved_policy added:    {stats['unresolved_policy_added']}")
    print(f"  expired_unresolved updated: {stats['expired_updated']}")

    if unparseable_samples:
        print("\nUnparseable oracle_deadline samples:")
        for pid, dl in unparseable_samples:
            print(f"  {pid}: {repr(dl)}")

    # 事後確認
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db2 = json.load(f)
    p2 = db2["predictions"]
    print("\nPost-run state:")
    print("  event_cutoff_at:", sum(1 for x in p2 if x.get("event_cutoff_at")))
    print("  evidence_grace_until:", sum(1 for x in p2 if x.get("evidence_grace_until")))
    print("  unresolved_policy:", dict(Counter(x.get("unresolved_policy") for x in p2)))
    print("  status:", dict(Counter(x.get("status") for x in p2)))
    print("  verdict:", dict(Counter(x.get("verdict") for x in p2)))

if __name__ == "__main__":
    main()
