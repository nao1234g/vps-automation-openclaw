# /predictions/ ブロークンリンク調査 — 2026-03-29

> prediction_page_builder.py の link checker が blocked と報告していた問題の根本原因調査

---

## 調査サマリー

| 項目 | 結果 |
|------|------|
| 現在の broken link 件数 | **0件** |
| 現在の link check 結果 | **20 unique URLs / 全件 200 OK** |
| 歴史的 404 URL | `genre-crypto/`, `genre-finance/`, `genre-geopolitics/` プレフィックス（4件） |
| prediction_db.json の genre- URL | **0件（grep確認済み）** |
| JA predictions ページ HTML の genre- URL | **0件（現在生成物）** |
| `--force` フラグ | cron で指定済み。link check をバイパス中 → 現時点では不要（ただし harmless） |

---

## 根本原因チェーン（歴史的問題）

### 2026-03-03 時点の状態（problem origin）

NP-2026-0020/0021/0025/0027 の4件の予測に、誤った `ghost_url` フィールドが設定されていた:

| prediction_id | 誤ったghost_url（2026-03-03時点） | 結果 |
|--------------|-------------------------------|------|
| NP-2026-0020 | `/genre-crypto/btc-70k-march-31-2026/` | 404 |
| NP-2026-0021 | `/genre-crypto/btc-90k-march-31-2026/` | 404 |
| NP-2026-0025 | `/genre-finance/fed-fomc-march-2026-rate-decision/` | 404 |
| NP-2026-0027 | `/genre-geopolitics/khamenei-assassination-iran-supreme-leader-succession-2026/` | 404 |

Ghost の記事は `/{slug}/` 形式でルーティングされるが、これらのエントリには `/{primary_tag}/{slug}/` 形式の genre-prefixed URL が設定されていた。

### `_resolve_ghost_url()` との関係

`prediction_page_builder.py` には `_resolve_ghost_url()` が定義されている（line 636付近）が、**この関数は一度も呼ばれていない**。仮に呼ばれた場合、`/{primary_tag}/{slug}/` 形式を生成していた。これが genre-prefixed URL の設計上の由来。

ただし、実際の `build_rows()` は `pred.get("ghost_url", "")` を使って prediction_db.json の値を直接参照するため、`_resolve_ghost_url()` は dead code となっている。

### 修正（いつ行われたか）

prediction_page.log の証拠から:
- 2026-03-03: 初回の genre-URL 404 エラーが記録される
- 以降のセッション（2026-03-08〜28の間）で、4件の prediction_db.json エントリの `ghost_url` フィールドが `/en/en-{slug}/` 形式に修正された
- 同時期に cron へ `--force` フラグが追加されロールバック（link check バイパス）
- 2026-03-29 調査時点: 4件の `ghost_url` は全て `/en/en-{slug}/` → HTTP 200

---

## 現在の状態確認

### JA predictions ページ HTML のリンク

```bash
# 20件中最初の5件
https://nowpattern.com/en/en-btc-70k-march-31-2026/
https://nowpattern.com/en/en-btc-90k-march-31-2026/
https://nowpattern.com/en/en-fed-fomc-march-2026-rate-decision/
https://nowpattern.com/en/en-khamenei-assassination-iran-supreme-leader-succession-2026/
# ...その他 16件すべて nowpattern.com/{slug}/ 形式
```

**全20件: HTTP 200 確認済み** ✅

### genre- URL の不在確認

```bash
grep -c 'genre-' /opt/shared/scripts/prediction_db.json
# → 0

# ページHTML
curl -s https://nowpattern.com/predictions/ | grep -c 'genre-'
# → 0
```

---

## 残存する軽微な Data Quality 問題

上記4件の予測は **JA タイトル（日本語）** を持つが **ghost_url が EN 記事** を指している:

| prediction_id | article_title | ghost_url |
|--------------|--------------|-----------|
| NP-2026-0020 | ビットコインは2026年3月末に$70,000を超えるか | `/en/en-btc-70k-march-31-2026/` |
| NP-2026-0021 | BTCは2026年3月末までに$90,000を回復するか | `/en/en-btc-90k-march-31-2026/` |
| NP-2026-0025 | FRBは2026年3月のFOMCで利下げするか | `/en/en-fed-fomc-march-2026-rate-decision/` |
| NP-2026-0027 | ハメネイ師暗殺後... | `/en/en-khamenei-assassination-iran-supreme-leader-succession-2026/` |

**現象**: JA /predictions/ ページに掲載された JA 予測が、クリックすると EN 記事に飛ぶ。

**JA 記事の存在確認**:
```sql
-- ghost.db で確認済み
btc-70k-march-31-2026       → "ビットコインは2026年3月末に..." (published, 200 OK)
btc-90k-march-31-2026       → "BTCは2026年3月末までに..." (published, 200 OK)
fed-fomc-march-2026-rate-decision → "FRBは2026年3月..." (published, 200 OK)
khamenei-assassination-iran-supreme-leader-succession-2026 → "ハメネイ師..." (published, 200 OK)
```

**対処方針**: prediction_db.json の4件の `ghost_url` を JA 版 slug に更新すれば解決。ただし UX 影響は軽微（リンクは機能中）。Month 1 後半の低優先 backlog へ。

---

## `--force` フラグの評価

```bash
crontab -l | grep prediction_page_builder
# → python3 /opt/shared/scripts/prediction_page_builder.py --force --update >> /opt/shared/polymarket/prediction_page.log 2>&1
```

現時点では `--force` は実質的に不要（link check はパスする状態）だが、harmless。将来的に link check を有効にしたい場合は `--force` を削除すれば良い。変更は低リスクだが急ぎではない。

---

## アクションアイテム

| 項目 | 優先度 | 状態 |
|------|--------|------|
| 現在の broken link = 0 確認 | ✅ 完了 | DONE |
| 根本原因調査 | ✅ 完了 | DONE |
| 4件の ghost_url を JA 版に修正（data quality） | 低 | Backlog |
| `--force` フラグ削除（オプション） | 低 | Backlog |

---

*作成: 2026-03-29 Phase 2 調査 | Engineer: Claude Code (local)*
