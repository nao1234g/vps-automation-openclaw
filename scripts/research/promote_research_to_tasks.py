"""
scripts/research/promote_research_to_tasks.py
Research → Task 昇格スクリプト

daily_paper_ingest.py の radar.json から高関連度アイテムを選別し、
task_ledger.json に「[Research] タイトル」形式のタスクとして登録する。

daily_paper_ingest.py の promote_to_task() との違い:
  - こちらは独立した CLIツール（スタンドアロン実行可）
  - より厳格なフィルタリング（min_relevance, min_freshness, already_promoted チェック）
  - Telegram通知付き
  - ドライランモード付き
  - バッチ処理（複数アイテムを一括処理）

使い方:
  python scripts/research/promote_research_to_tasks.py --top 3
  python scripts/research/promote_research_to_tasks.py --min-relevance 0.6 --dry-run
  python scripts/research/promote_research_to_tasks.py --all  # 基準を満たす全件

Geneenの原則: 「管理者は管理する。実行が伴っていなければ意味がない」
"""

import sys
import os
import json
import argparse
import urllib.request
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── パス定義 ──────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR",
    os.path.abspath(os.path.join(_HERE, "..", ".."))
)
_RESEARCH_DIR = os.path.join(_PROJECT_ROOT, "data", "research")
_RADAR_PATH = os.path.join(_RESEARCH_DIR, "radar.json")
_LEDGER_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "task_ledger.json")
_ENV_PATH = "/opt/cron-env.sh"

# ── タイムラインレコーダー ─────────────────────────────────────────────
try:
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from knowledge_timeline_recorder import record_run as _record_timeline_run
except Exception:
    def _record_timeline_run(*a, **kw): pass  # サイレントフォールバック

# デフォルト閾値
DEFAULT_MIN_RELEVANCE = 0.6
DEFAULT_MIN_FRESHNESS = 0.1  # 約 87 日以内
DEFAULT_TOP = 3


# ── 環境変数 ──────────────────────────────────────────────────────────

def _load_env() -> Dict[str, str]:
    env = {}
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    if os.path.exists(_ENV_PATH):
        try:
            for line in open(_ENV_PATH, encoding="utf-8"):
                line = line.strip()
                if line.startswith("export "):
                    k, _, v = line[7:].partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in env:
                        env[k] = v
        except Exception:
            pass
    return env


# ── レーダー・台帳操作 ────────────────────────────────────────────────

def _load_radar() -> Dict:
    if not os.path.exists(_RADAR_PATH):
        return {"items": []}
    try:
        return json.load(open(_RADAR_PATH, encoding="utf-8"))
    except Exception as e:
        print(f"[PROMOTE] radar.json 読み込みエラー: {e}", file=sys.stderr)
        return {"items": []}


def _save_radar(radar: Dict):
    with open(_RADAR_PATH, "w", encoding="utf-8") as f:
        json.dump(radar, f, ensure_ascii=False, indent=2)


def _load_ledger() -> Dict:
    if not os.path.exists(_LEDGER_PATH):
        return {"tasks": []}
    try:
        return json.load(open(_LEDGER_PATH, encoding="utf-8"))
    except Exception as e:
        print(f"[PROMOTE] task_ledger.json 読み込みエラー: {e}", file=sys.stderr)
        return {"tasks": []}


def _save_ledger(ledger: Dict):
    with open(_LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)


def _next_task_id(tasks: List[Dict]) -> str:
    max_num = 0
    for t in tasks:
        tid = t.get("id", "T000")
        try:
            num = int(tid[1:])
            max_num = max(max_num, num)
        except ValueError:
            pass
    return f"T{max_num + 1:03d}"


# ── フィルタリング ────────────────────────────────────────────────────

def _select_candidates(
    items: List[Dict],
    min_relevance: float,
    min_freshness: float,
    skip_promoted: bool = True,
    max_age_days: int = 90,
) -> List[Dict]:
    """
    昇格候補を選別する

    基準:
      - relevance >= min_relevance
      - freshness >= min_freshness
      - promoted_to_task == False (skip_promoted=True の場合)
      - ingested_at が max_age_days 以内
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    candidates = []

    for it in items:
        if skip_promoted and it.get("promoted_to_task"):
            continue
        if it.get("relevance", 0) < min_relevance:
            continue
        if it.get("freshness", 0) < min_freshness:
            continue
        if it.get("ingested_at", "") < cutoff:
            continue
        candidates.append(it)

    # composite スコアでソート
    def composite(it: Dict) -> float:
        return it.get("relevance", 0) * 0.6 + it.get("freshness", 0) * 0.4

    return sorted(candidates, key=composite, reverse=True)


# ── タスク生成 ────────────────────────────────────────────────────────

def _create_task(item: Dict, task_id: str) -> Dict:
    """research アイテムからタスクエントリを生成する"""
    now = datetime.now(timezone.utc).isoformat()
    title = item.get("title", "")[:60]
    source = item.get("source", "unknown")
    relevance = item.get("relevance", 0)
    url = item.get("url", "")
    abstract = item.get("abstract", "")[:200]

    return {
        "id": task_id,
        "title": f"[Research] {title}",
        "rationale": (
            f"Research Radar が高関連度論文を検出。\n"
            f"ソース: {source} | 関連度: {relevance:.2f}\n"
            f"概要: {abstract}"
        ),
        "target_files": [],
        "acceptance_criteria": [
            f"論文を読み、Nowpatternへの応用可能性を評価する",
            f"応用できる場合: 実装タスクを台帳に追加する",
            f"応用できない場合: タスクを archived にする",
            f"学習内容を docs/AGENT_WISDOM.md に記録する",
        ],
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "owner": "local-claude",
        "related_failures": [],
        "verification_links": [url] if url else [],
        "research_metadata": {
            "item_id": item.get("item_id", ""),
            "source": source,
            "relevance": relevance,
            "freshness": item.get("freshness", 0),
            "confidence": item.get("confidence", 0),
            "published_at": item.get("published_at", ""),
            "tags": item.get("tags", []),
        },
    }


# ── Telegram通知 ──────────────────────────────────────────────────────

def _send_telegram(message: str, env: Dict[str, str]) -> bool:
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15):
            pass
        return True
    except Exception as e:
        print(f"[PROMOTE] Telegram送信エラー: {e}", file=sys.stderr)
        return False


# ── メイン ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Research → Task 昇格スクリプト")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP,
                        help=f"上位 N 件を昇格（デフォルト: {DEFAULT_TOP}）")
    parser.add_argument("--all", action="store_true",
                        help="基準を満たす全件を昇格（--top を上書き）")
    parser.add_argument("--min-relevance", type=float, default=DEFAULT_MIN_RELEVANCE,
                        help=f"最低 relevance スコア（デフォルト: {DEFAULT_MIN_RELEVANCE}）")
    parser.add_argument("--min-freshness", type=float, default=DEFAULT_MIN_FRESHNESS,
                        help=f"最低 freshness スコア（デフォルト: {DEFAULT_MIN_FRESHNESS}）")
    parser.add_argument("--include-promoted", action="store_true",
                        help="すでに昇格済みのアイテムも対象に含める")
    parser.add_argument("--dry-run", action="store_true",
                        help="実際には書き込まない（確認用）")
    parser.add_argument("--telegram", action="store_true",
                        help="昇格結果を Telegram に通知する")
    args = parser.parse_args()

    print(f"[PROMOTE] リサーチ昇格スクリプト開始")
    print(f"  min_relevance={args.min_relevance} min_freshness={args.min_freshness}")

    # レーダーと台帳を読む
    radar = _load_radar()
    items = radar.get("items", [])
    ledger = _load_ledger()
    tasks = ledger.get("tasks", [])

    print(f"[PROMOTE] レーダーアイテム: {len(items)}件 | 既存タスク: {len(tasks)}件")

    # 候補を選別
    candidates = _select_candidates(
        items,
        min_relevance=args.min_relevance,
        min_freshness=args.min_freshness,
        skip_promoted=not args.include_promoted,
    )

    print(f"[PROMOTE] 昇格候補: {len(candidates)}件")

    if not candidates:
        print("[PROMOTE] 昇格候補なし。終了")
        return

    # 昇格数を決定
    promote_count = len(candidates) if args.all else min(args.top, len(candidates))
    targets = candidates[:promote_count]

    print(f"[PROMOTE] 昇格対象: {promote_count}件")
    for it in targets:
        print(f"  [{it['relevance']:.2f}] {it.get('title', '')[:60]}")

    if args.dry_run:
        print("[PROMOTE] --dry-run のため実際には登録しません")
        return

    # タスク昇格
    promoted_tasks = []
    radar_updated = False

    for item in targets:
        new_id = _next_task_id(tasks)
        new_task = _create_task(item, new_id)
        tasks.append(new_task)
        promoted_tasks.append(new_task)

        # radar.json の promoted_to_task フラグを更新
        for radar_item in radar.get("items", []):
            if radar_item.get("item_id") == item.get("item_id"):
                radar_item["promoted_to_task"] = True
                radar_updated = True
                break

        print(f"[PROMOTE] ✅ タスク登録: {new_id} — {new_task['title'][:50]}")

    # 保存
    ledger["tasks"] = tasks
    _save_ledger(ledger)

    if radar_updated:
        _save_radar(radar)

    print(f"[PROMOTE] 完了: {len(promoted_tasks)}件のタスクを登録しました")

    # Telegram通知
    if args.telegram and promoted_tasks:
        env = _load_env()
        lines = [f"📚 *Research → Task 昇格完了*\n{len(promoted_tasks)}件の論文をタスクに登録:\n"]
        for t in promoted_tasks:
            meta = t.get("research_metadata", {})
            lines.append(
                f"• *{t['title'][:60]}*\n"
                f"  rel={meta.get('relevance', 0):.2f} | {meta.get('source', '')} | ID: {t['id']}"
            )
        _send_telegram("\n".join(lines), env)

    _record_timeline_run(
        source="combined",
        items_ingested=0,  # promote は昇格処理のみで新規取り込みなし
        items_total=len(items),
        topics=[],
        promoted_count=len(promoted_tasks),
        top_items=[t["title"] for t in promoted_tasks[:3]],
        radar_size=len(items),
        run_status="ok",
        notes="promote run",
    )


if __name__ == "__main__":
    main()
