# 品質とトラスト リスクマップ
> 作成日: 2026-03-26 | nowpattern.com SEO Audit

---

## リスク評価マトリクス

| リスク | 深刻度 | 発生確率 | 優先度 | 状態 |
|--------|--------|---------|--------|------|
| 内部タクソノミータグのインデックス | 中 | 高 | P1 | ✅ 修正済み |
| hreflang 未実装（全記事） | 高 | 確実 | P1 | 🔄 修正中 |
| ホームページ hreflang なし | 中 | 確実 | P1 | ✅ 修正済み |
| 記事品質のばらつき（AI生成） | 高 | 中 | P2 | 未着手 |
| 薄いコンテンツ（短文記事） | 中 | 低 | P3 | 監視中 |
| 外部リンク品質（被リンク） | 中 | 不明 | P3 | 未評価 |
| Core Web Vitals | 低 | 中 | P4 | 未計測 |

---

## P1: 修正済み・修正中リスク

### 1.1 内部タクソノミータグのインデックス化
**修正**: Guard 1 拡張（`/tag/genre-*` を noindex 追加）

**リスクが存在した理由**:
- `genre-geopolitics`, `genre-economy` 等のタグページが Google に公開されていた
- これらは記事分類用の内部ツールであり、読者向けコンテンツではない
- Googlebotがこれらを低品質ページとしてスコアリングする可能性

**修正後の状態**:
```
X-Robots-Tag: noindex, follow
```
全 `/tag/genre-*`, `/tag/p-*`, `/tag/event-*`, `/tag/lang-*` が noindex 化済み

---

### 1.2 hreflang の全記事への展開
**修正**: a4-hreflang-injector.py 実行（70/1342 → 670/1342 完了）

**リスクが存在した理由**:
- バイリンガルサイトで hreflang がないと、Google が JA/EN 記事を互いの「重複コンテンツ」と判断する可能性
- Google が「どちらをメインにすべきか」を判断できず、クロール効率が低下
- 異言語ユーザーに誤ったページが表示される（例: 日本人に英語ページが表示）

---

## P2: AI生成コンテンツの品質リスク

### 現状
- 1,342記事のほぼ全てが AI 生成（NEO-ONE/NEO-TWO）
- Google は 2024年以降、AI生成コンテンツ自体を直接ペナルティの対象にはしないが、
  **品質が低い AI コンテンツはスパムポリシー違反になりうる**

### nowpattern.com の強み（リスク軽減要因）
1. **独自の予測データ**: 982件の予測 + Brier Score は他サイトにはない独自情報
2. **Deep Pattern フォーマット**: 単純要約ではなく力学分析 + シナリオ設計
3. **バイリンガル**: 同一コンテンツの JA/EN は hreflang で明示
4. **トラックレコード**: 予測の当たり外れを公開している透明性

### 残存リスク
- 記事タイトルが機械的（スラッグが中国語ピンインになっている記事が多い）
- 同一トピックへの高頻度更新が「スパム的行動」と判断されるリスク

---

## P3: コンテンツ薄さリスク

### 短文・薄いコンテンツ
Ghost の `article_validator.py` が以下を強制しているため、最小品質は担保されている:
- 必須マーカー 6種（np-fast-read, np-signal, np-between-lines, np-now-pattern, np-open-loop, np-tag-badge）
- 不足時: draft 降格

ただし、長さの最低値は設定されていない。極端に短い記事が存在する可能性がある。

---

## P4: Core Web Vitals（未評価）

### 懸念点
- `/predictions/` ページは 3,660行のPythonで生成される大型HTMLページ
- 予測カード × 982件のレンダリングコスト
- モバイルでの表示速度未測定

### 推奨測定コマンド
```bash
# PageSpeed Insights API 経由（要 API KEY）
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://nowpattern.com/&strategy=mobile"
```

---

## セキュリティ × SEO 交差リスク

### xmrig マイナー感染（2026-03-21 発見）
- VPS に Monero マイニングスクリプトが仕込まれていた
- **SEO への影響**: Google Safe Browsing がサイトを危険と判定するとインデックス除外
- **現状**: VPS は除去承認待ち → Naoto 確認が必要
- **優先度**: P0（最高）— これが未処理なら他の SEO 施策の効果が無効化される

⚠️ **xmrig 問題が未解決の場合、SEO 改善の優先順位は下がる**

---

## 今後の監視計画

| 指標 | 頻度 | 方法 |
|------|------|------|
| インデックス数 | 週次 | Google Search Console |
| Brier Score | 週次 | evolution_loop.py 自動 |
| サイト健全性 | 日次 | site_health_check.py（VPS cron） |
| hreflang エラー | 月次 | GSC の国際化レポート |
| Core Web Vitals | 月次 | PageSpeed Insights |

---

*作成: 2026-03-26 | Session: SEO Audit*
