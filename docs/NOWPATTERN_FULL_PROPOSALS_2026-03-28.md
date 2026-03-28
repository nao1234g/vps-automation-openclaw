# NOWPATTERN FULL PROPOSALS — 2026-03-28
> source: current_system_state + current_web_research + inferred_strategy
> 全提案をGAP番号と紐付けて分類

---

## 提案分類スキーマ

| 列 | 説明 |
|----|------|
| category | fix / growth / monetize / ai-access / ux / infra |
| impact | H（高）/ M（中）/ L（低） |
| effort | H（大）/ M（中）/ S（小）/ XS（極小） |
| confidence | 実装で効果が出ると確信できる度合い（0〜100%） |
| urgency | 今すぐ / 今週 / 今月 / 次フェーズ |
| reversible | yes / no / partial |
| gap | 対応するGAP番号 |
| expected_outcome | 実装後に期待される状態 |
| measurable_metric | 効果を測定するKPI |
| concrete_next_step | 次に実行する具体的コマンド/アクション |

---

## TIER A: 今すぐ実装すべき（即日・高効果）

### P-001: X PORTFOLIO REPLY → 0% に変更
```
category:                fix
impact:                  H（投稿量99%回復）
effort:                  XS（設定変更10行、30分）
confidence:              95%
urgency:                 今すぐ
reversible:              yes
gap:                     GAP-001
expected_outcome:        100件/日の投稿が再開。DLQ 79件をNATIVE/LINKに変換して再投稿
measurable_metric:       X投稿成功件数/日（目標 100件）
concrete_next_step:      ssh root@163.44.124.123
                         vi /opt/shared/scripts/x_swarm_dispatcher.py
                         PORTFOLIO["REPLY"] = 0.00
                         python3 /opt/shared/scripts/x_dlq_convert.py --to-native
```

---

### P-002: llms.txt EN URL修正（AIアクセシビリティ修正）
```
category:                ai-access
impact:                  H（AIアシスタントが正しいURLを案内できるようになる）
effort:                  XS（Ghost APIで5分）
confidence:              100%
urgency:                 今すぐ
reversible:              yes
gap:                     GAP-003
expected_outcome:        ChatGPT/Claude/GeminiがNowpatternの予測ページを正しく案内できる
measurable_metric:       curl https://nowpattern.com/llms.txt | grep "en/predictions" で確認
concrete_next_step:      Ghost Admin API PATCH /pages/en-predictions
                         codeinjection_head内のURLを en-predictions/ → en/predictions/ に変更
```

---

### P-003: Ghost portal_plans に monthly + yearly 追加
```
category:                monetize
impact:                  H（有料会員ゼロから脱出するための必須前提）
effort:                  S（SQLite更新 + Stripe設定、1時間）
confidence:              90%（Stripe設定完了が条件）
urgency:                 今すぐ
reversible:              yes
gap:                     GAP-009
expected_outcome:        Ghost Portalに有料プランが表示され、読者が購読可能になる
measurable_metric:       Ghost Admin > Members > Tiers に月額/年額が表示される
concrete_next_step:      1. Stripe Dashboardでアカウント接続
                         2. Ghost Admin > Settings > Memberships > Stripe connected
                         3. ghost.db: UPDATE settings SET value='["free","monthly","yearly"]' WHERE key='portal_plans'
                         4. Ghost再起動
```

---

### P-004: Caddy gzip圧縮有効化
```
category:                infra
impact:                  M（ページサイズ70%削減、Core Web Vitals改善）
effort:                  XS（Caddyfile 1行追加、10分）
confidence:              100%
urgency:                 今すぐ
reversible:              yes
gap:                     GAP-008
expected_outcome:        /predictions/ 282KB → 約85KB。TTFB維持またはTTFB改善
measurable_metric:       curl -I -H "Accept-Encoding: gzip" https://nowpattern.com/predictions/ | grep -i "content-encoding"
concrete_next_step:      echo 'encode zstd gzip' >> /etc/caddy/Caddyfile && caddy reload
```

---

### P-005: llms-full.txt 404修正
```
category:                ai-access
impact:                  M（AIエージェントが全記事リストを参照可能になる）
effort:                  XS（Caddy設定15分）
confidence:              85%
urgency:                 今すぐ
reversible:              yes
gap:                     GAP-002
expected_outcome:        curl https://nowpattern.com/llms-full.txt でHTTP 200を返す
measurable_metric:       curl -o /dev/null -w "%{http_code}" https://nowpattern.com/llms-full.txt == 200
concrete_next_step:      Caddyfileにhandle /llms-full.txt { file_server } を追加
```

---

### P-006: np-scoreboard / np-resolved ID追加
```
category:                ux
impact:                  M（デザインシステム準拠、アンカーリンク機能）
effort:                  S（prediction_page_builder.py 2箇所修正、30分）
confidence:              100%
urgency:                 今すぐ
reversible:              yes
gap:                     GAP-004
expected_outcome:        /predictions/#np-scoreboard がスコアボードにジャンプする
measurable_metric:       curl https://nowpattern.com/predictions/ | grep -c 'id="np-scoreboard"' == 1
concrete_next_step:      ssh + vi /opt/shared/scripts/prediction_page_builder.py
                         スコアボードdivに id="np-scoreboard" 追加
                         解決済みセクションdivに id="np-resolved" 追加
                         python3 prediction_page_builder.py --rebuild
```

---

## TIER B: 今週中に実装すべき（高効果・中作業量）

### P-007: Dataset schema追加（/predictions/）
```
category:                ai-access
impact:                  H（GoogleがNowpatternを「独自データセット」として認識）
effort:                  M（prediction_page_builder.py に30行追加、2時間）
confidence:              80%（AIO掲載率+効果は統計的に+60%）
urgency:                 今週
reversible:              yes
gap:                     GAP-006
expected_outcome:        Google Search Consoleでpredictions/*がDatasetとしてインデックスされる
measurable_metric:       Google Rich Results Test でDataset validatedと表示される
concrete_next_step:      prediction_page_builder.py の<head>セクションにJSON-LD Dataset schemaを挿入
                         {
                           "@type": "Dataset",
                           "name": "Nowpattern Prediction Tracker",
                           "description": "1,093 structured predictions with Brier Score tracking",
                           "creator": {"@type": "Organization", "name": "Nowpattern"}
                         }
```

---

### P-008: FAQPage schema追加（記事 + /predictions/）
```
category:                ai-access
impact:                  H（AI Overview掲載率+60%）
effort:                  M（Ghostのcodeinjection_headテンプレート更新、2時間）
confidence:              85%（複数の研究で+60%確認）
urgency:                 今週
reversible:              yes
gap:                     GAP-007
expected_outcome:        Google AI OverviewsでNowpatternが質問形クエリに引用される
measurable_metric:       Google AI Overviewで "nowpattern" を含む結果数
concrete_next_step:      Ghost default.hbs / page.hbs にFAQPage schema JSON-LDを追加
                         または Ghost Admin > Code Injection > Site Header に挿入
```

---

### P-009: /en/predictions/ WebPage/CollectionPage schemaに修正
```
category:                ai-access
impact:                  M（ENページのスキーマ正確性向上）
effort:                  S（Ghost APIで30分）
confidence:              75%
urgency:                 今週
reversible:              yes
gap:                     GAP-005
expected_outcome:        /en/predictions/ がCollectionPageとして正しく認識される
measurable_metric:       Google Rich Results Test でエラーなし
concrete_next_step:      en-predictions ページの codeinjection_head を更新
```

---

### P-010: X DLQ 79件をNATIVEコンテンツに変換
```
category:                fix
impact:                  H（79件の貯まった投稿資産を活用）
effort:                  M（変換スクリプト作成、2時間）
confidence:              80%
urgency:                 今週
reversible:              yes（再投稿の取り消しは可能）
gap:                     GAP-001
expected_outcome:        79件のREPLY DLQがNATIVEスレッドとして再投稿される
measurable_metric:       x_dlq.jsonの件数が0になる
concrete_next_step:      x_dlq_converter.py を作成: REPLYをNATIVEに変換してx_queue.jsonに再登録
```

---

## TIER C: 今月中に実装すべき（戦略的・中〜大作業量）

### P-011: Polymarketマッチング精度改善
```
category:                growth
impact:                  M（予測ページの「市場比較データ」が充実）
effort:                  M（polymarket_sync.py のマッチングロジック改善、1日）
confidence:              65%
urgency:                 今月
reversible:              yes
gap:                     GAP-013
expected_outcome:        2件 → 50件以上のPolymarketマッチ
measurable_metric:       prediction_db.json の market_consensus が埋まっている件数
concrete_next_step:      Jaccard閾値を下げる + 英語タイトルとPolymarket問題文の類似度比較に切り替え
```

---

### P-012: 個人キャリブレーション画面（TIER 1）
```
category:                growth
impact:                  H（読者リテンション、Superforecaster育成）
effort:                  H（フロントエンド実装、1〜2週間）
confidence:              70%
urgency:                 今月
reversible:              yes
gap:                     GAP-012（派生）
expected_outcome:        reader_predictions.db のデータが個人プロフィールページで可視化される
measurable_metric:       登録ユーザー数 / 個人ページのセッション数
concrete_next_step:      NORTH_STAR.md TIER 1の実装開始
                         UUID → 個人ページのマッピング設計
```

---

### P-013: Predictle型デイリーチャレンジ
```
category:                growth
impact:                  M（日次リピート訪問 + Xバイラル）
effort:                  M（フロントエンド 1週間）
confidence:              60%
urgency:                 今月
reversible:              yes
gap:                     GAP-012
expected_outcome:        Xで「#Nowpatternチャレンジ」が毎日トレンドに乗る契機
measurable_metric:       日次アクティブユーザー数 / デイリーチャレンジ参加率
concrete_next_step:      /challenge/ ページ設計
                         prediction_db.jsonからランダム5問を抽出するAPIエンドポイント作成
```

---

### P-014: Grok vs Nowpattern 週次比較投稿
```
category:                growth
impact:                  M（Xアルゴリズム有利 + 差別化）
effort:                  S（投稿テンプレート作成、半日）
confidence:              70%
urgency:                 今月
reversible:              yes
gap:                     — （新規戦略）
expected_outcome:        Xでの「Grok言及」でアルゴリズムブースト獲得
measurable_metric:       Grok言及投稿のエンゲージメント率 vs 非言及投稿比較
concrete_next_step:      Grok APIで同一予測トピックを照会 → 「NowpatternのAI vs Grok」を週次ツイート
```

---

### P-015: Nowpattern Premiumティアの有料コンテンツ設計
```
category:                monetize
impact:                  H（MRR構築の本質）
effort:                  M（コンテンツ設計 + Ghost Tiers設定、3日）
confidence:              60%
urgency:                 今月（P-003完了後）
reversible:              partial（コンテンツ設計は可逆、Stripe接続は半可逆）
gap:                     GAP-009派生
expected_outcome:        $9/月 Premiumティアで差別化コンテンツを提供開始
measurable_metric:       有料会員数 / MRR
concrete_next_step:      Nowpattern Premium特典設計:
                         - 個人予測トラックレコード（TIER 1）
                         - 週次「AI vs 読者」詳細レポート
                         - 解決時メール通知
                         - 月次キャリブレーションレポート
```

---

### P-016: Ghost 6.0アップグレード（ActivityPub）
```
category:                growth
impact:                  M（Bluesky/Mastodon経由のリーチ拡大）
effort:                  H（アップグレード + テーマ検証、半日〜1日）
confidence:              75%
urgency:                 今月
reversible:              partial（アップグレードは基本的に前進のみ）
gap:                     GAP-014
expected_outcome:        @nowpattern@nowpattern.com でBluesky/Mastodonからフォロー可能に
measurable_metric:       ActivityPub経由のフォロワー数 / フェデレーション経由のトラフィック
concrete_next_step:      1. バックアップ取得: ghost backup
                         2. ghost update --all
                         3. テーマ・カスタムコード検証
                         4. ActivityPub設定: Ghost Admin > Settings > Social accounts
```

---

## TIER D: 次フェーズ（Phase 2以降）

### P-017: 個人Brier Score + Sharpe ratioリーダーボード
```
category:                growth
impact:                  H（Superforecaster育成、長期コミュニティ形成）
effort:                  H（バックエンド設計 + フロントエンド、3〜4週間）
confidence:              70%
urgency:                 次フェーズ（TIER 1完了後）
gap:                     GAP-012（TIER 2）
concrete_next_step:      TIER 1（個人トラックレコード）の完成が前提
```

---

### P-018: 企業予測トーナメント（Bridgewater型）
```
category:                growth + monetize
impact:                  H（メディア露出 + PR効果 + B2B収益）
effort:                  H（設計 + スポンサー獲得、2〜3ヶ月）
confidence:              50%
urgency:                 次フェーズ（リーダーボード完成後）
gap:                     —
concrete_next_step:      読者基盤1,000人以上が前提
```

---

### P-019: 公開予測API（B2B $99〜$499/月）
```
category:                monetize
impact:                  H（スケールする収益）
effort:                  H（API設計 + 料金設計 + 契約インフラ）
confidence:              55%
urgency:                 次フェーズ（TIER 4）
gap:                     —
concrete_next_step:      NORTH_STAR.md TIER 4の計画参照
```

---

## 提案サマリー（優先度順）

| ID | 提案名 | category | impact | effort | urgency |
|----|--------|---------|--------|--------|---------|
| P-001 | X PORTFOLIO REPLY→0% | fix | H | XS | 今すぐ |
| P-003 | Ghost portal_plans修正 | monetize | H | S | 今すぐ |
| P-002 | llms.txt URL修正 | ai-access | H | XS | 今すぐ |
| P-005 | llms-full.txt 404修正 | ai-access | M | XS | 今すぐ |
| P-004 | Caddy gzip有効化 | infra | M | XS | 今すぐ |
| P-006 | np-scoreboard ID追加 | ux | M | S | 今すぐ |
| P-007 | Dataset schema追加 | ai-access | H | M | 今週 |
| P-008 | FAQPage schema追加 | ai-access | H | M | 今週 |
| P-010 | DLQ 79件NATIVE変換 | fix | H | M | 今週 |
| P-009 | ENページスキーマ修正 | ai-access | M | S | 今週 |
| P-011 | Polymarketマッチ改善 | growth | M | M | 今月 |
| P-012 | 個人キャリブレーション | growth | H | H | 今月 |
| P-013 | Predictle型チャレンジ | growth | M | M | 今月 |
| P-014 | Grok vs Nowpattern投稿 | growth | M | S | 今月 |
| P-015 | Premium有料コンテンツ設計 | monetize | H | M | 今月 |
| P-016 | Ghost 6.0アップグレード | growth | M | H | 今月 |
| P-017 | Brier + Sharpeリーダーボード | growth | H | H | 次フェーズ |
| P-018 | 企業トーナメント | growth | H | H | 次フェーズ |
| P-019 | 公開API B2B | monetize | H | H | 次フェーズ |

---

*最終更新: 2026-03-28 | source: current_system_state + current_web_research + inferred_strategy*
