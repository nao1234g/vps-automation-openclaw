"""
scripts/research/daily_research_digest.py
Research Radar 日次ダイジェスト — radar.json から人間が読める要約を生成する

Research Radar（daily_paper_ingest.py）が収集した論文データを
人間（Naoto）とエージェント（NEO-ONE/TWO）が消費しやすい形式に変換する。

出力形式:
  1. Telegramメッセージ（--telegram）
  2. Markdownレポート（--markdown、data/research/digest-YYYY-MM-DD.md）
  3. JSON要約（data/research/digest-YYYY-MM-DD.json）

使い方:
  python scripts/research/daily_research_digest.py
  python scripts/research/daily_research_digest.py --top 5
  python scripts/research/daily_research_digest.py --telegram
  python scripts/research/daily_research_digest.py --markdown --output data/research/

Geneenの原則: 「数字は言語。メトリクスなきシステムは盲目のパイロット」
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
_ENV_PATH = "/opt/cron-env.sh"  # VPS環境変数（Telegramトークン等）

# ── タイムラインレコーダー ─────────────────────────────────────────────
try:
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from knowledge_timeline_recorder import record_run as _record_timeline_run
except Exception:
    def _record_timeline_run(*a, **kw): pass  # サイレントフォールバック


# ── 環境変数読み込み ──────────────────────────────────────────────────

def _load_env() -> Dict[str, str]:
    """cron-env.sh または環境変数からトークン等を読む"""
    env = {}
    # まず環境変数を確認
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if os.environ.get(key):
            env[key] = os.environ[key]

    # VPS cron-env.sh から補完
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


# ── レーダー読み込み ──────────────────────────────────────────────────

def _load_radar() -> Dict:
    if not os.path.exists(_RADAR_PATH):
        return {"items": [], "last_updated": ""}
    try:
        return json.load(open(_RADAR_PATH, encoding="utf-8"))
    except Exception as e:
        print(f"[DIGEST] radar.json 読み込みエラー: {e}", file=sys.stderr)
        return {"items": [], "last_updated": ""}


def _filter_recent(items: List[Dict], days: int = 2) -> List[Dict]:
    """直近 N 日以内に取り込まれたアイテムを返す"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return [it for it in items if it.get("ingested_at", "") >= cutoff]


def _sort_by_score(items: List[Dict]) -> List[Dict]:
    """relevance × freshness × confidence で複合スコアを計算してソート"""
    def composite(it: Dict) -> float:
        r = it.get("relevance", 0)
        f = it.get("freshness", 0)
        c = it.get("confidence", 0.75)
        return r * 0.5 + f * 0.3 + c * 0.2

    return sorted(items, key=composite, reverse=True)


# ── フォーマット ──────────────────────────────────────────────────────

def _format_telegram(items: List[Dict], top_n: int = 5) -> str:
    """Telegram 向けフォーマット（Markdown）"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    top = items[:top_n]

    if not top:
        return f"📡 *Research Radar — {today}*\n新しい論文はありませんでした。"

    lines = [f"📡 *Research Radar — {today}*\n上位{len(top)}件の新着研究:\n"]

    for i, it in enumerate(top, 1):
        title = it.get("title", "")[:70]
        source = it.get("source", "")
        rel = it.get("relevance", 0)
        fresh = it.get("freshness", 0)
        url = it.get("url", "")
        promoted = "✅" if it.get("promoted_to_task") else ""

        source_label = "arXiv" if source == "arxiv" else "Semantic Scholar"
        lines.append(
            f"{i}. *{title}*\n"
            f"   {source_label} | rel={rel:.2f} fresh={fresh:.2f} {promoted}\n"
            f"   {url[:80]}\n"
        )

    # 統計
    total = len(items)
    promoted_count = sum(1 for it in items if it.get("promoted_to_task"))
    lines.append(f"\n📊 直近2日: {total}件 | タスク昇格: {promoted_count}件")

    return "\n".join(lines)


def _format_markdown(items: List[Dict], top_n: int = 10) -> str:
    """Markdown レポート形式"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    top = items[:top_n]

    lines = [
        f"# Research Radar Digest — {today}",
        "",
        f"生成日時: {datetime.now(timezone.utc).isoformat()}",
        f"直近2日の新規アイテム数: {len(items)}",
        f"タスク昇格済み: {sum(1 for it in items if it.get('promoted_to_task'))}件",
        "",
        "---",
        "",
        f"## TOP {top_n} 関連論文",
        "",
    ]

    for i, it in enumerate(top, 1):
        title = it.get("title", "")
        source = it.get("source", "")
        authors = ", ".join(it.get("authors", [])[:2])
        pub_date = it.get("published_at", "")
        rel = it.get("relevance", 0)
        fresh = it.get("freshness", 0)
        conf = it.get("confidence", 0)
        abstract = it.get("abstract", "")[:200]
        url = it.get("url", "")
        tags = ", ".join(it.get("tags", []))
        promoted = " ✅ タスク昇格済み" if it.get("promoted_to_task") else ""

        lines.extend([
            f"### {i}. {title}",
            "",
            f"- **ソース**: {source} | **著者**: {authors or 'N/A'}",
            f"- **公開日**: {pub_date} | **関連度**: {rel:.2f} | **新鮮度**: {fresh:.2f} | **信頼度**: {conf:.2f}",
            f"- **タグ**: {tags or 'なし'}{promoted}",
            f"- **URL**: {url}",
            "",
            f"> {abstract}...",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def _format_json_summary(items: List[Dict], top_n: int = 10) -> Dict:
    """JSON 要約形式"""
    top = items[:top_n]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": 2,
        "total_items": len(items),
        "promoted_to_task": sum(1 for it in items if it.get("promoted_to_task")),
        "top_items": [
            {
                "item_id": it.get("item_id"),
                "title": it.get("title", "")[:100],
                "source": it.get("source"),
                "relevance": it.get("relevance"),
                "freshness": it.get("freshness"),
                "url": it.get("url"),
                "promoted_to_task": it.get("promoted_to_task", False),
            }
            for it in top
        ],
        "source_breakdown": {
            "arxiv": sum(1 for it in items if it.get("source") == "arxiv"),
            "semantic_scholar": sum(1 for it in items if it.get("source") == "semantic_scholar"),
        },
        "avg_relevance": round(
            sum(it.get("relevance", 0) for it in items) / len(items), 3
        ) if items else 0,
    }


# ── Telegram 送信 ──────────────────────────────────────────────────────

def _send_telegram(message: str, env: Dict[str, str]) -> bool:
    """Telegram にメッセージを送信する"""
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("[DIGEST] Telegram設定なし。スキップ", file=sys.stderr)
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
        print("[DIGEST] Telegram送信成功", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[DIGEST] Telegram送信エラー: {e}", file=sys.stderr)
        return False


# ── メイン ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Research Radar 日次ダイジェスト")
    parser.add_argument("--top", type=int, default=5,
                        help="表示する上位件数（デフォルト: 5）")
    parser.add_argument("--days", type=int, default=2,
                        help="直近何日のアイテムを対象にするか（デフォルト: 2）")
    parser.add_argument("--telegram", action="store_true",
                        help="Telegram にダイジェストを送信する")
    parser.add_argument("--markdown", action="store_true",
                        help="Markdown レポートを保存する")
    parser.add_argument("--json", action="store_true",
                        help="JSON 要約を保存する")
    parser.add_argument("--output", type=str, default=None,
                        help="出力ディレクトリ（デフォルト: data/research/）")
    args = parser.parse_args()

    output_dir = args.output or _RESEARCH_DIR
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[DIGEST] ダイジェスト生成開始 — {today}")

    # レーダー読み込み
    radar = _load_radar()
    all_items = radar.get("items", [])

    # 直近 N 日のアイテムを抽出
    recent = _filter_recent(all_items, days=args.days)
    print(f"[DIGEST] 直近{args.days}日: {len(recent)}件 / 全体: {len(all_items)}件")

    if not recent:
        print(f"[DIGEST] 直近{args.days}日の新規アイテムなし")
        if args.telegram:
            env = _load_env()
            _send_telegram(
                f"📡 Research Radar — {today}\n直近{args.days}日の新規論文なし",
                env
            )
        return

    # スコアでソート
    sorted_items = _sort_by_score(recent)

    # --- Telegramダイジェスト ---
    if args.telegram:
        env = _load_env()
        telegram_text = _format_telegram(sorted_items, top_n=args.top)
        _send_telegram(telegram_text, env)

    # --- Markdownレポート ---
    if args.markdown:
        md_path = os.path.join(output_dir, f"digest-{today}.md")
        md_content = _format_markdown(sorted_items, top_n=args.top)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"[DIGEST] Markdownレポート保存: {md_path}")

    # --- JSON要約 ---
    if args.json:
        json_path = os.path.join(output_dir, f"digest-{today}.json")
        json_data = _format_json_summary(sorted_items, top_n=args.top)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"[DIGEST] JSON要約保存: {json_path}")

    # デフォルト: 標準出力にTelegramフォーマットで表示
    if not args.telegram and not args.markdown and not args.json:
        print(_format_telegram(sorted_items, top_n=args.top))

    # 統計出力
    print(f"\n=== ダイジェスト統計 ===")
    print(f"  対象アイテム: {len(sorted_items)}件")
    print(f"  TOP {args.top} 表示")
    if sorted_items:
        top_item = sorted_items[0]
        print(f"  最高関連度: [{top_item.get('relevance', 0):.2f}] {top_item.get('title', '')[:60]}")
    promoted = sum(1 for it in sorted_items if it.get("promoted_to_task"))
    print(f"  タスク昇格済み: {promoted}件")

    _record_timeline_run(
        source="combined",
        items_ingested=0,  # digest はレーダーを読むだけで新規取り込みなし
        items_total=len(all_items),
        topics=[],
        promoted_count=promoted,
        top_items=[it.get("title", "") for it in sorted_items[:3]],
        radar_size=len(all_items),
        run_status="ok",
        notes="digest run",
    )


if __name__ == "__main__":
    main()
