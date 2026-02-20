# Nowpattern 記事フォーマット — 完全ガイド

> 最終更新: 2026-02-20
> **記事執筆責任者: NEO-ONE, NEO-TWO**
> 参照: Jarvis（指示出し）、その他エージェントは内容確認のみ

---

## 🚨 絶対ルール（違反禁止）

1. **記事フォーマットはDeep Pattern一択**（Speed Logは廃止）
2. **タイトルに「観測ログ」「Speed Log」「Deep Pattern」は書かない**
3. **タイトルに番号（#0011 等）は入れない**
4. **フッターに `Tags: ...` の行を入れない**（スクリプトが自動追加するため）
5. **タイトルは「事実 + 独自インパクト」形式**で60文字以内を目指す

---

## 言語ルール（日本語 / 英語）

**記事の言語は1本まるごと統一する。混在禁止。**

| 記事の言語 | タイトル | タグ（ジャンル/イベント/力学） | 本文 |
|-----------|---------|--------------------------|------|
| **日本語記事** | 日本語 | 日本語タグ（例: `#地政学・安全保障`） | 日本語 |
| **英語記事** | English | English tags（例: `#Geopolitics`） | English |

### 英語タグ対応表

| 日本語タグ | English tag |
|-----------|-------------|
| 政治・政策 | Politics & Policy |
| 地政学・安全保障 | Geopolitics |
| 経済・金融 | Economy & Finance |
| ビジネス・企業 | Business |
| テクノロジー | Technology |
| 暗号資産・Web3 | Crypto & Web3 |
| エネルギー・環境 | Energy & Environment |
| 社会・人口 | Society |
| 規制変更 | Regulatory Change |
| 司法・制裁 | Sanctions & Law |
| 選挙・政権 | Elections & Power |
| 市場変動 | Market Shift |
| 技術進展 | Tech Breakthrough |
| プラットフォーム支配 | Platform Power |
| 規制の捕獲 | Regulatory Capture |
| 物語の覇権 | Narrative Control |
| 対立の螺旋 | Escalation Spiral |
| 同盟の亀裂 | Alliance Fracture |
| 経路依存 | Path Dependency |
| 制度の劣化 | Institutional Decay |
| 協調の失敗 | Coordination Failure |
| モラルハザード | Moral Hazard |
| 危機便乗 | Crisis Exploitation |
| 後発逆転 | Leapfrog |
| 勝者総取り | Winner-Takes-All |

---

## Deep Pattern — 唯一の記事フォーマット

**目標: 6,000〜7,000語 / 読了20-30分**

### 構造（7セクション固定）

```
1. タグバッジ（ジャンル/イベント/力学）
2. Why it matters（2〜3文）
3. What happened（事実5〜8項目）
4. The Big Picture（歴史的文脈 + 利害関係者マップ + データ + The delta）
5. NOW PATTERN（力学分析 × 2 + 力学の交差点）
6. Pattern History（過去の並行事例 × 2）
7. What's Next（3シナリオ + トリガー）
```

### nowpattern_article_builder.py での呼び出し方

```python
from nowpattern_article_builder import build_deep_pattern_html

html = build_deep_pattern_html(
    title="EUがAppleに2兆円の制裁金を課した構造 — プラットフォーム支配の終わりの始まり",
    why_it_matters="...",
    facts=[("2026年2月", "EUがAppleに18億ユーロの制裁金を正式決定"), ...],
    big_picture_history="過去30年間、AppleはApp Storeという場を独占し...",
    stakeholder_map=[
        ("Apple", "イノベーション保護", "収益構造維持", "$85B/年エコシステム", "手数料収入30%減"),
    ],
    data_points=[("$85B", "App Store年間取引額"), ...],
    delta="表面上はEU vs Appleに見えるが、本質は「プラットフォーム税は誰が決めるのか」という権力の問題だ。",
    dynamics_tags="プラットフォーム支配 × 規制の捕獲",
    dynamics_summary="場を持つ者がルールを書き、規制者を取り込む構造が限界に達した。",
    dynamics_sections=[
        {
            "tag": "プラットフォーム支配",
            "subheader": "App Store税の構造",
            "lead": "Appleはアプリ配信という場を独占し...",
            "quotes": [("Appleの手数料は...", "Reuters, 2026-02-18")],
            "analysis": "この引用が示しているのは...",
        },
        {
            "tag": "規制の捕獲",
            "subheader": "EUが30年かけて気づいたこと",
            "lead": "規制当局が...",
            "quotes": [],
            "analysis": "...",
        },
    ],
    dynamics_intersection="2つの力学が交差する点は...",
    pattern_history=[
        {"year": 2020, "title": "Google独禁法訴訟", "content": "DOJがGoogleを...", "similarity": "プラットフォーム支配の構造が同一"},
    ],
    history_pattern_summary="歴史が示すのは...",
    scenarios=[
        ("基本", "55-65%", "Appleが手数料を22%に引き下げ...", "手数料引き下げに備えApple依存度を下げるPF構築"),
        ("楽観", "15-25%", "各国がEUに追随し...", "規制関連銘柄への投資を検討"),
        ("悲観", "15-25%", "Appleが上訴で勝利し...", "DMA関連の投資判断を保留"),
    ],
    triggers=[("Apple上訴判決", "2026年Q4に欧州裁判所の判断。勝敗でシナリオが確定")],
    genre_tags="テクノロジー / 経済・金融",
    event_tags="司法・制裁 / 標準化・独占",
    source_urls=[("EU公式プレスリリース", "https://ec.europa.eu/...")],
)
```

---

## タイトルの書き方

**公式: `[固有名詞 + 出来事] — [独自の視点/インパクト]`（60文字以内）**

| ❌ NG | ✅ OK |
|------|------|
| `[観測ログ #0011] 米・イスラエルが...` | `米・イスラエルのイラン制裁強化 — 焦点は中国への原油遮断と米中経済戦争の新戦線` |
| `【観測ログ】ハイパーリキッドが...` | `HyperliquidがDCにロビー団体設立 — DeFiが「規制される側」から「規制を書く側」へ` |

---

## タグ付けルール

### ジャンル（1〜2個）
政治・政策 / 地政学・安全保障 / 経済・金融 / ビジネス・企業 / テクノロジー / 暗号資産・Web3 / エネルギー・環境 / 社会・人口

### イベントタグ（1〜2個）
規制変更 / 司法・制裁 / 選挙・政権 / 地政学・安全保障 / 公共政策・税制 / 市場変動 / 資本移動・投資 / 技術進展 / セキュリティ・事故 / 標準化・独占

### 力学タグ（1〜2個）
プラットフォーム支配 / 規制の捕獲 / 物語の覇権 / 対立の螺旋 / 同盟の亀裂 / 経路依存 / 制度の劣化 / 協調の失敗 / モラルハザード / 危機便乗 / 後発逆転 / 勝者総取り

---

## よくある間違い

| ミス | 正しい対応 |
|------|-----------|
| Speed Log形式で書いた | Speed Logは廃止。全てDeep Patternで書く |
| タイトルに「観測ログ #XXXX」を入れた | タイトルは「事実 — インパクト」形式のみ |
| Big Pictureを省略した | 必ず歴史的文脈400語以上を入れる |
| What's Nextが1シナリオしかない | 基本/楽観/悲観の3シナリオ必須 |
| フッターに `Tags:` を手書きした | 手書き禁止。スクリプトが自動追加する |

---
*タクソノミー定義: `docs/NOWPATTERN_TAXONOMY_v2.md`*
*X投稿ルール: `docs/AGENT_WISDOM.md` セクション3*
*NEO完全指示書: `docs/NEO_INSTRUCTIONS_V2.md`*
