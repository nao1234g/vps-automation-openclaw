#!/usr/bin/env python3
"""
private-leak-checker.py — ZONE 0/1 データの public surface 混入を検出

使い方:
  python private-leak-checker.py                    # git staged files をチェック
  python private-leak-checker.py --all              # git tracked 全ファイルをチェック
  python private-leak-checker.py --file path.py     # 特定ファイルをチェック
  python private-leak-checker.py --content "text"   # テキスト内容をチェック
  python private-leak-checker.py --all --summary    # サマリーのみ表示
  python private-leak-checker.py --all --severity critical  # CRITICAL のみ表示

終了コード:
  0 = 問題なし
  1 = ZONE 0/1 データの混入を検出（ブロック）
  2 = エラー

pre-commit hook または Claude Code hook から呼び出される。
"""

import argparse
import os
import re
import subprocess
import sys

# ─────────────────────────────────────────────
# 重要度レベル
# ─────────────────────────────────────────────
SEVERITY_CRITICAL = "CRITICAL"  # 秘密情報の直接漏洩
SEVERITY_HIGH = "HIGH"          # ZONE 0/1 ファイルの追跡・参照
SEVERITY_MEDIUM = "MEDIUM"      # 運用上意図的だがリスクのある情報
SEVERITY_INFO = "INFO"          # 注意喚起のみ

# ─────────────────────────────────────────────
# ZONE 0/1 パス（これらのファイルは public surface に含めてはならない）
# ─────────────────────────────────────────────
BLOCKED_PATHS = [
    ".claude/memory/",
    ".claude/state/",
    ".claude/projects/",
    ".claude/plans/",
    "founder_memory/",
    "brainstorm/",
    "decisions/",
    "intelligence/",
    "secrets.txt",
]

# git staged に含まれていたらブロックするパスパターン
BLOCKED_STAGED_PATTERNS = [
    r"^\.claude/memory/",
    r"^\.claude/state/",
    r"^\.claude/projects/",
    r"^\.claude/plans/",
    r"^founder_memory/",
    r"^brainstorm/",
    r"^decisions/",
    r"^intelligence/",
    r"^secrets\.txt$",
    r"\.credentials\.json$",
    r"\.env$",
    r"\.env\.local$",
    r"\.env\.\w+\.local$",
    r"\.pem$",
    r"\.key$",
    r"private_key",
]

# ─────────────────────────────────────────────
# コンテンツ内の危険パターン（public surface に含めてはならない）
# severity: CRITICAL > HIGH > MEDIUM > INFO
# ─────────────────────────────────────────────
BLOCKED_CONTENT_PATTERNS = [
    # CRITICAL: 秘密情報の直接漏洩
    (r"\d{9,10}:[A-Za-z0-9_-]{35}", "Telegram Bot Token", SEVERITY_CRITICAL),
    (r"sk-ant-[a-zA-Z0-9-]{20,}", "Anthropic API Key", SEVERITY_CRITICAL),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "SSH Private Key", SEVERITY_CRITICAL),
    (r"(?i)(api[_-]?key|api[_-]?secret|access[_-]?token)\s*[=:]\s*['\"][^'\"]{20,}", "API Key/Secret", SEVERITY_CRITICAL),
    (r"(?i)oauth.*token.*[=:]\s*['\"][^'\"]{20,}", "OAuth Token", SEVERITY_CRITICAL),
    # HIGH: 個人情報・インフラ情報
    (r"163\.44\.124\.123", "VPS IP address", SEVERITY_HIGH),
    (r"marketingiiyone@gmail\.com", "Founder personal email", SEVERITY_HIGH),
    (r"nakamura-ai@ewg\.co\.jp", "Founder company email", SEVERITY_HIGH),
    # MEDIUM: ZONE 0/1 コンテンツの引用
    (r"(?i)founder_memory/(decisions|philosophy)\.yaml", "Founder memory file reference", SEVERITY_MEDIUM),
    (r"(?i)brainstorm/sessions/", "Brainstorm session reference", SEVERITY_MEDIUM),
    (r"(?i)decisions/DECISION_LOG", "Decision log reference", SEVERITY_MEDIUM),
]

# ─────────────────────────────────────────────
# 許容リスト（--all 監査時の既知許容パターン）
# これらのファイルに含まれる VPS IP 等は運用上意図的なので MEDIUM に降格
# ─────────────────────────────────────────────
KNOWN_ALLOWLIST = {
    # ファイルパス（前方一致）: 許容するパターンラベルのセット
    ".claude/rules/infrastructure.md": {"VPS IP address"},
    ".claude/rules/NORTH_STAR.md": set(),  # ルールファイルは内容チェックスキップ
    "scripts/sync-neo-token.ps1": {"VPS IP address"},
    "scripts/sync-nowpattern-vps.ps1": {"VPS IP address"},
    "scripts/setup-": {"VPS IP address"},  # setup-*.sh 系
    "docs/HIGH_RISK_RUNBOOK.md": {"VPS IP address", "Founder personal email", "Founder company email"},
    "docs/PRIVACY_POLICY.md": {"VPS IP address"},
    ".claude/CLAUDE.md": {"VPS IP address"},
    "CLAUDE.md": {"VPS IP address"},
}

def is_allowlisted(filepath, label):
    """ファイルパスとパターンラベルが許容リストに含まれるか判定"""
    for prefix, allowed_labels in KNOWN_ALLOWLIST.items():
        if filepath.replace("\\", "/").startswith(prefix):
            if label in allowed_labels:
                return True
    return False

# ─────────────────────────────────────────────
# チェック関数
# ─────────────────────────────────────────────

def check_staged_files():
    """git staged ファイルに ZONE 0/1 のファイルが含まれていないか確認"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10
        )
        staged = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception as e:
        print(f"[ERROR] git diff failed: {e}", file=sys.stderr)
        return []

    violations = []
    for f in staged:
        for pattern in BLOCKED_STAGED_PATTERNS:
            if re.search(pattern, f):
                violations.append({
                    "severity": SEVERITY_CRITICAL,
                    "source": f,
                    "label": "ZONE 0/1 file staged",
                    "count": 1,
                    "message": f"  [{SEVERITY_CRITICAL}] STAGED: {f} (matches {pattern})",
                })
                break
    return violations


def check_content(text, source="<input>"):
    """テキスト内容に ZONE 0/1 のデータが含まれていないか確認"""
    violations = []
    for pattern, label, severity in BLOCKED_CONTENT_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            # 許容リストに含まれる場合は MEDIUM に降格
            effective_severity = severity
            if is_allowlisted(source, label):
                effective_severity = SEVERITY_MEDIUM
            # 実際の値は表示しない（漏洩防止）
            violations.append({
                "severity": effective_severity,
                "source": source,
                "label": label,
                "count": len(matches),
                "message": f"  [{effective_severity}] {source}: {label} ({len(matches)} match(es))",
            })
    return violations


def check_file(filepath):
    """ファイルの内容をチェック"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return check_content(content, source=filepath)
    except Exception as e:
        print(f"[WARN] Cannot read {filepath}: {e}", file=sys.stderr)
        return []


def check_all_tracked():
    """git tracked の全ファイルをチェック"""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, timeout=30
        )
        files = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception as e:
        print(f"[ERROR] git ls-files failed: {e}", file=sys.stderr)
        return []

    violations = []
    # パスチェック
    for f in files:
        for pattern in BLOCKED_STAGED_PATTERNS:
            if re.search(pattern, f):
                violations.append({
                    "severity": SEVERITY_HIGH,
                    "source": f,
                    "label": "ZONE 0/1 file tracked",
                    "count": 1,
                    "message": f"  [{SEVERITY_HIGH}] TRACKED: {f} (should be untracked with git rm --cached)",
                })
                break

    # コンテンツチェック（テキストファイルのみ）
    text_extensions = {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".sh", ".html", ".css", ".js", ".ts", ".ps1"}
    for f in files:
        _, ext = os.path.splitext(f)
        if ext.lower() in text_extensions and os.path.isfile(f):
            file_violations = check_file(f)
            violations.extend(file_violations)

    return violations


def check_staged_content():
    """staged ファイルの差分内容をチェック"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, timeout=30
        )
        diff_text = result.stdout
    except Exception as e:
        print(f"[ERROR] git diff --cached failed: {e}", file=sys.stderr)
        return []

    if not diff_text:
        return []

    return check_content(diff_text, source="staged diff")


def format_summary(violations):
    """重要度別のサマリーを生成"""
    counts = {SEVERITY_CRITICAL: 0, SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 0, SEVERITY_INFO: 0}
    for v in violations:
        if isinstance(v, dict):
            counts[v["severity"]] = counts.get(v["severity"], 0) + 1
        else:
            counts[SEVERITY_HIGH] += 1  # legacy format
    lines = [
        f"\n{'='*60}",
        f"  AUDIT SUMMARY",
        f"{'='*60}",
        f"  CRITICAL : {counts[SEVERITY_CRITICAL]:>4}  (secrets / tokens / keys)",
        f"  HIGH     : {counts[SEVERITY_HIGH]:>4}  (ZONE 0/1 tracked files + PII)",
        f"  MEDIUM   : {counts[SEVERITY_MEDIUM]:>4}  (known-intentional but risky)",
        f"  INFO     : {counts[SEVERITY_INFO]:>4}  (advisory only)",
        f"{'-'*60}",
        f"  TOTAL    : {sum(counts.values()):>4}",
        f"{'='*60}",
    ]
    if counts[SEVERITY_CRITICAL] > 0:
        lines.append("  [!] CRITICAL > 0: repo MUST NOT be public")
    if counts[SEVERITY_HIGH] > 0:
        lines.append("  [!] HIGH > 0: run git rm --cached + make repo private")
    return "\n".join(lines)


def filter_by_severity(violations, min_severity):
    """指定した重要度以上の違反だけを返す"""
    order = {SEVERITY_CRITICAL: 4, SEVERITY_HIGH: 3, SEVERITY_MEDIUM: 2, SEVERITY_INFO: 1}
    min_level = order.get(min_severity.upper(), 0)
    return [v for v in violations if isinstance(v, dict) and order.get(v["severity"], 0) >= min_level]


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Private data leak checker")
    parser.add_argument("--all", action="store_true", help="Check all git tracked files")
    parser.add_argument("--file", type=str, help="Check a specific file")
    parser.add_argument("--content", type=str, help="Check text content directly")
    parser.add_argument("--summary", action="store_true", help="Show summary only (with --all)")
    parser.add_argument("--severity", type=str, default="", help="Filter: critical, high, medium, info")
    args = parser.parse_args()

    violations = []

    if args.content:
        violations = check_content(args.content)
    elif args.file:
        violations = check_file(args.file)
    elif args.all:
        print("[AUDIT] Checking all git tracked files...")
        violations = check_all_tracked()
    else:
        # Default: check staged files
        print("[CHECK] Checking git staged files...")
        path_violations = check_staged_files()
        content_violations = check_staged_content()
        violations = path_violations + content_violations

    # フィルタリング
    if args.severity:
        violations = filter_by_severity(violations, args.severity)

    if violations:
        print("\n[FAIL] Private data leak detected!\n")
        if not args.summary:
            for v in violations:
                if isinstance(v, dict):
                    print(v["message"])
                else:
                    print(v)  # legacy format
        print(format_summary(violations))
        print(f"\nSee docs/PRIVACY_POLICY.md for ZONE classification.")

        # pre-commit hook: CRITICAL/HIGH でのみブロック
        has_blocking = any(
            isinstance(v, dict) and v["severity"] in (SEVERITY_CRITICAL, SEVERITY_HIGH)
            for v in violations
        )
        if has_blocking:
            print("To proceed anyway (DANGEROUS): git commit --no-verify")
            sys.exit(1)
        else:
            print("[WARN] MEDIUM/INFO violations only — no block, but review recommended.")
            sys.exit(0)
    else:
        print("[PASS] No private data leaks detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
