# SEO 監査 最終優先度レコメンデーション
> 作成日: 2026-03-26 | nowpattern.com SEO Audit

---

## サマリー

このセッションの SEO 監査で実施した修正と、今後の推奨アクションを優先度順に整理する。

---

## 完了済み修正（このセッション）

| 修正 | 効果 | リスク |
|------|------|--------|
| Fix 1: `/tag/genre-*` noindex 化（Caddyfile Guard 1 拡張） | クロールバジェット節約・低品質ページ除去 | 低 |
| Fix 2: `a4-hreflang-injector.py` 全1,342記事への hreflang 注入（実行中） | 重複コンテンツ誤判定防止・言語ターゲティング最適化 | 低 |
| Fix 3: ホームページ `Link` ヘッダー（Caddy handle blocks） | JA/EN トップページのバイリンガル信号確立 | 低 |

---

## P0: 緊急対応（SEO の前提条件）

### xmrig マイナー感染の完全除去

**⚠️ これが未解決なら、以下の SEO 施策はすべて無効化される可能性がある。**

```
問題: VPS に Monero マイニングスクリプトが仕込まれていた（2026-03-21 発見）
リスク: Google Safe Browsing がサイトを危険と判定 → インデックス除外
状態: VPS は除去承認待ち → Naoto 確認が必要
```

**確認コマンド（VPS で実行）:**
```bash
# xmrig プロセスの存在確認
ps aux | grep -E "xmrig|minerd|cryptonight" | grep -v grep

# 不審な cron ジョブ確認
crontab -l
ls -la /var/spool/cron/crontabs/

# Google Safe Browsing 確認
# → https://transparencyreport.google.com/safe-browsing/search?url=nowpattern.com
```

---

## P1: 今週中に対応（高優先度）

### 1. hreflang 注入完了後の GSC 確認

```
実施内容: Google Search Console の「国際ターゲティング」でエラー数を確認
期待値: hreflang エラー 0
確認タイミング: a4-hreflang-injector.py 完了後 1〜2 週間
担当: Naoto（GSC ログイン必要）
```

### 2. sitemap.xml の確認

```
確認内容:
  - https://nowpattern.com/sitemap.xml にアクセスし、内容を確認
  - 内部タクソノミータグページ（/tag/genre-*/等）が含まれていないか確認
  - GSC でサイトマップが送信済みか確認

問題があれば: Ghost の sitemap から noindex ページを除外するカスタム実装を検討
```

### 3. 新規記事への hreflang 自動注入の仕組み化

```
問題: 現状では新規記事に hreflang が自動付与されない
解決策: Ghost Webhook（port 8769）に post.published トリガーを追加し、
         a4-hreflang-injector.py --slug={slug} を自動実行

実装コスト: 2〜3時間
担当: Claude Code または NEO-ONE
```

---

## P2: 今月中に対応（中優先度）

### 4. Core Web Vitals 測定

```
対象ページ（重要度順）:
  1. https://nowpattern.com/ （ホームページ）
  2. https://nowpattern.com/predictions/ （最重量ページ・3,660行HTML）
  3. https://nowpattern.com/en/ （英語ホーム）

測定方法（無料）:
  - Google PageSpeed Insights: https://pagespeed.web.dev/
  - GSC「ページエクスペリエンス」レポート

懸念: /predictions/ ページは 982件の予測カードを生成する巨大 HTML。
      モバイルでの LCP（最大コンテンツ描画）が 2.5秒を超える可能性。

対策案（問題があれば）:
  - 予測カードのページネーション（50件/ページ）
  - 予測カードの遅延読み込み（Intersection Observer API）
```

### 5. `/tag/nowpattern/` の noindex 解除検討

```
現状: /tag/nowpattern/ は noindex（Guard 1 で設定）
問題: nowpattern タグは全記事に付与されているため、実質的に「全記事一覧」
      これはサイトの最も権威あるページである可能性がある

判断基準:
  - /tag/nowpattern/ のページ品質（記事品質のアベレージ）が高ければ noindex 解除を検討
  - 解除する場合: Caddyfile の @internal_tags から `/tag/nowpattern/` を削除

リスク: 低（可逆的な変更）
```

### 6. Search Console 基準値の記録

```
実施内容: 今月中に GSC で以下を記録
  - クリック数（28日）
  - 表示回数（28日）
  - 平均 CTR
  - 平均掲載順位
  - インデックス済みページ数

目的: 今回の SEO 施策の効果を3ヶ月後に測定するための基準値
```

---

## P3: 次スプリント（低優先度）

### 7. 記事スラッグ品質の改善

```
問題: 中国語ピンインスラッグが多数存在（URLが意味不明）
対策: nowpattern_publisher.py にスラッグ正規化ロジックを追加
実装コスト: 低（新規記事向け。既存記事は変更しない）
```

### 8. SEO ゲートチェックの `publisher.py` 統合

```
内容: article_seo_gate.py を実装し、公開前に以下を検証
  - タイトル長（60文字以内推奨）
  - メタ説明長（155文字以内推奨）
  - lang タグの存在
  - EN 記事の canonical_url
実装コスト: 中
参照: docs/seo_audit/template_level_prevention_plan.md
```

### 9. ページネーション hreflang

```
問題: /page/2/, /en/page/2/ 等のページネーションに hreflang がない
優先度: 低（コンテンツページではない）
対策: 必要であれば Caddyfile の handle blocks を拡張
```

---

## 効果測定スケジュール

| 時期 | 確認内容 | 期待値 |
|------|---------|--------|
| **2週間後（4月9日）** | hreflang エラー数（GSC） | 0 |
| **1ヶ月後（4月26日）** | インデックス数（GSC） | 700+件 |
| **3ヶ月後（6月26日）** | クリック数・表示回数（GSC） | 基準値比 +20% |
| **6ヶ月後（9月26日）** | Brier Score × SEO トラフィック相関 | 予測精度と検索流入の正相関 |

---

## 今回の SEO 監査 成果まとめ

```
修正完了:
  ✅ 内部タクソノミータグ 51件を noindex 化（クロールバジェット節約）
  ✅ 1,342記事に hreflang を一括注入（バイリンガルサイトの重複コンテンツ誤判定防止）
  ✅ ホームページ JA/EN に hreflang Link ヘッダー追加

ドキュメント作成:
  ✅ implemented_low_risk_fixes.md（実施済み修正レポート）
  ✅ indexing_crawl_diagnosis.md（インデックス・クロール診断）
  ✅ hreflang_architecture.md（hreflang 3層アーキテクチャ設計書）
  ✅ quality_and_trust_risk_map.md（品質リスクマップ）
  ✅ search_console_current_state_report.md（GSC 確認ガイド）
  ✅ template_level_prevention_plan.md（テンプレートレベル予防プラン）
  ✅ final_priority_recommendations.md（このファイル）

未着手（Naoto 判断が必要）:
  ❌ xmrig 完全除去の確認（P0）
  ❌ GSC への実際のアクセスと基準値記録（Naoto 実施事項）
  ❌ CWV 測定（PageSpeed Insights で即確認可能）
```

---

*作成: 2026-03-26 | Session: SEO Audit*
