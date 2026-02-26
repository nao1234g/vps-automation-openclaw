# Nowpattern 実装ロードマップ
> ここが唯一の「やること管理」ファイル。セッションをまたいでも続きから始める。
> 更新日: 2026-02-25

---

## 全体フロー（決定済み）

```
B（バグ修正）→ A（モート構築）→ C（表示統合）
```

理由: B は既存サイトの壊れた部分で即修正が必要。A は C のデータ基盤。C は A のデータが入って初めて意味のある数字が出る。

---

## B: サイト品質バグ修正（最優先）

| # | タスク | ステータス | 詳細 |
|---|---|---|---|
| B1 | ENページに日本語記事が混入 | ✅ 完了 | `/en/` の言語フィルタJS + Caddy rewrite で修正済み（2026-02-23） |
| B2 | 日本語ナビに「予測トラッカー」がない | ✅ 完了 | Ghost CMS codeinjection で追加済み（2026-02-24） |
| B3 | 日本語ナビに「力学」がない | ✅ 完了 | Ghost CMS ナビゲーション設定で追加済み（2026-02-24） |

---

## A: モート構築（予測市場データベース）

### A の全体像

```
世界の予測市場（Polymarket / Manifold / Metaculus）
    ↓ 毎日 09:00 JST にクロール
/opt/shared/market_history/market_history.db（SQLite）
    現状: markets=1326件 / probability_snapshots積み上げ中 / nowpattern_links=1件
    ↓ 解決検出 → prediction_resolver.py
prediction_db.json（7件の予測、全て resolution_question 入力済み）
    ↓
NEO 記事指示書（新記事から resolution_question 必須化 ← 2026-02-25に追加）
```

### A のスキーマ（4テーブル）

```
markets:              市場マスタ（1326件）
probability_snapshots: 日次確率推移（1市場×365日）
nowpattern_links:     記事↔市場の紐付け + resolution_direction（現状1件）
news_events:          確率急変日のニュース記録（≥15%変化）
```

### A の判定ロジック

```
resolution_direction = "pessimistic": YES→悲観, NO→楽観
resolution_direction = "optimistic":  YES→楽観, NO→悲観
確率 35〜65% で期日到来 → 基本シナリオ（不確定）
確率 ≥95% or ≤5% → 自動判定
確率 70〜95%      → Gemini確認後に自動
確率 30〜70%      → Telegram手動ボタン
```

### A のタスク

| # | タスク | ステータス | ファイル | 備考 |
|---|---|---|---|---|
| A1 | 市場クローラー | ✅ 完了 | `/opt/shared/scripts/market_history_crawler.py` | cron 毎日09:00稼働中 |
| A2 | 自動判定エンジン | ✅ 完了 | `/opt/shared/scripts/prediction_resolver.py` | `--auto-resolve` 稼働中 |
| A3 | NEO 指示書更新 | ✅ 完了 | `docs/NEO_INSTRUCTIONS_V2.md` | resolution_question 必須化 + 5ステップワークフロー追加済み |
| A3+ | 既存予測への resolution_question 追加 | ✅ 完了 | `/opt/shared/scripts/prediction_db.json` | 7件全て入力済み（2026-02-25） |
| A4 | 予測↔市場リンク蓄積 | 🔄 継続中 | `prediction_db.json` + `nowpattern_links` テーブル | 現状1件（NP-2026-0003↔市場1559）。残6件はManifoldカバレッジ待ち |

### A1 の実装詳細

**対象 API（認証不要、全て無料）:**
- Polymarket Gamma API: `gamma-api.polymarket.com` → `/markets`, `/prices-history`
- Manifold Markets: `api.manifold.markets/v0` → `/markets`, `/bets`
- Metaculus: `metaculus.com/api2/questions/` → `aggregations.history`

**cron 設定（稼働中）:**
```bash
0 9 * * * source /opt/cron-env.sh && python3 /opt/shared/scripts/market_history_crawler.py
```

**手動で予測を市場に紐付ける方法:**
```bash
# 検索
python3 /opt/shared/scripts/prediction_resolver.py --search "GENIUS stablecoin 2026" --limit 10
# 紐付け
python3 /opt/shared/scripts/prediction_resolver.py --add-link \
  --prediction-id NP-2026-0001 --market-id <DB_ID> --direction optimistic
# 確認
python3 /opt/shared/scripts/prediction_resolver.py --link
```

---

## C: 予測ページ表示（A完了後に実装）

| # | タスク | ステータス | 詳細 |
|---|---|---|---|
| C1 | Pattern A 実装 | 🔴 未着手 | `prediction_page_builder.py` — 問い中心型、クリック展開 |
| C2 | スコアボード（累計的中率） | 🔴 未着手 | 実際の Brier Score データを表示 |
| C3 | 検索/フィルター | 🔴 C1 待ち | カテゴリ・期日・ステータスでフィルタ |

### Pattern A の仕様（決定済み）

```
トラッカーページ:
  ┌─────────────────────────────────────────────┐
  │ スコアボード（的中XX/XX件、Brier XX）         │
  ├─────────────────────────────────────────────┤
  │ 🔲 [追跡中の問い: ○○は起きるか？]            │
  │    [楽観 30%] [基本 50%] [悲観 20%]  市場:72%│
  │    ↓クリックで展開                           │
  │    詳細カード（R1形式）                       │
  └─────────────────────────────────────────────┘

記事ページ内:
  大カード（A形式）で表示
```

---

## D: UI自動検証システム（新規）

> UIの変更後に人間が目視確認する手間をゼロにする。Playwright headless browser でCSSを自動検証。

| # | タスク | ステータス | 詳細 |
|---|---|---|---|
| D1 | VPS に Playwright インストール | 🔄 進行中 | Python playwright + Chromium |
| D2 | `verify_ui.py` 作成 | 🔄 進行中 | computed style チェック（display:none / font-size:0 検出） |
| D3 | `fact-checker.py` 統合 | 🔴 未着手 | Playwright PASS なしに「直りました」をブロック |

---

## 決定事項メモ（変更しない）

- 的中判定: **resolution_direction** フィールドで YES/NO→シナリオをマッピング
- 精度指標: **Brier Score**（0に近いほど良い、0.25=ランダム、0.15=上位10%）
- 自動化: 手動判定は 30〜70% の不確定ケースのみ（Telegram ボタン）
- データ保存先: `/opt/shared/market_history/market_history.db`
- 「基本シナリオ偏り問題」: Brier Score で自動解決（基本を選び続けても精度は出ない）

---

*最終更新: 2026-02-25 — B全完了 / A1-A3完了・A4継続中 / D新規追加*
