#!/usr/bin/env python3
"""
prediction_cron_update.py — 予測システム日次自動更新（cron用）

毎日1回実行して以下を自動処理:
1. overdue予測のTelegram通知
2. 予測ページ（/predictions/ + /en-predictions/）をGhostに再生成
3. 市場データの自動リンク試行

VPS cron (毎日10:00 JST = 01:00 UTC):
  0 1 * * * /usr/bin/python3 /opt/shared/scripts/prediction_cron_update.py >> /var/log/prediction-cron.log 2>&1
"""

import subprocess
import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run(cmd, label):
    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=SCRIPTS_DIR
        )
        if result.stdout:
            print(result.stdout[:2000])
        if result.returncode != 0 and result.stderr:
            print(f"WARN: {result.stderr[:500]}")
        return result.returncode == 0
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print("=== Prediction Cron Update Start ===")

    # Step 1: Overdue通知
    run(
        [sys.executable, os.path.join(SCRIPTS_DIR, "prediction_tracker.py"), "overdue", "--notify"],
        "Step 1: Overdue Notifications"
    )

    # Step 2: 予測ページ更新（日英両方）
    run(
        [sys.executable, os.path.join(SCRIPTS_DIR, "prediction_page_builder.py"), "--update"],
        "Step 2: Update /predictions/ pages (JA+EN)"
    )

    # Step 3: 市場自動リンク（未リンクの予測をPolymarket/Manifoldで検索）
    run(
        [sys.executable, os.path.join(SCRIPTS_DIR, "prediction_resolver.py"), "--auto-link"],
        "Step 3: Auto-link predictions to markets"
    )

    # Step 4: 予測解決エンジン（リンク済み予測の確率チェック → 自動判定）
    run(
        [sys.executable, os.path.join(SCRIPTS_DIR, "prediction_resolver.py")],
        "Step 4: Resolve predictions (market probability check)"
    )

    # Step 5: AI検証ループ（期限切れトリガーをGeminiで判定 → 自動適用）
    run(
        [sys.executable, os.path.join(SCRIPTS_DIR, "prediction_verifier.py"), "--auto-judge"],
        "Step 5: AI verification + auto-judge (Gemini)"
    )

    print("\n=== Prediction Cron Update Complete ===")


if __name__ == "__main__":
    main()
