# KNOWLEDGE_TIMELINE.md — 知識タイムラインの設計書

> **knowledge_timeline.json のスキーマ定義・使い方・運用ガイド。**
> knowledge_ingestion.py が実行されるたびにここにランを記録する。
> 更新: 変更時は末尾のCHANGELOGに1行追記。

---

## 概要

知識タイムラインは Research Intelligence Layer（Layer 4）の全実行履歴を
APPEND ONLY で記録するデータベースである。

**目的:**
1. 「どのソースから何件の知識を取り込んだか」の透明な履歴
2. 取り込みが正常に機能しているかのモニタリング
3. タスク昇格（promotion）の効率追跡

---

## ファイルの場所

```
ローカル: .claude/state/knowledge_timeline.json
VPS:     /opt/shared/knowledge_timeline.json（Hive Mind同期対象）
```

---

## スキーマ定義

```json
{
  "_schema_version": "1.0",
  "_description": "知識タイムライン — knowledge_ingestion の実行履歴",
  "_field_definitions": { ... },
  "runs": [ ... ],
  "stats": { ... }
}
```

### `runs` エントリの全フィールド

| フィールド | 型 | 必須 | 説明 | 例 |
|-----------|-----|------|------|-----|
| `run_id` | string | ✅ | UUID4形式の実行ID | `"a1b2c3d4-..."` |
| `ran_at` | string | ✅ | 実行日時（ISO 8601 UTC） | `"2026-03-14T12:00:00Z"` |
| `source` | string | ✅ | 知識ソース種別 | `"arxiv"` |
| `items_ingested` | integer | ✅ | 今回取り込んだアイテム数 | `15` |
| `items_total` | integer | ✅ | 累計アイテム数（radar.json全体） | `142` |
| `topics` | array | ✅ | 検索トピックのリスト | `["prediction markets", "LLM agents"]` |
| `promoted_count` | integer | ✅ | タスク昇格した件数 | `2` |
| `top_items` | array | ✅ | 上位3件のタイトルリスト | `["Paper Title 1", ...]` |
| `radar_size` | integer | ✅ | radar.json の累計件数 | `238` |
| `run_status` | string | ✅ | 実行結果 | `"ok"` |
| `notes` | string | ❌ | エラー詳細・補足 | `""` |

### `source` の取り得る値

| 値 | 意味 |
|----|------|
| `"arxiv"` | arXiv API から取得 |
| `"semantic_scholar"` | Semantic Scholar API から取得 |
| `"manual"` | 手動追加（URL直接指定等） |
| `"vps_sync"` | VPS→ローカル同期 |
| `"combined"` | 複数ソースの混合実行 |

### `run_status` の取り得る値

| 値 | 意味 |
|----|------|
| `"ok"` | 正常完了 |
| `"partial_error"` | 一部エラー（一部は成功） |
| `"error"` | 失敗（0件取り込み） |

---

### `stats` オブジェクト

```json
{
  "total_runs": 42,
  "total_items_ingested": 1250,
  "total_promoted": 18,
  "last_run_at": "2026-03-14T12:00:00Z",
  "first_run_at": "2026-03-01T09:00:00Z"
}
```

| フィールド | 意味 |
|-----------|------|
| `total_runs` | 全実行回数 |
| `total_items_ingested` | 全取り込みアイテム数の累計 |
| `total_promoted` | 全タスク昇格件数の累計 |
| `last_run_at` | 最後の実行日時 |
| `first_run_at` | 最初の実行日時 |

**`stats` は runs から再計算可能。ただし都度計算を避けるため redundant に保持する。**

---

## 記録のタイミング

`knowledge_timeline.json` へのランの追加は以下のタイミングで行う:

1. `scripts/research/daily_paper_ingest.py` 実行後（VPS cron）
2. `promote_research_to_tasks.py` で昇格処理後（promoted_count更新）
3. 手動でナレッジを取り込んだ後（source: "manual"）
4. VPSからのHive Mind同期後（source: "vps_sync"）

---

## 記録の実装例

```python
import uuid, json
from datetime import datetime, timezone

def record_run(
    source: str,
    items_ingested: int,
    items_total: int,
    topics: list,
    promoted_count: int,
    top_items: list,
    radar_size: int,
    run_status: str = "ok",
    notes: str = ""
):
    timeline_path = os.path.join(PROJECT_ROOT, ".claude/state/knowledge_timeline.json")
    with open(timeline_path, encoding="utf-8") as f:
        data = json.load(f)

    now = datetime.now(timezone.utc).isoformat()
    run = {
        "run_id": str(uuid.uuid4()),
        "ran_at": now,
        "source": source,
        "items_ingested": items_ingested,
        "items_total": items_total,
        "topics": topics,
        "promoted_count": promoted_count,
        "top_items": top_items[:3],
        "radar_size": radar_size,
        "run_status": run_status,
        "notes": notes,
    }
    data["runs"].append(run)  # APPEND ONLY

    # stats を更新
    data["stats"]["total_runs"] += 1
    data["stats"]["total_items_ingested"] += items_ingested
    data["stats"]["total_promoted"] += promoted_count
    data["stats"]["last_run_at"] = now
    if data["stats"]["first_run_at"] is None:
        data["stats"]["first_run_at"] = now

    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 不変性ルール

```
✅ runs への追記 = 許可（APPEND ONLY）
❌ runs エントリの変更・削除 = 禁止（audit trailとして保持）
✅ stats の更新 = 許可（runs から再計算可能なため）
```

**ローテーション**: runs が 365件を超えたら古い方から削除（年間ローテーション）。
ただし promoted_count > 0 のランは保持優先。

---

## ダイジェストとの連携

```
daily_paper_ingest.py
  → radar.json に論文を追加
  → knowledge_timeline.json にランを記録
  ↓
daily_research_digest.py
  → radar.json を読んで上位アイテムをフォーマット
  → Telegram / Markdown / JSON で出力
  ↓
promote_research_to_tasks.py
  → radar.json の高関連度アイテムをタスクに昇格
  → knowledge_timeline.json の promoted_count を更新
```

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-03-14 | 初版。knowledge_timeline.jsonのスキーマ完全定義。記録実装例。ローテーションルール。 |
