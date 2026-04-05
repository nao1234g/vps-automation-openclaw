#!/usr/bin/env python3
"""
Benchmark: prediction_similarity_search.py の検索精度テスト
==========================================================
B'' 改善の検証: 10組の同義語ペアでTF-IDF単体/embedding単体/ハイブリッドRRFの
Recall@5を計測する。

使い方:
  python scripts/test_similarity_search_benchmark.py
  python scripts/test_similarity_search_benchmark.py --verbose

前提: prediction_db.json がローカルまたはVPSに存在すること。
      Gemini embedding テストには GEMINI_API_KEY が必要。
"""

import sys
import os
from pathlib import Path

# prediction_similarity_search.py をインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from prediction_similarity_search import (
    TFIDFEngine, EmbeddingEngine, load_predictions, _init_genai
)

# ── 同義語ベンチマークペア（10組）─────────────────────────────────
# (クエリA, クエリB, 説明)
# 正しく動くなら、AとBはほぼ同じ結果セットを返すべき
SYNONYM_PAIRS = [
    ("Fed利下げ", "米国金融緩和", "金融政策の同義語"),
    ("Trump tariff", "米国関税政策", "日英混合の同義語"),
    ("台湾有事", "中台軍事衝突", "地政学用語の同義語"),
    ("半導体不足", "チップサプライチェーン危機", "産業用語の同義語"),
    ("ビットコイン暴落", "BTC価格下落", "暗号資産の略語"),
    ("AI規制", "人工知能ガバナンス", "テクノロジー政策の同義語"),
    ("原油価格高騰", "エネルギーコスト上昇", "エネルギー市場の同義語"),
    ("選挙結果", "投票日の勝敗", "選挙用語の同義語"),
    ("GDP成長率", "経済成長見通し", "マクロ経済の同義語"),
    ("サイバー攻撃", "ハッキング被害", "セキュリティ用語の同義語"),
]


def overlap_ids(results_a: list, results_b: list) -> set:
    """2つの結果セットのID重複を計算"""
    ids_a = {pred.get("id") for pred, _ in results_a}
    ids_b = {pred.get("id") for pred, _ in results_b}
    return ids_a & ids_b


def recall_at_k(results_a: list, results_b: list, k: int = 5) -> float:
    """Recall@K: AのTop-K結果がBのTop-K結果とどれだけ重なるか"""
    ids_a = {pred.get("id") for pred, _ in results_a[:k]}
    ids_b = {pred.get("id") for pred, _ in results_b[:k]}
    if not ids_a or not ids_b:
        return 0.0
    return len(ids_a & ids_b) / max(len(ids_a), len(ids_b))


def run_benchmark(verbose: bool = False):
    """ベンチマーク実行"""
    try:
        predictions = load_predictions()
    except SystemExit:
        print("SKIP: prediction_db.json not found (run on VPS for full benchmark)")
        return

    print(f"Loaded {len(predictions)} predictions\n")

    # TF-IDF エンジン
    tfidf = TFIDFEngine(predictions)

    # Embedding エンジン（利用可能な場合のみ）
    gemini_ok = _init_genai()
    embed = None
    if gemini_ok:
        try:
            embed = EmbeddingEngine(predictions)
        except Exception as e:
            print(f"WARNING: Embedding engine init failed: {e}")

    print("=" * 70)
    print(f"{'Pair':<40} {'TF-IDF':>8} {'Embed':>8} {'Hybrid':>8}")
    print("=" * 70)

    tfidf_scores = []
    embed_scores = []
    hybrid_scores = []

    for query_a, query_b, desc in SYNONYM_PAIRS:
        # TF-IDF
        res_a = tfidf.search(query_a, top_n=5, min_score=0.001)
        res_b = tfidf.search(query_b, top_n=5, min_score=0.001)
        tfidf_recall = recall_at_k(res_a, res_b, 5)
        tfidf_scores.append(tfidf_recall)

        # Embedding
        embed_recall = -1.0
        if embed:
            try:
                eres_a = embed.search(query_a, top_n=5, min_score=0.1)
                eres_b = embed.search(query_b, top_n=5, min_score=0.1)
                embed_recall = recall_at_k(eres_a, eres_b, 5)
                embed_scores.append(embed_recall)
            except Exception:
                embed_recall = -1.0

        # Hybrid RRF (simulate)
        hybrid_recall = -1.0
        if embed:
            try:
                hybrid_recall = _hybrid_rrf_recall(
                    tfidf, embed, query_a, query_b
                )
                hybrid_scores.append(hybrid_recall)
            except Exception:
                hybrid_recall = -1.0

        tfidf_str = f"{tfidf_recall:.2f}"
        embed_str = f"{embed_recall:.2f}" if embed_recall >= 0 else "N/A"
        hybrid_str = f"{hybrid_recall:.2f}" if hybrid_recall >= 0 else "N/A"

        print(f"{desc:<40} {tfidf_str:>8} {embed_str:>8} {hybrid_str:>8}")

        if verbose and res_a:
            print(f"  A({query_a}): {[p.get('id','?')[:20] for p,_ in res_a[:3]]}")
            print(f"  B({query_b}): {[p.get('id','?')[:20] for p,_ in res_b[:3]]}")

    print("=" * 70)

    avg_tfidf = sum(tfidf_scores) / len(tfidf_scores) if tfidf_scores else 0
    print(f"{'AVG TF-IDF Recall@5:':<40} {avg_tfidf:>8.3f}")

    if embed_scores:
        avg_embed = sum(embed_scores) / len(embed_scores)
        print(f"{'AVG Embedding Recall@5:':<40} {avg_embed:>8.3f}")

    if hybrid_scores:
        avg_hybrid = sum(hybrid_scores) / len(hybrid_scores)
        print(f"{'AVG Hybrid RRF Recall@5:':<40} {avg_hybrid:>8.3f}")

    # PASS/FAIL判定
    print()
    if embed_scores and hybrid_scores:
        avg_embed = sum(embed_scores) / len(embed_scores)
        avg_hybrid = sum(hybrid_scores) / len(hybrid_scores)
        if avg_hybrid > avg_tfidf:
            print("PASS: Hybrid RRF > TF-IDF (synonym handling improved)")
        else:
            print("WARN: Hybrid RRF <= TF-IDF (may need weight tuning)")
    else:
        print("INFO: Embedding not available. TF-IDF only benchmark complete.")
        print("      Set GEMINI_API_KEY for full benchmark.")


def _hybrid_rrf_recall(
    tfidf_eng: TFIDFEngine,
    embed_eng: EmbeddingEngine,
    query_a: str,
    query_b: str,
    k: int = 5,
) -> float:
    """Hybrid RRF でRecall@Kを計算"""
    RRF_K = 60

    def rrf_search(query: str) -> list:
        tfidf_res = tfidf_eng.search(query, top_n=k * 5, min_score=0.001)
        embed_res = embed_eng.search(query, top_n=k * 5, min_score=0.1)
        combined = {}
        for rank, (pred, _) in enumerate(tfidf_res):
            pid = pred.get("id", id(pred))
            combined[pid] = (pred, 1.0 / (RRF_K + rank + 1))
        for rank, (pred, _) in enumerate(embed_res):
            pid = pred.get("id", id(pred))
            rrf = 1.0 / (RRF_K + rank + 1)
            if pid in combined:
                combined[pid] = (combined[pid][0], combined[pid][1] + rrf)
            else:
                combined[pid] = (pred, rrf)
        return sorted(combined.values(), key=lambda x: x[1], reverse=True)[:k]

    res_a = rrf_search(query_a)
    res_b = rrf_search(query_b)
    return recall_at_k(res_a, res_b, k)


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    run_benchmark(verbose=verbose)
