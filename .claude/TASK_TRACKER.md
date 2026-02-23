# TASK TRACKER — Nowpattern 全タスク進捗管理

> **このファイルの目的**: セッションが切れても、次のOpusがここを読めば全体状況と作業の続きが分かる。
> **更新ルール**: タスク完了ごとに即座に✅をつける。新タスク発見時は即追加。

**最終更新**: 2026-02-22 12:30 JST
**担当**: Claude Opus 4.6（ローカル）

---

## 🔴 最優先: マシン（モート自動生成システム）の未完成パーツ

Nowpatternの商品 = 「予測を構造化→自動検証→精度証明し続けるマシン」

### マシンの設計図
```
ニュース → ①力学判定 → ②3シナリオ構造化 → ③Ghost公開
  → ④prediction_db記録 → ⑤自動判定 → ⑥/predictions/反映
  → ⑦ナレッジグラフ蓄積 → ⑧フライホイール（次の予測精度向上）
```

| # | パーツ | 状態 | 作業内容 |
|---|--------|------|----------|
| ① | 力学判定 | ✅完了 | taxonomy v3.0（16力学×13ジャンル）定義済み |
| ② | 3シナリオ構造化 | ✅完了 | article_builder v3.0 |
| ③ | Ghost公開 | ✅完了 | publisher.py + Admin API（HTTPS修復済み） |
| ④ | prediction_db自動記録 | ✅完了 | breaking_pipeline_helper.py Step4で接続済み（L269-280） |
| ⑤ | 自動判定 | 🟡半完成 | prediction_verifier.py（Gemini判定+Telegram通知）存在。cron済。--auto-judgeは未有効化 |
| ⑥ | /predictions/ページ自動更新 | ✅完了 | update_predictions_page.py作成、cron登録済み（JST 15:05） |
| ⑦ | ナレッジグラフ | ✅完了 | 37記事バックフィル済み。publisher.pyにもindex更新コードあり（L594-614） |
| ⑧ | フライホイール | ✅完了 | neo_article_writer.pyにget_flywheel_context()追加。過去予測+過去記事を参照して記事精度向上 |

---

## 🟡 今日やったこと（2026-02-22、このセッション）

| # | タスク | 状態 | 備考 |
|---|--------|------|------|
| B | Ghost Admin API修復 + cron-env.sh HTTPS化 | ✅完了 | HTTP→HTTPSリダイレクトが原因だった |
| C | Schema Markup追加（Google SEO） | ✅完了 | NewsMediaOrganization + WebSite JSON-LD |
| D | x_quote_repost.py v3.0更新 | ✅完了 | リンク本文化（ペナルティ撤廃対応）、VPS同期済み |
| - | ディスクレーマー追加（Ghost footer） | ✅完了 | JA/EN二言語、Code Injection |
| - | /predictions/ ページ作成 | ✅完了 | 枠のみ。自動更新は未実装 |
| - | prediction_tracker overdue cron化 | ✅完了 | 毎日JST 9:00 |
| - | 通知スパム修正（healthcheck.sh v2） | ✅完了 | 状態変化時のみ通知に変更 |
| - | 通知スパム修正（check-neo-token.sh v2） | ✅完了 | 同上。**ただしCRLF問題で実行不可→要修正** |

---

## 🔴 未完了タスク一覧（優先順）

### Tier 1: マシン完成に必須（今日中）

| # | タスク | 状態 | 詳細 |
|---|--------|------|------|
| M1 | ④ publisher.py → prediction_tracker 自動接続 | ✅完了 | breaking_pipeline_helper.py Step4で既に接続済み |
| M2 | ⑥ /predictions/ページ自動更新スクリプト | ✅完了 | update_predictions_page.py作成、VPS配置、cron登録（JST 15:05） |
| M3 | ⑦ article_index自動登録 + 37記事バックフィル | ✅完了 | Ghost DB全37記事をindex.jsonに登録完了 |
| M4 | check-neo-token.sh CRLF修正 | ✅完了 | sed -i で改行コード修正 |
| M5 | crontab重複エントリ削除 | ✅完了 | 189行→169行（22重複削除 + predictions cron追加） |

### Tier 2: 運用品質（今日〜明日）

| # | タスク | 状態 | 詳細 |
|---|--------|------|------|
| O1 | Operations Manual更新 | ✅完了 | v3.0変更、HTTPS化、Schema等を反映済み |
| O2 | Neo間ステート共有の仕組み | ✅完了 | neo_shared_state.py作成、VPS配置済み |
| O3 | CLAUDE.md更新（ローカル↔VPS同期） | 🟡要確認 | 今日の変更がVPS側CLAUDE.mdに未反映の可能性 |

### Tier 3: オーナーから依頼済み（未着手）

| # | タスク | 状態 | 詳細 |
|---|--------|------|------|
| A | prediction_tracker cron化 | ✅完了 | overdue checkを毎日JST 9:00で登録済み |
| E | AIで稼ぐ方法の調査→記事化 | 🟡調査完了 | 調査完了（勝者総取り+PF支配+経路依存の3力学分析が最適）。記事執筆はNEOに委任 |
| F | OpenClawの最新状況確認 | ✅完了 | v2026.2.15→v2026.2.21（3バージョン遅れ）、セキュリティ修正多数、アップデート推奨 |

### Tier 4: CLAUDE.md記載の未解決課題

| # | タスク | 状態 | 詳細 |
|---|--------|------|------|
| U1 | NAVER Blog韓国語自動投稿 | 🔴未着手 | API廃止、Selenium方式、SMS認証必要 |
| U2 | Medium MEDIUM_TOKEN取得 | 🔴未着手 | スクリプト完成済み、トークン登録待ち |
| U3 | noteアカウント新規作成 | 🔴未着手 | noindex問題で新規作成検討中 |
| U4 | X APIキーローテーション | 🔴未着手 | 手動: developer.x.com → Keys再生成 |

### Tier 5: インフラ課題（発見済み）

| # | タスク | 状態 | 詳細 |
|---|--------|------|------|
| I1 | OpenClawコンテナ停止中 | 🟡要確認 | CLAUDE.mdでは稼働中と記載だが、docker psでは見えない |
| I2 | Neo2停止中（自動再起動されない） | 🟡要確認 | status=0正常終了のためRestart=alwaysが効いていない |
| I3 | Breaking Queue 104件滞留 | 🟡パイプライン停止中 | SUSPENDED-EMERGENCYのため。再開判断はオーナー |
| I4 | SUSPENDED-EMERGENCYのcron群 | 🟡判断待ち | X投稿系、Deep Pattern生成、note公開等。再開タイミングは商品完成後 |
| I5 | cron-env.sh GHOST_URL重複定義 | 🟡軽微 | 同じ値が2回定義（動作に影響なし） |

---

## 📊 VPS実態サマリー（2026-02-22 11:00時点）

- **Ghost**: 37記事 + 6ページ（published）
- **prediction_db**: 7件（全てopen、判定0件）
- **article_index**: 37件（バックフィル済み）
- **breaking_queue**: 104件滞留（99 pending + 5 article_ready）
- **稼働サービス**: Ghost, Neo1, NeoGPT
- **停止サービス**: Neo2, OpenClaw, PostgreSQL, N8N
- **cron**: 約30本稼働 + 約30本SUSPENDED（重複あり）

---

## 🔧 作業ログ（完了するたびに記録）

### 2026-02-22
- 11:00 — TASK_TRACKER.md作成、全タスク棚卸し完了
- 11:10 — M1確認: breaking_pipeline_helper.pyに既存接続あり✅
- 11:12 — M2完了: update_predictions_page.py作成、VPS配置、Ghost /predictions/ 更新成功、cron登録
- 11:15 — M3完了: Ghost DB 37記事をarticle_index.jsonにバックフィル
- 11:16 — M4完了: check-neo-token.sh CRLF修正（sed）
- 11:18 — M5完了: crontab 22重複削除（189→169行）
- 11:20 — O2完了: neo_shared_state.py作成、VPS配置、4エージェント初期状態登録
- 11:25 — ⑧完了: neo_article_writer.pyにフライホイール（get_flywheel_context）追加、VPS同期
- 11:25 — O1/E/F: バックグラウンドエージェントで並行実行中
- 12:00 — O1完了: Operations Manual更新（9項目反映）
- 12:00 — E完了: AI収益調査（勝者総取り+PF支配+経路依存が最適、記事化はNEOに委任）
- 12:00 — F完了: OpenClaw v2026.2.21（セキュリティ修正多数、Grok修正、アップデート推奨）
- 12:00 — Delta（差分）セクション設計: MAXコーチ分析完了
- 12:30 — D1完了: Delta v5.0実装（Level1+2+3骨格）
  - article_builder.py: _build_delta_section_html() + 構造化delta_dataパラメータ
  - neo_article_writer.py: find_previous_article() + build_delta_context()
  - prediction_tracker.py: probability_history初期化 + update_probability()
  - publisher.py: bottom_line + scenario_summary をarticle_indexに保存
  - ARTICLE_FORMAT.md: Delta記事フォーマット・行動心理学原則追記
  - 全4スクリプトVPS同期済み

### 🆕 新規発見タスク
| # | タスク | 状態 | 詳細 |
|---|--------|------|------|
| D1 | Delta（差分）セクション実装 | ✅完了 | Level1+2+3骨格。article_builder v5.0 + neo_writer Delta + prediction_db probability_history + publisher bottom_line保存。VPS同期済み |
| I6 | OpenClaw v2026.2.21へアップデート | 🔴未着手 | セキュリティ修正多数。docker pull + recreate |

---

> **次のセッションへ**: このファイル（.claude/TASK_TRACKER.md）を最初に読んでください。
> 全体の進捗と未完了タスクが分かります。
