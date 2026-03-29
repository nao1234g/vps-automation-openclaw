#!/usr/bin/env python3
"""
Phase 6: 予測DB 改ざん耐性・監査証跡システム
- manifest.json: 全予測のSHA-256ハッシュ + 登録タイムスタンプ
- event_ledger.jsonl: append-only イベントログ (NDJSON形式)
- integrity_check: 現在のDBとmanifestを照合して改ざんを検知

manifest フォーマット:
{
  "generated_at": "ISO8601",
  "schema_version": "2.0",
  "total": 1115,
  "predictions": {
    "NP-2026-0001": {
      "hash": "sha256hex",
      "recorded_at": "ISO8601",
      "status": "RESOLVED",
      "verdict": "HIT"
    }
  }
}

event_ledger フォーマット (NDJSON - 1行1イベント):
{"ts":"ISO8601","event":"CREATED","prediction_id":"NP-2026-0001","hash":"...","actor":"phase6"}
{"ts":"ISO8601","event":"RESOLVED","prediction_id":"NP-2026-0001","verdict":"HIT","brier":0.09,"actor":"auto_verifier"}
"""
import json
import hashlib
import os
import sys
from datetime import datetime, timezone

DB_PATH      = "/opt/shared/scripts/prediction_db.json"
MANIFEST_PATH = "/opt/shared/scripts/prediction_manifest.json"
LEDGER_PATH   = "/opt/shared/scripts/prediction_ledger.jsonl"

def canonical_hash(pred: dict) -> str:
    """
    予測の canonical JSON をSHA-256でハッシュ化。
    可変フィールド（phase系の内部フィールド、article_links等）を除外して
    「予測の本質」を固定する。
    """
    CORE_FIELDS = [
        "prediction_id",
        "title",
        "title_en",
        "resolution_question",
        "resolution_question_en",
        "our_pick",
        "our_pick_prob",
        "oracle_deadline",
        "oracle_criteria",
        "hit_condition_en",
        "hit_condition_ja",
        "question_type",
        "ghost_url",
    ]
    core = {k: pred.get(k) for k in CORE_FIELDS}
    canonical = json.dumps(core, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"generated_at": None, "schema_version": "2.0", "total": 0, "predictions": {}}


def save_manifest(manifest: dict):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def append_ledger_event(event: dict):
    """NDJSON に1行追記（append-only）"""
    line = json.dumps(event, ensure_ascii=False)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manifest(preds: list, actor: str = "phase6") -> dict:
    """DB全件からmanifestを構築し、event_ledgerにCREATEDイベントを記録。"""
    now = now_iso()
    manifest = load_manifest()
    existing = manifest.get("predictions", {})

    new_entries = 0
    updated_entries = 0

    for p in preds:
        pid = p.get("prediction_id", "")
        if not pid:
            continue
        h = canonical_hash(p)

        if pid not in existing:
            # 新規エントリ
            existing[pid] = {
                "hash": h,
                "recorded_at": now,
                "status": p.get("status", ""),
                "verdict": p.get("verdict", "PENDING"),
            }
            append_ledger_event({
                "ts": now,
                "event": "REGISTERED",
                "prediction_id": pid,
                "hash": h,
                "status": p.get("status", ""),
                "actor": actor,
            })
            new_entries += 1
        else:
            old_h = existing[pid]["hash"]
            if old_h != h:
                # ハッシュ変化 = コアフィールドが変更された
                existing[pid]["hash"] = h
                existing[pid]["updated_at"] = now
                append_ledger_event({
                    "ts": now,
                    "event": "CORE_UPDATED",
                    "prediction_id": pid,
                    "old_hash": old_h,
                    "new_hash": h,
                    "actor": actor,
                })
                updated_entries += 1

            # status/verdict は常に最新を反映
            existing[pid]["status"]  = p.get("status", "")
            existing[pid]["verdict"] = p.get("verdict", "PENDING")

    manifest["generated_at"] = now
    manifest["schema_version"] = "2.0"
    manifest["total"] = len(preds)
    manifest["predictions"] = existing

    return manifest, new_entries, updated_entries


def integrity_check(preds: list, manifest: dict) -> dict:
    """
    現在のDBとmanifestを照合。
    Returns: {ok: bool, tampered: [], missing: [], extra: []}
    """
    existing = manifest.get("predictions", {})
    db_pids   = {p.get("prediction_id") for p in preds if p.get("prediction_id")}
    man_pids  = set(existing.keys())

    tampered = []
    for p in preds:
        pid = p.get("prediction_id")
        if not pid or pid not in existing:
            continue
        h = canonical_hash(p)
        if h != existing[pid]["hash"]:
            tampered.append(pid)

    missing = list(man_pids - db_pids)  # manifest にあるが DB にない
    extra   = list(db_pids - man_pids)  # DB にあるが manifest にない

    return {
        "ok": len(tampered) == 0 and len(missing) == 0,
        "tampered": tampered,
        "missing": missing,
        "extra_unregistered": extra,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true",
                        help="整合性チェックのみ（DB更新なし）")
    parser.add_argument("--actor", default="phase6",
                        help="イベントの実行者名")
    args = parser.parse_args()

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    preds = db["predictions"]
    print(f"Loaded DB: {len(preds)} predictions")

    if args.check_only:
        manifest = load_manifest()
        if not manifest.get("generated_at"):
            print("No manifest found. Run without --check-only first.")
            sys.exit(1)
        result = integrity_check(preds, manifest)
        print(f"\n=== Integrity Check ===")
        print(f"  Status:             {'✅ OK' if result['ok'] else '❌ TAMPERED'}")
        print(f"  Tampered hashes:    {len(result['tampered'])}")
        print(f"  Missing from DB:    {len(result['missing'])}")
        print(f"  Unregistered (new): {len(result['extra_unregistered'])}")
        if result["tampered"]:
            print(f"  Tampered IDs: {result['tampered'][:5]}")
        sys.exit(0 if result["ok"] else 1)

    # マニフェスト構築
    print("\nBuilding manifest...")
    manifest, new_entries, updated_entries = build_manifest(preds, actor=args.actor)
    save_manifest(manifest)

    print(f"  New registrations:  {new_entries}")
    print(f"  Core field updates: {updated_entries}")
    print(f"  Manifest total:     {manifest['total']}")
    print(f"  Saved to: {MANIFEST_PATH}")

    # 構築直後に整合性確認
    result = integrity_check(preds, manifest)
    print(f"\n=== Integrity Check (post-build) ===")
    print(f"  Status:             {'✅ OK' if result['ok'] else '❌ TAMPERED'}")
    print(f"  Tampered hashes:    {len(result['tampered'])}")
    print(f"  Unregistered (new): {len(result['extra_unregistered'])}")

    # ledger の行数を確認
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            ledger_lines = sum(1 for _ in f)
        print(f"\nEvent ledger entries: {ledger_lines}")
        print(f"Ledger path: {LEDGER_PATH}")

    print("\nPhase 6 complete.")


if __name__ == "__main__":
    main()
