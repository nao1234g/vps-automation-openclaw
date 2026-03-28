# CTRスニペット改善計画（CTR Snippet Fixes）

> 作成: 2026-03-28 | 担当: LEFT_EXECUTOR
> 前提: Google Search Console への直接APIアクセスなし。分析はコンテンツ構造 + SEO原則に基づく。

---

## 重要な前提（データ制約の明示）

**現セッションでは Google Search Console への直接アクセスは実施していない。**
GSCのクリック数・表示回数・CTR・掲載順位の実データは取得できていない。

本ファイルは以下に基づく改善計画：
- 既存コンテンツのタイトル・フォーマットの構造分析
- CTR改善の一般的なSEOベストプラクティス
- nowpatternの記事フォーマット（Deep Pattern v6.0）の弱点分析

**実データを使った改善を行うには、Naotoが GSC にログインして以下を確認すること：**
- 「検索パフォーマンス」→ 「クエリ」でインプレッション上位100件を確認
- CTR 2%以下かつ表示回数100回以上の URL を特定
- その URL のタイトル / meta description を改善対象とする

---

## 現状の構造的弱点

### 1. タイトルの末尾切れ問題

現在のEN記事タイトルに「—」（em dash）を多用し、後半が切れる。
Googleのタイトル表示上限は約55〜60文字。

**問題例（実際のスラッグから推測）：**
```
"The Shock of the Danish General Election — The Collapse of..."
→ Google では "The Shock of the Danish General Election — The Col..." で切れる
→ 「of」で終わることで内容が伝わらない
```

**改善方針：**
- 重要情報を前半55文字に集約する
- em dashより前で意味が完結するタイトル構造にする
- 例: `Denmark Election Collapse: Green Party Falls as Security Tops Agenda`

### 2. meta descriptionの欠如

Ghost CMSはmeta descriptionを自動生成しない（空白）。
Googleが本文の冒頭を自動抽出するが、記事冒頭は「⚡ FAST READ」見出しから始まり、
スニペットとして意味をなさない可能性が高い。

**改善方針：**
Ghost Admin APIで各記事に`custom_excerpt`（Ghost でのmeta description）を設定する。
推奨長: 120〜155文字。

```python
# 実装案（Ghost Admin API）
payload = {
    "posts": [{
        "id": post_id,
        "custom_excerpt": "Force 5 analysis of {topic}: {key_insight}. {probability}% probability assessed.",
        "updated_at": updated_at_iso
    }]
}
```

### 3. 数値・確率を含まないタイトル

nowpatternの差別化はBrier Score/確率値。
しかしタイトルに「70%確率」「Brier 0.15」等の数値が含まれない記事が多い。

**改善方針：**
予測記事のタイトルに確率を含める（一部記事のみ）。
例: `US-China Standoff: 65% Chance of Escalation by Q3`

### 4. ENタイトルに¥記号

例: `Bitcoin Predicted to Surpass ¥15 Million`
英語記事に日本円記号（¥）を含めることで、英語圏ユーザーのCTRが下がる可能性。

**改善方針：**
EN記事の通貨表記: ¥ → `JPY` or `$XX million (JPY 15M)` 等に変更。

---

## 高優先度改善ターゲット（GSCデータなしの推定）

### 予測記事（prediction_db紐付き）

予測に関連する記事は検索意図と合致しやすい。
以下のタイトルパターンが CTR を改善しやすい：

| パターン | 例 |
|---------|-----|
| `[トピック]: X% Probability of [結果] by [日付]` | `Taiwan Strait: 65% Probability of Military Incident by Q4` |
| `Why [有名機関] Is Wrong About [トピック]` | `Why the IMF Is Wrong About Japan's Inflation Trajectory` |
| `[数値] Signs That [予測]` | `5 Signs That Bitcoin Will Cross ¥20M This Quarter` |
| `[トピック] vs [比較対象]: Who Wins?` | `US vs China in South China Sea: Naval Balance by 2027` |

### 地政学記事（geopolitics タグ）

- 現在のタイトルは「力学分析」を示すが、検索クエリとのミスマッチがある可能性
- 改善: クエリと一致する具体的な地名・人名・出来事を前半に置く

### 暗号資産記事（crypto タグ）

- Brier Score分析で最弱カテゴリ（0.3334 POOR）
- タイトル精度改善と並行してコンテンツ品質改善が必要

---

## 実行すべきCTR改善アクション（優先度順）

| 優先度 | アクション | 実施方法 | 証跡 |
|--------|-----------|---------|------|
| **P1** | GSCで表示回数100回以上かつCTR 2%以下のURLを特定 | GSCログイン（Naoto） | GSCスクショ |
| **P1** | 特定記事にcustom_excerpt（meta description）を設定 | Ghost Admin API | API response 200 |
| **P2** | ENタイトルの¥記号 → JPY表記に変換 | publisher.pyで変換 | SQLiteクエリ確認 |
| **P2** | タイトル55文字以内に重要情報を収める | 新記事生成ルール追加 | 記事サンプル確認 |
| **P3** | 確率数値をタイトルに含める（予測記事） | NEO指示書更新 | 記事サンプル確認 |

---

## meta description設定スクリプト（設計案）

```python
# /opt/shared/scripts/set_meta_descriptions.py（設計案 — 未実装）
"""
Ghost Admin APIでcustom_excerpt（meta description）を一括設定。

手順:
1. 全EN published記事を取得
2. custom_excerptが空のものを抽出
3. タイトルから155文字以内のdescriptionをClaude Opus 4.6で生成
4. Ghost Admin API PATCHで更新

注意: 1記事あたり1 API call → 1130記事に約10〜20分
"""
```

**実装の前提条件：**
- [ ] GSCでターゲット記事URLリストを取得（Naoto実施）
- [ ] タイトルフォーマット改善ルールをNEO指示書に反映
- [ ] 1バッチあたりの記事数制限（APIレート制限考慮）

---

## 現状スコア（推定）

| 指標 | 推定値 | 根拠 |
|------|--------|------|
| 平均CTR | 不明 | GSCアクセスなし |
| meta description設定率 | ~0% | Ghost自動生成なし・custom_excerpt未設定 |
| タイトル55文字以内率 | ~40% | サンプル10件目視確認 |
| ¥記号含有EN記事率 | ~5% | SQLiteサンプル確認 |

---

## GSCアクセス後の必須アクション（Naoto実施）

```
1. GSC「検索パフォーマンス」→ 期間:過去28日 → ページ別表示
2. 「クリック数」「表示回数」「CTR」「掲載順位」を全ページCSVでエクスポート
3. CSVを /opt/shared/reports/gsc_performance_YYYYMMDD.csv で保存
4. 次のセッションでClaude Codeに渡す → 自動分析 + meta description生成

期待される成果:
- 表示回数上位100ページのCTR改善
- meta description設定による +1〜3% CTR改善（業界平均）
```

---

*作成: 2026-03-28 | LEFT_EXECUTOR*
*GSC実データ取得後に更新予定*
