#!/usr/bin/env python3
"""
repo-audit.py — リポジトリ自動監査スクリプト
========================================
古いファイル・廃止コンテンツを検出して PENDING_CLEANUP.md に書き出す。
VSCode のサイドバーで確認して「承認して」と Claude Code に伝えると実行される。

実行方法:
  python scripts/repo-audit.py            # 監査実行
  python scripts/repo-audit.py --verbose  # 詳細ログあり
  python scripts/repo-audit.py --schedule # Windows タスクスケジューラに月1回登録

出力: PENDING_CLEANUP.md（リポジトリルート）
"""

import sys
import io
import subprocess
import re
from datetime import datetime
from pathlib import Path

# Windows コンソールの cp932 エラー対策（絵文字・日本語を安全に出力）
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ==================== 設定 ====================

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = REPO_ROOT / "PENDING_CLEANUP.md"
STALE_DAYS = 180  # 6ヶ月超で「古い」と判定

# これが本文に含まれているファイルは廃止コンテンツとして検出
DEPRECATED_PATTERNS = [
    ("Speed Log",          "Speed Log形式は廃止済み（Deep Pattern一択）"),
    ("Antigravity",        "Antigravity体制は廃止済み（2025年7月）"),
    ("AISA Newsletter",    "AISAブランドは廃止済み（Nowpattern統合）"),
    ("aisaintel",          "@aisaintelアカウントは廃止済み"),
    ("OpenNotebook",       "OpenNotebookサービスは現在未使用"),
    ("7AI Architecture",   "7AI体制ドキュメントはアーカイブ済み"),
    ("QUICKSTART_7AI",     "7AIクイックスタートは廃止済み"),
    ("MULTI_AGENT_SETUP",  "マルチエージェントセットアップは廃止済み"),
    ("claude-code.yml",    "旧CI設定ファイル参照"),
]

# スキャン除外ディレクトリ
EXCLUDE_DIRS = {
    "docs/archives",
    ".git",
    ".claude",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "assets",
}

# スキャン除外ファイル（廃止ワードを意図的に含む正規ドキュメント含む）
EXCLUDE_FILES = {
    "PENDING_CLEANUP.md",
    "repo-audit.py",
    "CLAUDE.md",
    "KNOWN_MISTAKES.md",       # ミス記録は廃止ワード含んでOK
    "AGENT_WISDOM.md",
    "ARTICLE_FORMAT.md",       # Deep Pattern権威文書（Speed Logは「廃止」として記述）
    "NEO_INSTRUCTIONS_V2.md",  # NEO執筆指示書（Speed Logは廃止通知として記述）
    "OPERATIONS_GUIDE.md",     # 運用ガイド（歴史的記述あり）
    "README.md",               # READMEは随時更新するメインドキュメント
    "ARCHITECTURE.md",         # アーキテクチャは随時更新するメインドキュメント
}

# このプレフィックスの .py は一回限りの修正スクリプト（候補に上げる）
ONEOFF_PREFIXES = ["_fix_", "_check_", "_verify_", "_recreate_", "_update_neo", "_add_", "_final_", "_site_"]

VERBOSE = "--verbose" in sys.argv

# ==================== ユーティリティ ====================

def git_last_commit_date(filepath: Path) -> datetime | None:
    """ファイルの最終コミット日時を git log から取得"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", "--", str(filepath)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        line = result.stdout.strip()
        if not line:
            return None
        # "2026-02-10 15:30:00 +0900" 形式
        return datetime.fromisoformat(line[:19])
    except Exception:
        return None



def is_excluded(filepath: Path) -> bool:
    """除外対象かどうかを判定"""
    rel = filepath.relative_to(REPO_ROOT).as_posix()
    for excl in EXCLUDE_DIRS:
        if rel.startswith(excl):
            return True
    if filepath.name in EXCLUDE_FILES:
        return True
    return False


def scan_md_files() -> list[dict]:
    """docs/ 配下と ルートの .md ファイルをスキャン"""
    candidates = []
    now = datetime.now()

    # スキャン対象: docs/*.md, ルート *.md
    targets = list(REPO_ROOT.glob("*.md")) + list(REPO_ROOT.glob("docs/*.md")) + list(REPO_ROOT.glob("n8n-workflows/*.md"))

    for filepath in sorted(targets):
        if is_excluded(filepath):
            continue

        rel = filepath.relative_to(REPO_ROOT).as_posix()
        last_commit = git_last_commit_date(filepath)

        # git log が空 = 未コミット（新規ファイルorリネーム直後）→ stale 扱いしない
        if last_commit is None:
            if VERBOSE:
                print(f"  [skip] {rel}: no git history (new/renamed file)")
            continue

        age_days = (now - last_commit).days

        issues = []

        # 1. 古いファイル（6ヶ月超）
        if age_days >= STALE_DAYS:
            issues.append(f"最終更新 {age_days}日前（{last_commit.strftime('%Y-%m-%d') if last_commit else '不明'}）")

        # 2. 廃止キーワード検出
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            for keyword, reason in DEPRECATED_PATTERNS:
                if keyword in content:
                    # タイトルやヘッダーに含まれる場合のみ flagging（本文の単なる言及は除外）
                    lines_with_keyword = [l.strip() for l in content.splitlines() if keyword in l and not l.strip().startswith("#")]
                    if lines_with_keyword:
                        issues.append(f'廃止ワード「{keyword}」を含む: {reason}')
                        break  # 1ファイルにつき最初の1件だけ
        except Exception:
            pass

        if issues:
            severity = "🔴" if len(issues) >= 2 or age_days >= STALE_DAYS * 2 else "🟡"
            candidates.append({
                "path": rel,
                "severity": severity,
                "age_days": age_days,
                "issues": issues,
                "action": "archive" if age_days < STALE_DAYS * 2 else "delete",
            })
            if VERBOSE:
                print(f"  [{severity}] {rel}: {', '.join(issues)}")

    return candidates


def scan_oneoff_scripts() -> list[dict]:
    """一回限りの修正スクリプト（_プレフィックス）を検出"""
    candidates = []
    for filepath in sorted((REPO_ROOT / "scripts").glob("*.py")):
        name = filepath.name
        if any(name.startswith(pfx) for pfx in ONEOFF_PREFIXES):
            last_commit = git_last_commit_date(filepath)
            now = datetime.now()
            age_days = (now - last_commit).days if last_commit else 9999
            if age_days >= 30:  # 1ヶ月以上触れていない一回スクリプト
                candidates.append({
                    "path": f"scripts/{name}",
                    "severity": "🟡",
                    "age_days": age_days,
                    "issues": [f"一回限りの修正スクリプト（最終更新 {age_days}日前）"],
                    "action": "delete",
                })
                if VERBOSE:
                    print(f"  [🟡] scripts/{name}: 一回スクリプト {age_days}日前")
    return candidates


def scan_broken_references() -> list[dict]:
    """docs/ 内の .md ファイルが参照している他ファイルの存在確認"""
    broken = []
    for filepath in sorted((REPO_ROOT / "docs").glob("*.md")):
        if is_excluded(filepath):
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            # [テキスト](パス) 形式の参照を抽出（プレースホルダーは除外）
            refs = re.findall(r'\[.*?\]\(([^)#]+)\)', content)
            # "URL", "path/to/file" のようなプレースホルダーを除外
            refs = [r for r in refs if r not in ("URL", "path/to/file", "link") and not r.startswith("{")]
            for ref in refs:
                if ref.startswith("http"):
                    continue
                ref_path = (filepath.parent / ref).resolve()
                if not ref_path.exists() and not (REPO_ROOT / ref).exists():
                    broken.append({
                        "path": filepath.relative_to(REPO_ROOT).as_posix(),
                        "severity": "🟡",
                        "age_days": 0,
                        "issues": [f"リンク切れ: `{ref}` が存在しない"],
                        "action": "fix",
                    })
        except Exception:
            pass
    return broken


def write_output(
    md_candidates: list[dict],
    script_candidates: list[dict],
    broken_refs: list[dict],
):
    """PENDING_CLEANUP.md を生成"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_items = md_candidates + script_candidates + broken_refs

    # 番号付け
    numbered = []
    for i, item in enumerate(all_items, start=1):
        item["no"] = i
        numbered.append(item)

    high = [x for x in numbered if x["severity"] == "🔴"]
    mid  = [x for x in numbered if x["severity"] == "🟡"]

    lines = [
        f"# PENDING_CLEANUP — {now}",
        "",
        "> このファイルは `scripts/repo-audit.py` が自動生成しました。",
        "> **使い方**: Claude Code に「N番を削除して」「N番をアーカイブして」と伝えるだけ。",
        "> **無視したい場合**: 該当行を削除してから保存してください（次回監査まで無視されます）。",
        "",
        f"検出件数: 🔴 要対応 {len(high)}件 / 🟡 要確認 {len(mid)}件",
        "",
        "---",
        "",
    ]

    if not numbered:
        lines += [
            "## ✅ 問題なし",
            "",
            "現在のリポジトリに整理が必要なファイルは見つかりませんでした。",
        ]
    else:
        if high:
            lines += ["## 🔴 要対応（古いまたは廃止済みコンテンツ）", ""]
            for item in high:
                action_label = {"delete": "削除推奨", "archive": "アーカイブ推奨", "fix": "修正推奨"}.get(item["action"], "確認")
                lines.append(f"### [{item['no']}] `{item['path']}`")
                lines.append(f"**推奨アクション**: {action_label}")
                for issue in item["issues"]:
                    lines.append(f"- {issue}")
                lines.append("")

        if mid:
            lines += ["## 🟡 要確認", ""]
            for item in mid:
                action_label = {"delete": "削除候補", "archive": "アーカイブ候補", "fix": "修正候補"}.get(item["action"], "確認")
                lines.append(f"### [{item['no']}] `{item['path']}`")
                lines.append(f"**推奨アクション**: {action_label}")
                for issue in item["issues"]:
                    lines.append(f"- {issue}")
                lines.append("")

    lines += [
        "---",
        "",
        "## 承認方法",
        "",
        "Claude Code にそのまま伝えるだけ：",
        "",
        "```",
        "「1番と3番を削除して」",
        "「2番をアーカイブして」",
        "「全部承認して」",
        "「今回は全部スキップ」",
        "```",
        "",
        f"*次回自動実行: 月1回（Windows タスクスケジューラ）*",
        f"*手動実行: `python scripts/repo-audit.py`*",
    ]

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    return len(numbered)


def register_task_scheduler():
    """Windows タスクスケジューラに月1回の自動実行を登録"""
    script_path = Path(__file__).resolve()
    python_exe = sys.executable

    # タスク名
    task_name = "VPS-RepoAudit-Monthly"

    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-03-01T10:00:00</StartBoundary>
      <ScheduleByMonth>
        <DaysOfMonth><Day>1</Day></DaysOfMonth>
        <Months><January/><February/><March/><April/><May/><June/>
                <July/><August/><September/><October/><November/><December/></Months>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{script_path}"</Arguments>
      <WorkingDirectory>{REPO_ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
  </Settings>
</Task>"""

    xml_file = REPO_ROOT / ".claude" / "repo-audit-task.xml"
    xml_file.write_text(xml, encoding="utf-16")

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", task_name, "/XML", str(xml_file), "/F"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"✅ タスクスケジューラ登録完了: {task_name}")
        print("   毎月1日 10:00 に自動実行されます。")
    else:
        print(f"❌ 登録失敗: {result.stderr}")
        print(f"   手動で実行してください: python scripts/repo-audit.py")


# ==================== メイン ====================

def main():
    if "--schedule" in sys.argv:
        register_task_scheduler()
        return

    print(f"=== repo-audit.py ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
    print(f"repo: {REPO_ROOT}")
    print()

    print("[1/3] Markdown scan...")
    md_candidates = scan_md_files()
    print(f"  -> {len(md_candidates)} items")

    print("[2/3] One-off scripts scan...")
    script_candidates = scan_oneoff_scripts()
    print(f"  -> {len(script_candidates)} items")

    print("[3/3] Broken links check...")
    broken_refs = scan_broken_references()
    print(f"  -> {len(broken_refs)} items")

    print()
    total = write_output(md_candidates, script_candidates, broken_refs)

    if total == 0:
        print("OK: no issues found.")
    else:
        print(f"DONE: {total} items -> PENDING_CLEANUP.md")
        print(f"  Open PENDING_CLEANUP.md in VSCode and tell Claude Code which items to approve.")

    print()
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
