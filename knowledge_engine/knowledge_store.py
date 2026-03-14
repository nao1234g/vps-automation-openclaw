"""
knowledge_engine/knowledge_store.py
知識ストア — Nowpatternが学習した全ての事実を保存・検索する

Unshakeable facts だけを永続化し、
Wishful facts を拒否するフィルター付きストレージ。
"""

import sys
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class KnowledgeEntry:
    """単一の知識エントリー"""
    id: str
    content: str                      # 知識の内容
    fact_type: str                    # UNSHAKEABLE / SURFACE / REPORTED / ASSUMED / WISHFUL
    source: str                       # 出典（URL / DB / 観測）
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0           # 0.0〜1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    used_count: int = 0               # 予測に使われた回数
    verified: bool = False            # 検証済みフラグ

    def to_dict(self) -> Dict:
        return asdict(self)


# 受け入れ可能なファクトタイプ（Wishful は保存しない）
ACCEPTABLE_FACT_TYPES = {"UNSHAKEABLE", "SURFACE", "REPORTED", "ASSUMED"}
TRUSTED_FACT_TYPES = {"UNSHAKEABLE"}


class KnowledgeStore:
    """
    知識永続化ストレージ

    原則:
    1. WISHFUL facts は保存拒否
    2. UNSHAKEABLE facts が最優先で返される
    3. タグ・キーワード・ファクトタイプで検索可能
    """

    DEFAULT_PATH = "data/knowledge_store.json"

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DEFAULT_PATH
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._load()

    # ── 書き込み ──────────────────────────────────────

    def add(self, content: str, fact_type: str, source: str,
            tags: List[str] = None, confidence: float = 1.0) -> Optional[KnowledgeEntry]:
        """
        知識を追加する

        Returns:
            KnowledgeEntry if added, None if rejected
        """
        if fact_type == "WISHFUL":
            print(f"[REJECTED] WISHFUL fact は保存できません: {content[:60]}...")
            return None

        if fact_type not in ACCEPTABLE_FACT_TYPES:
            print(f"[REJECTED] 未知のファクトタイプ: {fact_type}")
            return None

        entry_id = self._generate_id()
        entry = KnowledgeEntry(
            id=entry_id,
            content=content,
            fact_type=fact_type,
            source=source,
            tags=tags or [],
            confidence=confidence,
        )
        self._entries[entry_id] = entry
        self._save()
        return entry

    def verify(self, entry_id: str) -> bool:
        """エントリーを検証済みにマークする"""
        if entry_id in self._entries:
            self._entries[entry_id].verified = True
            self._save()
            return True
        return False

    def mark_used(self, entry_id: str):
        """予測で使用された回数をインクリメント"""
        if entry_id in self._entries:
            self._entries[entry_id].used_count += 1
            self._save()

    # ── 読み取り ──────────────────────────────────────

    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self._entries.get(entry_id)

    def search(self, query: str = None, tags: List[str] = None,
               fact_type: str = None, trusted_only: bool = False,
               limit: int = 20) -> List[KnowledgeEntry]:
        """
        知識を検索する

        Args:
            query: キーワード検索（コンテンツ部分一致）
            tags: 指定タグを持つエントリーのみ
            fact_type: ファクトタイプでフィルター
            trusted_only: True なら UNSHAKEABLE のみ返す
            limit: 最大件数
        """
        results = list(self._entries.values())

        # UNSHAKEABLE優先ソート（信頼度→使用回数降順）
        results.sort(key=lambda e: (
            1 if e.fact_type == "UNSHAKEABLE" else 0,
            e.confidence,
            e.used_count,
        ), reverse=True)

        if trusted_only:
            results = [e for e in results if e.fact_type in TRUSTED_FACT_TYPES]

        if fact_type:
            results = [e for e in results if e.fact_type == fact_type]

        if tags:
            results = [e for e in results
                       if any(t in e.tags for t in tags)]

        if query:
            q = query.lower()
            results = [e for e in results if q in e.content.lower()]

        return results[:limit]

    def get_by_tags(self, tags: List[str]) -> List[KnowledgeEntry]:
        """タグで知識を取得（UNSHAKEABLE 優先）"""
        return self.search(tags=tags, trusted_only=False)

    def stats(self) -> Dict:
        entries = list(self._entries.values())
        by_type = {}
        for e in entries:
            by_type[e.fact_type] = by_type.get(e.fact_type, 0) + 1

        return {
            "total_entries": len(entries),
            "by_fact_type": by_type,
            "verified_count": sum(1 for e in entries if e.verified),
            "unshakeable_pct": round(
                by_type.get("UNSHAKEABLE", 0) / max(len(entries), 1) * 100, 1
            ),
            "most_used": sorted(entries, key=lambda e: e.used_count, reverse=True)[:3],
        }

    # ── 永続化 ──────────────────────────────────────

    def _load(self):
        if not os.path.exists(self.db_path):
            return
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for entry_id, data in raw.items():
                self._entries[entry_id] = KnowledgeEntry(**data)
        except Exception as e:
            print(f"[WARNING] KnowledgeStore load error: {e}")

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        try:
            data = {eid: e.to_dict() for eid, e in self._entries.items()}
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] KnowledgeStore save error: {e}")

    def _generate_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        count = len(self._entries) + 1
        return f"KE-{ts}-{count:04d}"


if __name__ == "__main__":
    store = KnowledgeStore("data/knowledge_store.json")

    # デモ: 知識追加
    e1 = store.add(
        content="2008年の金融危機後、FRBは量的緩和を3回実施した（QE1/QE2/QE3）。",
        fact_type="UNSHAKEABLE",
        source="FED Historical Records",
        tags=["経済・金融", "FRB", "量的緩和"],
        confidence=0.99,
    )
    e2 = store.add(
        content="対立の螺旋が発動すると、次の12ヶ月以内に紛争が激化する確率は62%。",
        fact_type="UNSHAKEABLE",
        source="prediction_db.json resolved predictions (2024-2026)",
        tags=["地政学・安全保障", "対立の螺旋"],
        confidence=0.85,
    )

    # WISHFUL は拒否される
    store.add(
        content="BTCは2026年末に$200,000になるはず。",
        fact_type="WISHFUL",
        source="Twitter speculation",
        tags=["暗号資産"],
    )

    print(f"ストア統計: {json.dumps(store.stats()['by_fact_type'], ensure_ascii=False)}")
    results = store.search(tags=["経済・金融"], trusted_only=True)
    print(f"UNSHAKEABLE 経済・金融: {len(results)}件")
