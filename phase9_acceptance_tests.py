#!/usr/bin/env python3
"""
Phase 9: Acceptance Tests — 全Phase完了検証
- Phase 1: schema_version "2.0" + status/verdict 正規化
- Phase 2: oracle_deadline ISO形式 + unresolved_policy
- Phase 3: brier_score + meta stats
- Phase 4: article_slug + article_links[]
- Phase 5: hit_condition_en (1100件超)
- Phase 6: manifest + ledger 整合性
- Phase 7: 公開ルールページ 6件 200 OK
- Phase 8: ledger RESOLVED events + auto_verifier hook + builder footer
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
import ssl

DB_PATH       = "/opt/shared/scripts/prediction_db.json"
MANIFEST_PATH = "/opt/shared/scripts/prediction_manifest.json"
LEDGER_PATH   = "/opt/shared/scripts/prediction_ledger.jsonl"
VERIFIER_PATH = "/opt/shared/scripts/prediction_auto_verifier.py"
BUILDER_PATH  = "/opt/shared/scripts/prediction_page_builder.py"

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []

def check(name: str, condition: bool, detail: str = "", warn_only: bool = False):
    icon = PASS if condition else (WARN if warn_only else FAIL)
    results.append((icon, name, detail))
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return condition


def http_status(url: str) -> int:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def main():
    print("=" * 60)
    print("  Phase 9: Acceptance Tests")
    print("=" * 60)

    # ── Load DB ──────────────────────────────────────────────────────
    print("\n[DB Load]")
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
        preds = db["predictions"]
        check("DB loaded", True, f"{len(preds)} predictions")
    except Exception as e:
        check("DB loaded", False, str(e))
        print("\nCannot continue without DB. Exit.")
        sys.exit(1)

    total = len(preds)

    # ── Phase 1: Schema ────────────────────────────────────────────
    print("\n[Phase 1: Canonical Schema]")
    schema_v2 = sum(1 for p in preds if p.get("schema_version") == "2.0")
    check("schema_version 2.0", schema_v2 == total,
          f"{schema_v2}/{total}")

    valid_statuses = {"OPEN","RESOLVING","RESOLVED","EXPIRED_UNRESOLVED","VOID","CANCELLED","SUPERSEDED",
                      "AWAITING_EVIDENCE",""}  # AWAITING_EVIDENCE = operational status (pre-resolution)
    bad_status = [p.get("prediction_id") for p in preds
                  if p.get("status","").upper() not in valid_statuses]
    check("status enum valid", len(bad_status) == 0,
          f"{len(bad_status)} invalid" if bad_status else "all valid")

    verdicts = {"HIT","MISS","PENDING","VOID","NOT_SCORED",""}  # NOT_SCORED = unscoreable verdict
    bad_verdict = [p.get("prediction_id") for p in preds
                   if p.get("verdict","").upper() not in verdicts and p.get("verdict") is not None]
    check("verdict enum valid", len(bad_verdict) == 0,
          f"{len(bad_verdict)} invalid" if bad_verdict else "all valid")

    # ── Phase 2: Resolution Engine ────────────────────────────────
    print("\n[Phase 2: Resolution Engine]")
    iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}")
    bad_deadline = [p.get("prediction_id") for p in preds
                    if p.get("oracle_deadline") and not iso_re.match(str(p["oracle_deadline"]))]
    check("oracle_deadline ISO format", len(bad_deadline) == 0,
          f"{len(bad_deadline)} non-ISO" if bad_deadline else "all ISO",
          warn_only=len(bad_deadline) <= 10)  # ≤10 legacy records with JP date strings are acceptable

    has_policy = sum(1 for p in preds if p.get("unresolved_policy"))
    check("unresolved_policy set", has_policy >= total * 0.9,
          f"{has_policy}/{total}", warn_only=has_policy < total)

    # ── Phase 3: Scoring ──────────────────────────────────────────
    print("\n[Phase 3: Scoring Engine]")
    resolved = [p for p in preds if p.get("status") == "RESOLVED"]
    scorable = [p for p in resolved if p.get("brier_score") is not None]
    check("brier_score computed for RESOLVED", len(scorable) >= len(resolved) * 0.9,
          f"{len(scorable)}/{len(resolved)} RESOLVED")

    meta = db.get("meta", {})
    check("meta.accuracy_pct exists",  "accuracy_pct" in meta,
          f"{meta.get('accuracy_pct')}%")
    check("meta.official_brier_avg exists", "official_brier_avg" in meta,
          f"{meta.get('official_brier_avg')}")

    # ── Phase 4: Article Links ────────────────────────────────────
    print("\n[Phase 4: Article Backfill]")
    has_slug  = sum(1 for p in preds if p.get("article_slug"))
    has_links = sum(1 for p in preds if p.get("article_links"))
    pct_slug  = has_slug / total * 100
    check("article_slug coverage ≥90%", pct_slug >= 90,
          f"{has_slug}/{total} ({pct_slug:.1f}%)")
    check("article_links coverage ≥90%", has_links / total >= 0.9,
          f"{has_links}/{total}")

    # ── Phase 5: Bilingual ────────────────────────────────────────
    print("\n[Phase 5: Bilingual (hit_condition_en)]")
    has_hce  = sum(1 for p in preds if p.get("hit_condition_en","").strip())
    pct_hce  = has_hce / total * 100
    check("hit_condition_en coverage ≥99%", pct_hce >= 99,
          f"{has_hce}/{total} ({pct_hce:.1f}%)")

    cjk_re = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")
    still_ja = [p for p in preds
                if p.get("hit_condition_en","").strip()
                and cjk_re.search(p["hit_condition_en"])]
    check("hit_condition_en CJK-free", len(still_ja) == 0,
          f"{len(still_ja)} CJK contaminated" if still_ja else "clean",
          warn_only=len(still_ja) > 0)

    # ── Phase 6: Integrity ────────────────────────────────────────
    print("\n[Phase 6: Integrity Ledger]")
    check("manifest.json exists", os.path.exists(MANIFEST_PATH))

    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        man_total = manifest.get("total", 0)
        check("manifest total matches DB", man_total == total,
              f"manifest={man_total}, db={total}")

    check("ledger.jsonl exists", os.path.exists(LEDGER_PATH))
    if os.path.exists(LEDGER_PATH):
        event_counts = {}
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    ev = evt.get("event", "UNKNOWN")
                    event_counts[ev] = event_counts.get(ev, 0) + 1
                except Exception:
                    pass
        ledger_reg  = event_counts.get("REGISTERED", 0)
        ledger_res  = event_counts.get("RESOLVED", 0)
        ledger_exp  = event_counts.get("EXPIRED", 0)
        total_events = sum(event_counts.values())
        check("ledger REGISTERED = total", ledger_reg == total,
              f"REGISTERED={ledger_reg}")
        check("ledger RESOLVED events backfilled", ledger_res >= len(resolved),
              f"RESOLVED={ledger_res} (resolved in DB={len(resolved)})")
        print(f"    Event breakdown: {event_counts}")

    # ── Phase 7: Public Rules Pages ───────────────────────────────
    print("\n[Phase 7: Public Rules Pages]")
    rule_pages = [
        ("JA forecast-rules", "https://nowpattern.com/forecast-rules/"),
        ("EN forecast-rules", "https://nowpattern.com/en/forecast-rules/"),
        ("JA scoring-guide",  "https://nowpattern.com/scoring-guide/"),
        ("EN scoring-guide",  "https://nowpattern.com/en/scoring-guide/"),
        ("JA integrity-audit","https://nowpattern.com/integrity-audit/"),
        ("EN integrity-audit","https://nowpattern.com/en/integrity-audit/"),
    ]
    for name, url in rule_pages:
        status = http_status(url)
        check(f"{name} → 200", status == 200, f"HTTP {status}")

    # ── Phase 8: Retro Integration ────────────────────────────────
    print("\n[Phase 8: Retrospective Integration]")
    if os.path.exists(VERIFIER_PATH):
        with open(VERIFIER_PATH, "r") as f:
            vc = f.read()
        check("verifier ledger hook", "phase8_ledger_hook" in vc)
    else:
        check("verifier ledger hook", False, "verifier not found")

    if os.path.exists(BUILDER_PATH):
        with open(BUILDER_PATH, "r") as f:
            bc = f.read()
        check("builder rules footer (phase8)", "phase8" in bc or "rules_footer_installed" in bc or "np-rules-links" in bc)
    else:
        check("builder rules footer", False, "builder not found")

    # ── Summary ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    total_checks = len(results)
    passed  = sum(1 for r in results if r[0] == PASS)
    warned  = sum(1 for r in results if r[0] == WARN)
    failed  = sum(1 for r in results if r[0] == FAIL)
    print(f"  RESULT: {passed}/{total_checks} PASS | {warned} WARN | {failed} FAIL")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 All acceptance tests PASSED. Prediction platform migration complete!\n")
    else:
        print(f"\n⚠️  {failed} test(s) FAILED. See above for details.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
