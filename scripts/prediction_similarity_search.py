#!/usr/bin/env python3
"""
prediction_similarity_search.py — AI Notion 最小実装

NowPatternを「AIのNotion（判断の第二の脳）」として機能させるための検索エンジン。
prediction_db.json から類似予測を検索し、過去の精度・教訓を返す。

使い方:
  python scripts/prediction_similarity_search.py "台湾 半導体"
  python scripts/prediction_similarity_search.py "Trump tariff" --top 10
  python scripts/prediction_similarity_search.py "Fed利下げ" --category economics --resolved-only
  python scripts/prediction_similarity_search.py --stats

NORTH_STAR.md §12 「AIのNotion = 判断を支える基盤サービス」の実装:
  1. 過去に似た予測はあったか？ → このスクリプトが検索
  2. そのとき当たったか外したか？ → result + brier を返す
  3. なぜ外したか？ → 関連する AGENT_WISDOM エントリを表示
"""

import json
import re
import sys
import argparse
from pathlib import Path
from typing import Optional

# prediction_db.json のパス（ローカル / VPS 両対応）
DB_PATHS = [
    Path(__file__).parent.parent / "data" / "prediction_db.json",
    Path("/opt/shared/prediction_db.json"),
]


def load_predictions() -> list[dict]:
    """prediction_db.json を読み込む"""
    for path in DB_PATHS:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "predictions" in data:
                return data["predictions"]
            if isinstance(data, list):
                return data
            break
    print("ERROR: prediction_db.json not found", file=sys.stderr)
    sys.exit(1)


def tokenize(text: str) -> set[str]:
    """テキストをトークンに分割（日本語+英語対応）"""
    text = text.lower()
    # 英語: 単語分割
    en_tokens = set(re.findall(r'[a-z]{2,}', text))
    # 日本語: 2-gram + 3-gram（形態素解析なしで動く簡易版）
    ja_chars = re.sub(r'[a-z0-9\s]', '', text)
    ja_tokens = set()
    for n in (2, 3):
        for i in range(len(ja_chars) - n + 1):
            ja_tokens.add(ja_chars[i:i+n])
    return en_tokens | ja_tokens


def calculate_similarity(query_tokens: set[str], pred: dict) -> float:
    """クエリと予測の類似度を計算（0-1）"""
    # 検索対象フィールド
    text_parts = [
        pred.get("title", ""),
        pred.get("question", ""),
        pred.get("our_pick", ""),
        pred.get("summary", ""),
    ]
    # タグも検索対象に含める
    tags = pred.get("tags", [])
    if isinstance(tags, list):
        text_parts.extend(tags)

    pred_text = " ".join(str(p) for p in text_parts if p)
    pred_tokens = tokenize(pred_text)

    if not query_tokens or not pred_tokens:
        return 0.0

    # Jaccard 類似度 + クエリカバレッジ重み
    intersection = query_tokens & pred_tokens
    if not intersection:
        return 0.0

    jaccard = len(intersection) / len(query_tokens | pred_tokens)
    query_coverage = len(intersection) / len(query_tokens)

    # クエリカバレッジを重視（検索語が全部含まれているほど高スコア）
    return 0.4 * jaccard + 0.6 * query_coverage


def format_prediction(pred: dict, score: float) -> str:
    """予測を人間が読める形式でフォーマット"""
    lines = []
    lines.append(f"  Score: {score:.3f}")
    lines.append(f"  ID: {pred.get('id', 'N/A')}")
    lines.append(f"  Title: {pred.get('title', 'N/A')}")
    lines.append(f"  Question: {pred.get('question', 'N/A')}")
    lines.append(f"  Our Pick: {pred.get('our_pick', 'N/A')} ({pred.get('our_pick_prob', '?')}%)")
    lines.append(f"  Status: {pred.get('status', 'N/A')}")

    result = pred.get("result")
    if result:
        lines.append(f"  Result: {result}")

    brier = pred.get("brier")
    if brier is not None:
        grade = brier_grade(brier)
        lines.append(f"  Brier: {brier} ({grade})")

    tags = pred.get("tags", [])
    if tags:
        lines.append(f"  Tags: {', '.join(tags) if isinstance(tags, list) else tags}")

    registered = pred.get("registered_at", "")
    if registered:
        lines.append(f"  Registered: {registered}")

    return "\n".join(lines)


def brier_grade(score: float) -> str:
    """Brier Score のグレードを返す"""
    if score < 0.05:
        return "EXCEPTIONAL"
    elif score < 0.10:
        return "EXCELLENT"
    elif score < 0.15:
        return "GOOD"
    elif score < 0.20:
        return "DECENT"
    elif score < 0.25:
        return "AVERAGE"
    else:
        return "POOR"


def search(
    query: str,
    predictions: list[dict],
    top_n: int = 5,
    category: Optional[str] = None,
    resolved_only: bool = False,
    min_score: float = 0.05,
) -> list[tuple[dict, float]]:
    """類似予測を検索"""
    query_tokens = tokenize(query)
    results = []

    for pred in predictions:
        # フィルタリング
        if resolved_only and pred.get("status") != "resolved":
            continue
        if category:
            tags = pred.get("tags", [])
            tag_str = " ".join(tags) if isinstance(tags, list) else str(tags)
            if category.lower() not in tag_str.lower():
                continue

        score = calculate_similarity(query_tokens, pred)
        if score >= min_score:
            results.append((pred, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


def print_stats(predictions: list[dict]) -> None:
    """prediction_db の統計を表示"""
    total = len(predictions)
    resolved = [p for p in predictions if p.get("status") == "resolved"]
    hits = [p for p in resolved if p.get("result") == "HIT"]
    misses = [p for p in resolved if p.get("result") == "MISS"]
    briers = [p.get("brier") for p in resolved if p.get("brier") is not None]

    print(f"=== Prediction DB Stats ===")
    print(f"Total predictions: {total}")
    print(f"Resolved: {len(resolved)}")
    print(f"  HIT: {len(hits)}")
    print(f"  MISS: {len(misses)}")
    if briers:
        avg_brier = sum(briers) / len(briers)
        print(f"  Avg Brier: {avg_brier:.4f} ({brier_grade(avg_brier)})")
        print(f"  Best Brier: {min(briers):.4f}")
        print(f"  Worst Brier: {max(briers):.4f}")

    # カテゴリ別集計
    tag_counts: dict[str, int] = {}
    for p in predictions:
        tags = p.get("tags", [])
        if isinstance(tags, list):
            for t in tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1
    if tag_counts:
        print(f"\nTop 10 Tags:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {tag}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description="prediction_similarity_search.py — AI Notion 最小実装"
    )
    parser.add_argument("query", nargs="?", help="検索クエリ（例: '台湾 半導体', 'Trump tariff'）")
    parser.add_argument("--top", type=int, default=5, help="表示件数（デフォルト: 5）")
    parser.add_argument("--category", type=str, help="カテゴリでフィルタ（例: economics, geopolitics）")
    parser.add_argument("--resolved-only", action="store_true", help="解決済み予測のみ表示")
    parser.add_argument("--min-score", type=float, default=0.05, help="最低類似度（デフォルト: 0.05）")
    parser.add_argument("--stats", action="store_true", help="prediction_db の統計を表示")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")

    args = parser.parse_args()
    predictions = load_predictions()

    if args.stats:
        print_stats(predictions)
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    results = search(
        query=args.query,
        predictions=predictions,
        top_n=args.top,
        category=args.category,
        resolved_only=args.resolved_only,
        min_score=args.min_score,
    )

    if not results:
        print(f"No similar predictions found for: '{args.query}'")
        sys.exit(0)

    if args.json:
        output = []
        for pred, score in results:
            entry = {
                "similarity_score": round(score, 4),
                "id": pred.get("id"),
                "title": pred.get("title"),
                "question": pred.get("question"),
                "our_pick": pred.get("our_pick"),
                "our_pick_prob": pred.get("our_pick_prob"),
                "status": pred.get("status"),
                "result": pred.get("result"),
                "brier": pred.get("brier"),
                "tags": pred.get("tags"),
            }
            output.append(entry)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"=== Similar predictions for: '{args.query}' ({len(results)} results) ===\n")
        for i, (pred, score) in enumerate(results, 1):
            print(f"[{i}]")
            print(format_prediction(pred, score))
            print()


if __name__ == "__main__":
    main()
