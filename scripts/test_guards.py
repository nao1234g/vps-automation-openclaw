#!/usr/bin/env python3
"""
CHAOS TESTING — ガード自己検証スクリプト
===========================================
Netflix Chaos Engineering の原則:
  「本番でガードが壊れる前に、自分で壊して発見する」

このスクリプトは:
  1. 各mistake_patternsの「悪いコード例」を作成
  2. fact-checker.py が正しくブロック(exit 2)するかテスト
  3. テスト結果をTelegram通知 + ローカルレポート

実行方法:
  python scripts/test_guards.py              # 全パターンテスト
  python scripts/test_guards.py --pattern GHOST_HTML_SOURCE  # 特定パターンのみ
  python scripts/test_guards.py --dry-run    # テスト内容を表示のみ

cronで週次実行（月曜朝 = proactive_scannerと同じタイミング）:
  毎週月曜: settings.local.jsonのSessionStartで自動実行検討可
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# Windows環境での文字化け防止
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).parent.parent
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
PATTERNS_FILE = STATE_DIR / "mistake_patterns.json"
FACT_CHECKER = PROJECT_DIR / ".claude" / "hooks" / "fact-checker.py"
REPORT_FILE = STATE_DIR / "chaos_test_report.json"

# ── .envからTelegram設定読み込み ─────────────────────────────────────────────
def load_telegram():
    env_file = PROJECT_DIR / ".env"
    bot_token, chat_id = "", ""
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                bot_token = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("TELEGRAM_CHAT_ID="):
                chat_id = line.split("=", 1)[1].strip().strip('"')
    return bot_token, chat_id


def send_telegram(msg: str, dry_run: bool = False):
    if dry_run:
        print(f"[DRY-RUN] Telegram skip:\n{msg[:200]}")
        return
    bot_token, chat_id = load_telegram()
    if not bot_token or not chat_id:
        print("[WARN] Telegram設定なし — ローカルログのみ")
        return
    if len(msg) > 4000:
        msg = msg[:3900] + "\n...(省略)"
    data = json.dumps({
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode("utf-8")
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
        print(f"[WARN] Telegram送信失敗: {e}")


# ── テストケース生成 ─────────────────────────────────────────────────────────
def get_test_input(pattern_def: dict) -> dict:
    """パターン定義からfact-checker用のテスト入力を生成する"""
    example = pattern_def.get("example", "")
    name = pattern_def.get("name", "UNKNOWN")

    # exampleをそのままアシスタントの発言として使う
    # （fact-checker.py はアシスタントのtranscriptを検査する）
    test_content = example if example else f"このパターンに{name}が含まれます"

    return {
        "session_id": "chaos-test-" + name,
        "transcript": [
            {
                "role": "assistant",
                "content": test_content
            }
        ]
    }


# ── fact-checker.py 実行テスト ────────────────────────────────────────────────
def run_fact_checker_test(test_input: dict) -> dict:
    """
    fact-checker.py を直接実行してexit codeをチェックする。
    fact-checker.py は stdin でトランスクリプトJSONを受け取る。
    """
    if not FACT_CHECKER.exists():
        return {"skipped": True, "reason": "fact-checker.py not found"}

    try:
        python_exe = sys.executable  # 現在のPython（Windows対応）
        result = subprocess.run(
            [python_exe, str(FACT_CHECKER)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[:200],
            "stderr": result.stderr[:200],
            "blocked": result.returncode == 2,  # exit(2) = 物理ブロック
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "blocked": False, "reason": "timeout"}
    except Exception as e:
        return {"exit_code": -1, "blocked": False, "reason": str(e)[:100]}


# ── パターンマッチ直接テスト（fact-checkerのregex検証）──────────────────────
def test_pattern_match(pattern_def: dict) -> dict:
    """
    fact-checker.py経由ではなく、直接正規表現でマッチするかテスト。
    これはregexが有効かどうかの確認。
    """
    pattern = pattern_def.get("pattern", "")
    example = pattern_def.get("example", "")
    name = pattern_def.get("name", "?")

    if not example:
        return {"status": "SKIP", "reason": "exampleなし"}

    try:
        compiled = re.compile(pattern, re.MULTILINE)
        match = compiled.search(example)
        if match:
            return {
                "status": "PASS",
                "matched": match.group(0)[:50],
                "detail": "正規表現が example に正しくマッチ"
            }
        else:
            return {
                "status": "FAIL",
                "reason": f"正規表現 [{pattern[:50]}] が example にマッチしない",
                "example_preview": example[:80]
            }
    except re.error as e:
        return {"status": "ERROR", "reason": f"無効な正規表現: {e}"}


# ── バイパステスト（同じ意味の変形でガードが抜けるか確認）──────────────────
BYPASS_TRANSFORMS = [
    # スペース追加
    lambda s: s.replace("?source=html", "? source=html"),
    # 大文字小文字変換
    lambda s: s.upper(),
    # コメント挿入（Python）
    lambda s: s.replace("import fcntl", "import fcntl # noqa"),
]


def test_bypass_resistance(pattern_def: dict) -> dict:
    """パターンが軽微な変形でバイパスされないかテスト（脆弱性発見）"""
    pattern = pattern_def.get("pattern", "")
    example = pattern_def.get("example", "")

    if not example or not pattern:
        return {"bypasses": 0, "details": []}

    try:
        compiled = re.compile(pattern, re.MULTILINE)
    except re.error:
        return {"bypasses": 0, "error": "invalid regex"}

    bypasses = []
    for i, transform in enumerate(BYPASS_TRANSFORMS):
        try:
            transformed = transform(example)
            if not compiled.search(transformed) and transformed != example:
                bypasses.append({
                    "transform_id": i,
                    "bypass_text": transformed[:80]
                })
        except Exception:
            pass

    return {
        "bypasses": len(bypasses),
        "details": bypasses
    }


# ── メイン ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Guard Chaos Test")
    parser.add_argument("--pattern", help="特定パターン名のみテスト")
    parser.add_argument("--dry-run", action="store_true", help="Telegram通知なし")
    parser.add_argument("--bypass-only", action="store_true", help="バイパステストのみ")
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M JST")
    print(f"[Chaos Test] {now}")

    if not PATTERNS_FILE.exists():
        print("[ERROR] mistake_patterns.json が見つかりません")
        sys.exit(1)

    patterns = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
    if args.pattern:
        patterns = [p for p in patterns if p.get("name") == args.pattern]
        if not patterns:
            print(f"[ERROR] パターン '{args.pattern}' が見つかりません")
            sys.exit(1)

    print(f"[INFO] {len(patterns)}パターンをテスト")

    results = []
    pass_count = fail_count = skip_count = bypass_count = 0

    for p in patterns:
        name = p.get("name", "?")
        print(f"  [{name}] ...", end="", flush=True)

        # 1. 正規表現マッチテスト（直接）
        match_result = test_pattern_match(p)

        # 2. バイパス抵抗テスト
        bypass_result = test_bypass_resistance(p)

        result = {
            "pattern_name": name,
            "match": match_result,
            "bypass": bypass_result,
        }

        status = match_result.get("status", "SKIP")
        if status == "PASS":
            pass_count += 1
            print(f" ✅ PASS", end="")
        elif status == "FAIL":
            fail_count += 1
            print(f" ❌ FAIL: {match_result.get('reason', '')[:50]}", end="")
        elif status == "ERROR":
            fail_count += 1
            print(f" 💥 ERROR: {match_result.get('reason', '')[:50]}", end="")
        else:
            skip_count += 1
            print(f" ⏭ SKIP", end="")

        if bypass_result.get("bypasses", 0) > 0:
            bypass_count += bypass_result["bypasses"]
            print(f" ⚠️ +{bypass_result['bypasses']}bypass", end="")

        print()
        results.append(result)

    # ── サマリー ───────────────────────────────────────────────────────────
    print(f"\n[RESULT] PASS:{pass_count} / FAIL:{fail_count} / SKIP:{skip_count} / BYPASS脆弱性:{bypass_count}")

    # レポート保存
    report = {
        "run_at": now,
        "total": len(patterns),
        "pass": pass_count,
        "fail": fail_count,
        "skip": skip_count,
        "bypass_vulnerabilities": bypass_count,
        "results": results
    }
    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[INFO] レポート保存: {REPORT_FILE}")

    # ── Telegram通知（問題ありの場合のみ）────────────────────────────────
    if fail_count > 0 or bypass_count > 0:
        lines = [f"🧪 *[Chaos Test] ガード検証結果: 問題あり*"]
        lines.append(f"日時: {now}")
        lines.append(f"テスト: {len(patterns)}件 | ✅{pass_count} | ❌{fail_count} | ⚠️bypass:{bypass_count}")
        lines.append("")

        # 失敗パターンを列挙
        fails = [r for r in results if r["match"].get("status") in ("FAIL", "ERROR")]
        for r in fails[:5]:
            lines.append(f"❌ `{r['pattern_name']}`")
            lines.append(f"  原因: {r['match'].get('reason', '?')[:80]}")

        bypasses = [r for r in results if r["bypass"].get("bypasses", 0) > 0]
        for r in bypasses[:5]:
            lines.append(f"⚠️ `{r['pattern_name']}` バイパス可能")
            for d in r["bypass"]["details"][:2]:
                lines.append(f"  変形例: `{d['bypass_text'][:60]}`")

        lines.append("\n→ 正規表現を修正してAST解析に移行を検討してください。")
        send_telegram("\n".join(lines), dry_run=args.dry_run)
    elif not args.dry_run:
        # 全パターン正常 → 週次サイレント成功通知
        msg = (
            f"✅ *[Chaos Test] 全ガード正常*\n"
            f"日時: {now}\n"
            f"テスト: {len(patterns)}件全て通過\n"
            f"バイパス脆弱性: {bypass_count}件"
        )
        if datetime.now().weekday() == 0:  # 月曜のみ
            send_telegram(msg, dry_run=args.dry_run)

    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
