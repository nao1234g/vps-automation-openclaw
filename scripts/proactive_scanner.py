#!/usr/bin/env python3
"""
PROACTIVE SCANNER — 既知アンチパターンをVPSスクリプトから事前検出
=========================================================================
mistake_patterns.json のガードパターンを使い、VPS上のPythonスクリプトを
スキャンして「壊れる前に」危険なコードを発見してTelegram通知する。

設計原則:
  エラーが起きた後に記録するのではなく、
  エラーが起きる前にコードを検査して根絶する。

  Google SRE: 「本番障害をテストに変換する」
  DORA: 「シフトレフト = 問題を上流で発見する」

cronコマンド（VPSで設定）:
  0 9 * * 1 python3 /opt/shared/scripts/proactive_scanner.py  # 毎週月曜9:00

実行方法:
  python3 /opt/shared/scripts/proactive_scanner.py
  python3 /opt/shared/scripts/proactive_scanner.py --dry-run  # Telegram通知なし
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# ── 設定 ─────────────────────────────────────────────────────────────────────
PATTERNS_FILE = "/opt/shared/state/mistake_patterns.json"
SCAN_DIRS = [
    "/opt/shared/scripts/",
    "/opt/neo-telegram/",
    "/opt/neo2-telegram/",
    "/opt/neo3-codex/",
]
HISTORY_FILE = "/opt/shared/state/proactive_scan_history.json"

# 除外ファイル（スキャン対象外）
SKIP_FILES = {
    "proactive_scanner.py",  # 自分自身
}


# ── 環境変数 ──────────────────────────────────────────────────────────────────
def load_env():
    env = {}
    try:
        with open("/opt/cron-env.sh") as f:
            for line in f:
                if line.startswith("export "):
                    k, _, v = line[7:].strip().partition("=")
                    env[k] = v.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[WARN] cron-env.sh 読み込み失敗: {e}")
    return env


ENV = load_env()
BOT_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = ENV.get("TELEGRAM_CHAT_ID", "")

DRY_RUN = "--dry-run" in sys.argv


# ── Telegram送信 ──────────────────────────────────────────────────────────────
def send_telegram(msg: str):
    if DRY_RUN:
        print(f"[DRY-RUN] Telegram送信スキップ:\n{msg}")
        return
    if not BOT_TOKEN or not CHAT_ID:
        print("[WARN] Telegram設定なし")
        return
    # 4096文字制限
    if len(msg) > 4000:
        msg = msg[:3900] + "\n...(省略)"
    data = json.dumps({
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"[ERROR] Telegram送信失敗: {e}")


# ── パターン読み込み ───────────────────────────────────────────────────────────
def load_patterns():
    if not os.path.exists(PATTERNS_FILE):
        print(f"[WARN] {PATTERNS_FILE} が見つかりません")
        return []
    try:
        with open(PATTERNS_FILE, encoding="utf-8") as f:
            patterns = json.load(f)
        # 正規表現としてコンパイル可能なもののみ有効化
        valid = []
        for p in patterns:
            try:
                re.compile(p["pattern"])
                valid.append(p)
            except re.error as e:
                print(f"[WARN] 無効な正規表現 ({p.get('name','?')}): {e}")
        return valid
    except Exception as e:
        print(f"[ERROR] パターン読み込み失敗: {e}")
        return []


# ── スキャン ──────────────────────────────────────────────────────────────────
def scan_file(file_path: str, patterns: list) -> list:
    """1ファイルをスキャンしてヒットしたパターンのリストを返す"""
    hits = []
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[SKIP] {file_path}: {e}")
        return []

    for pattern_def in patterns:
        pat = pattern_def["pattern"]
        name = pattern_def.get("name", "?")
        feedback = pattern_def.get("feedback", "")
        try:
            compiled = re.compile(pat, re.MULTILINE)
            for lineno, line in enumerate(lines, 1):
                if compiled.search(line):
                    hits.append({
                        "file": file_path,
                        "line": lineno,
                        "pattern_name": name,
                        "feedback": feedback,
                        "matched_text": line.strip()[:120],
                    })
                    break  # 1パターンにつき1回のみ報告（行数節約）
        except Exception:
            continue
    return hits


# ── AST構造解析（regexバイパス防止 — 意味ベース検知）────────────────────────
# 設計原則: regexは「文字」を見る。ASTは「構造」を見る。
# 構文を変えてもASTノードは同一 → バイパス不可能。

import ast as _ast

# AST検出ルール（{name, check_fn, feedback}）
_AST_RULES = []


def _ast_rule(name: str, feedback: str):
    """デコレータ: check_fn(tree, lines) -> list of {line, matched_text}"""
    def decorator(fn):
        _AST_RULES.append({"name": name, "feedback": feedback, "fn": fn})
        return fn
    return decorator


@_ast_rule(
    name="FCNTL_LINUX_ONLY_AST",
    feedback="⛔ fcntlはLinux専用。if sys.platform != 'win32': import fcntl でガードしてください"
)
def _check_fcntl(tree, lines):
    """import fcntl が platform checkなしに使われている"""
    hits = []
    has_platform_check = False
    # sys.platform チェックがファイル内に存在するか確認
    src = "\n".join(lines)
    if "sys.platform" in src or "platform.system" in src:
        has_platform_check = True

    if not has_platform_check:
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    if alias.name == "fcntl":
                        line = getattr(node, "lineno", 0)
                        hits.append({
                            "line": line,
                            "matched_text": lines[line-1].strip()[:120] if line > 0 else "import fcntl"
                        })
    return hits


@_ast_rule(
    name="UNGUARDED_HTTP_RESPONSE_AST",
    feedback="⛔ HTTP応答送信はBrokenPipeError をキャッチしてください: try: self.send_response(...) except BrokenPipeError: pass"
)
def _check_http_response(tree, lines):
    """self.send_response / self.wfile.write が try-except なしに呼ばれている"""
    hits = []
    for node in _ast.walk(tree):
        # send_response呼び出しを検索
        if isinstance(node, _ast.Call):
            if isinstance(node.func, _ast.Attribute):
                if node.func.attr in ("send_response", "end_headers") and \
                   isinstance(node.func.value, _ast.Name) and \
                   node.func.value.id == "self":
                    # 親ノードがTry文か確認（簡易チェック: ソース行に try が近くにあるか）
                    line = getattr(node, "lineno", 0)
                    if line > 0:
                        context = "\n".join(lines[max(0, line-5):line+2])
                        if "try:" not in context and "BrokenPipeError" not in context:
                            hits.append({
                                "line": line,
                                "matched_text": lines[line-1].strip()[:120]
                            })
                            break  # 1ファイル1件のみ
    return hits


@_ast_rule(
    name="LARGE_PAYLOAD_READ_AST",
    feedback="⛔ rfile.read()はmin()ガードが必要: read_size = min(content_length, 65536)"
)
def _check_large_read(tree, lines):
    """self.rfile.read() が min() なしに呼ばれている"""
    hits = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            if isinstance(node.func, _ast.Attribute):
                if node.func.attr == "read" and isinstance(node.func.value, _ast.Attribute):
                    if node.func.value.attr == "rfile":
                        # 引数にmin()が含まれているか
                        has_min = any(
                            isinstance(arg, _ast.Call) and
                            isinstance(arg.func, _ast.Name) and
                            arg.func.id == "min"
                            for arg in node.args
                        )
                        if not has_min and node.args:  # 引数あり（read(n)形式）
                            line = getattr(node, "lineno", 0)
                            if line > 0:
                                hits.append({
                                    "line": line,
                                    "matched_text": lines[line-1].strip()[:120]
                                })
                            break
    return hits


@_ast_rule(
    name="REQUESTS_NO_VERIFY_AST",
    feedback="⛔ requests.get/postはnowpattern.comへはverify=Falseが必要です"
)
def _check_requests_verify(tree, lines):
    """requests.get/post/put で nowpattern を含むURLに verify=False がない"""
    hits = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            if isinstance(node.func, _ast.Attribute):
                if node.func.attr in ("get", "post", "put") and \
                   isinstance(node.func.value, _ast.Name) and \
                   node.func.value.id == "requests":
                    # URL引数に nowpattern が含まれているか
                    url_arg = ""
                    if node.args:
                        first_arg = node.args[0]
                        if isinstance(first_arg, _ast.Constant):
                            url_arg = str(first_arg.value)
                    if "nowpattern" in url_arg:
                        # verify=False キーワードがあるか
                        has_verify = any(
                            kw.arg == "verify" for kw in node.keywords
                        )
                        if not has_verify:
                            line = getattr(node, "lineno", 0)
                            if line > 0:
                                hits.append({
                                    "line": line,
                                    "matched_text": lines[line-1].strip()[:120]
                                })
    return hits


def scan_file_ast(file_path: str) -> list:
    """1ファイルをAST解析してヒットしたパターンのリストを返す"""
    hits = []
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            source = f.read()
            lines = source.splitlines()
    except Exception:
        return []

    try:
        tree = _ast.parse(source, filename=file_path)
    except SyntaxError:
        return []  # 構文エラーのファイルはスキップ

    for rule in _AST_RULES:
        try:
            rule_hits = rule["fn"](tree, lines)
            for h in rule_hits:
                hits.append({
                    "file": file_path,
                    "line": h.get("line", 0),
                    "pattern_name": rule["name"] + " [AST]",
                    "feedback": rule["feedback"],
                    "matched_text": h.get("matched_text", ""),
                    "detection_type": "AST",
                })
        except Exception:
            continue

    return hits


def scan_all(patterns: list) -> list:
    """全スキャン対象ディレクトリをスキャン（regex + AST）"""
    all_hits = []
    scanned = 0
    ast_hits_total = 0
    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            continue
        for fname in os.listdir(scan_dir):
            if fname in SKIP_FILES:
                continue
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(scan_dir, fname)
            # regex スキャン
            hits = scan_file(fpath, patterns)
            all_hits.extend(hits)
            # AST スキャン（regexバイパス防止）
            ast_hits = scan_file_ast(fpath)
            all_hits.extend(ast_hits)
            ast_hits_total += len(ast_hits)
            scanned += 1
    print(f"[SCAN] {scanned}ファイルをスキャン、{len(all_hits)}件ヒット（うちAST検知: {ast_hits_total}件）")
    return all_hits


# ── 履歴（前回から新しいヒットのみ通知）────────────────────────────────────────
def load_history() -> dict:
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"known_hits": []}


def save_history(history: dict):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_hit_key(hit: dict) -> str:
    return f"{hit['file']}:{hit['line']}:{hit['pattern_name']}"


# ── メイン ────────────────────────────────────────────────────────────────────
def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M JST")
    print(f"[Proactive Scanner] {now}")
    print(f"  DRY-RUN: {DRY_RUN}")

    # パターン読み込み
    patterns = load_patterns()
    if not patterns:
        print("[WARN] 有効なパターンが0件。スキャンをスキップします。")
        return
    print(f"[INFO] {len(patterns)}件のガードパターンをロード")

    # スキャン実行
    hits = scan_all(patterns)

    # 履歴で差分を取る（既知ヒットは通知しない）
    history = load_history()
    known_keys = set(history.get("known_hits", []))
    new_hits = [h for h in hits if get_hit_key(h) not in known_keys]

    # 履歴更新（現在のヒット全件を保存）
    history["known_hits"] = [get_hit_key(h) for h in hits]
    history["last_scan"] = now
    history["total_patterns"] = len(patterns)
    save_history(history)

    if not new_hits:
        print(f"[OK] 新規ヒットなし（既知: {len(known_keys)}件）")
        # 月曜のみサイレント成功をサマリー送信
        if datetime.now().weekday() == 0:
            send_telegram(
                f"✅ *[Proactive Scanner] 週次スキャン: 新規ヒットなし*\n"
                f"日時: {now}\n"
                f"スキャン対象: {len(patterns)}パターン\n"
                f"既知の問題: {len(known_keys)}件（解決済み or 継続監視中）"
            )
        return

    # 新規ヒットをTelegram通知
    lines = [f"⚠️ *[Proactive Scanner] 新規アンチパターン検出: {len(new_hits)}件*"]
    lines.append(f"日時: {now}")
    lines.append(f"スキャンパターン数: {len(patterns)}")
    lines.append("")

    for i, hit in enumerate(new_hits[:10], 1):  # 最大10件
        fname = os.path.basename(hit["file"])
        lines.append(f"*{i}. {hit['pattern_name']}*")
        lines.append(f"  ファイル: `{fname}` L{hit['line']}")
        lines.append(f"  コード: `{hit['matched_text'][:80]}`")
        lines.append(f"  対処: {hit['feedback'][:100]}")
        lines.append("")

    if len(new_hits) > 10:
        lines.append(f"（他 {len(new_hits) - 10}件は省略）")

    lines.append("→ 修正後は次回スキャン時に自動的に既知扱いになります。")
    msg = "\n".join(lines)
    print(msg)
    send_telegram(msg)

    # 終了コード: 新規ヒットがあれば1（cronのエラー検知に使える）
    sys.exit(1 if new_hits else 0)


if __name__ == "__main__":
    main()
