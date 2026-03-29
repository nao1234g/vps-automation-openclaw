# NOWPATTERN BLOCKED ITEMS — 2026-03-28
> Round 3 実施後の未着手・ブロック済み項目の完全記録
> ベース: docs/NOWPATTERN_FIX_PRIORITY_2026-03-28.md + 実測データ

---

## REQ-002: portal_plans に monthly/yearly を追加する

| フィールド | 内容 |
|-----------|------|
| **状態** | 🚫 BLOCKED |
| **ROI スコア** | 8（ビジネスインパクト最大級） |
| **ブロッカー** | Stripe 未接続。portal_plans に paid プランを追加しても、Stripe 接続なしでは実際の課金フローが動かない |
| **必要な前提条件** | (1) Stripe アカウント設定、(2) Ghost Admin → Settings → Stripe 連携、(3) その後に portal_plans 更新 |
| **SQLite コマンド（Stripe接続後）** | `sqlite3 /var/www/nowpattern/content/data/ghost.db "UPDATE settings SET value='{\"plans\":[\"free\",\"monthly\",\"yearly\"]}' WHERE key='portal_plans';"` + Ghost再起動 |
| **現在の値** | `portal_plans: ["free"]` |
| **解除条件** | Naoto が Stripe を Ghost Admin に接続済みであることを確認してから |
| **解決後の効果** | Phase 2 有料転換（$9〜19/月 個人トラックレコード）が実現可能になる |
| **PVQE 貢献** | Q（行動量）/ E間接（収益化で継続投資が可能になる） |
| **参照** | NORTH_STAR.md「マネタイズ戦略 Phase 2」 |

---

## REQ-010: X DLQ エラーの解消（次セッション最優先）

| フィールド | 内容 |
|-----------|------|
| **状態** | ⚠️ 未着手（Week 1 実施予定 — 次セッション #1） |
| **ROI スコア** | 7（E波及力への直接影響）/ **PVQE-E補正後 実質9** |
| **現在の状態** | DLQ に **82件滞留**: `error:true` 79件 + `error:429` 3件 |
| **⚠️ 文書訂正** | FIX_PRIORITY_2026-03-28.md には「403エラー79件」と記載されているが、**実測値は Python ブール `True`（HTTPステータスコードではない）**。`error:429` は HTTP 429 Rate Limit（こちらは正確）。 |
| **DLQ確認コマンド** | `ssh root@163.44.124.123 "python3 -c \"import json; d=json.load(open('/opt/shared/scripts/x_dlq.json')); print(len(d), 'items'); [print(i, x.get('format'), x.get('error')) for i,x in enumerate(d[:5])]\""` |
| **エラー種別調査コマンド** | `ssh root@163.44.124.123 "python3 -c \"import json; d=json.load(open('/opt/shared/scripts/x_dlq.json')); errors=[str(x.get('error')) for x in d]; print({e: errors.count(e) for e in set(errors)})\""` |
| **内容** | RED_TEAM（スレッド）・LINK・REPLY 等の予測/記事投稿 |
| **PVQE 影響** | **E（波及力）がボトルネック**（OPERATING_PRINCIPLES.md 診断: 「Eが最大のボトルネック。配信チャネルの拡充が最優先」） |
| **優先理由** | Xへの投稿82件が届いていない = E（波及力）直接損失 |
| **解決後の効果** | X からの流入回復（82件の予測/記事投稿が実際に届く）|
| **推奨着手アプローチ** | 1) DLQ内容確認（上記コマンド）→ 2) error:true の根本原因特定 → 3) 再試行 or 除外 → 4) 0件化 |
| **完了定義** | `x_dlq.json` が 0件、または `error:429` の 3件のみに減少 |
| **effort** | 調査込みで 30〜60分 |
| **reversible** | ✅（DLQ drain は可逆。X 投稿は送ったら取り消せないが、retry 自体は安全） |
| **blast_radius** | 小（X 投稿のみ。本番 DB・Ghost に影響なし） |

---

## REQ-011: PARSE_ERROR スキーマの根本原因調査（Month 1）

| フィールド | 内容 |
|-----------|------|
| **状態** | ⏭ Month 1 実施予定 |
| **ROI スコア** | 5 |
| **理由** | 調査フェーズが必要。Ghost自動生成 vs codeinjection_head 手動追加の切り分けが先決。調査なしに修正不可 |
| **調査内容** | Google Search Console → エンハンスメント → 構造化データ でエラー種別確認 |
| **PVQE 貢献** | V間接（構造化データ品質 → クロール効率） |
| **confidence** | Low（調査前は原因不明） |

---

## Week 1 未着手項目（ブロックなし — 次セッション実施可能）

### REQ-008: FAQPage schema（/predictions/ + /en/predictions/）

| フィールド | 内容 |
|-----------|------|
| **状態** | ⏳ Week 1（次セッション #2） |
| **ROI** | 8（Google AI Overview 掲載率向上）|
| **作業** | Ghost Admin → ページ → /predictions/ → Code injection → `<head>` に FAQPage JSON-LD 追加 |
| **推定時間** | 30分 |
| **reversible** | ✅（Ghost Admin から削除するだけ） |
| **blast_radius** | 最小（codeinjection_head 変更のみ） |
| **confidence** | High（JSON-LD テンプレートは REPRIORITIZED_TODO に記載済み） |

### REQ-006: Dataset schema — /en/predictions/（EN）

| フィールド | 内容 |
|-----------|------|
| **状態** | ⏳ Week 1（次セッション #3 — REQ-007 と同時） |
| **ROI** | 7 |
| **作業** | `prediction_page_builder.py` に Dataset JSON-LD テンプレート追加（EN ページ用） |
| **推定時間** | REQ-007 と合わせて 60分 |

### REQ-007: Dataset schema — /predictions/（JA）

| フィールド | 内容 |
|-----------|------|
| **状態** | ⏳ Week 1（次セッション #3 — REQ-006 と同時） |
| **ROI** | 8 |
| **作業** | `prediction_page_builder.py` に Dataset JSON-LD テンプレート追加（JA ページ用）+ ページ再生成 |
| **推定時間** | REQ-006 と合わせて 60分（E2Eテスト必須） |
| **reversible** | ✅（バックアップから戻せる） |
| **blast_radius** | 中（ページ再生成が必要） |

---

## Month 1 未着手項目（後回しでよい）

| REQ/ISS | 内容 | 理由 |
|---------|------|------|
| REQ-011 / ISS-013 | PARSE_ERROR根本原因調査 | 調査フェーズ必要 |
| ISS-012 | about/taxonomy ページの WebPage schema 修正 | 影響小 |
| ISS-014 | WebSite 重複削除 | PARSE_ERROR 調査後に判断 |
| ISS-015 | robots.txt AI クローラー許可 | 現状でも AI クローラーは問題なくアクセス可能 |
| ISS-016 | /en/predictions/ 言語切り替えリンク | UX 改善だが緊急性低 |

---

*作成: 2026-03-28 | Round 3 完了後 | エンジニア: Claude Code (local)*
*PVQE-E: REQ-010 が最優先（E直接支援）。REQ-002 は Stripe 接続後まで BLOCKED。*
