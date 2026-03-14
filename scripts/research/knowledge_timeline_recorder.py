"""
scripts/research/knowledge_timeline_recorder.py
知識タイムライン記録ユーティリティ — 全 Research スクリプト共有モジュール

このモジュールを使って knowledge_timeline.json に実行ランを APPEND ONLY で記録する。
インポート方法:
  from scripts.research.knowledge_timeline_recorder import record_run
または
  sys.path.insert(0, ...) で直接 import

スキーマ定義: .claude/KNOWLEDGE_TIMELINE.md
"""

import os
import sys
import json
import uuid
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR",
    os.path.abspath(os.path.join(_HERE, "..", ".."))
)
_TIMELINE_PATH = os.path.join(_PROJECT_ROOT, ".claude", "state", "knowledge_timeline.json")

# 年間ローテーション上限
_MAX_RUNS = 365


def _load_timeline() -> dict:
    """knowledge_timeline.json を読み込む。存在しない場合は初期状態を返す"""
    if not os.path.exists(_TIMELINE_PATH):
        return {
            "_schema_version": "1.0",
            "_description": "知識タイムライン — knowledge_ingestion の実行履歴を追跡する",
            "runs": [],
            "stats": {
                "total_runs": 0,
                "total_items_ingested": 0,
                "total_promoted": 0,
                "last_run_at": None,
                "first_run_at": None,
            },
        }
    try:
        with open(_TIMELINE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[TIMELINE] warning: 読み込みエラー ({e}) — 初期状態で続行", file=sys.stderr)
        return _load_timeline.__wrapped__()  # 再帰呼び出し防止のため上書き不可なのでコピー

_load_timeline.__wrapped__ = _load_timeline  # sentinel を設定しない簡易対応


def _save_timeline(data: dict) -> None:
    """knowledge_timeline.json に書き込む"""
    os.makedirs(os.path.dirname(_TIMELINE_PATH), exist_ok=True)
    with open(_TIMELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _rotate_if_needed(data: dict) -> dict:
    """runs が _MAX_RUNS を超えたら古いエントリを削除する（promoted_count>0 は保持優先）"""
    runs = data.get("runs", [])
    if len(runs) <= _MAX_RUNS:
        return data

    # 昇格ありは保持、なしは古い順から削除
    keep_promoted = [r for r in runs if r.get("promoted_count", 0) > 0]
    keep_regular = [r for r in runs if r.get("promoted_count", 0) == 0]

    # 保持が必要な総数
    target = _MAX_RUNS - len(keep_promoted)
    if target > 0:
        keep_regular = keep_regular[-target:]  # 直近のみ保持

    data["runs"] = sorted(keep_promoted + keep_regular, key=lambda r: r.get("ran_at", ""))
    return data


def record_run(
    source: str,
    items_ingested: int,
    items_total: int,
    topics: list,
    promoted_count: int,
    top_items: list,
    radar_size: int,
    run_status: str = "ok",
    notes: str = "",
) -> None:
    """
    knowledge_timeline.json にランを APPEND ONLY で記録する。

    Args:
        source:          "arxiv" | "semantic_scholar" | "manual" | "vps_sync" | "combined" | "digest" | "promote"
        items_ingested:  今回のセッションで取り込んだアイテム数（digest/promote は 0）
        items_total:     累計アイテム数（radar.json 全体の件数）
        topics:          検索トピックのリスト（なければ []）
        promoted_count:  タスク昇格した件数
        top_items:       上位アイテムのタイトルリスト（最大3件使用）
        radar_size:      radar.json の累計件数
        run_status:      "ok" | "partial_error" | "error"
        notes:           任意補足（エラー詳細等）
    """
    try:
        data = _load_timeline()
        now = datetime.now(timezone.utc).isoformat()

        run = {
            "run_id": str(uuid.uuid4()),
            "ran_at": now,
            "source": source,
            "items_ingested": items_ingested,
            "items_total": items_total,
            "topics": list(topics)[:10],      # 最大10件
            "promoted_count": promoted_count,
            "top_items": [str(t)[:120] for t in top_items[:3]],
            "radar_size": radar_size,
            "run_status": run_status,
            "notes": str(notes)[:200],
        }

        data["runs"].append(run)  # APPEND ONLY

        # stats 更新
        stats = data.setdefault("stats", {})
        stats["total_runs"] = stats.get("total_runs", 0) + 1
        stats["total_items_ingested"] = stats.get("total_items_ingested", 0) + items_ingested
        stats["total_promoted"] = stats.get("total_promoted", 0) + promoted_count
        stats["last_run_at"] = now
        if not stats.get("first_run_at"):
            stats["first_run_at"] = now

        data = _rotate_if_needed(data)
        _save_timeline(data)

        print(
            f"[TIMELINE] ✅ ラン記録: source={source} ingested={items_ingested} "
            f"promoted={promoted_count} status={run_status} "
            f"(累計 {stats['total_runs']}回 / {stats['total_items_ingested']}件)"
        )

    except Exception as e:
        # タイムライン記録はサイレントフェイル（パイプラインを止めない）
        print(f"[TIMELINE] ⚠️ 記録スキップ: {e}", file=sys.stderr)


if __name__ == "__main__":
    # 動作確認用スモークテスト
    print(f"[TIMELINE] タイムラインパス: {_TIMELINE_PATH}")
    record_run(
        source="manual",
        items_ingested=1,
        items_total=1,
        topics=["test"],
        promoted_count=0,
        top_items=["smoke test item"],
        radar_size=1,
        run_status="ok",
        notes="smoke test from knowledge_timeline_recorder.py __main__",
    )
    data = json.load(open(_TIMELINE_PATH, encoding="utf-8"))
    print(f"[TIMELINE] 確認: runs={len(data['runs'])} total_runs={data['stats']['total_runs']}")
