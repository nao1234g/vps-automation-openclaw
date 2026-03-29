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
import tempfile
import time
from pathlib import Path
from datetime import datetime
from guard_pattern_utils import extract_guard_pattern_names

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent.parent
FACT_CHECKER = PROJECT_DIR / ".claude" / "hooks" / "fact-checker.py"
NORTH_STAR_GUARD = PROJECT_DIR / ".claude" / "hooks" / "north-star-guard.py"
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

def _safe_unlink(path: Path) -> None:
    for _ in range(8):
        try:
            path.unlink()
            return
        except FileNotFoundError:
            return
        except PermissionError:
            time.sleep(0.05)
        except OSError:
            return


def run_fact_checker(test_message: str, extra_env: dict | None = None) -> int:
    """fact-checker.py を test_message で実行し、exit codeを返す"""
    if not FACT_CHECKER.exists():
        return -1
    env_vars = os.environ.copy()
    env_vars["CLAUDE_PROJECT_DIR"] = str(PROJECT_DIR)
    if extra_env:
        env_vars.update(extra_env)

    # テスト用トランスクリプトを作成（fact-checker.py が期待する形式）
    # {"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}]}}
    test_transcript: Path | None = None
    transcript_entry = {
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": test_message}]
        }
    }
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".jsonl",
        prefix="fact_checker_",
        delete=False,
    ) as f:
        test_transcript = Path(f.name)
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
        if test_transcript is not None:
            _safe_unlink(test_transcript)


def run_fact_checker_with_edits(last_message: str, edited_files: list[str] | None = None, extra_env: dict | None = None) -> int:
    """Edit tool_use を含むトランスクリプトで fact-checker.py を実行。
    proof-checking gate（未検証Edit検知）をテストするために使用。
    edited_files: Edit対象ファイルパスのリスト（例: ["/tmp/test.py"]）
    """
    if not FACT_CHECKER.exists():
        return -1
    env_vars = os.environ.copy()
    env_vars["CLAUDE_PROJECT_DIR"] = str(PROJECT_DIR)
    if extra_env:
        env_vars.update(extra_env)

    test_transcript: Path | None = None
    entries = []
    # Edit tool_use エントリを追加（検証Bashなし → 未検証状態を作る）
    if edited_files:
        for fp in edited_files:
            entries.append({
                "type": "assistant",
                "message": {
                    "content": [{
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": fp, "old_string": "x", "new_string": "y"}
                    }]
                }
            })
    # 最後にテキストメッセージ（fact-checkerが last_message として読む）
    entries.append({
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": last_message}]
        }
    })

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".jsonl",
        prefix="fact_checker_edit_", delete=False,
    ) as f:
        test_transcript = Path(f.name)
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    input_data = json.dumps({"transcript_path": str(test_transcript)})
    try:
        result = subprocess.run(
            [sys.executable, str(FACT_CHECKER)],
            input=input_data, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15, env=env_vars
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        return -2
    except Exception as e:
        print(f"[REGRESSION] 実行エラー (with_edits): {e}")
        return -3
    finally:
        if test_transcript is not None:
            _safe_unlink(test_transcript)


def run_north_star_guard(payload: dict, extra_env: dict | None = None) -> int:
    if not NORTH_STAR_GUARD.exists():
        return -1
    env_vars = os.environ.copy()
    env_vars["CLAUDE_PROJECT_DIR"] = str(PROJECT_DIR)
    if extra_env:
        env_vars.update(extra_env)
    try:
        result = subprocess.run(
            [sys.executable, ".claude/hooks/north-star-guard.py"],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            env=env_vars,
            cwd=PROJECT_DIR,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        return -2
    except Exception as e:
        print(f"[REGRESSION] north-star-guard 繧ｨ繝ｩ繝ｼ: {e}")
        return -3

# ── T036: 機能的証明ヘルパー関数 ─────────────────────────────────────────────────
def _hg22_functional_test() -> str:
    """T036-P4: HG-22 mp→km 機能的証明 — orphan mp エントリを注入して exit 2 を確認"""
    if not PATTERNS_FILE.exists():
        return "SKIP (mistake_patterns.json not found)"
    SENTINEL = "__T036_HG22_FUNCTIONAL_SENTINEL__"
    mp_source = PATTERNS_FILE.read_text(encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory(prefix="cc_regression_") as temp_dir:
            temp_patterns = Path(temp_dir) / "mistake_patterns.json"
            mp_data = json.loads(mp_source)
        mp_data.append({
            "name": SENTINEL,
            "pattern": "SENTINEL_PATTERN_T036_DO_NOT_USE",
            "example": "SENTINEL_EXAMPLE_T036_DO_NOT_USE"
        })
        PATTERNS_FILE.write_text(json.dumps(mp_data, ensure_ascii=False, indent=2), encoding="utf-8")
        exit_code = run_fact_checker("nowpattern.comの記事を確認しました。テスト用メッセージです。")
        return "PASS" if exit_code == 2 else f"FAIL (exit={exit_code}, expected 2)"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        try:
            PATTERNS_FILE.write_text(mp_backup, encoding="utf-8")
        except Exception:
            pass


def _hg23_functional_test() -> str:
    """T036-P1: HG-23 km→mp 機能的証明 — orphan km エントリを注入して exit 2 を確認"""
    km_file = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"
    if not km_file.exists():
        return "SKIP (KNOWN_MISTAKES.md not found)"
    SENTINEL = "__T036_HG23_FUNCTIONAL_SENTINEL__"
    sentinel_block = (
        f"\n\n### T036-P1 HG-23 Functional Test Sentinel (auto-removed)\n"
        f'**GUARD_PATTERN**: `{{"name": "{SENTINEL}", "pattern": "SENTINEL_PATTERN_T036_DO_NOT_USE"}}`\n'
    )
    km_backup = km_file.read_text(encoding="utf-8")
    try:
        km_file.write_text(km_backup + sentinel_block, encoding="utf-8")
        exit_code = run_fact_checker("nowpattern.comの記事を確認しました。テスト用メッセージです。")
        return "PASS" if exit_code == 2 else f"FAIL (exit={exit_code}, expected 2)"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        try:
            km_file.write_text(km_backup, encoding="utf-8")
        except Exception:
            pass


# ── テストケース定義 ─────────────────────────────────────────────────────────────
def _hg22_functional_test() -> str:
    """T036-P4: HG-22 mp→km functional proof with copy-on-write temp files."""
    if not PATTERNS_FILE.exists():
        return "SKIP (mistake_patterns.json not found)"
    sentinel = "__T036_HG22_FUNCTIONAL_SENTINEL__"
    source_text = PATTERNS_FILE.read_text(encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory(prefix="cc_regression_") as temp_dir:
            temp_patterns = Path(temp_dir) / "mistake_patterns.json"
            patterns = json.loads(source_text)
            patterns.append({
                "name": sentinel,
                "pattern": "SENTINEL_PATTERN_T036_DO_NOT_USE",
                "example": "SENTINEL_EXAMPLE_T036_DO_NOT_USE",
            })
            temp_patterns.write_text(
                json.dumps(patterns, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            exit_code = run_fact_checker(
                "nowpattern.comの記事を確認しました。テスト用メッセージです。",
                extra_env={"CLAUDE_FACT_CHECKER_PATTERNS_FILE": str(temp_patterns)},
            )
        if exit_code != 2:
            return f"FAIL (exit={exit_code}, expected 2)"
        if PATTERNS_FILE.read_text(encoding="utf-8") != source_text:
            return "FAIL (source mutated during CoW test)"
        return "PASS"
    except Exception as e:
        return f"ERROR: {e}"


def _hg23_functional_test() -> str:
    """T036-P1: HG-23 km→mp functional proof with copy-on-write temp files."""
    km_file = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"
    if not km_file.exists():
        return "SKIP (KNOWN_MISTAKES.md not found)"
    sentinel = "__T036_HG23_FUNCTIONAL_SENTINEL__"
    source_text = km_file.read_text(encoding="utf-8")
    sentinel_block = (
        f"\n\n### T036-P1 HG-23 Functional Test Sentinel (auto-removed)\n"
        f'**GUARD_PATTERN**: `{{"name": "{sentinel}", "pattern": "SENTINEL_PATTERN_T036_DO_NOT_USE"}}`\n'
    )
    try:
        with tempfile.TemporaryDirectory(prefix="cc_regression_") as temp_dir:
            temp_km = Path(temp_dir) / "KNOWN_MISTAKES.md"
            temp_km.write_text(source_text + sentinel_block, encoding="utf-8")
            exit_code = run_fact_checker(
                "nowpattern.comの記事を確認しました。テスト用メッセージです。",
                extra_env={"CLAUDE_FACT_CHECKER_KNOWN_MISTAKES_FILE": str(temp_km)},
            )
        if exit_code != 2:
            return f"FAIL (exit={exit_code}, expected 2)"
        if km_file.read_text(encoding="utf-8") != source_text:
            return "FAIL (source mutated during CoW test)"
        return "PASS"
    except Exception as e:
        return f"ERROR: {e}"


def _hg23_skip_guard_test() -> str:
    """T037-P1: _dynamic=None（読込失敗/ファイル不在）→ HG-23スキップ。
    Codex Fix 2 (2026-03-29): None=スキップ, []=HG-23実行 の区別が正しいことを確認。
    テスト: パターンファイルが存在しない状態 → HG-23スキップ → false positive しない。
    """
    km_file = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"
    if not km_file.exists():
        return "SKIP (KNOWN_MISTAKES.md not found)"
    sentinel = "__T037_HG23_SKIP_SENTINEL__"
    sentinel_block = (
        f"\n\n### T037-P1 HG-23 Skip Guard Sentinel (auto-removed)\n"
        f'**GUARD_PATTERN**: `{{"name": "{sentinel}", "pattern": "SENTINEL_PATTERN_T037_DO_NOT_USE"}}`\n'
    )
    try:
        with tempfile.TemporaryDirectory(prefix="cc_regression_") as temp_dir:
            # パターンファイルを作成しない → _dynamic=None → HG-23スキップ
            nonexistent_patterns = Path(temp_dir) / "nonexistent_patterns.json"
            temp_km = Path(temp_dir) / "KNOWN_MISTAKES.md"
            temp_km.write_text(km_file.read_text(encoding="utf-8") + sentinel_block, encoding="utf-8")
            exit_code = run_fact_checker(
                "nowpattern.comの記事を確認しました。テスト用メッセージです。",
                extra_env={
                    "CLAUDE_FACT_CHECKER_PATTERNS_FILE": str(nonexistent_patterns),
                    "CLAUDE_FACT_CHECKER_KNOWN_MISTAKES_FILE": str(temp_km),
                },
            )
        return "PASS" if exit_code == 0 else f"FAIL (exit={exit_code}, expected 0)"
    except Exception as e:
        return f"ERROR: {e}"


def _regression_floor_edit_guard_test() -> str:
    """T037-P2: regression_floor.json floor edits must be blocked."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": ".claude/hooks/state/regression_floor.json",
            "old_string": '{\n  "floor": 50,\n  "updated_at": "2026-03-29 14:04 JST"\n}',
            "new_string": '{\n  "floor": 1,\n  "updated_at": "2026-03-29 14:04 JST"\n}',
        },
    }
    exit_code = run_north_star_guard(payload)
    return "PASS" if exit_code != 0 else f"FAIL (exit={exit_code}, expected non-zero block)"


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
    # ── Codex Review Fix 1: proof-checking 2-bucket tests（2026-03-29） ──
    # これらは run_fact_checker_with_edits で実行（Edit付きトランスクリプト）
    # BUILTIN_TESTS には含めるがフラグで区別（後述のmain()で特殊処理）
]

# Codex Review Fix 1 テスト: 委譲フレーズ単独 vs 委譲フレーズ+具体コマンド
PROOF_GATE_TESTS = [
    ("CODEX_FIX1_HANDOFF_ALONE_BLOCKED",
     "ファイルを修正しました。確認してください。",
     ["/tmp/test_codex_fix1.py"],
     True),   # 委譲フレーズ単独（具体コマンドなし）→ ブロックされるべき
    ("CODEX_FIX1_HANDOFF_WITH_CMD_PASSES",
     "ファイルを修正しました。確認してください。\n`bash site_health_check.py --quick` で確認できます。",
     ["/tmp/test_codex_fix1b.py"],
     False),  # 委譲フレーズ + 具体コマンド → 通過すべき
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

    # ── Codex Review Fix 1: proof-checking 2-bucket gate tests ───────────────
    # Edit付きトランスクリプトで _has_proof() の2バケット分離をテスト
    for name, message, edit_files, should_block in PROOF_GATE_TESTS:
        exit_code = run_fact_checker_with_edits(message, edit_files)
        actually_blocked = (exit_code == 2)
        passed = (actually_blocked == should_block)
        status = "✅ PASS" if passed else "❌ FAIL"
        results.append((name, status, exit_code, should_block))
        if not passed:
            failures.append((name, should_block, exit_code))
        print(f"  {status}: [{name}] exit={exit_code} (expect_block={should_block})")

    # ── Hard Gate 15 Path 3: GUARD_PATTERN name-set parity check ─────────────
    # KNOWN_MISTAKES.md の全 GUARD_PATTERN "name" が mistake_patterns.json に存在するか確認
    # 両フォーマット（標準 **GUARD_PATTERN**: / 非標準 `GUARD_PATTERN: ）を検出
    _MISTAKES_FILE = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"
    if _MISTAKES_FILE.exists() and PATTERNS_FILE.exists():
        _km_names = extract_guard_pattern_names(_MISTAKES_FILE.read_text(encoding="utf-8"))
        _mp_names = {p.get("name", "") for p in json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))}
        _mp_names.discard("")
        _gaps = _km_names - _mp_names
        if _gaps:
            _gap_str = ", ".join(sorted(_gaps))
            print(f"  ❌ FAIL: [GUARD_PATTERN_PARITY] KNOWN_MISTAKES.mdにあるがmistake_patterns.jsonにない: {_gap_str}")
            failures.append(("GUARD_PATTERN_PARITY", True, -4))
            results.append(("GUARD_PATTERN_PARITY", "❌ FAIL", -4, True))
        else:
            print(f"  ✅ PASS: [GUARD_PATTERN_PARITY] km={len(_km_names)}件 ⊆ mp={len(_mp_names)}件 (全件登録確認)")
            results.append(("GUARD_PATTERN_PARITY", "✅ PASS", 0, True))

    # ── Hard Gate 16: GUARD_FORMAT_NORMAL — 非標準フォーマット検出 ───────────────
    # KNOWN_MISTAKES.md に `GUARD_PATTERN: {...}` 形式（backtick-first）が残っていないか確認
    # この形式は auto-codifier.py の標準 regex を迂回し、sync gap の根本原因になる（T031参照）
    if _MISTAKES_FILE.exists():
        _km_text_g16 = _MISTAKES_FILE.read_text(encoding="utf-8")
        # backtick-first パターン: 行頭（または行頭空白後）に `GUARD_PATTERN: { が来るもの
        # 例示・説明文中のインライン参照（``...``等）は除外するためMULTILINE+行頭アンカーを使う
        _alt_hits = re.findall(r"^[ \t]*`GUARD_PATTERN:\s*\{", _km_text_g16, re.MULTILINE)
        if _alt_hits:
            print(f"  ❌ FAIL: [GUARD_FORMAT_NORMAL] 非標準フォーマット {len(_alt_hits)}件検出。標準形式(**GUARD_PATTERN**: `...`)に変換してください（T032参照）")
            failures.append(("GUARD_FORMAT_NORMAL", True, -5))
            results.append(("GUARD_FORMAT_NORMAL", "❌ FAIL", -5, True))
        else:
            print(f"  ✅ PASS: [GUARD_FORMAT_NORMAL] 非標準GUARD_PATTERN フォーマット 0件（全件標準形式）")
            results.append(("GUARD_FORMAT_NORMAL", "✅ PASS", 0, True))

    # ── Hard Gate 17: TASK_STATE_GATE — active_task_id ↔ task_ledger 整合性 ────
    # active_task_id.txt の値が task_ledger.json と一致するか確認
    # T-DONE → ledger status=done, T（進行中）→ ledger に存在するか確認
    _ACTIVE_TASK_FILE = PROJECT_DIR / ".claude" / "hooks" / "state" / "active_task_id.txt"
    _TASK_LEDGER_FILE = PROJECT_DIR / ".claude" / "state" / "task_ledger.json"
    if _ACTIVE_TASK_FILE.exists() and _TASK_LEDGER_FILE.exists():
        try:
            _active_raw = _ACTIVE_TASK_FILE.read_text(encoding="utf-8").strip()
            _ledger_data = json.loads(_TASK_LEDGER_FILE.read_text(encoding="utf-8"))
            _all_tasks = {t.get("task_id"): t for t in _ledger_data.get("tasks", [])}
            _gate17_fail = False
            if _active_raw.endswith("-DONE"):
                _tid = _active_raw[:-5]  # remove "-DONE"
                _task_entry = _all_tasks.get(_tid, {})
                if not _task_entry:
                    print(f"  ❌ FAIL: [TASK_STATE_GATE] active={_active_raw} だが ledger に {_tid} が存在しない")
                    _gate17_fail = True
                elif _task_entry.get("status") != "done":
                    _st = _task_entry.get("status", "missing")
                    print(f"  ❌ FAIL: [TASK_STATE_GATE] active={_active_raw} だが ledger status={_st}（doneでない）")
                    _gate17_fail = True
                else:
                    print(f"  ✅ PASS: [TASK_STATE_GATE] {_active_raw} → ledger status=done 一致")
            else:
                # 進行中タスク: ledger に存在するか確認（T032など実行中は正常）
                _task_entry = _all_tasks.get(_active_raw, {})
                if not _task_entry:
                    print(f"  ❌ FAIL: [TASK_STATE_GATE] active={_active_raw} だが ledger に未登録（実装前にタスク登録が必要）")
                    _gate17_fail = True
                else:
                    print(f"  ✅ PASS: [TASK_STATE_GATE] {_active_raw} → ledger存在確認（status={_task_entry.get('status','?')}）")
            if _gate17_fail:
                failures.append(("TASK_STATE_GATE", True, -6))
                results.append(("TASK_STATE_GATE", "❌ FAIL", -6, True))
            else:
                results.append(("TASK_STATE_GATE", "✅ PASS", 0, True))
        except Exception as _e17:
            print(f"  ⚠️ WARN: [TASK_STATE_GATE] 読み込みエラー: {_e17} → PASS扱い")
            results.append(("TASK_STATE_GATE", "✅ PASS", 0, True))

    # ── Hard Gate 19: MP_KM_REVERSE_PARITY — mp→km 逆方向パリティチェック ─────────
    # mistake_patterns.json の全エントリが KNOWN_MISTAKES.md に GUARD_PATTERN として文書化されているか確認
    # Hard Gate 15（km⊆mp）の逆方向: mp⊆km を検証する
    # 「直接 mp に注入したが km に記録しなかった」docs-state gap を検出する（T033 HG-19）
    if _MISTAKES_FILE.exists() and PATTERNS_FILE.exists():
        try:
            _mp_data = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
            _mp_all_names = {p.get("name", "") for p in _mp_data}
            _mp_all_names.discard("")
            _km_names_g19 = extract_guard_pattern_names(_MISTAKES_FILE.read_text(encoding="utf-8"))
            _reverse_gaps = _mp_all_names - _km_names_g19
            if _reverse_gaps:
                _rg_str = ", ".join(sorted(_reverse_gaps))
                print(f"  ❌ FAIL: [MP_KM_REVERSE_PARITY] mp={len(_mp_all_names)}件のうち km未記録: {_rg_str}")
                print(f"          → KNOWN_MISTAKES.md に **GUARD_PATTERN**: エントリを追加してください（T033 HG-19）")
                failures.append(("MP_KM_REVERSE_PARITY", True, -7))
                results.append(("MP_KM_REVERSE_PARITY", "❌ FAIL", -7, True))
            else:
                print(f"  ✅ PASS: [MP_KM_REVERSE_PARITY] mp={len(_mp_all_names)}件 ⊆ km={len(_km_names_g19)}件 (双方向パリティ確認)")
                results.append(("MP_KM_REVERSE_PARITY", "✅ PASS", 0, True))
        except Exception as _e19:
            print(f"  ⚠️ WARN: [MP_KM_REVERSE_PARITY] 読み込みエラー: {_e19} → PASS扱い")
            results.append(("MP_KM_REVERSE_PARITY", "✅ PASS", 0, True))

    # ── Hard Gate 22+24: RT パリティゲート ─────────────────────────────────────────
    # T034: RT_PARITY_GATE — fact-checker.py Stop hook に HG-22（mp→km）チェック存在確認
    # T035: HG-24 RT_KM_MP_GATE — HG-23（km→mp）チェック存在確認（歴史的失敗7件対策）
    # T035 P2: 浅い文字列存在チェック → 両方向同時確認に強化
    _fc_path = PROJECT_DIR / ".claude" / "hooks" / "fact-checker.py"
    if _fc_path.exists():
        _fc_src = _fc_path.read_text(encoding="utf-8")
        # HG-22: mp→km 方向チェック（RT_PARITY_GATE）
        if "HG-22" in _fc_src and "MP_KM_PARITY_VIOLATION" in _fc_src:
            print(f"  ✅ PASS: [RT_PARITY_GATE] fact-checker.py に HG-22 mp→km パリティチェック存在確認")
            results.append(("RT_PARITY_GATE", "✅ PASS", 0, True))
        else:
            print(f"  ❌ FAIL: [RT_PARITY_GATE] fact-checker.py に HG-22 mp→km チェックが見つかりません（T034 未実装）")
            failures.append(("RT_PARITY_GATE", True, -9))
            results.append(("RT_PARITY_GATE", "❌ FAIL", -9, True))
        # HG-24: km→mp 方向チェック（RT_KM_MP_GATE）— T035 新設
        if "HG-23" in _fc_src and "KM_MP_PARITY_VIOLATION" in _fc_src:
            print(f"  ✅ PASS: [RT_KM_MP_GATE] fact-checker.py に HG-23 km→mp パリティチェック存在確認（歴史的失敗7件対策）")
            results.append(("RT_KM_MP_GATE", "✅ PASS", 0, True))
        else:
            print(f"  ❌ FAIL: [RT_KM_MP_GATE] fact-checker.py に HG-23 km→mp チェックが見つかりません（T035 未実装）")
            failures.append(("RT_KM_MP_GATE", True, -9))
            results.append(("RT_KM_MP_GATE", "❌ FAIL", -9, True))
    else:
        print(f"  ⚠️ SKIP: [RT_PARITY_GATE] fact-checker.py が見つかりません")
        results.append(("RT_PARITY_GATE", "⚠️ SKIP", 0, True))
        print(f"  ⚠️ SKIP: [RT_KM_MP_GATE] fact-checker.py が見つかりません")
        results.append(("RT_KM_MP_GATE", "⚠️ SKIP", 0, True))

    # ── Hard Gate T036-P1+P4: 機能的証明テスト (Functional Proof Tests) ──────────
    # 浅い文字列存在チェック（RT_PARITY_GATE / RT_KM_MP_GATE）では「文字列はあるがコードが壊れている」
    # ケースを検出できない。機能的証明テストは実際に sentinel を注入して exit 2 を確認する。
    if _fc_path.exists():
        _fp_result_hg22 = _hg22_functional_test()
        if _fp_result_hg22 == "PASS":
            print(f"  ✅ PASS: [RT_MP_KM_FUNCTIONAL] HG-22 機能的証明 — orphan mp 注入 → exit 2 確認")
            results.append(("RT_MP_KM_FUNCTIONAL", "✅ PASS", 0, True))
        elif _fp_result_hg22.startswith("SKIP"):
            print(f"  ⚠️ SKIP: [RT_MP_KM_FUNCTIONAL] {_fp_result_hg22}")
            results.append(("RT_MP_KM_FUNCTIONAL", "⚠️ SKIP", 0, True))
        else:
            print(f"  ❌ FAIL: [RT_MP_KM_FUNCTIONAL] HG-22 機能的証明 失敗 — {_fp_result_hg22}")
            failures.append(("RT_MP_KM_FUNCTIONAL", True, -9))
            results.append(("RT_MP_KM_FUNCTIONAL", "❌ FAIL", -9, True))

        _fp_result_hg23 = _hg23_functional_test()
        if _fp_result_hg23 == "PASS":
            print(f"  ✅ PASS: [RT_KM_MP_FUNCTIONAL] HG-23 機能的証明 — orphan km 注入 → exit 2 確認")
            results.append(("RT_KM_MP_FUNCTIONAL", "✅ PASS", 0, True))
        elif _fp_result_hg23.startswith("SKIP"):
            print(f"  ⚠️ SKIP: [RT_KM_MP_FUNCTIONAL] {_fp_result_hg23}")
            results.append(("RT_KM_MP_FUNCTIONAL", "⚠️ SKIP", 0, True))
        else:
            print(f"  ❌ FAIL: [RT_KM_MP_FUNCTIONAL] HG-23 機能的証明 失敗 — {_fp_result_hg23}")
            failures.append(("RT_KM_MP_FUNCTIONAL", True, -9))
            results.append(("RT_KM_MP_FUNCTIONAL", "❌ FAIL", -9, True))
    else:
        print(f"  ⚠️ SKIP: [RT_MP_KM_FUNCTIONAL] fact-checker.py が見つかりません")
        results.append(("RT_MP_KM_FUNCTIONAL", "⚠️ SKIP", 0, True))
        print(f"  ⚠️ SKIP: [RT_KM_MP_FUNCTIONAL] fact-checker.py が見つかりません")
        results.append(("RT_KM_MP_FUNCTIONAL", "⚠️ SKIP", 0, True))

    # ── Hard Gate 22: RT_ECC_INVARIANTS_GATE — ecc_invariants.json 接続ゲート ─────
    # T037-P4: ecc_invariants.json を regression-runner.py に接続する。
    # 全 7 不変条件（INV-01〜07）の存在 + 対応 regression_gate の実装を確認。
    # これにより ecc_invariants.json の見出し「regression-runner.py がこれをハードゲートとして検証する」が
    # 実際に true になる（CHECK-1 で確認された gap を解消）。
    _skip_guard_result = _hg23_skip_guard_test()
    if _skip_guard_result == "PASS":
        print(f"  ✅ PASS: [RT_HG23_SKIP_GUARD] _dynamic 空時は HG-23 をスキップし false positive しない")
        results.append(("RT_HG23_SKIP_GUARD", "✅ PASS", 0, True))
    elif _skip_guard_result.startswith("SKIP"):
        print(f"  ⚠️ SKIP: [RT_HG23_SKIP_GUARD] {_skip_guard_result}")
        results.append(("RT_HG23_SKIP_GUARD", "⚠️ SKIP", 0, True))
    else:
        print(f"  ❌ FAIL: [RT_HG23_SKIP_GUARD] {_skip_guard_result}")
        failures.append(("RT_HG23_SKIP_GUARD", True, -9))
        results.append(("RT_HG23_SKIP_GUARD", "❌ FAIL", -9, True))

    _floor_guard_result = _regression_floor_edit_guard_test()
    if _floor_guard_result == "PASS":
        print(f"  ✅ PASS: [REGRESSION_FLOOR_EDIT_GUARD] regression_floor.json の Edit 抜け穴を遮断")
        results.append(("REGRESSION_FLOOR_EDIT_GUARD", "✅ PASS", 0, True))
    elif _floor_guard_result.startswith("SKIP"):
        print(f"  ⚠️ SKIP: [REGRESSION_FLOOR_EDIT_GUARD] {_floor_guard_result}")
        results.append(("REGRESSION_FLOOR_EDIT_GUARD", "⚠️ SKIP", 0, True))
    else:
        print(f"  ❌ FAIL: [REGRESSION_FLOOR_EDIT_GUARD] {_floor_guard_result}")
        failures.append(("REGRESSION_FLOOR_EDIT_GUARD", True, -9))
        results.append(("REGRESSION_FLOOR_EDIT_GUARD", "❌ FAIL", -9, True))

    _inv_path = PROJECT_DIR / ".claude" / "hooks" / "state" / "ecc_invariants.json"
    if _inv_path.exists():
        try:
            _inv_data = json.loads(_inv_path.read_text(encoding="utf-8"))
            _invariants = _inv_data.get("invariants", [])
            _inv_ids = {inv.get("id") for inv in _invariants}
            _expected_inv_ids = {f"INV-{i:02d}" for i in range(1, 8)}  # INV-01〜INV-07
            _missing_inv = _expected_inv_ids - _inv_ids
            if _missing_inv:
                print(f"  ❌ FAIL: [RT_ECC_INVARIANTS_GATE] 欠損 invariant: {sorted(_missing_inv)}")
                failures.append(("RT_ECC_INVARIANTS_GATE", True, -7))
                results.append(("RT_ECC_INVARIANTS_GATE", "❌ FAIL", -7, True))
            else:
                _result_names = {name for name, _, _, _ in results}
                _inv_gate_map = {
                    "INV-01": ["RT_PARITY_GATE", "RT_MP_KM_FUNCTIONAL"],
                    "INV-02": ["RT_KM_MP_GATE", "RT_KM_MP_FUNCTIONAL"],
                    "INV-03": ["RT_PARITY_GATE"],
                    "INV-04": ["RT_KM_MP_FUNCTIONAL"],
                    "INV-05": ["RT_MP_KM_FUNCTIONAL", "RT_KM_MP_FUNCTIONAL"],
                    "INV-06": ["BASELINE_FLOOR_GATE"],  # 次のゲートで自己証明
                    "INV-07": ["BASELINE_FLOOR_GATE"],
                }
                _skip_in_context = {"BASELINE_FLOOR_GATE"}  # 実行順序上、次のゲートで証明
                _orphans = []
                for _inv_id, _gates in _inv_gate_map.items():
                    for _g in _gates:
                        if _g not in _result_names and _g not in _skip_in_context:
                            _orphans.append(f"{_inv_id}:{_g}")
                if _orphans:
                    print(f"  ❌ FAIL: [RT_ECC_INVARIANTS_GATE] regression_gate 未実装: {_orphans}")
                    failures.append(("RT_ECC_INVARIANTS_GATE", True, -7))
                    results.append(("RT_ECC_INVARIANTS_GATE", "❌ FAIL", -7, True))
                else:
                    print(f"  ✅ PASS: [RT_ECC_INVARIANTS_GATE] {len(_invariants)}不変条件 全て確認 — INV-01〜INV-07 全保護済み")
                    results.append(("RT_ECC_INVARIANTS_GATE", "✅ PASS", 0, True))
        except Exception as _e_inv:
            print(f"  ⚠️ WARN: [RT_ECC_INVARIANTS_GATE] JSON読込エラー: {_e_inv}", file=sys.stderr)
            results.append(("RT_ECC_INVARIANTS_GATE", "⚠️ WARN", 0, True))
    else:
        print(f"  ❌ FAIL: [RT_ECC_INVARIANTS_GATE] {_inv_path.name} が存在しません")
        failures.append(("RT_ECC_INVARIANTS_GATE", True, -7))
        results.append(("RT_ECC_INVARIANTS_GATE", "❌ FAIL", -7, True))

    # ── Hard Gate 21: BASELINE_FLOOR_GATE — 総テスト数フロアチェック ────────────
    # T035 P4 アップグレード: 静的 46 → 動的ロード（state/regression_floor.json）
    # PASS 時に _current_count でフロアを更新 → 次回以降はその値が下限になる（後退禁止）
    _floor_path = PROJECT_DIR / ".claude" / "hooks" / "state" / "regression_floor.json"
    _floor_data = {}
    if _floor_path.exists():
        try:
            _floor_data = json.loads(_floor_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    BASELINE_FLOOR = _floor_data.get("floor", 46)  # デフォルト: T034-DONE 時点の 46
    _current_count = len(results)
    if _current_count < BASELINE_FLOOR:
        print(f"  ❌ FAIL: [BASELINE_FLOOR_GATE] テスト数 {_current_count} < floor {BASELINE_FLOOR}（{_floor_path.name} 参照）")
        failures.append(("BASELINE_FLOOR_GATE", True, -8))
        results.append(("BASELINE_FLOOR_GATE", "❌ FAIL", -8, True))
    else:
        print(f"  ✅ PASS: [BASELINE_FLOOR_GATE] テスト数 {_current_count} ≥ floor {BASELINE_FLOOR}（フロア保証確認）")
        results.append(("BASELINE_FLOOR_GATE", "✅ PASS", 0, True))

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
        # P4: フロア更新（全テストPASS時 + _current_count がフロアを超える場合のみ）
        if _current_count > BASELINE_FLOOR:
            try:
                _floor_path.parent.mkdir(parents=True, exist_ok=True)
                _floor_path.write_text(
                    json.dumps({"floor": _current_count, "updated_at": now}, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                print(f"  📈 フロア更新: {BASELINE_FLOOR} → {_current_count} ({_floor_path.name})")
            except Exception:
                pass  # フロア更新失敗はサイレント無視
        # 週次レポートとして送信（毎日は送らない — 月曜のみ）
        if datetime.now().weekday() == 0:  # 月曜日
            send_telegram(msg)
        sys.exit(0)

if __name__ == "__main__":
    main()
