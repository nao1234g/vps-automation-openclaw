#!/usr/bin/env python3
"""
Phase 8: Retrospective Loop Integration
- RESOLVED/EXPIRED/VOID イベントを prediction_ledger.jsonl にバックフィル
- manifest の status/verdict を最新DB状態に同期
- prediction_auto_verifier.py に ledger hook を追加（将来の解決を自動記録）
- prediction_page_builder.py の footer に公開ルールページへのリンク追加
"""
import json
import os
import re
import shutil
from datetime import datetime, timezone

DB_PATH        = "/opt/shared/scripts/prediction_db.json"
MANIFEST_PATH  = "/opt/shared/scripts/prediction_manifest.json"
LEDGER_PATH    = "/opt/shared/scripts/prediction_ledger.jsonl"
VERIFIER_PATH  = "/opt/shared/scripts/prediction_auto_verifier.py"
BUILDER_PATH   = "/opt/shared/scripts/prediction_page_builder.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_ledger_event(event: dict):
    line = json.dumps(event, ensure_ascii=False)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_existing_ledger_events() -> set:
    """ledger 内の (prediction_id, event) タプルのセット"""
    existing = set()
    if not os.path.exists(LEDGER_PATH):
        return existing
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                existing.add((evt.get("prediction_id"), evt.get("event")))
            except json.JSONDecodeError:
                pass
    return existing


def backfill_resolved_events(preds: list) -> int:
    """
    解決済み予測の RESOLVED / EXPIRED_UNRESOLVED / VOID イベントをバックフィル
    """
    existing = get_existing_ledger_events()
    count = 0

    # status→event name マッピング
    status_event_map = {
        "RESOLVED":             "RESOLVED",
        "EXPIRED_UNRESOLVED":   "EXPIRED",
        "VOID":                 "VOID",
        "CANCELLED":            "CANCELLED",
        "SUPERSEDED":           "SUPERSEDED",
    }

    for p in preds:
        pid    = p.get("prediction_id", "")
        status = p.get("status", "").upper()

        if not pid or status not in status_event_map:
            continue

        event_name = status_event_map[status]
        key = (pid, event_name)

        if key in existing:
            continue  # 既に記録済み

        # 解決タイムスタンプ（なければ now）
        ts = p.get("resolved_at") or p.get("oracle_deadline") or now_iso()
        if ts and len(ts) < 11:
            ts = ts + "T00:00:00Z"

        event = {
            "ts":            ts,
            "event":         event_name,
            "prediction_id": pid,
            "actor":         "phase8_backfill",
        }

        if event_name == "RESOLVED":
            event["verdict"]     = p.get("verdict", "PENDING")
            event["brier_score"] = p.get("brier_score")

        append_ledger_event(event)
        count += 1

    return count


def sync_manifest(preds: list) -> int:
    """manifest の status/verdict を現在の DB に同期（ハッシュ再計算はしない）"""
    if not os.path.exists(MANIFEST_PATH):
        print("  manifest not found — skipping sync")
        return 0

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    entries = manifest.get("predictions", {})
    updated = 0

    for p in preds:
        pid = p.get("prediction_id", "")
        if not pid or pid not in entries:
            continue
        old_status  = entries[pid].get("status", "")
        old_verdict = entries[pid].get("verdict", "")
        new_status  = p.get("status", "")
        new_verdict = p.get("verdict", "PENDING")

        if old_status != new_status or old_verdict != new_verdict:
            entries[pid]["status"]  = new_status
            entries[pid]["verdict"] = new_verdict
            updated += 1

    manifest["predictions"] = entries
    manifest["generated_at"] = now_iso()

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return updated


# ── Hook: prediction_auto_verifier.py ─────────────────────────────────────────

VERIFIER_HOOK_MARKER = "# [Phase8] ledger_hook_installed"
VERIFIER_HOOK_CODE = '''
# [Phase8] ledger_hook_installed
def _phase8_ledger_hook(prediction_id: str, verdict: str, brier_score, ts: str = None):
    """解決時に prediction_ledger.jsonl へ RESOLVED イベントを追記する（Phase 8 hook）"""
    import hashlib
    ledger_path = "/opt/shared/scripts/prediction_ledger.jsonl"
    event = {
        "ts":            ts or __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event":         "RESOLVED",
        "prediction_id": prediction_id,
        "verdict":       verdict,
        "brier_score":   brier_score,
        "actor":         "auto_verifier",
    }
    try:
        with open(ledger_path, "a", encoding="utf-8") as _f:
            _f.write(__import__("json").dumps(event, ensure_ascii=False) + "\\n")
    except Exception as _e:
        pass  # ledger書き込み失敗は無視（本体処理を止めない）
'''

VERIFIER_CALL_MARKER = "# [Phase8] call_ledger_hook"
VERIFIER_CALL_CODE = '''            # [Phase8] call_ledger_hook
            _brier = updated_pred.get("brier_score") if updated_pred else None
            _verdict = updated_pred.get("verdict") if updated_pred else "PENDING"
            _ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            _phase8_ledger_hook(prediction_id, _verdict, _brier, _ts_now)
'''


def inject_verifier_hook() -> str:
    """
    prediction_auto_verifier.py に _phase8_ledger_hook 関数と呼び出しを注入する。
    既に注入済みならスキップ。
    """
    if not os.path.exists(VERIFIER_PATH):
        return "SKIP: verifier not found"

    with open(VERIFIER_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if VERIFIER_HOOK_MARKER in content:
        return "SKIP: hook already installed"

    # バックアップ
    ts_str = datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copy2(VERIFIER_PATH, f"{VERIFIER_PATH}.bak-phase8-{ts_str}")

    # 1. 関数定義をファイル末尾の if __name__ == "__main__": の直前に挿入
    if 'if __name__ == "__main__":' in content:
        content = content.replace(
            'if __name__ == "__main__":',
            VERIFIER_HOOK_CODE + '\nif __name__ == "__main__":',
            1
        )
    else:
        content = content + "\n" + VERIFIER_HOOK_CODE

    # 2. 呼び出しコードを DB 保存直後に挿入
    # DB保存のコード: "with open(PREDICTION_DB, "w", encoding="utf-8") as f:"
    # その直後の `json.dump` 行の後に挿入
    # ターゲット：resolved_atを設定した後のjson.dump+
    CALL_TARGET = '    log(f"DB updated: {prediction_id}'
    if CALL_TARGET in content and VERIFIER_CALL_MARKER not in content:
        content = content.replace(
            CALL_TARGET,
            VERIFIER_CALL_CODE + "\n" + CALL_TARGET,
            1
        )

    with open(VERIFIER_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    return "OK: hook injected"


# ── Footer links in prediction_page_builder.py ────────────────────────────────

BUILDER_FOOTER_MARKER = "# [Phase8] rules_footer_installed"
BUILDER_RULES_LINKS_JA = """
        <div class="np-rules-links" style="margin-top:2em;padding:1.2em 1.5em;background:#f8f9fa;border-radius:8px;font-size:0.9em;">
          <strong>📚 Nowpatternの予測について</strong><br>
          <a href="/forecast-rules/">予測ルール</a> ·
          <a href="/scoring-guide/">スコアリングガイド（Brier Score）</a> ·
          <a href="/integrity-audit/">整合性・監査</a>
        </div>
"""
BUILDER_RULES_LINKS_EN = """
        <div class="np-rules-links" style="margin-top:2em;padding:1.2em 1.5em;background:#f8f9fa;border-radius:8px;font-size:0.9em;">
          <strong>📚 About Nowpattern Predictions</strong><br>
          <a href="/en/forecast-rules/">Forecast Rules</a> ·
          <a href="/en/scoring-guide/">Scoring Guide (Brier Score)</a> ·
          <a href="/en/integrity-audit/">Integrity &amp; Audit</a>
        </div>
"""


def inject_builder_footer() -> str:
    """prediction_page_builder.py にルールページへのリンクを注入"""
    if not os.path.exists(BUILDER_PATH):
        return "SKIP: builder not found"

    with open(BUILDER_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if BUILDER_FOOTER_MARKER in content:
        return "SKIP: footer already installed"

    # バックアップ
    ts_str = datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copy2(BUILDER_PATH, f"{BUILDER_PATH}.bak-phase8-{ts_str}")

    # JA page footer: </body> タグの直前に挿入
    # ターゲット: build_ja_page() 関数内の </body> → </html> の手前
    # 実際は np-resolved セクション閉じタグ or </main> の直前
    # builder の構造を確認して適切な場所に入れる

    # JA版フッター — _footer_html または </body> の直前
    target_ja = '# [Phase8] rules_footer_installed\n'
    insert_comment = f"# [Phase8] rules_footer_installed\n# Rules links injected into page HTML below\n"

    # 簡易実装: np-scoreboard の下にスタティックHTMLとして注入するのではなく
    # ページ生成関数の末尾 (</div>\n</body>) の直前に注入
    JA_END_MARKER = "</body>\n</html>"
    if JA_END_MARKER in content:
        content = content.replace(
            JA_END_MARKER,
            BUILDER_RULES_LINKS_JA + JA_END_MARKER,
            1  # 最初の出現のみ (JA page)
        )
        # EN page (2回目の出現)
        if JA_END_MARKER in content:
            idx = content.rfind(JA_END_MARKER)
            content = content[:idx] + BUILDER_RULES_LINKS_EN + content[idx:]

    # マーカーを先頭に追加
    content = insert_comment + content

    with open(BUILDER_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    return "OK: footer injected"


def main():
    print("=== Phase 8: Retrospective Loop Integration ===\n")

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    preds = db["predictions"]
    print(f"Loaded DB: {len(preds)} predictions")

    # Step 1: Backfill resolved events to ledger
    print("\n[Step 1] Backfilling RESOLVED events to ledger...")
    n_backfilled = backfill_resolved_events(preds)
    print(f"  Backfilled: {n_backfilled} events")

    # Verify ledger count
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            total_lines = sum(1 for _ in f)
        print(f"  Ledger total entries now: {total_lines}")

    # Step 2: Sync manifest status/verdict
    print("\n[Step 2] Syncing manifest status/verdict...")
    n_updated = sync_manifest(preds)
    print(f"  Manifest entries updated: {n_updated}")

    # Step 3: Inject ledger hook into auto_verifier
    print("\n[Step 3] Injecting ledger hook into prediction_auto_verifier.py...")
    result = inject_verifier_hook()
    print(f"  {result}")

    # Step 4: Add rules links to prediction_page_builder.py
    print("\n[Step 4] Adding rules page links to prediction_page_builder.py...")
    result = inject_builder_footer()
    print(f"  {result}")

    # Step 5: Rebuild prediction pages (trigger builder)
    print("\n[Step 5] Triggering prediction page rebuild...")
    import subprocess
    r = subprocess.run(
        ["python3", BUILDER_PATH, "--lang", "ja"],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode == 0:
        print(f"  ✅ JA page rebuilt")
    else:
        print(f"  ⚠️  JA builder: {r.stderr[:200]}")

    r = subprocess.run(
        ["python3", BUILDER_PATH, "--lang", "en"],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode == 0:
        print(f"  ✅ EN page rebuilt")
    else:
        print(f"  ⚠️  EN builder: {r.stderr[:200]}")

    # Step 6: Final ledger summary
    print("\n[Step 6] Final ledger summary...")
    event_counts = {}
    if os.path.exists(LEDGER_PATH):
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
    for ev, cnt in sorted(event_counts.items()):
        print(f"  {ev}: {cnt}")

    print("\n=== Phase 8 Complete ===")


if __name__ == "__main__":
    main()
