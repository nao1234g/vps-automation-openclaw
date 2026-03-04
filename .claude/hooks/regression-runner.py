#!/usr/bin/env python3
"""
REGRESSION RUNNER — ECC Pipeline: Error → Codify → Check → Verify
===================================================================
目的:
  fact-checker.py の全ガードパターンを意図的にトリガーするメッセージで
  実際にブロックされるか確認し、ガードが壊れていれば Telegram 通知する。

  「ガードを追加しても、ガード自体が壊れていたら意味がない」
  → 毎朝このスクリプトが全ガードの動作を確認する。

使い方:
  python3 regression-runner.py [PROJECT_DIR]

VPS cron 例 (04:00 JST):
  0 19 * * * python3 /opt/shared/scripts/regression-runner.py /opt >> /var/log/regression.log 2>&1

世界標準の根拠:
  Netflix Chaos Engineering: 意図的に障害を起こし回復力を確認
  GitHub CI: PRごとにテストが動き、壊れたらマージ不可
  Amazon PIE: パターン × テスト × 自動化
"""
import sys
import os
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent.parent
FACT_CHECKER = PROJECT_DIR / ".claude" / "hooks" / "fact-checker.py"
PATTERNS_FILE = PROJECT_DIR / ".claude" / "hooks" / "state" / "mistake_patterns.json"
CRON_ENV = Path("/opt/cron-env.sh")

def load_env():
    env = {}
    if CRON_ENV.exists():
        for line in CRON_ENV.read_text().splitlines():
            if line.startswith("export "):
                k, _, v = line[7:].strip().partition("=")
                env[k] = v.strip().strip('"').strip("'")
    return env

def send_telegram(msg: str):
    env = load_env()
    bot_token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        print("[REGRESSION] Telegram設定なし、通知スキップ")
        return
    import urllib.request
    data = json.dumps({
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"[REGRESSION] Telegram送信エラー: {e}")

def run_fact_checker(test_message: str) -> int:
    """fact-checker.py を test_message で実行し、exit codeを返す"""
    if not FACT_CHECKER.exists():
        return -1
    env_vars = os.environ.copy()
    env_vars["CLAUDE_PROJECT_DIR"] = str(PROJECT_DIR)

    # テスト用トランスクリプトを作成（fact-checker.py が期待する形式）
    # {"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}]}}
    test_transcript = PROJECT_DIR / ".claude" / "hooks" / "state" / "_test_transcript.jsonl"
    test_transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript_entry = {
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": test_message}]
        }
    }
    with open(test_transcript, "w", encoding="utf-8") as f:
        f.write(json.dumps(transcript_entry, ensure_ascii=False) + "\n")

    # stdin: fact-checker.py は {"transcript_path": "..."} を受け取る
    input_data = json.dumps({
        "transcript_path": str(test_transcript)
    })

    try:
        result = subprocess.run(
            [sys.executable, str(FACT_CHECKER)],
            input=input_data,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            env=env_vars
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        return -2
    except Exception as e:
        print(f"[REGRESSION] 実行エラー: {e}")
        return -3
    finally:
        # テスト用トランスクリプトを削除
        if test_transcript.exists():
            test_transcript.unlink()

# ── テストケース定義 ─────────────────────────────────────────────────────────────
# format: (guard_name, trigger_message, should_block)
BUILTIN_TESTS = [
    # パターンに対して、直接マッチする文字列で試験する
    ("X_API_SUBSCRIPTION",
     "X API $100/月のプランがあります。",  # X API[$]数字/月 に直接マッチ
     True),
    ("X_API_TIER",
     "X API Pro plan を利用してください。",  # X API Pro plan にマッチ
     True),
    ("ANTHROPIC_API_BILLING",
     "Anthropic API従量課金を使用する方法です。",  # Anthropic API従量...を使用 にマッチ
     True),
    ("AISAINTEL_GHOST",
     "@aisaintelに投稿しましょう。",
     True),
    ("NEGATIVE_CONTROL_1",
     "nowpattern.comの記事を更新しました。確認してください。",
     False),  # これはブロックされてはいけない（正常なメッセージ）
]

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M JST")
    print(f"\n[REGRESSION RUNNER] 開始: {now}")
    print(f"  Project: {PROJECT_DIR}")
    print(f"  fact-checker: {'OK' if FACT_CHECKER.exists() else 'MISSING'}")

    if not FACT_CHECKER.exists():
        msg = f"⛔ [REGRESSION] fact-checker.py が見つかりません！\n{FACT_CHECKER}"
        print(msg)
        send_telegram(msg)
        sys.exit(1)

    # ── 動的パターンも含めてテスト ───────────────────────────────────────────
    dynamic_tests = []
    if PATTERNS_FILE.exists():
        try:
            patterns = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
            for p in patterns:
                name = p.get("name", "")
                pattern = p.get("pattern", "")
                if name and pattern:
                    # example フィールドがあればそれを使う（推奨）
                    # なければパターンにマッチする最小限の文字列を試みる
                    example = p.get("example", "")
                    if example:
                        trigger = example
                    else:
                        # フォールバック: 正規表現から最小限のリテラル部分を抽出
                        # ルックアヘッドなど複雑な構文を含む場合は不正確になる可能性がある
                        simple = re.sub(r"[\\()[\]{}.*+?^$|]", "", pattern)[:30]
                        trigger = f"テスト: {simple} に関連する作業を行いました。"
                    dynamic_tests.append((name, trigger, True))
        except Exception:
            pass

    all_tests = BUILTIN_TESTS + dynamic_tests
    results = []
    failures = []

    for name, message, should_block in all_tests:
        exit_code = run_fact_checker(message)
        actually_blocked = (exit_code == 2)
        passed = (actually_blocked == should_block)
        status = "✅ PASS" if passed else "❌ FAIL"
        results.append((name, status, exit_code, should_block))
        if not passed:
            failures.append((name, should_block, exit_code))
        print(f"  {status}: [{name}] exit={exit_code} (expect_block={should_block})")

    total = len(results)
    passed_count = sum(1 for _, s, _, _ in results if "PASS" in s)

    print(f"\n結果: {passed_count}/{total} PASS")

    # ── Telegram 通知 ─────────────────────────────────────────────────────────
    if failures:
        lines = [f"⛔ *[REGRESSION] ガード異常検知* ({now})"]
        lines.append(f"失敗: {len(failures)}/{total}")
        for name, should_block, exit_code in failures:
            action = "ブロックされるべきだった" if should_block else "通過すべきだった"
            lines.append(f"  ❌ {name}: {action} (exit={exit_code})")
        lines.append("\n→ fact-checker.py を今すぐ確認してください")
        msg = "\n".join(lines)
        print(msg)
        send_telegram(msg)
        sys.exit(1)
    else:
        msg = (
            f"✅ *[REGRESSION] 全ガード正常* ({now})\n"
            f"  {total}件のテスト、全PASS\n"
            f"  保護されているミスパターン: {total - len([t for t in BUILTIN_TESTS if not t[2]])}件"
        )
        print(msg)
        # 週次レポートとして送信（毎日は送らない — 月曜のみ）
        if datetime.now().weekday() == 0:  # 月曜日
            send_telegram(msg)
        sys.exit(0)

if __name__ == "__main__":
    main()
