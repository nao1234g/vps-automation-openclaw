# NOWPATTERN GAP ANALYSIS — 2026-03-28
> source: current_system_state + current_web_research
> 構成: 現在の状態 vs 世界水準 vs 目標状態 — 差分と根本原因の特定

---

## 分析フレームワーク

各ギャップを5軸で評価:
- **重大度**: 致命的(★★★) / 高(★★) / 中(★) / 低(-)
- **可逆性**: 可逆（今すぐ直せる）/ 準可逆（1週間以内）/ 不可逆（3ヶ月以上）
- **根本原因カテゴリ**: 設定ミス / 実装漏れ / 構造的問題 / 戦略的問題

---

## BLOCK 1: 即時ブロッカー（今日機能を止めているもの）

### GAP-001: X投稿 99%停止 ★★★
| 項目 | 値 |
|------|-----|
| 現在 | 1/100件 投稿成功（1%達成率） |
| 目標 | 100件/日 |
| 根本原因 | x_swarm_dispatcher.pyのREPLY 30%が全件403エラー |
| エラー内容 | "Quoting this post is not allowed because you have not been mentioned" |
| DLQ蓄積 | 79件（全件REPLYフォーマット） |
| 可逆性 | **可逆（設定変更のみ、30分で修正可能）** |
| 重大度 | ★★★ 致命的（Eが毎日ゼロ） |
| 根本原因カテゴリ | 設定ミス（PORTFOLIO比率） |

**修正方法:**
```python
# x_swarm_dispatcher.py のPORTFOLIOを変更
PORTFOLIO = {
    "LINK":     0.35,  # 20% → 35%（+15）
    "NATIVE":   0.40,  # 30% → 40%（+10）
    "RED_TEAM": 0.25,  # 20% → 25%（+5）
    "REPLY":    0.00,  # 30% → 0%（DISABLED）
}
# DLQ 79件はNATIVE/LINKに変換して再投稿
```

---

### GAP-002: llms-full.txt 404（AIエージェントが参照不能）★★
| 項目 | 値 |
|------|-----|
| 現在 | /llms-full.txt → 301 → /llms-full.txt/ → 404 |
| 目標 | HTTP 200で全コンテンツを返す |
| 根本原因 | Caddyがextensionlessファイルにtrailing slashを付ける |
| 影響 | GPTBot/ClaudeBot等がfull contextを取得できない |
| 可逆性 | **可逆（Caddy設定変更、15分）** |
| 重大度 | ★★ 高（AIアクセシビリティに直結） |
| 根本原因カテゴリ | 設定ミス（Caddyfile） |

**修正方法:**
```
# Caddyfileに追加（llms.txtより上位に配置）
handle /llms-full.txt {
    root * /var/www/nowpattern/content/files
    file_server
}
```

---

### GAP-003: llms.txt に誤ったEN URL ★★
| 項目 | 値 |
|------|-----|
| 現在 | `https://nowpattern.com/en-predictions/` |
| 正しい値 | `https://nowpattern.com/en/predictions/` |
| 根本原因 | Ghost内部スラッグ（en-predictions）を公開URLに誤記 |
| 影響 | AIアシスタント（ChatGPT/Claude/Gemini）が間違ったURLを案内する |
| 可逆性 | **可逆（Ghost Admin APIで更新、5分）** |
| 重大度 | ★★ 高（AIアクセシビリティ） |
| 根本原因カテゴリ | 実装漏れ（URL確認ミス） |

---

## BLOCK 2: UI/UXコンプライアンス違反（デザインシステム違反）

### GAP-004: np-scoreboardとnp-resolved IDが欠落 ★★
| 項目 | 値 |
|------|-----|
| 現在 | prediction_page_builder.pyのHTML出力に`id="np-scoreboard"`, `id="np-resolved"`なし |
| デザインシステム要件 | prediction-design-system.md で両IDが必須と定義 |
| 根本原因 | prediction_page_builder.pyの実装漏れ（np-tracking-listのみ実装） |
| 影響 | ページ内アンカーリンクが壊れる / CSSセレクタが効かない |
| 可逆性 | **可逆（python編集、30分）** |
| 重大度 | ★★ 高（設計違反） |
| 根本原因カテゴリ | 実装漏れ |

---

### GAP-005: /en/predictions/ に不適切なスキーマ ★
| 項目 | 値 |
|------|-----|
| 現在 | Article schema（記事向け） |
| 正しい値 | WebPage または CollectionPage schema |
| 根本原因 | ENページがJAの記事スキーマをそのまま流用 |
| 可逆性 | 可逆（Ghost API更新） |
| 重大度 | ★ 中（SEO精度） |
| 根本原因カテゴリ | 実装漏れ |

---

## BLOCK 3: SEO・AIアクセシビリティ欠落

### GAP-006: Dataset schema なし ★★
| 項目 | 値 |
|------|-----|
| 現在 | /predictions/ にDataset schemaなし |
| 目標 | prediction_db.json全データをDataset schemaで構造化公開 |
| 根本原因 | prediction_page_builder.pyへの未実装 |
| 影響 | GoogleがNowpatternの予測データを「独自データセット」として認識しない |
| 可逆性 | **可逆（prediction_page_builder.pyに20行追加）** |
| 重大度 | ★★ 高（AI Overview掲載率に影響） |
| 根本原因カテゴリ | 実装漏れ |

---

### GAP-007: FAQPage schema なし ★★
| 項目 | 値 |
|------|-----|
| 現在 | FAQPage schemaなし |
| 目標 | 各記事の「よくある質問」セクションにFAQPage schema |
| 影響 | AI Overview掲載率 **-60%**（未実装の機会損失） |
| 可逆性 | 可逆（Ghostのcodeinjection_headで追加可能） |
| 重大度 | ★★ 高（AIO掲載率直結） |
| 根本原因カテゴリ | 実装漏れ |

---

### GAP-008: gzip/brotli圧縮なし ★
| 項目 | 値 |
|------|-----|
| 現在 | /predictions/ 282KB 非圧縮、/en/predictions/ 320KB 非圧縮 |
| 目標 | gzip圧縮時のサイズ推定 85〜95KB（約70%削減） |
| 根本原因 | Caddyfileに`encode gzip`または`encode zstd gzip`が未設定 |
| 影響 | 遅い読み込み → Core Web Vitals悪化 → ランキング低下 |
| 可逆性 | **可逆（Caddyfile 1行追加、10分）** |
| 重大度 | ★ 中（ページ速度） |
| 根本原因カテゴリ | 設定ミス |

---

## BLOCK 4: マネタイズ欠落

### GAP-009: Ghost有料プランが非表示 ★★★
| 項目 | 値 |
|------|-----|
| 現在 | `portal_plans: ["free"]` — 有料プランが一般ユーザーに非表示 |
| 正しい値 | `portal_plans: ["free", "monthly", "yearly"]` |
| Stripe連携 | 未設定（stripe_products: 0件） |
| 影響 | 有料会員ゼロ（月額$0収益） |
| 可逆性 | **可逆（Ghost SQLite更新 + Stripe設定、1時間）** |
| 重大度 | ★★★ 致命的（収益完全ゼロ） |
| 根本原因カテゴリ | 設定ミス + Stripe未接続 |

**修正方法:**
```sql
-- Ghost SQLiteで実行
UPDATE settings SET value='["free","monthly","yearly"]' WHERE key='portal_plans';
-- その後 Stripe接続 → Ghost Admin > Settings > Memberships
```

---

### GAP-010: 有料会員0人 ★★★
| 項目 | 値 |
|------|-----|
| 現在 | 0人（無料会員1人のみ） |
| 根本原因 | GAP-009（有料プラン非表示）+ 読者基盤未形成 |
| 中期目標 | 1,000無料読者 × 5%転換 = 50有料会員 × $9 = $450 MRR |
| 可逆性 | 準可逆（設定修正は即日、読者獲得は1〜3ヶ月） |
| 重大度 | ★★★ 致命的（ビジネス継続性） |
| 根本原因カテゴリ | 構造的問題（GAP-009の連鎖） |

---

## BLOCK 5: エンゲージメント欠落

### GAP-011: ユニーク投票者7人 ★★★
| 項目 | 値 |
|------|-----|
| 現在 | reader_predictions.db ユニーク投票者: 7人 |
| 目標（TIER 0完了時） | 100人以上 |
| 根本原因 | X投稿停止（GAP-001）→ トラフィックゼロ |
| 可逆性 | X修正（GAP-001）が先決。その後1〜2週間で改善 |
| 重大度 | ★★★ 致命的（予測プラットフォームの本質が機能しない） |
| 根本原因カテゴリ | 構造的問題（GAP-001の連鎖） |

---

### GAP-012: デイリーチャレンジなし ★
| 項目 | 値 |
|------|-----|
| 現在 | 読者が一方的に閲覧するだけ（非双方向） |
| 目標 | Predictle型：日次5問の確率当てゲーム |
| 根本原因 | 未実装 |
| 影響 | リピート訪問率 低下 / Xバイラル機会損失 |
| 可逆性 | 準可逆（フロントエンド実装 1〜2週間） |
| 重大度 | ★ 中（エンゲージメント向上機会） |
| 根本原因カテゴリ | 戦略的問題（TIER 1機能） |

---

## BLOCK 6: 競合差別化欠落

### GAP-013: Polymarketマッチが2件のみ ★
| 項目 | 値 |
|------|-----|
| 現在 | polymarket_sync.py稼働中だが Jaccard係数マッチが2件 |
| 目標 | 50件以上のマッチで「市場比較データ」を本格運用 |
| 根本原因 | Jaccard類似度閾値が高すぎるか、日本語vs英語の対応が不十分 |
| 影響 | ORACLE STATEMENT の「市場の予測（Polymarket）」欄が大半「未取得」 |
| 可逆性 | 準可逆（アルゴリズム改善 1〜2日） |
| 重大度 | ★ 中（差別化要素） |
| 根本原因カテゴリ | 実装漏れ |

---

### GAP-014: Ghost 5.130.6 — ActivityPub未使用 -
| 項目 | 値 |
|------|-----|
| 現在 | Ghost 5.130.6（6.0のActivityPub/ネイティブアナリティクスが未使用） |
| 目標 | Ghost 6.0にアップグレードしてActivityPub経由でBluesky/Mastodonに配信 |
| 根本原因 | アップグレード未実施 |
| 影響 | Bluesky/Mastodon経由のリーチ機会損失 |
| 可逆性 | 準可逆（アップグレード 半日） |
| 重大度 | - 低（現在の優先度では後回し） |
| 根本原因カテゴリ | 戦略的問題 |

---

## ギャップ優先度マトリクス

```
重大度           可逆性         GAP番号   推定作業時間
★★★ 致命的    可逆          001       30分    X PORTFOLIO修正
★★★ 致命的    可逆          009       1時間   Ghost portal_plans + Stripe
★★★ 致命的    構造的         010,011   1〜4週  読者基盤形成（GAP001,009修正が先）

★★  高         可逆          002       15分    Caddy llms-full.txt
★★  高         可逆          003       5分     llms.txt URL修正
★★  高         可逆          004       30分    np-scoreboard ID追加
★★  高         可逆          006       2時間   Dataset schema実装
★★  高         可逆          007       1時間   FAQPage schema実装

★   中          可逆          008       10分    gzip有効化
★   中          可逆          005       30分    ENスキーマ修正
★   中          準可逆         013       1日     Polymarketマッチ改善
★   中          準可逆         012       1週     デイリーチャレンジ実装

-   低           準可逆         014       半日    Ghost 6.0アップグレード
```

---

## 根本原因の分類（なぜこれだけギャップがあるか）

### 1. 設定ミス（Config Gap） — 即日修正可能
- X PORTFOLIO REPLY 30%設定（GAP-001）
- Ghost portal_plans=["free"]（GAP-009）
- Caddy gzip未設定（GAP-008）
- Caddy llms-full.txt未設定（GAP-002）

### 2. 実装漏れ（Implementation Gap） — 数時間で修正可能
- np-scoreboard / np-resolved ID（GAP-004）
- Dataset schema（GAP-006）
- FAQPage schema（GAP-007）
- llms.txt URL誤記（GAP-003）
- ENページスキーマ（GAP-005）

### 3. 構造的問題（Structural Gap） — ガップ修正が先決
- 有料会員0人（GAP-010）← GAP-009修正が先
- 投票者7人（GAP-011）← GAP-001修正が先

### 4. 戦略的問題（Strategic Gap） — Phase 2以降
- デイリーチャレンジ（GAP-012）
- Ghost 6.0アップグレード（GAP-014）

---

## 最重要インサイト

**GAP-001（X停止）→ GAP-011（投票者7人）→ GAP-010（有料会員0人）**

この3つは連鎖している。X投稿が復旧するだけで、読者獲得 → 投票参加 → 有料転換のフライホイールが始動する可能性がある。

**GAP-001の修正（30分作業）が最大ROI。**

---

*最終更新: 2026-03-28 | source: current_system_state + current_web_research*
