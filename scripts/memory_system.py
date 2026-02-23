#!/usr/bin/env python3
"""
LONG-TERM MEMORY SYSTEM — ChromaDB + Gemini Embedding + Markdown
=================================================================
全エージェント共有の長期記憶。セッションをまたいで知識を保持する。

構成:
- ChromaDB: ベクトル検索（類似度検索）
- Gemini Embedding: テキスト→ベクトル変換（無料枠: 100RPM, 1000RPD）
- Markdown: 人間が読める形式でもバックアップ保存

使い方:
  from memory_system import MemorySystem
  mem = MemorySystem("/opt/shared/memory")
  mem.store("ghost_api", "Ghost APIはverify=Falseが必要", {"agent": "local-claude"})
  results = mem.search("Ghost API認証")
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ChromaDB import（VPSにpip installが必要）
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# Gemini Embedding（google-genai preferred, google-generativeai fallback）
HAS_GENAI = False
genai = None
try:
    from google import genai as _genai
    genai = _genai
    HAS_GENAI = True
except ImportError:
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as _genai_legacy
            genai = _genai_legacy
            HAS_GENAI = True
    except ImportError:
        pass


class MemorySystem:
    """長期記憶の保存・検索・管理"""

    COLLECTION_NAME = "agent_memory"

    def __init__(self, base_dir: str = "/opt/shared/memory"):
        self.base_dir = Path(base_dir)
        self.chromadb_dir = self.base_dir / "chromadb"
        self.entries_dir = self.base_dir / "entries"
        self.index_file = self.base_dir / "INDEX.json"

        # ディレクトリ作成
        self.chromadb_dir.mkdir(parents=True, exist_ok=True)
        self.entries_dir.mkdir(parents=True, exist_ok=True)

        # ChromaDB初期化
        self.client = None
        self.collection = None
        if HAS_CHROMADB:
            try:
                self.client = chromadb.PersistentClient(
                    path=str(self.chromadb_dir)
                )
                self.collection = self.client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                print(f"[WARN] ChromaDB初期化失敗: {e}", file=sys.stderr)

        # Gemini Embedding初期化
        self.embedding_model = None
        self._use_new_genai = False
        if HAS_GENAI:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if api_key:
                # 新SDK（google-genai）か旧SDK（google-generativeai）かを判定
                if hasattr(genai, 'Client'):
                    self._genai_client = genai.Client(api_key=api_key)
                    self._use_new_genai = True
                else:
                    genai.configure(api_key=api_key)
                self.embedding_model = "models/gemini-embedding-001"

    def _generate_id(self, category: str, content: str) -> str:
        """コンテンツのハッシュからユニークIDを生成"""
        raw = f"{category}:{content}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _get_embedding(self, text: str) -> list:
        """Gemini Embeddingでテキストをベクトル化"""
        if not HAS_GENAI or not self.embedding_model:
            return None
        try:
            if self._use_new_genai:
                result = self._genai_client.models.embed_content(
                    model=self.embedding_model,
                    contents=text,
                )
                return result.embeddings[0].values
            else:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="RETRIEVAL_DOCUMENT"
                )
                return result["embedding"]
        except Exception as e:
            print(f"[WARN] Embedding failed: {e}", file=sys.stderr)
            return None

    def _get_query_embedding(self, text: str) -> list:
        """検索クエリ用のEmbedding"""
        if not HAS_GENAI or not self.embedding_model:
            return None
        try:
            if self._use_new_genai:
                result = self._genai_client.models.embed_content(
                    model=self.embedding_model,
                    contents=text,
                )
                return result.embeddings[0].values
            else:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="RETRIEVAL_QUERY"
                )
                return result["embedding"]
        except Exception as e:
            print(f"[WARN] Query embedding failed: {e}", file=sys.stderr)
            return None

    def store(self, category: str, content: str, metadata: dict = None) -> str:
        """
        記憶を保存する。

        Args:
            category: カテゴリ（例: "ghost_api", "docker", "pipeline_design"）
            content: 記憶の内容（自然言語テキスト）
            metadata: 追加情報（agent, source, importance等）

        Returns:
            memory_id: 保存された記憶のID
        """
        memory_id = self._generate_id(category, content)
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # メタデータ構築
        meta = {
            "category": category,
            "created_at": time_str,
            "agent": (metadata or {}).get("agent", "unknown"),
            "importance": (metadata or {}).get("importance", "normal"),
            "source": (metadata or {}).get("source", "session"),
        }

        # 1. ChromaDBに保存（ベクトル検索用）
        if self.collection is not None:
            embedding = self._get_embedding(content)
            try:
                if embedding:
                    self.collection.upsert(
                        ids=[memory_id],
                        documents=[content],
                        metadatas=[meta],
                        embeddings=[embedding]
                    )
                else:
                    # Embedding失敗時はChromaDBのデフォルトEmbeddingを使用
                    self.collection.upsert(
                        ids=[memory_id],
                        documents=[content],
                        metadatas=[meta]
                    )
            except Exception as e:
                print(f"[WARN] ChromaDB保存失敗: {e}", file=sys.stderr)

        # 2. Markdownファイルに保存（人間が読める形式）
        safe_category = re.sub(r'[^\w\-]', '_', category)
        md_filename = f"{date_str}_{safe_category}_{memory_id[:8]}.md"
        md_path = self.entries_dir / md_filename

        md_content = f"""# Memory: {category}
> ID: {memory_id}
> Created: {time_str}
> Agent: {meta['agent']}
> Importance: {meta['importance']}
> Source: {meta['source']}

## Content

{content}
"""
        try:
            md_path.write_text(md_content, encoding="utf-8")
        except Exception as e:
            print(f"[WARN] Markdown保存失敗: {e}", file=sys.stderr)

        # 3. インデックス更新
        self._update_index(memory_id, category, content[:100], meta)

        return memory_id

    def search(self, query: str, n_results: int = 5, category: str = None) -> list:
        """
        記憶を検索する。

        Args:
            query: 検索クエリ（自然言語）
            n_results: 返す結果数
            category: カテゴリでフィルタ（省略時は全カテゴリ）

        Returns:
            list of dict: [{id, content, category, created_at, distance}, ...]
        """
        results = []

        # ChromaDBベクトル検索
        if self.collection is not None and self.collection.count() > 0:
            try:
                where_filter = {"category": category} if category else None
                query_embedding = self._get_query_embedding(query)

                if query_embedding:
                    raw = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=min(n_results, self.collection.count()),
                        where=where_filter
                    )
                else:
                    raw = self.collection.query(
                        query_texts=[query],
                        n_results=min(n_results, self.collection.count()),
                        where=where_filter
                    )

                if raw and raw.get("ids") and raw["ids"][0]:
                    for i, doc_id in enumerate(raw["ids"][0]):
                        results.append({
                            "id": doc_id,
                            "content": raw["documents"][0][i],
                            "category": raw["metadatas"][0][i].get("category", ""),
                            "created_at": raw["metadatas"][0][i].get("created_at", ""),
                            "agent": raw["metadatas"][0][i].get("agent", ""),
                            "distance": raw["distances"][0][i] if raw.get("distances") else None,
                        })
            except Exception as e:
                print(f"[WARN] ChromaDB検索失敗: {e}", file=sys.stderr)

        # ChromaDB使えない場合はMarkdownフォールバック
        if not results:
            results = self._search_markdown(query, n_results, category)

        return results

    def _search_markdown(self, query: str, n_results: int = 5, category: str = None) -> list:
        """Markdownファイルからキーワード検索（フォールバック）"""
        results = []
        query_lower = query.lower()
        keywords = query_lower.split()

        for md_file in sorted(self.entries_dir.glob("*.md"), reverse=True):
            try:
                text = md_file.read_text(encoding="utf-8")
                text_lower = text.lower()

                # カテゴリフィルタ
                if category and f"# Memory: {category}" not in text:
                    continue

                # キーワードマッチスコア
                score = sum(1 for kw in keywords if kw in text_lower)
                if score > 0:
                    # メタデータ抽出
                    cat_match = re.search(r'^# Memory: (.+)$', text, re.MULTILINE)
                    date_match = re.search(r'^> Created: (.+)$', text, re.MULTILINE)
                    agent_match = re.search(r'^> Agent: (.+)$', text, re.MULTILINE)
                    content_match = re.search(r'## Content\n\n(.+)', text, re.DOTALL)

                    results.append({
                        "id": md_file.stem,
                        "content": content_match.group(1).strip() if content_match else text,
                        "category": cat_match.group(1) if cat_match else "",
                        "created_at": date_match.group(1) if date_match else "",
                        "agent": agent_match.group(1) if agent_match else "",
                        "distance": 1.0 - (score / len(keywords)),
                    })
            except Exception:
                continue

        results.sort(key=lambda x: x.get("distance", 1.0))
        return results[:n_results]

    def _update_index(self, memory_id: str, category: str, summary: str, meta: dict):
        """INDEX.jsonを更新"""
        try:
            index = []
            if self.index_file.exists():
                index = json.loads(self.index_file.read_text(encoding="utf-8"))

            # 重複排除
            index = [e for e in index if e.get("id") != memory_id]

            index.append({
                "id": memory_id,
                "category": category,
                "summary": summary,
                "created_at": meta.get("created_at", ""),
                "agent": meta.get("agent", ""),
            })

            # 最新1000件のみ保持
            if len(index) > 1000:
                index = index[-1000:]

            self.index_file.write_text(
                json.dumps(index, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[WARN] INDEX更新失敗: {e}", file=sys.stderr)

    def get_stats(self) -> dict:
        """記憶システムの統計情報"""
        stats = {
            "chromadb_available": HAS_CHROMADB,
            "gemini_available": HAS_GENAI and self.embedding_model is not None,
            "total_memories": 0,
            "categories": {},
            "markdown_files": 0,
        }

        if self.collection is not None:
            stats["total_memories"] = self.collection.count()

        # Markdownファイル数
        stats["markdown_files"] = len(list(self.entries_dir.glob("*.md")))

        # カテゴリ別カウント（INDEX.jsonから）
        if self.index_file.exists():
            try:
                index = json.loads(self.index_file.read_text(encoding="utf-8"))
                for entry in index:
                    cat = entry.get("category", "unknown")
                    stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
            except Exception:
                pass

        return stats

    def get_recent(self, n: int = 10) -> list:
        """最近の記憶をn件取得"""
        if self.index_file.exists():
            try:
                index = json.loads(self.index_file.read_text(encoding="utf-8"))
                return index[-n:]
            except Exception:
                pass
        return []

    def export_all(self) -> str:
        """全記憶をMarkdown形式でエクスポート"""
        output = "# Long-Term Memory Export\n"
        output += f"> Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for md_file in sorted(self.entries_dir.glob("*.md")):
            try:
                output += md_file.read_text(encoding="utf-8") + "\n---\n\n"
            except Exception:
                continue

        return output
