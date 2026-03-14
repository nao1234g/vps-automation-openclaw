#!/usr/bin/env python
"""
audit_retired_refs.py — 退役済み artifact への参照を検出・分類する
使い方: python scripts/audit_retired_refs.py [--vps] [--fix-suggest] [--json]
  --vps          VPS もチェック（SSH 必要）
  --fix-suggest  修正提案を表示
  --json         JSON 形式で出力

終了コード:
  0 = クリーン（不正参照なし）
  1 = 警告あり
  2 = エラーあり（不正参照あり）
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path

# Windows CP932 環境で絵文字・日本語を含む出力が壊れないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).parent.parent
VPS_HOST = "root@163.44.124.123"

# retirement_registry.yaml から手動で同期したパターン
# （yaml を読む外部依存を避けるため Python 内に直定義）
RETIRED_PATTERNS = [
    {
        "id": "opt-claude-md",
        "pattern": "/opt/CLAUDE.md",
        "severity": "ERROR",
        "note": "退役済みパス。tombstone への参照は OK。",
        # これらのコンテキストが含まれる行は OK（tombstone参照・退役注記）
        "allow_context": [
            ".retired",
            "retired-20260314",
            "退役済み",
            "retired",
            "tombstone",
            "RETIRED",
            "2026-03-14",
            "opt-claude-md-20260314",
            "retirement_registry",
            "runtime_truth_registry",
            "tombstone のみ残存",
            "NOTE:",
        ],
        "fix": "/opt/claude-code-telegram/CLAUDE.md (NEO-ONE) または /opt/claude-code-telegram-neo2/CLAUDE.md (NEO-TWO)"
    },
    {
        "id": "aisaintel",
        "pattern": "@aisaintel",
        "severity": "ERROR",
        "note": "削除済み X アカウント。参照禁止。",
        "allow_context": [
            "retirement_registry", "KNOWN_MISTAKES", "存在しない", "削除済み",
            "廃止", "DEPRECATED", "retired", "RETIRED",
            # session-start.sh「存在しない」注記
            "存在しない", "は存在しない",
            # fact-checker / research-gate / regression-runner のガード定義
            "BANNED", "banned", "block", "禁止",
        ],
        "fix": "@nowpattern を使う"
    },
    {
        "id": "aisa-brand",
        "pattern": "aisaintel",
        "severity": "WARNING",
        "note": "AISA ブランドは廃止済み。",
        "allow_context": [
            "retirement_registry", "KNOWN_MISTAKES", "廃止", "存在しない",
            "DEPRECATED", "retired", "RETIRED",
            "BANNED", "banned", "block", "禁止",
            "generate-aisa-header",  # スクリプト名として参照
        ],
        "fix": "Nowpattern に統合済み"
    },
]

# チェック対象パス（ローカル）
LOCAL_SCAN_PATHS = [
    ".claude/rules",
    ".claude/hooks",
    "docs",
    "scripts",
    "policy",
]

# VPS でチェックするパス
VPS_SCAN_PATHS = [
    "/opt/shared/rules",
    "/opt/shared/scripts",
    "/opt/shared/docs",
    "/opt/claude-code-telegram",
    "/opt/claude-code-telegram-neo2",
    "/opt/openclaw",
]

# 除外するファイルパターン（監査ファイル自体はスキップ）
EXCLUDE_FILES = [
    "audit_retired_refs.py",
    "doctor.py",              # 退役チェックスクリプト自体は tombstone 参照が必要
    "repo-audit.py",          # 退役パターン検知スクリプト
    "fact-checker.py",        # ブロックパターン定義が含まれる（正当な参照）
    "regression-runner.py",   # ガードテスト（正当な参照）
    "research-gate.py",       # BANNED_TERMS 定義（正当な参照）
    "prevention_log.json",    # 過去の防止イベントログ
    "retirement_registry.yaml",
    "runtime_truth_registry.yaml",
    "generated_artifacts.yaml",
    "KNOWN_MISTAKES.md",
    "BACKLOG.md",             # 歴史的タスク記録
    "/archive/",              # アーカイブドキュメント（歴史的記録）
    ".bak-",                  # バックアップファイル（.bak-YYYYMMDD パターン）
]


def c(color, text):
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
              "blue": "\033[94m", "reset": "\033[0m", "bold": "\033[1m"}
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def should_exclude(filepath):
    for excl in EXCLUDE_FILES:
        if excl in filepath:
            return True
    return False


def scan_local(pattern_def, verbose=False):
    """ローカル repo をスキャン"""
    findings = []
    pattern = pattern_def["pattern"]
    allow_contexts = pattern_def.get("allow_context", [])

    for rel_path in LOCAL_SCAN_PATHS:
        abs_path = REPO_ROOT / rel_path
        if not abs_path.exists():
            continue
        try:
            result = subprocess.run(
                ["grep", "-rn", "--include=*.md", "--include=*.py",
                 "--include=*.yaml", "--include=*.json", "--include=*.sh",
                 "--include=*.txt", pattern, str(abs_path)],
                capture_output=True, encoding="utf-8", errors="replace"
            )
            for line in result.stdout.splitlines():
                if should_exclude(line):
                    continue
                is_allowed = any(ctx in line for ctx in allow_contexts)
                if not is_allowed:
                    findings.append({
                        "location": "local",
                        "line": line.strip(),
                        "severity": pattern_def["severity"],
                    })
                elif verbose:
                    findings.append({
                        "location": "local (allowed)",
                        "line": line.strip(),
                        "severity": "INFO",
                    })
        except FileNotFoundError:
            # grep コマンドが見つからない（まれ）
            pass

    return findings


def scan_vps(pattern_def, verbose=False):
    """VPS をスキャン"""
    findings = []
    pattern = pattern_def["pattern"]
    allow_contexts = pattern_def.get("allow_context", [])

    paths_str = " ".join(VPS_SCAN_PATHS)
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", VPS_HOST,
             f"grep -rn '{pattern}' {paths_str} 2>/dev/null || true"],
            capture_output=True, text=True, timeout=15, errors="replace"
        )
        for line in result.stdout.splitlines():
            if should_exclude(line):
                continue
            is_allowed = any(ctx in line for ctx in allow_contexts)
            if not is_allowed:
                findings.append({
                    "location": "vps",
                    "line": line.strip(),
                    "severity": pattern_def["severity"],
                })
            elif verbose:
                findings.append({
                    "location": "vps (allowed)",
                    "line": line.strip(),
                    "severity": "INFO",
                })
    except Exception as e:
        findings.append({
            "location": "vps",
            "line": f"SSH error: {e}",
            "severity": "WARN",
        })

    return findings


def main():
    parser = argparse.ArgumentParser(description="退役済み artifact の参照監査")
    parser.add_argument("--vps", action="store_true", help="VPS もチェック")
    parser.add_argument("--fix-suggest", action="store_true", help="修正提案を表示")
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力")
    parser.add_argument("--verbose", action="store_true", help="許可済み参照も表示")
    args = parser.parse_args()

    all_findings = []
    error_count = 0
    warn_count = 0

    if not args.json:
        print(f"\n{c('bold', '=== Retired Refs Audit ===')} ({REPO_ROOT.name})\n")

    for pdef in RETIRED_PATTERNS:
        local_findings = scan_local(pdef, args.verbose)

        vps_findings = []
        if args.vps:
            vps_findings = scan_vps(pdef, args.verbose)

        findings = local_findings + vps_findings
        bad_findings = [f for f in findings if f["severity"] in ("ERROR", "WARNING")]

        if not args.json:
            icon = "❌" if bad_findings else "✅"
            severity_bad = any(f["severity"] == "ERROR" for f in bad_findings)
            color = "red" if severity_bad else ("yellow" if bad_findings else "green")
            print(f"{icon} {c(color, pdef['id'])} — pattern: '{pdef['pattern']}'")
            if bad_findings:
                for f in bad_findings:
                    sev_color = "red" if f["severity"] == "ERROR" else "yellow"
                    print(f"   {c(sev_color, f['severity'])} [{f['location']}] {f['line'][:120]}")
                if args.fix_suggest and pdef.get("fix"):
                    print(f"   {c('blue', '→ FIX:')} {pdef['fix']}")
            elif args.verbose:
                allowed = [f for f in findings if f["severity"] == "INFO"]
                for f in allowed:
                    print(f"   {c('blue', 'OK')} [{f['location']}] {f['line'][:100]}")
            print()

        for f in bad_findings:
            all_findings.append({**f, "pattern_id": pdef["id"], "pattern": pdef["pattern"]})
            if f["severity"] == "ERROR":
                error_count += 1
            else:
                warn_count += 1

    if args.json:
        output = {
            "summary": {
                "errors": error_count,
                "warnings": warn_count,
                "total_bad": error_count + warn_count,
                "exit_code": 2 if error_count > 0 else (1 if warn_count > 0 else 0)
            },
            "findings": all_findings
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("─" * 50)
        if error_count > 0:
            print(c("red", f"❌ FAIL — エラー: {error_count}件, 警告: {warn_count}件"))
        elif warn_count > 0:
            print(c("yellow", f"⚠️  WARN — 警告: {warn_count}件"))
        else:
            print(c("green", "✅ CLEAN — 不正参照: 0件"))
        print()

    return 2 if error_count > 0 else (1 if warn_count > 0 else 0)


if __name__ == "__main__":
    sys.exit(main())
