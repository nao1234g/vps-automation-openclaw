"""
scripts/research/daily_paper_ingest.py
Research Radar — 日次論文・最新知識取得スクリプト

Persistent Intelligence OS の「知識の継続流入」コンポーネント。

データソース:
  - arXiv API（無料、認証不要）
  - Semantic Scholar API（無料、認証不要）

出力:
  - data/research/YYYY-MM-DD.json  — 日次生データ
  - data/research/radar.json       — 累積レーダー（90日）

各アイテムの構造:
  {
    "item_id": "arXiv:2401.12345 or ss:abcdef",
    "title": "...",
    "abstract": "...(200文字)",
    "authors": ["A", "B"],
    "source": "arxiv | semantic_scholar",
    "url": "https://...",
    "published_at": "2026-03-14",
    "ingested_at": "2026-03-14T10:00:00Z",
    "freshness": 1.0,           # 0〜1: 今日=1.0, 30日前=0.0
    "confidence": 0.9,          # 査読あり=1.0, プレプリント=0.7
    "relevance": 0.8,           # キーワードマッチスコア 0〜1
    "promoted_to_task": false,  # task_ledger.json に昇格済みか
    "tags": ["prediction", "calibration", "AI"]
  }

使い方:
  python scripts/research/daily_paper_ingest.py --topics prediction calibration
  python scripts/research/daily_paper_ingest.py --dry-run
  python scripts/research/daily_paper_ingest.py --promote-top 3

Geneenの原則: 「数字は言語。メトリクスなきシステムは盲目のパイロット」
"""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.parse
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 設定 ──────────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR",
    os.path.abspath(os.path.join(_HERE, "..", ".."))
)
_RESEARCH_DIR = os.path.join(_PROJECT_ROOT, "data", "research")
_RADAR_PATH = os.path.join(_RESEARCH_DIR, "radar.json")
_LEDGER_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "task_ledger.json")
_ACTIVE_ID_PATH = os.path.join(_PROJECT_ROOT, ".claude", "hooks", "state", "active_task_id.txt")

# ── タイムラインレコーダー ─────────────────────────────────────────────
try:
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from knowledge_timeline_recorder import record_run as _record_timeline_run
except Exception:
    def _record_timeline_run(*a, **kw): pass  # サイレントフォールバック

MAX_RADAR_DAYS = 90
DEFAULT_TOPICS = [
    "prediction calibration",
    "forecasting AI",
    "superforecasting machine learning",
    "Brier score prediction",
    "large language model agent",
    "AI knowledge base",
    "retrieval augmented generation",
]

RELEVANCE_KEYWORDS = [
    "prediction", "forecast", "calibration", "brier", "superforecaster",
    "knowledge graph", "retrieval", "agent", "reasoning", "ai", "llm",
    "nowpattern", "oracle", "pattern", "geopolitics", "economic",
]


# ── arXiv API ────────────────────────────────────────────────────────

def fetch_arxiv(query: str, max_results: int = 10) -> List[Dict]:
    """arXiv API から論文を取得する"""
    encoded = urllib.parse.quote(query)
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query=all:{encoded}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    items = []
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            content = resp.read().decode("utf-8")

        # 簡易XMLパース（ET不要でlightweight）
        import re
        entries = re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL)

        for entry in entries:
            title_m = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
            abs_m = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
            id_m = re.search(r"<id>(.*?)</id>", entry)
            pub_m = re.search(r"<published>(.*?)</published>", entry)
            authors = re.findall(r"<name>(.*?)</name>", entry)

            if not (title_m and id_m):
                continue

            title = title_m.group(1).strip().replace("\n", " ")
            abstract = abs_m.group(1).strip().replace("\n", " ")[:300] if abs_m else ""
            arxiv_id = id_m.group(1).strip()
            published = pub_m.group(1).strip()[:10] if pub_m else ""

            items.append({
                "item_id": f"arxiv:{arxiv_id.split('/')[-1]}",
                "title": title,
                "abstract": abstract,
                "authors": authors[:3],
                "source": "arxiv",
                "url": arxiv_id,
                "published_at": published,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "freshness": _calc_freshness(published),
                "confidence": 0.75,  # プレプリント
                "relevance": _calc_relevance(title + " " + abstract),
                "promoted_to_task": False,
                "tags": _extract_tags(title + " " + abstract),
            })
            time.sleep(0.1)  # arXivへの礼儀

    except Exception as e:
        print(f"[RADAR] arXiv取得エラー: {e}", file=sys.stderr)

    return items


# ── Semantic Scholar API ─────────────────────────────────────────────

def fetch_semantic_scholar(query: str, max_results: int = 10) -> List[Dict]:
    """Semantic Scholar API から論文を取得する（無認証）"""
    encoded = urllib.parse.quote(query)
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={encoded}&limit={max_results}&fields=title,abstract,authors,year,externalIds,url,openAccessPdf"
    )
    items = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NowpatternResearchRadar/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)

        for paper in data.get("data", []):
            paper_id = paper.get("paperId", "")
            title = paper.get("title", "")
            abstract = (paper.get("abstract") or "")[:300]
            authors = [a.get("name", "") for a in paper.get("authors", [])[:3]]
            year = str(paper.get("year") or "")
            pub_date = f"{year}-01-01" if year else ""
            pdf_url = ""
            if paper.get("openAccessPdf"):
                pdf_url = paper["openAccessPdf"].get("url", "")
            page_url = paper.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"

            if not title:
                continue

            items.append({
                "item_id": f"ss:{paper_id[:16]}",
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "source": "semantic_scholar",
                "url": pdf_url or page_url,
                "published_at": pub_date,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "freshness": _calc_freshness(pub_date),
                "confidence": 0.85,  # インデックス済み = やや高め
                "relevance": _calc_relevance(title + " " + abstract),
                "promoted_to_task": False,
                "tags": _extract_tags(title + " " + abstract),
            })

    except Exception as e:
        print(f"[RADAR] Semantic Scholar取得エラー: {e}", file=sys.stderr)

    return items


# ── スコアリング ──────────────────────────────────────────────────────

def _calc_freshness(published_at: str) -> float:
    """今日からの日数に基づく freshness スコア（0〜1）"""
    if not published_at:
        return 0.3
    try:
        pub_date = datetime.fromisoformat(published_at[:10])
        days_old = (datetime.now() - pub_date).days
        return max(0.0, 1.0 - days_old / 30.0)
    except Exception:
        return 0.3


def _calc_relevance(text: str) -> float:
    """キーワードマッチに基づく relevance スコア（0〜1）"""
    text_lower = text.lower()
    matches = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text_lower)
    return min(1.0, matches / 5.0)


def _extract_tags(text: str) -> List[str]:
    """テキストから関連タグを抽出する"""
    text_lower = text.lower()
    return [kw for kw in RELEVANCE_KEYWORDS if kw in text_lower][:5]


# ── 重複排除 ──────────────────────────────────────────────────────────

def deduplicate(items: List[Dict], existing: List[Dict]) -> List[Dict]:
    """既存の item_id と重複するものを除去する"""
    existing_ids = {e["item_id"] for e in existing}
    return [it for it in items if it["item_id"] not in existing_ids]


# ── レーダー管理 ──────────────────────────────────────────────────────

def load_radar() -> Dict:
    if not os.path.exists(_RADAR_PATH):
        return {"_schema_version": "1.0", "items": [], "last_updated": ""}
    try:
        return json.load(open(_RADAR_PATH, encoding="utf-8"))
    except Exception:
        return {"_schema_version": "1.0", "items": [], "last_updated": ""}


def save_radar(radar: Dict):
    os.makedirs(_RESEARCH_DIR, exist_ok=True)
    radar["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(_RADAR_PATH, "w", encoding="utf-8") as f:
        json.dump(radar, f, ensure_ascii=False, indent=2)


def rotate_radar(radar: Dict) -> Dict:
    """90日より古いアイテムを除去する"""
    cutoff = (datetime.now() - timedelta(days=MAX_RADAR_DAYS)).isoformat()
    radar["items"] = [
        it for it in radar["items"]
        if it.get("ingested_at", "") >= cutoff
    ]
    return radar


def save_daily_snapshot(items: List[Dict]):
    """今日分のスナップショットを保存する"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(_RESEARCH_DIR, f"{today}.json")
    os.makedirs(_RESEARCH_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "items": items}, f, ensure_ascii=False, indent=2)


# ── タスク昇格 ───────────────────────────────────────────────────────

def _next_task_id(tasks: List[Dict]) -> str:
    """タスク台帳の次のIDを生成する"""
    max_num = 0
    for t in tasks:
        tid = t.get("id", "T000")
        try:
            max_num = max(max_num, int(tid[1:]))
        except ValueError:
            pass
    return f"T{max_num + 1:03d}"


def promote_to_task(item: Dict) -> bool:
    """関連度の高いアイテムをタスク台帳に昇格させる"""
    if not os.path.exists(_LEDGER_PATH):
        return False
    try:
        ledger = json.load(open(_LEDGER_PATH, encoding="utf-8"))
        tasks = ledger.get("tasks", [])

        new_id = _next_task_id(tasks)
        now = datetime.now(timezone.utc).isoformat()

        new_task = {
            "id": new_id,
            "title": f"[Research] {item['title'][:60]}",
            "rationale": f"Research Radar が高関連度論文を検出: relevance={item['relevance']:.2f}",
            "target_files": [],
            "acceptance_criteria": [
                f"論文を読み、Nowpatternへの応用可能性を評価する",
                f"応用できる場合: 実装タスクを台帳に追加する",
                f"応用できない場合: archived にする",
            ],
            "status": "open",
            "created_at": now,
            "updated_at": now,
            "owner": "local-claude",
            "related_failures": [],
            "verification_links": [item.get("url", "")],
            "research_source": item.get("source", ""),
            "research_item_id": item.get("item_id", ""),
        }

        tasks.append(new_task)
        ledger["tasks"] = tasks
        with open(_LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)

        print(f"[RADAR] タスク昇格: {new_id} — {item['title'][:50]}")
        return True

    except Exception as e:
        print(f"[RADAR] タスク昇格エラー: {e}", file=sys.stderr)
        return False


# ── メイン ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Research Radar — 日次論文取得")
    parser.add_argument("--topics", nargs="+", default=DEFAULT_TOPICS[:3],
                        help="検索トピック（スペース区切り）")
    parser.add_argument("--max-per-source", type=int, default=5,
                        help="ソースあたり最大取得件数")
    parser.add_argument("--dry-run", action="store_true",
                        help="レーダーを更新せずに取得結果のみ表示")
    parser.add_argument("--promote-top", type=int, default=0,
                        help="関連度上位N件をタスクに昇格する")
    parser.add_argument("--min-relevance", type=float, default=0.4,
                        help="タスク昇格の最低 relevance スコア")
    args = parser.parse_args()

    print(f"[RADAR] 日次取得開始 — {len(args.topics)}トピック")

    # 既存レーダーを読む
    radar = load_radar()
    existing_items = radar.get("items", [])

    # 取得
    new_items: List[Dict] = []
    for topic in args.topics:
        print(f"[RADAR] arXiv: '{topic}'")
        new_items.extend(fetch_arxiv(topic, args.max_per_source))
        time.sleep(1)

        print(f"[RADAR] Semantic Scholar: '{topic}'")
        new_items.extend(fetch_semantic_scholar(topic, args.max_per_source))
        time.sleep(1)

    # 重複排除
    deduped = deduplicate(new_items, existing_items)
    print(f"[RADAR] 取得: {len(new_items)}件 / 新規: {len(deduped)}件")

    if not deduped:
        print("[RADAR] 新規アイテムなし。終了")
        return

    # 関連度でソート
    deduped.sort(key=lambda x: x["relevance"], reverse=True)

    # 結果表示
    print("\n=== TOP 5 ===")
    for item in deduped[:5]:
        print(f"  [{item['relevance']:.2f}] {item['title'][:70]}")
        print(f"    source={item['source']} freshness={item['freshness']:.2f}")

    if args.dry_run:
        print("[RADAR] --dry-run のため保存をスキップ")
        return

    # 保存
    save_daily_snapshot(deduped)
    radar["items"] = existing_items + deduped
    radar = rotate_radar(radar)
    save_radar(radar)
    print(f"[RADAR] レーダー更新: 累計 {len(radar['items'])}件")

    # タスク昇格
    promoted = 0  # _record_timeline_run で参照するため if ブロックの外で初期化
    if args.promote_top > 0:
        candidates = [it for it in deduped if it["relevance"] >= args.min_relevance]
        for item in candidates[:args.promote_top]:
            if promote_to_task(item):
                item["promoted_to_task"] = True
                promoted += 1
        save_radar(radar)  # promoted_to_task フラグを反映
        print(f"[RADAR] タスク昇格: {promoted}件")

    print(f"[RADAR] 完了 — radar.json: {len(radar['items'])}件")

    _record_timeline_run(
        source="combined",
        items_ingested=len(deduped),
        items_total=len(existing_items) + len(deduped),
        topics=list(args.topics),
        promoted_count=promoted,
        top_items=[it["title"] for it in deduped[:3]],
        radar_size=len(radar["items"]),
        run_status="ok",
    )


if __name__ == "__main__":
    main()
