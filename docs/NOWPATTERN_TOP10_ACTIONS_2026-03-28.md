# NOWPATTERN TOP 10 ACTIONS — 2026-03-28
> source: FULL_PROPOSALS + GAP_ANALYSIS を基に最大ROIの10アクションを厳選
> 選定基準: impact × confidence ÷ effort（ROI順）

---

## 選定原則

```
ROI = impact × confidence ÷ effort

+ 収益直結（有料会員）
+ 即日可逆
+ 設定ミス修正（実装不要）
を優先。実装コストが大きいものは後回し。
```

---

## TOP 1: X PORTFOLIO修正（REPLY 0%）

| 項目 | 値 |
|------|-----|
| ROI | ★★★★★（最高） |
| 提案ID | P-001 |
| GAP | GAP-001 |
| 作業時間 | **30分** |
| 効果 | X投稿が1件/日 → 100件/日に回復 |
| 測定方法 | X投稿成功件数（@nowpatternのタイムライン確認） |

**実行手順:**
```bash
ssh root@163.44.124.123
# バックアップ
cp /opt/shared/scripts/x_swarm_dispatcher.py /opt/shared/scripts/x_swarm_dispatcher.py.bak-$(date +%Y%m%d)
# 変更
# PORTFOLIO["REPLY"] = 0.00
# PORTFOLIO["LINK"] = 0.35
# PORTFOLIO["NATIVE"] = 0.40
# PORTFOLIO["RED_TEAM"] = 0.25
```

**なぜ1位か:** Eが毎日ゼロな状態を即日解決できる唯一の施策。読者獲得・投票増加・有料転換の全てはX投稿が機能することが前提。

---

## TOP 2: Ghost portal_plans に monthly + yearly 追加

| 項目 | 値 |
|------|-----|
| ROI | ★★★★★ |
| 提案ID | P-003 |
| GAP | GAP-009 |
| 作業時間 | **1時間**（Stripe設定含む） |
| 効果 | 有料会員$0 → 購読可能状態に移行 |
| 測定方法 | Ghost Admin > Tiers に月額プランが表示される |

**実行手順:**
```bash
# Step 1: Stripe接続 (Ghost Admin > Settings > Memberships)
# Step 2: SQLite更新
ssh root@163.44.124.123
sqlite3 /var/www/nowpattern/content/data/ghost.db \
  "UPDATE settings SET value='[\"free\",\"monthly\",\"yearly\"]' WHERE key='portal_plans';"
# Step 3: Ghost再起動
systemctl restart ghost-nowpattern
```

**なぜ2位か:** 現在$0の収益を$0より上にできる唯一の即効策。Stripe未接続が最大の障壁だが、Ghost Admin UIから5分で接続可能。

---

## TOP 3: llms.txt EN URL修正

| 項目 | 値 |
|------|-----|
| ROI | ★★★★ |
| 提案ID | P-002 |
| GAP | GAP-003 |
| 作業時間 | **5分** |
| 効果 | AIアシスタントが正しいURLを案内できる |
| 測定方法 | `curl https://nowpattern.com/llms.txt \| grep "en/predictions"` |

**実行手順:**
```
Ghost Admin → Pages → llms.txt ページを開く
"en-predictions/" を "en/predictions/" に変更（URLが1箇所あるはず）
保存・公開
```

**なぜ3位か:** 5分で完了するのに、ChatGPT/Claude/Geminiが間違ったURLを案内し続けるのを止められる。AIアクセシビリティは2026年においてSEOの核心。

---

## TOP 4: Caddy gzip有効化

| 項目 | 値 |
|------|-----|
| ROI | ★★★★ |
| 提案ID | P-004 |
| GAP | GAP-008 |
| 作業時間 | **10分** |
| 効果 | /predictions/ 282KB → 約85KB（70%削減）。Core Web Vitals改善 |
| 測定方法 | `curl -H "Accept-Encoding: gzip" -I https://nowpattern.com/predictions/ \| grep content-encoding` |

**実行手順:**
```bash
ssh root@163.44.124.123
# Caddyfileの適切な場所に追加（nowpattern.comブロック内）
vi /etc/caddy/Caddyfile
# encode zstd gzip を追加
caddy reload --config /etc/caddy/Caddyfile
```

**なぜ4位か:** 10分で282KBのページが85KBになる。ページ速度はCore Web Vitalsに直結し、Googleランキングに影響する。

---

## TOP 5: llms-full.txt 404修正

| 項目 | 値 |
|------|-----|
| ROI | ★★★ |
| 提案ID | P-005 |
| GAP | GAP-002 |
| 作業時間 | **15分** |
| 効果 | AIエージェントが全記事リストを参照できる |
| 測定方法 | `curl -o /dev/null -w "%{http_code}" https://nowpattern.com/llms-full.txt` → 200 |

**実行手順:**
```bash
ssh root@163.44.124.123
vi /etc/caddy/Caddyfile
# nowpattern.comブロックの上部に追加（Ghost reverseproxy より前）:
# handle /llms-full.txt {
#     root * /var/www/nowpattern/content/files
#     file_server
# }
# ※llms-full.txtのサーブパスはGhostの設定に依存。まず場所を確認する
caddy reload
```

**なぜ5位か:** AIクローラーがllms.txtとllms-full.txtの両方を確認する。full版が404だとAIエージェントへの情報提供が不完全。

---

## TOP 6: np-scoreboard / np-resolved ID追加

| 項目 | 値 |
|------|-----|
| ROI | ★★★ |
| 提案ID | P-006 |
| GAP | GAP-004 |
| 作業時間 | **30分** |
| 効果 | デザインシステム準拠。ページ内アンカーリンクが機能する |
| 測定方法 | `curl https://nowpattern.com/predictions/ \| grep -c 'np-scoreboard'` → 1 |

**実行手順:**
```bash
ssh root@163.44.124.123
vi /opt/shared/scripts/prediction_page_builder.py
# スコアボードセクション: <div class="np-scoreboard-wrapper"> → <div id="np-scoreboard" class="np-scoreboard-wrapper">
# 解決済みセクション: <div class="resolved-section"> → <div id="np-resolved" class="resolved-section">
python3 /opt/shared/scripts/prediction_page_builder.py
```

---

## TOP 7: Dataset schema追加（/predictions/）

| 項目 | 値 |
|------|-----|
| ROI | ★★★★ |
| 提案ID | P-007 |
| GAP | GAP-006 |
| 作業時間 | **2時間** |
| 効果 | AI Overview掲載率向上。Googleが1,093件の予測を「独自データセット」として認識 |
| 測定方法 | Google Rich Results Test で Dataset validated |

**実行手順:**
```python
# prediction_page_builder.py の _build_page_html() で <head>に追加
dataset_schema = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "name": "Nowpattern Prediction Tracker",
    "description": f"Structured predictions with Brier Score tracking. {total_count} predictions, avg Brier Score {avg_brier:.4f}.",
    "url": "https://nowpattern.com/predictions/",
    "creator": {"@type": "Organization", "name": "Nowpattern"},
    "dateModified": datetime.now().strftime("%Y-%m-%d"),
    "variableMeasured": "Brier Score"
}
```

---

## TOP 8: FAQPage schema追加（記事全体）

| 項目 | 値 |
|------|-----|
| ROI | ★★★★ |
| 提案ID | P-008 |
| GAP | GAP-007 |
| 作業時間 | **2時間** |
| 効果 | AI Overview掲載率 **+60%**。質問形クエリへの出現率向上 |
| 測定方法 | Google AI Overviewsでの引用数（月次計測） |

**実行手順:**
```
Ghost Admin → Code Injection → Site Header に追加:
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Nowpatternの予測はどのように検証されますか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "全ての予測はprediction_auto_verifier.pyによって自動検証され、Brier Scoreで精度が計測されます。"
      }
    }
  ]
}
</script>
```

---

## TOP 9: Polymarketマッチング精度改善

| 項目 | 値 |
|------|-----|
| ROI | ★★★ |
| 提案ID | P-011 |
| GAP | GAP-013 |
| 作業時間 | **1日** |
| 効果 | ORACLE STATEMENTの市場確率データが充実（2件 → 50件以上） |
| 測定方法 | prediction_db.json で market_consensus が埋まっている件数 |

**実行手順:**
```python
# polymarket_sync.py のマッチングロジック改善
# Jaccard係数 0.4 → 0.3 に緩和 + 英語タイトル優先
# Nowpattern予測タイトル（JA）を英語に翻訳してからPolymarket問題文と比較
```

---

## TOP 10: DLQ 79件をNATIVEコンテンツに変換

| 項目 | 値 |
|------|-----|
| ROI | ★★★ |
| 提案ID | P-010 |
| GAP | GAP-001（派生） |
| 作業時間 | **2時間** |
| 効果 | 蓄積したDLQコンテンツ79件をNATIVEスレッドとして再活用 |
| 測定方法 | x_dlq.jsonが空になる / @nowpatternのタイムライン確認 |

**実行手順:**
```python
# x_dlq.py（新規作成）
# x_dlq.json を読み込み → format=REPLYをformat=NATIVEに変換
# x_queue.json に追加（P-001完了後に実行）
```

---

## 実装優先順（マスタースケジュール）

```
Day 0（今すぐ）:
  TOP 3: llms.txt URL修正           → 5分
  TOP 4: Caddy gzip有効化           → 10分
  TOP 5: llms-full.txt 404修正      → 15分
  TOP 1: X PORTFOLIO修正            → 30分
  TOP 6: np-scoreboard ID追加       → 30分
  TOP 2: Ghost portal_plans修正     → 1時間（Stripe設定含む）
  合計: 約3時間で6アクション完了

Day 1〜3（今週）:
  TOP 7: Dataset schema             → 2時間
  TOP 8: FAQPage schema             → 2時間
  TOP 10: DLQ 79件変換              → 2時間
  合計: 1〜2日で3アクション完了

Day 4〜14（今月）:
  TOP 9: Polymarketマッチ改善       → 1日
  TIER C の提案群                   → 随時
```

---

## 期待される結果（10アクション完了後）

| 指標 | 現在 | 目標（10アクション後） |
|------|------|---------------------|
| X投稿/日 | 1件 | **100件** |
| AI overview引用数 | 未測定 | 向上（FAQSchema +60%） |
| llms.txt正確性 | URL誤り1件 | **エラーゼロ** |
| /predictions/ ページサイズ | 282KB | **~85KB** |
| np-scoreboard ID | 欠落 | **存在** |
| 有料会員への導線 | ゼロ | **Portalに表示** |
| Polymarketマッチ | 2件 | **50件以上** |

---

*最終更新: 2026-03-28 | source: FULL_PROPOSALS + GAP_ANALYSIS*
