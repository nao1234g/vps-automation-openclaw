#!/usr/bin/env python3
"""
VPS FEEDBACK SYNC — 双方向学習フィードバック
=============================================
現状: ローカル → VPS (一方向)
改善: VPS → ローカル (双方向フィードバックループを完成させる)

NEO-ONE/TWOがVPSで犯したミスを → ローカルの mistake_patterns.json に反映する。
「NEOのミス = ローカルのガードに即反映」という閉ループ。

処理フロー:
  1. VPSのエラーログを取得（SSH経由）
  2. 新しいエラーパターン候補を抽出
  3. 既存パターンと重複チェック
  4. 新候補をTelegramに通知（Naotoの承認待ち）
  5. 承認されたものをmistake_patterns.jsonに追加

実行方法:
  python scripts/vps_feedback_sync.py           # 通常実行
  python scripts/vps_feedback_sync.py --dry-run # Telegram通知なし
  python scripts/vps_feedback_sync.py --auto-approve # 全自動承認（危険: テスト用のみ）

cronで実行（週次 or SessionEnd後）:
  session-end.py の step 6として追加 → セッション終了時にVPSから最新ミスを取得
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).parent.parent
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
PATTERNS_FILE = STATE_DIR / "mistake_patterns.json"
SYNC_STATE_FILE = STATE_DIR / "vps_feedback_sync.json"
VPS = "root@163.44.124.123"

# VPS上のエラーログパス
VPS_ERROR_LOGS = [
    "/opt/shared/task-log/",          # タスクログ
    "/opt/neo-telegram/logs/",         # NEO-ONEログ
    "/opt/neo2-telegram/logs/",        # NEO-TWOログ
    "/tmp/neo_errors.log",             # 一時エラーログ
]

# エラーパターン検出用正規表現（VPSログから）
ERROR_INDICATORS = [
    r"Error|ERROR|エラー|失敗|failed|FAILED|Traceback",
    r"404|500|403|401|Connection refused",
    r"ModuleNotFoundError|ImportError|AttributeError",
]

# ── .env読み込み ─────────────────────────────────────────────────────────────
def load_config():
    env_file = PROJECT_DIR / ".env"
    config = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                config[k.strip()] = v.strip().strip('"').strip("'")
    return config


def send_telegram(msg: str, dry_run: bool = False):
    if dry_run:
        print(f"[DRY-RUN] Telegram skip:\n{msg[:300]}")
        return
    config = load_config()
    bot_token = config.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = config.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        print("[WARN] Telegram設定なし")
        return
    if len(msg) > 4000:
        msg = msg[:3900] + "\n...(省略)"
    data = json.dumps({
        "chat_id": chat_id, "text": msg, "parse_mode": "Markdown"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"[WARN] Telegram: {e}")


# ── VPSからエラーログ取得 ────────────────────────────────────────────────────
def fetch_vps_recent_errors(since_days: int = 7) -> list:
    """VPSの直近N日分のエラーを取得して返す"""
    errors = []

    # 方法1: task-logから最近のエラーを検索
    cmd = (
        f"find /opt/shared/task-log/ -name '*.md' -newer /tmp/.sync_marker 2>/dev/null | "
        f"xargs grep -l 'Error\\|ERROR\\|エラー\\|失敗' 2>/dev/null | head -20"
    )
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
             "-o", "BatchMode=yes", VPS, cmd],
            capture_output=True, text=True, encoding="utf-8", timeout=15
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        for fpath in files[:10]:
            # ファイル内容の最初の部分を取得
            cat_result = subprocess.run(
                ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
                 "-o", "BatchMode=yes", VPS, f"head -50 '{fpath}'"],
                capture_output=True, text=True, encoding="utf-8", timeout=10
            )
            if cat_result.stdout:
                errors.append({
                    "source": fpath,
                    "content": cat_result.stdout[:1000]
                })
    except Exception as e:
        print(f"[WARN] task-log取得失敗: {e}")

    # 方法2: NEO-ONEの最近のエラーを直接取得
    neo_cmd = (
        "journalctl -u neo-telegram.service -n 100 --no-pager 2>/dev/null | "
        "grep -E 'Error|ERROR|Traceback|failed' | tail -30"
    )
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
             "-o", "BatchMode=yes", VPS, neo_cmd],
            capture_output=True, text=True, encoding="utf-8", timeout=15
        )
        if result.stdout.strip():
            errors.append({
                "source": "neo-telegram.service (journalctl)",
                "content": result.stdout[:1000]
            })
    except Exception as e:
        print(f"[WARN] NEOログ取得失敗: {e}")

    return errors


# ── エラーからパターン候補を抽出 ─────────────────────────────────────────────
def extract_pattern_candidates(errors: list, existing_patterns: list) -> list:
    """
    エラーログから再発しやすいパターンを抽出する。
    シンプルなヒューリスティック + 既存パターンとの差分チェック。
    """
    existing_names = {p.get("name", "") for p in existing_patterns}
    existing_examples = {p.get("example", "")[:50] for p in existing_patterns}

    candidates = []
    seen_patterns = set()

    # エラーメッセージのよくある構造を抽出
    extractors = [
        # Ghost API エラー
        (r"Ghost.*?(?:Error|error).*?:\s*(.{20,80})", "GHOST_API"),
        # Python エラー
        (r"(ModuleNotFoundError|ImportError|AttributeError):\s*(.{10,60})", "PYTHON_IMPORT"),
        # HTTP エラー
        (r"(?:HTTP|http)\s+(\d{3})\s+(?:on\s+)?(.{10,60})", "HTTP_ERROR"),
        # SSH/接続エラー
        (r"(Connection refused|timeout|TIMEOUT).*?(\S+:\d+)", "CONNECTION"),
        # NEOのミス
        (r"(?:ERROR|Error).*?neo.*?:\s*(.{20,80})", "NEO_ERROR"),
    ]

    for error_entry in errors:
        content = error_entry.get("content", "")
        source = error_entry.get("source", "?")

        for pattern_re, category in extractors:
            matches = re.findall(pattern_re, content, re.IGNORECASE)
            for match in matches[:2]:
                if isinstance(match, tuple):
                    example = " ".join(match).strip()
                else:
                    example = match.strip()

                # 重複チェック
                key = example[:40]
                if key in seen_patterns:
                    continue
                if example[:40] in existing_examples:
                    continue
                seen_patterns.add(key)

                candidates.append({
                    "category": category,
                    "example": example,
                    "source": source,
                    "raw_snippet": content[:200]
                })

    return candidates[:10]  # 最大10候補


# ── 同期状態の管理 ───────────────────────────────────────────────────────────
def load_sync_state() -> dict:
    if SYNC_STATE_FILE.exists():
        try:
            return json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_sync": "2000-01-01T00:00:00", "synced_hashes": []}


def save_sync_state(state: dict):
    SYNC_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── メイン ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-approve", action="store_true",
                        help="全候補を自動承認（テスト用のみ）")
    parser.add_argument("--force", action="store_true",
                        help="前回同期済みでも再実行")
    args = parser.parse_args()

    now_str = datetime.now().isoformat()
    now_display = datetime.now().strftime("%Y-%m-%d %H:%M JST")
    print(f"[VPS Feedback Sync] {now_display}")

    # 同期頻度チェック（週1回で十分）
    sync_state = load_sync_state()
    if not args.force:
        last_sync = datetime.fromisoformat(sync_state.get("last_sync", "2000-01-01"))
        if (datetime.now() - last_sync) < timedelta(days=6):
            days_ago = (datetime.now() - last_sync).days
            print(f"[SKIP] 前回同期から{days_ago}日（週1回で十分）。--forceで強制実行可能。")
            sys.exit(0)

    # 既存パターン読み込み
    existing = []
    if PATTERNS_FILE.exists():
        try:
            existing = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    print(f"[INFO] 既存パターン: {len(existing)}件")

    # VPSからエラー取得
    print("[INFO] VPSからエラーログを取得中...")
    errors = fetch_vps_recent_errors(since_days=7)
    print(f"[INFO] エラーエントリ取得: {len(errors)}件")

    if not errors:
        print("[OK] VPSエラーなし（または取得失敗）")
        # 同期日時を更新
        sync_state["last_sync"] = now_str
        save_sync_state(sync_state)
        sys.exit(0)

    # パターン候補抽出
    candidates = extract_pattern_candidates(errors, existing)
    print(f"[INFO] 新パターン候補: {len(candidates)}件")

    if not candidates:
        print("[OK] 新規パターン候補なし")
        sync_state["last_sync"] = now_str
        save_sync_state(sync_state)
        sys.exit(0)

    # 自動承認モード（テスト用）
    if args.auto_approve:
        today = datetime.now().strftime("%Y-%m-%d")
        added = 0
        for c in candidates:
            name = f"VPS_AUTO_{c['category']}_{datetime.now().strftime('%H%M%S')}"
            new_pattern = {
                "pattern": re.escape(c["example"][:40]),
                "feedback": f"⛔ VPSフィードバックから自動登録: {c['example'][:60]}",
                "name": name,
                "example": c["example"],
                "added_at": today,
                "source": "vps-feedback-sync",
            }
            existing.append(new_pattern)
            added += 1
        if added > 0:
            PATTERNS_FILE.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"[AUTO-APPROVE] {added}件のパターンを自動登録しました")

    # Telegram通知（承認を求める）
    lines = [f"🔄 *[VPS Feedback Sync] 新しいエラーパターン候補*"]
    lines.append(f"日時: {now_display}")
    lines.append(f"VPSエラーエントリ: {len(errors)}件")
    lines.append(f"新パターン候補: {len(candidates)}件")
    lines.append("")
    lines.append("以下を `mistake_patterns.json` に追加しますか？")
    lines.append("（docs/KNOWN_MISTAKES.md に GUARD_PATTERN フィールドで追記してください）")
    lines.append("")

    for i, c in enumerate(candidates[:5], 1):
        lines.append(f"*{i}. [{c['category']}]*")
        lines.append(f"  例: `{c['example'][:70]}`")
        lines.append(f"  出所: `{Path(c['source']).name}`")
        lines.append("")

    if len(candidates) > 5:
        lines.append(f"（他{len(candidates)-5}件 — レポート: {SYNC_STATE_FILE}）")

    lines.append("\n→ 承認: KNOWN_MISTAKES.md に GUARD_PATTERN として追加")
    lines.append("→ 却下: このメッセージを無視するだけ")

    send_telegram("\n".join(lines), dry_run=args.dry_run)

    # 状態保存（候補をファイルに残す）
    sync_state["last_sync"] = now_str
    sync_state["last_candidates"] = candidates
    sync_state["last_error_count"] = len(errors)
    save_sync_state(sync_state)

    print(f"[DONE] 候補{len(candidates)}件をTelegramに送信しました")
    print(f"[INFO] レポート: {SYNC_STATE_FILE}")


if __name__ == "__main__":
    main()
