#!/usr/bin/env python3
"""
playwright_verify.py — ローカルから verify_ui.py を実行し state を保存するラッパー
=================================================================================
Usage:
  python3 scripts/playwright_verify.py             # quick suite (default)
  python3 scripts/playwright_verify.py full         # full suite
  python3 scripts/playwright_verify.py --clear      # state をリセット

このスクリプトを実行することで:
1. VPS上の verify_ui.py が headless Chromium で nowpattern.com をテスト
2. 結果を .claude/hooks/state/ui_verification.json に保存
3. fact-checker.py がこのstateを参照し、PASS時のみ「直りました」報告を許可

Exit code:
  0 = PLAYWRIGHT_PASS
  1 = PLAYWRIGHT_FAIL
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Windows cp932 対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VPS_IP = "163.44.124.123"
LOCAL_STATE = Path(__file__).parent.parent / ".claude" / "hooks" / "state" / "ui_verification.json"


def main():
    if "--clear" in sys.argv:
        if LOCAL_STATE.exists():
            LOCAL_STATE.unlink()
            print("✅ ui_verification.json をリセットしました")
        else:
            print("⚠️ state ファイルが見つかりません（すでにリセット済み）")
        sys.exit(0)

    suite = "full" if "full" in sys.argv else "quick"

    print(f"🎭 Playwright UI検証 [{suite}] を実行中...")
    print(f"   接続先: root@{VPS_IP}")
    print(f"   スクリプト: /opt/shared/scripts/verify_ui.py")
    print()

    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "ConnectTimeout=15",
                "-o", "StrictHostKeyChecking=no",
                f"root@{VPS_IP}",
                f"python3 /opt/shared/scripts/verify_ui.py --suite {suite} 2>&1"
            ],
            capture_output=False,
            text=True,
            timeout=90
        )
        all_pass = result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ タイムアウト: VPSに接続できませんでした")
        all_pass = False
    except Exception as e:
        print(f"❌ エラー: {e}")
        all_pass = False

    # ローカルstateに保存
    LOCAL_STATE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "checked_at": datetime.now().isoformat(),
        "all_pass": all_pass,
        "suite": suite
    }
    LOCAL_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    if all_pass:
        print(f"\n✅ PLAYWRIGHT_PASS — ローカルstateに保存: {LOCAL_STATE.name}")
        print("   → fact-checker.py が 30分間 UI完了報告を許可します")
    else:
        print(f"\n❌ PLAYWRIGHT_FAIL — エラーを修正して再実行してください")
        print("   → 「直りました」は PLAYWRIGHT_PASS まで報告できません")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
