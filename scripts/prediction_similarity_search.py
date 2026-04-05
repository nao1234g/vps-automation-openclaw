#!/usr/bin/env python3
"""
prediction_similarity_search.py — AI Notion 検索エンジン (TF-IDF + Gemini Embedding)

NowPatternを「AIのNotion（判断の第二の脳）」として機能させるための検索エンジン。
prediction_db.json から類似予測を検索し、過去の精度・教訓を返す。

使い方:
  python scripts/prediction_similarity_search.py "台湾 半導体"
  python scripts/prediction_similarity_search.py "Trump tariff" --top 10
  python scripts/prediction_similarity_search.py "Fed利下げ" --category economics --resolved-only
  python scripts/prediction_similarity_search.py "米国金融緩和" --embed   # Gemini embedding使用
  python scripts/prediction_similarity_search.py --stats
  python scripts/prediction_similarity_search.py --build-index            # TF-IDFインデックス構築

NORTH_STAR.md §12 「AIのNotion = 判断を支える基盤サービス」の実装:
  1. 過去に似た予測はあったか？ → このスクリプトが検索
  2. そのとき当たったか外したか？ → result + brier を返す
  3. なぜ外したか？ → 関連する AGENT_WISDOM エントリを表示

v2 改善点（2026-04-05）:
  - Jaccard + character n-gram → TF-IDF + cosine similarity（語の重要度を考慮）
  - オプションで Gemini embedding-001 によるセマンティック検索（--embed）
  - 「Fed利下げ」↔「米国金融緩和」のような同義語的クエリでもヒット可能に
"""

import json
import math
import os
import re
import sys
import argparse
from collections import Counter
from pathlib import Path
from typing import Optional

# prediction_db.json のパス（ローカル / VPS 両対応）
DB_PATHS = [
    Path(__file__).parent.parent / "data" / "prediction_db.json",
    Path("/opt/shared/prediction_db.json"),
]

# TF-IDFインデックスのキャッシュパス
INDEX_PATH = Path(__file__).parent.parent / "data" / "prediction_tfidf_index.json"

# Gemini embeddingキャッシュパス
EMBED_CACHE_PATH = Path(__file__).parent.parent / "data" / "prediction_embeddings.json"


# ── Gemini Embedding（オプション）──────────────────────────────────
HAS_GENAI = False
_genai_client = None

try:
    from google import genai as _genai_module
    HAS_GENAI = True
except ImportError:
    try:
        import google.generativeai as _genai_module
        HAS_GENAI = True
    except ImportError:
        pass


def _init_genai():
    """Gemini APIクライアントを初期化"""
    global _genai_client
    if _genai_client is not None:
        return True
    if not HAS_GENAI:
        return False
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return False
    try:
        # 新SDK (google-genai)
        if hasattr(_genai_module, "Client"):
            _genai_client = _genai_module.Client(api_key=api_key)
        else:
            # 旧SDK (google-generativeai)
            _genai_module.configure(api_key=api_key)
            _genai_client = _genai_module
        return True
    except Exception:
        return False


def get_embedding(text: str) -> list[float]:
    """Gemini embedding-001 でテキストのembeddingを取得"""
    if not _init_genai():
        raise RuntimeError("Gemini API not available. Set GEMINI_API_KEY.")
    try:
        if hasattr(_genai_client, "models"):
            # 新SDK
            result = _genai_client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text[:2048],  # embedding-001の入力制限
            )
            return result.embeddings[0].values
        else:
            # 旧SDK
            result = _genai_client.embed_content(
                model="models/embedding-001",
                content=text[:2048],
            )
            return result["embedding"]
    except Exception as e:
        raise RuntimeError(f"Embedding API error: {e}")


# ── データ読み込み ────────────────────────────────────────────────
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


# ── トークナイザー ───────────────────────────────────────────────
def tokenize(text: str) -> list[str]:
    """テキストをトークンに分割（日本語+英語対応）。リスト返し（TF-IDF用に出現回数を保持）"""
    text = text.lower()
    tokens = []

    # 英語: 単語分割（2文字以上）
    en_tokens = re.findall(r'[a-z]{2,}', text)
    tokens.extend(en_tokens)

    # 日本語: character n-gram (2, 3, 4-gram)
    # 句読点・記号を除去してからn-gram
    ja_chars = re.sub(r'[a-z0-9\s\.,;:!?\-\(\)\[\]{}「」（）【】、。・]', '', text)
    for n in (2, 3, 4):
        for i in range(len(ja_chars) - n + 1):
            tokens.append(ja_chars[i:i + n])

    return tokens


def get_pred_text(pred: dict) -> str:
    """予測から検索対象テキストを構築"""
    text_parts = [
        pred.get("title", ""),
        pred.get("question", ""),
        pred.get("our_pick", ""),
        pred.get("summary", ""),
    ]
    tags = pred.get("tags", [])
    if isinstance(tags, list):
        text_parts.extend(tags)
    return " ".join(str(p) for p in text_parts if p)


# ── TF-IDF エンジン ──────────────────────────────────────────────
class TFIDFEngine:
    """TF-IDF + cosine similarity による検索エンジン"""

    def __init__(self, predictions: list[dict]):
        self.predictions = predictions
        self.doc_tokens: list[list[str]] = []
        self.doc_tfs: list[dict[str, float]] = []
        self.idf: dict[str, float] = {}
        self._build_index()

    def _build_index(self):
        """全予測のTF-IDFインデックスを構築"""
        n_docs = len(self.predictions)

        # ドキュメント頻度（DF）カウント用
        df_counter: Counter = Counter()

        for pred in self.predictions:
            text = get_pred_text(pred)
            tokens = tokenize(text)
            self.doc_tokens.append(tokens)

            # TF（Term Frequency）計算: log(1 + count) で正規化
            token_counts = Counter(tokens)
            total = len(tokens) if tokens else 1
            tf = {}
            unique_tokens = set()
            for token, count in token_counts.items():
                tf[token] = math.log(1 + count / total)
                unique_tokens.add(token)
            self.doc_tfs.append(tf)

            # DF更新
            for token in unique_tokens:
                df_counter[token] += 1

        # IDF（Inverse Document Frequency）計算: log(N / (1 + df))
        for token, df in df_counter.items():
            self.idf[token] = math.log(n_docs / (1 + df))

    def search(
        self,
        query: str,
        top_n: int = 5,
        category: Optional[str] = None,
        resolved_only: bool = False,
        min_score: float = 0.01,
    ) -> list[tuple[dict, float]]:
        """TF-IDF cosine similarity で検索"""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # クエリのTF-IDF ベクトル
        query_counts = Counter(query_tokens)
        query_total = len(query_tokens)
        query_tfidf = {}
        for token, count in query_counts.items():
            tf = math.log(1 + count / query_total)
            idf = self.idf.get(token, math.log(len(self.predictions)))  # 未知語は最大IDF
            query_tfidf[token] = tf * idf

        # クエリベクトルのノルム
        query_norm = math.sqrt(sum(v * v for v in query_tfidf.values()))
        if query_norm == 0:
            return []

        results = []
        for i, pred in enumerate(self.predictions):
            # フィルタリング
            if resolved_only and pred.get("status") != "resolved":
                continue
            if category:
                tags = pred.get("tags", [])
                tag_str = " ".join(tags) if isinstance(tags, list) else str(tags)
                if category.lower() not in tag_str.lower():
                    continue

            # ドキュメントのTF-IDFベクトル
            doc_tf = self.doc_tfs[i]
            doc_tfidf = {}
            for token, tf_val in doc_tf.items():
                idf = self.idf.get(token, 0)
                doc_tfidf[token] = tf_val * idf

            # cosine similarity
            dot_product = 0.0
            for token, q_val in query_tfidf.items():
                if token in doc_tfidf:
                    dot_product += q_val * doc_tfidf[token]

            doc_norm = math.sqrt(sum(v * v for v in doc_tfidf.values()))
            if doc_norm == 0:
                continue

            score = dot_product / (query_norm * doc_norm)
            if score >= min_score:
                results.append((pred, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]


# ── Embedding エンジン ───────────────────────────────────────────
class EmbeddingEngine:
    """Gemini Embedding によるセマンティック検索エンジン"""

    def __init__(self, predictions: list[dict]):
        self.predictions = predictions
        self.embeddings: list[list[float]] = []
        self._load_or_build()

    def _load_or_build(self):
        """キャッシュがあれば読み込み、なければ構築"""
        if EMBED_CACHE_PATH.exists():
            try:
                with open(EMBED_CACHE_PATH, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                # IDでマッチング
                cache_map = {e["id"]: e["embedding"] for e in cache.get("embeddings", [])}
                missing = []
                for i, pred in enumerate(self.predictions):
                    pid = pred.get("id", f"idx_{i}")
                    if pid in cache_map:
                        self.embeddings.append(cache_map[pid])
                    else:
                        missing.append(i)
                        self.embeddings.append([])

                if missing:
                    print(f"  {len(missing)} predictions not in cache, computing...", file=sys.stderr)
                    self._compute_missing(missing)
                    self._save_cache()
                return
            except Exception:
                pass

        # キャッシュなし → 全件構築
        print(f"  Building embeddings for {len(self.predictions)} predictions...", file=sys.stderr)
        self._compute_all()
        self._save_cache()

    def _compute_all(self):
        """全予測のembeddingを計算"""
        self.embeddings = []
        for i, pred in enumerate(self.predictions):
            text = get_pred_text(pred)
            try:
                emb = get_embedding(text)
                self.embeddings.append(emb)
            except Exception as e:
                print(f"  WARNING: embedding failed for prediction {i}: {e}", file=sys.stderr)
                self.embeddings.append([])
            if (i + 1) % 50 == 0:
                print(f"  ...embedded {i + 1}/{len(self.predictions)}", file=sys.stderr)

    def _compute_missing(self, indices: list[int]):
        """キャッシュにない予測のembeddingを計算"""
        for i in indices:
            pred = self.predictions[i]
            text = get_pred_text(pred)
            try:
                emb = get_embedding(text)
                self.embeddings[i] = emb
            except Exception as e:
                print(f"  WARNING: embedding failed for prediction {i}: {e}", file=sys.stderr)

    def _save_cache(self):
        """embeddingキャッシュを保存"""
        cache = {"embeddings": []}
        for i, pred in enumerate(self.predictions):
            if self.embeddings[i]:
                cache["embeddings"].append({
                    "id": pred.get("id", f"idx_{i}"),
                    "embedding": self.embeddings[i],
                })
        EMBED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EMBED_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"  Saved {len(cache['embeddings'])} embeddings to cache", file=sys.stderr)

    def search(
        self,
        query: str,
        top_n: int = 5,
        category: Optional[str] = None,
        resolved_only: bool = False,
        min_score: float = 0.3,
    ) -> list[tuple[dict, float]]:
        """cosine similarity で検索"""
        query_emb = get_embedding(query)
        q_norm = math.sqrt(sum(x * x for x in query_emb))
        if q_norm == 0:
            return []

        results = []
        for i, pred in enumerate(self.predictions):
            if resolved_only and pred.get("status") != "resolved":
                continue
            if category:
                tags = pred.get("tags", [])
                tag_str = " ".join(tags) if isinstance(tags, list) else str(tags)
                if category.lower() not in tag_str.lower():
                    continue

            emb = self.embeddings[i]
            if not emb:
                continue

            # cosine similarity
            dot = sum(a * b for a, b in zip(query_emb, emb))
            d_norm = math.sqrt(sum(x * x for x in emb))
            if d_norm == 0:
                continue
            score = dot / (q_norm * d_norm)

            if score >= min_score:
                results.append((pred, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]


# ── フォーマット・ユーティリティ ─────────────────────────────────
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
        description="prediction_similarity_search.py — AI Notion 検索エンジン (TF-IDF + Gemini)"
    )
    parser.add_argument("query", nargs="?", help="検索クエリ（例: '台湾 半導体', 'Trump tariff', 'Fed利下げ'）")
    parser.add_argument("--top", type=int, default=5, help="表示件数（デフォルト: 5）")
    parser.add_argument("--category", type=str, help="カテゴリでフィルタ（例: economics, geopolitics）")
    parser.add_argument("--resolved-only", action="store_true", help="解決済み予測のみ表示")
    parser.add_argument("--min-score", type=float, default=None, help="最低類似度（TF-IDF: 0.01, Embed: 0.3）")
    parser.add_argument("--stats", action="store_true", help="prediction_db の統計を表示")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--embed", action="store_true", help="Gemini embedding-001 でセマンティック検索")
    parser.add_argument("--build-index", action="store_true", help="embeddingキャッシュを事前構築")

    args = parser.parse_args()
    predictions = load_predictions()

    if args.stats:
        print_stats(predictions)
        return

    if args.build_index:
        if not _init_genai():
            print("ERROR: GEMINI_API_KEY not set. Cannot build embedding index.", file=sys.stderr)
            sys.exit(1)
        print(f"Building embedding index for {len(predictions)} predictions...")
        engine = EmbeddingEngine(predictions)
        print(f"Done. Cache saved to {EMBED_CACHE_PATH}")
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    # 検索エンジン選択
    # B'' ハイブリッドデフォルト: GEMINI_API_KEY が存在すれば自動で
    # Reciprocal Rank Fusion (RRF) によるハイブリッドスコアリングを使用。
    # --embed フラグで embedding 100% に切り替え可能。
    gemini_available = _init_genai()
    use_hybrid = gemini_available and not args.embed  # --embed時は純embedding

    if args.embed:
        if not gemini_available:
            print("WARNING: Gemini API not available. Falling back to TF-IDF.", file=sys.stderr)
            engine = TFIDFEngine(predictions)
            min_score = args.min_score or 0.01
            mode = "TF-IDF"
        else:
            print("Using Gemini embedding search...", file=sys.stderr)
            engine = EmbeddingEngine(predictions)
            min_score = args.min_score or 0.3
            mode = "Gemini Embedding"
    elif use_hybrid:
        print("Using hybrid search (RRF: TF-IDF + Embedding)...", file=sys.stderr)
        tfidf_engine = TFIDFEngine(predictions)
        embed_engine = EmbeddingEngine(predictions)
        min_score = args.min_score or 0.01
        mode = "Hybrid RRF (TF-IDF + Embedding)"
    else:
        engine = TFIDFEngine(predictions)
        min_score = args.min_score or 0.01
        mode = "TF-IDF"

    # ハイブリッド検索: Reciprocal Rank Fusion (RRF)
    # B'' 改善: max-normalization → RRF。スコア分布に依存しない安定した結合。
    # RRF: score(d) = Σ 1/(k + rank_i(d))  (Cormack et al. 2009, k=60が標準)
    RRF_K = 60
    if use_hybrid:
        tfidf_results = tfidf_engine.search(
            query=args.query, top_n=args.top * 5,
            category=args.category, resolved_only=args.resolved_only,
            min_score=0.001,
        )
        embed_results = embed_engine.search(
            query=args.query, top_n=args.top * 5,
            category=args.category, resolved_only=args.resolved_only,
            min_score=0.1,
        )

        # RRF: 各リストのランクから逆数スコアを計算
        combined: dict[str, tuple[dict, float]] = {}
        for rank, (pred, _score) in enumerate(tfidf_results):
            pid = pred.get("id", id(pred))
            rrf_score = 1.0 / (RRF_K + rank + 1)
            combined[pid] = (pred, rrf_score)
        for rank, (pred, _score) in enumerate(embed_results):
            pid = pred.get("id", id(pred))
            rrf_score = 1.0 / (RRF_K + rank + 1)
            if pid in combined:
                combined[pid] = (combined[pid][0], combined[pid][1] + rrf_score)
            else:
                combined[pid] = (pred, rrf_score)

        results = sorted(combined.values(), key=lambda x: x[1], reverse=True)
        results = results[:args.top]
    else:
        results = engine.search(
            query=args.query,
            top_n=args.top,
            category=args.category,
            resolved_only=args.resolved_only,
            min_score=min_score,
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
        print(f"=== Similar predictions for: '{args.query}' [{mode}] ({len(results)} results) ===\n")
        for i, (pred, score) in enumerate(results, 1):
            print(f"[{i}]")
            print(format_prediction(pred, score))
            print()


if __name__ == "__main__":
    main()
