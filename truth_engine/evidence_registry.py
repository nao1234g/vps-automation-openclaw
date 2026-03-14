"""
truth_engine/evidence_registry.py
証拠登録簿 — 予測の根拠を不変の記録として保存する

Nowpatternの予測は「証拠ベース」でなければならない。
このモジュールはAIが予測を生成した際の根拠（ニュース、データ、歴史パターン）を
タイムスタンプ付きで保存し、後から検証可能にする。
"""

import sys
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "evidence_registry.json"
)


@dataclass
class Evidence:
    """単一証拠のデータ構造"""
    evidence_id: str
    prediction_id: str
    evidence_type: str      # NEWS / DATA / HISTORY / ANALYSIS / MARKET
    source: str             # URL またはデータソース名
    content: str            # 証拠の内容（要約）
    fact_type: str          # UNSHAKEABLE / SURFACE / REPORTED / ASSUMED
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str = "local-claude"


class EvidenceRegistry:
    """
    証拠登録簿 — AIがなぜその予測をしたかを永続記録する

    Nowpatternが他のメディアと違う点:
    「なんとなく」ではなく「証拠がある」と言い切れること
    """

    def __init__(self, registry_path: str = REGISTRY_PATH):
        self.path = registry_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._data: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def register(self, evidence: Evidence) -> str:
        """証拠を登録する"""
        record = asdict(evidence)
        self._data.append(record)
        self._save()
        return evidence.evidence_id

    def get_for_prediction(self, prediction_id: str) -> List[Dict]:
        """特定予測の証拠一覧"""
        return [e for e in self._data if e["prediction_id"] == prediction_id]

    def get_unshakeable_only(self, prediction_id: str) -> List[Dict]:
        """
        揺るぎない事実（UNSHAKEABLE）のみを返す
        Geneen原則: Unshakeable factsのみで判断する
        """
        return [
            e for e in self.get_for_prediction(prediction_id)
            if e["fact_type"] == "UNSHAKEABLE"
        ]

    def validate_prediction(self, prediction_id: str) -> Dict:
        """
        予測の証拠品質を検証する
        UNSHAKEABLE が1件以上あれば合格
        """
        all_evidence = self.get_for_prediction(prediction_id)
        unshakeable = self.get_unshakeable_only(prediction_id)
        wishful = [e for e in all_evidence if e["fact_type"] == "WISHFUL"]

        return {
            "prediction_id": prediction_id,
            "total_evidence": len(all_evidence),
            "unshakeable_count": len(unshakeable),
            "wishful_count": len(wishful),
            "is_valid": len(unshakeable) >= 1 and len(wishful) == 0,
            "verdict": (
                "APPROVED" if len(unshakeable) >= 1 and len(wishful) == 0
                else "REJECTED" if len(wishful) > 0
                else "INSUFFICIENT"
            ),
        }

    def stats(self) -> Dict:
        """証拠登録簿の統計"""
        by_type = {}
        for e in self._data:
            ft = e.get("fact_type", "UNKNOWN")
            by_type[ft] = by_type.get(ft, 0) + 1

        return {
            "total_evidence": len(self._data),
            "predictions_covered": len(set(e["prediction_id"] for e in self._data)),
            "by_fact_type": by_type,
        }


if __name__ == "__main__":
    registry = EvidenceRegistry()
    print(f"[EvidenceRegistry] {registry.stats()}")
