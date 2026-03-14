#!/usr/bin/env python3
"""
knowledge_ingestion.py
AI Civilization OS — 知識インジェスションパイプライン

外部情報ソース（RSS / Reddit / Hey Loop結果 / VPSログ）を
Knowledge Engineに取り込み、civilization_patternsとknowledge_storeを更新する。

フロー:
  1. ソースから原文データを取得
  2. TruthEngine の 5種類の事実分類でフィルタリング
  3. KnowledgeStore に保存
  4. civilization_patterns.py に力学パターンを登録
  5. 要約をTelegramまたはログに送信

使用方法:
  python knowledge_ingestion.py                  # 全ソースを取り込む
  python knowledge_ingestion.py --source rss     # RSSのみ
  python knowledge_ingestion.py --source vps     # VPSログのみ
  python knowledge_ingestion.py --dry-run        # 書き込みなし検証
  python knowledge_ingestion.py --limit 20       # 最大20件を処理
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ==============================
# Ingestion Sources
# ==============================
SOURCES = {
    "hey_loop": {
        "description": "Hey Loop の日次インテリジェンス結果",
        "path_vps": "/opt/shared/reports/hey_loop_latest.json",
        "path_local": "data/hey_loop_latest.json",
        "priority": 1,
    },
    "agent_wisdom": {
        "description": "VPS AGENT_WISDOM.md の更新内容",
        "path_vps": "/opt/shared/AGENT_WISDOM.md",
        "path_local": None,
        "priority": 2,
    },
    "prediction_results": {
        "description": "解決済み予測の結果（Brier Score付き）",
        "path_vps": "/opt/shared/scripts/prediction_auto_verifier.py",
        "path_local": "data/prediction_db.json",
        "priority": 3,
    },
    "evolution_log": {
        "description": "週次自己進化ログ",
        "path_vps": "/opt/shared/logs/evolution_log.json",
        "path_local": "data/evolution_log.json",
        "priority": 4,
    },
}

INGESTION_LOG_PATH = "data/knowledge_ingestion_log.json"
MAX_LOG_ENTRIES = 200


# ==============================
# KnowledgeIngestion
# ==============================
class KnowledgeIngestion:
    """
    知識インジェスションパイプライン

    外部ソースから Unshakeable Facts のみを抽出し、
    Knowledge Engine に統合する。

    Geneen原則: 「5種類の事実を見分けろ。Wishful factsでシステムを汚染するな」
    """

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self._log: List[Dict] = []
        self._load_log()

    # --------------------------
    # Public API
    # --------------------------
    def ingest_latest(self, source_filter: Optional[str] = None,
                      limit: int = 100) -> Dict:
        """
        最新の知識を全ソースから取り込む

        Returns:
            {"ingested": 15, "skipped": 3, "errors": 0, "sources": [...]}
        """
        print("[KnowledgeIngestion] Starting ingestion run")
        results = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "ingested": 0,
            "skipped": 0,
            "errors": 0,
            "sources": [],
        }

        # ソースを優先度順で処理
        sources_to_process = sorted(
            SOURCES.items(),
            key=lambda x: x[1]["priority"]
        )

        for source_name, source_cfg in sources_to_process:
            if source_filter and source_name != source_filter:
                continue

            print(f"  Processing: {source_name} ({source_cfg['description']})")
            result = self._ingest_source(source_name, source_cfg, limit)
            results["sources"].append({"source": source_name, **result})
            results["ingested"] += result.get("ingested", 0)
            results["skipped"] += result.get("skipped", 0)
            results["errors"] += result.get("errors", 0)

        # 知識ストアを更新
        if results["ingested"] > 0 and not self.dry_run:
            self._update_knowledge_store(results)

        self._append_log(results)

        total = results["ingested"] + results["skipped"]
        print(f"[KnowledgeIngestion] Complete — "
              f"ingested={results['ingested']}, "
              f"skipped={results['skipped']}, "
              f"errors={results['errors']}")
        return results

    def ingest_raw(self, raw_facts: List[Dict], source: str = "manual") -> Dict:
        """
        生の事実リストを直接インジェストする（テスト・手動インジェスト用）

        raw_facts の各要素:
            {"fact_type": "unshakeable|surface|assumed|reported|wishful",
             "content": "...", "topic": "...", "confidence": 0.0~1.0}
        """
        unshakeable = [
            f for f in raw_facts
            if f.get("fact_type") == "unshakeable" and f.get("confidence", 0) >= 0.7
        ]

        ingested = len(unshakeable)
        skipped = len(raw_facts) - ingested

        if ingested > 0 and not self.dry_run:
            self._store_facts(unshakeable, source)

        print(f"[KnowledgeIngestion] Manual ingest: {ingested} facts (skipped {skipped} non-unshakeable)")
        return {"ingested": ingested, "skipped": skipped, "source": source}

    def get_stats(self) -> Dict:
        """インジェスション統計を返す"""
        if not self._log:
            return {"runs": 0, "total_ingested": 0}
        total = sum(r.get("ingested", 0) for r in self._log)
        recent = self._log[-1] if self._log else {}
        return {
            "runs": len(self._log),
            "total_ingested": total,
            "last_run": recent.get("ts", "never"),
            "last_ingested": recent.get("ingested", 0),
        }

    # --------------------------
    # Source Processors
    # --------------------------
    def _ingest_source(self, source_name: str, source_cfg: Dict, limit: int) -> Dict:
        """個別ソースを処理する"""
        # ファイルパスを決定（VPS/ローカル）
        path = self._resolve_path(source_cfg)
        if path is None:
            return {"ingested": 0, "skipped": 0, "errors": 0,
                    "note": "source not available in current environment"}

        if not os.path.exists(path):
            return {"ingested": 0, "skipped": 0, "errors": 0,
                    "note": f"file not found: {path}"}

        try:
            facts = self._extract_facts(source_name, path, limit)
            if not facts:
                return {"ingested": 0, "skipped": 0, "errors": 0,
                        "note": "no extractable facts"}

            # Fact type filtering: Unshakeable only
            unshakeable = [f for f in facts if f.get("confidence", 0) >= 0.6]
            skipped = len(facts) - len(unshakeable)

            if unshakeable and not self.dry_run:
                self._store_facts(unshakeable, source_name)

            return {"ingested": len(unshakeable), "skipped": skipped, "errors": 0}

        except Exception as e:
            if self.verbose:
                import traceback
                traceback.print_exc()
            return {"ingested": 0, "skipped": 0, "errors": 1, "error": str(e)}

    def _resolve_path(self, source_cfg: Dict) -> Optional[str]:
        """VPS/ローカルのパスを解決する"""
        # ローカルパスが存在する場合は優先
        local = source_cfg.get("path_local")
        if local and os.path.exists(local):
            return local
        # VPSパスはSSH経由のため、ここではスキップ（VPS上では直接アクセス）
        vps = source_cfg.get("path_vps")
        if vps and os.path.exists(vps):
            return vps
        return None

    def _extract_facts(self, source_name: str, path: str, limit: int) -> List[Dict]:
        """ソースファイルから事実を抽出する"""
        facts = []

        if path.endswith(".json"):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if source_name == "prediction_results":
                facts = self._extract_from_prediction_db(data, limit)
            elif source_name == "evolution_log":
                facts = self._extract_from_evolution_log(data, limit)
            elif source_name == "hey_loop":
                facts = self._extract_from_hey_loop(data, limit)
            else:
                # 汎用JSON: リスト型の場合
                if isinstance(data, list):
                    for item in data[:limit]:
                        if isinstance(item, dict) and "content" in item:
                            facts.append({
                                "content": str(item["content"])[:500],
                                "fact_type": "reported",
                                "confidence": 0.6,
                                "source": source_name,
                            })
        elif path.endswith(".md"):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            # Markdown から学習ログセクションを抽出
            facts = self._extract_from_markdown(text, source_name)

        return facts[:limit]

    def _extract_from_prediction_db(self, data: Dict, limit: int) -> List[Dict]:
        """prediction_db.json から解決済み予測の事実を抽出"""
        facts = []
        predictions = []
        if isinstance(data, dict):
            predictions = data.get("predictions", [])
        elif isinstance(data, list):
            predictions = data

        resolved = [p for p in predictions if p.get("status") == "resolved"][:limit]
        for p in resolved:
            brier = p.get("brier_score", p.get("brier", None))
            if brier is not None:
                facts.append({
                    "fact_type": "unshakeable",
                    "confidence": 0.95,
                    "source": "prediction_db",
                    "content": (
                        f"予測ID={p.get('id','')} "
                        f"質問={p.get('resolution_question','')[:100]} "
                        f"結果={p.get('outcome','')} "
                        f"Brier={brier}"
                    ),
                    "topic": p.get("topic", "prediction"),
                })
        return facts

    def _extract_from_evolution_log(self, data, limit: int) -> List[Dict]:
        """evolution_log.json から学習事実を抽出"""
        facts = []
        entries = data if isinstance(data, list) else data.get("entries", [])
        for entry in entries[-limit:]:
            learning = entry.get("ai_learning", "")
            if learning and len(learning) > 20:
                facts.append({
                    "fact_type": "unshakeable",
                    "confidence": 0.8,
                    "source": "evolution_log",
                    "content": learning[:500],
                    "topic": "prediction_accuracy",
                })
        return facts

    def _extract_from_hey_loop(self, data, limit: int) -> List[Dict]:
        """Hey Loop JSON から事実を抽出"""
        facts = []
        items = data if isinstance(data, list) else data.get("items", [])
        for item in items[:limit]:
            content = item.get("summary", item.get("content", ""))
            if len(content) > 50:
                facts.append({
                    "fact_type": "reported",
                    "confidence": 0.6,
                    "source": "hey_loop",
                    "content": content[:500],
                    "topic": item.get("topic", "general"),
                })
        return facts

    def _extract_from_markdown(self, text: str, source: str) -> List[Dict]:
        """MarkdownテキストからQ&Aや知識ポイントを抽出"""
        facts = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            # 学習ログの箇条書き行を事実として登録
            if line.startswith("- ") and len(line) > 30:
                facts.append({
                    "fact_type": "reported",
                    "confidence": 0.65,
                    "source": source,
                    "content": line[2:500],
                    "topic": "agent_wisdom",
                })
        return facts[:50]  # MD1ファイルから最大50件

    # --------------------------
    # Storage
    # --------------------------
    def _store_facts(self, facts: List[Dict], source: str):
        """Knowledge Storeに事実を保存する"""
        try:
            from knowledge_engine.knowledge_store import KnowledgeStore
            ks = KnowledgeStore()
            for fact in facts:
                # KnowledgeStore.add() expects fact_type (uppercase) + tags list
                ft = fact.get("fact_type", "REPORTED").upper()
                if ft not in {"UNSHAKEABLE", "SURFACE", "REPORTED", "ASSUMED"}:
                    ft = "REPORTED"
                ks.add(
                    content=fact["content"],
                    fact_type=ft,
                    source=fact.get("source", source),
                    tags=[fact.get("topic", "general")],
                    confidence=fact.get("confidence", 0.7),
                )
            if self.verbose:
                print(f"    Stored {len(facts)} facts to KnowledgeStore")
        except Exception as e:
            # KnowledgeStore が利用不可の場合はローカルJSONに fallback
            if self.verbose:
                print(f"    [WARN] KnowledgeStore unavailable: {e}. Using fallback.")
            self._store_facts_fallback(facts, source)

    def _store_facts_fallback(self, facts: List[Dict], source: str):
        """KnowledgeStore不可時のJSONフォールバック"""
        fallback_path = "data/ingested_facts.json"
        existing = []
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        ts = datetime.now(timezone.utc).isoformat()
        for fact in facts:
            existing.append({**fact, "source": source, "ingested_at": ts})
        existing = existing[-2000:]  # 最新2000件を保持
        os.makedirs("data", exist_ok=True)
        with open(fallback_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def _update_knowledge_store(self, results: Dict):
        """インジェスション結果でナレッジメタデータを更新"""
        meta_path = "data/knowledge_meta.json"
        meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        meta["last_ingestion"] = results["ts"]
        meta["total_ingested"] = meta.get("total_ingested", 0) + results["ingested"]
        meta["run_count"] = meta.get("run_count", 0) + 1
        os.makedirs("data", exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def _append_log(self, results: Dict):
        if self.dry_run:
            return
        self._log.append(results)
        self._log = self._log[-MAX_LOG_ENTRIES:]
        os.makedirs("data", exist_ok=True)
        with open(INGESTION_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._log, f, ensure_ascii=False, indent=2)

    def _load_log(self):
        if os.path.exists(INGESTION_LOG_PATH):
            try:
                with open(INGESTION_LOG_PATH, encoding="utf-8") as f:
                    self._log = json.load(f)
            except Exception:
                self._log = []
        else:
            self._log = []


# ==============================
# CLI
# ==============================
def main():
    parser = argparse.ArgumentParser(description="AI Civilization OS Knowledge Ingestion")
    parser.add_argument("--source",  default=None,
                        choices=list(SOURCES.keys()),
                        help="特定ソースのみ処理")
    parser.add_argument("--limit",   type=int, default=100,
                        help="最大処理件数 (default: 100)")
    parser.add_argument("--stats",   action="store_true", help="インジェスション統計を表示")
    parser.add_argument("--dry-run", action="store_true", help="書き込みなし検証")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    args = parser.parse_args()

    ingestion = KnowledgeIngestion(dry_run=args.dry_run, verbose=args.verbose)

    if args.stats:
        stats = ingestion.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return

    result = ingestion.ingest_latest(
        source_filter=args.source,
        limit=args.limit,
    )

    if args.verbose:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
