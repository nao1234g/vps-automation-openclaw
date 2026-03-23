# コンテンツルール — 唯一の正（Single Source of Truth）
<!-- [Nowpattern固有] — Ghost記事・Xハッシュタグ・配信ルール。OSレベルのルールではない。 -->

> **このファイルが全ルールの原本。他のドキュメントはここを参照するだけ。**
> 矛盾が見つかったら → このファイルが正しい。他を直す。
> CLAUDE.mdの `@.claude/rules/content-rules.md` で毎セッション自動読み込み。

---

## 1. Xハッシュタグルール（コードで強制済み）

### 必須タグ（x-auto-post.py が物理的に追加）

```python
# scripts/x-auto-post.py:21
# scripts/x_quote_repost.py:43
MANDATORY_HASHTAGS = ["#Nowpattern", "#ニュース分析"]
```

| 種類 | タグ | 必須/任意 | 強制方法 |
|------|------|----------|---------|
| ブランド | `#Nowpattern` | **必須** | コードが自動追加 |
| カテゴリ | `#ニュース分析`（JP） / `#NewsAnalysis`（EN） | **必須** | コードが自動追加 |
| 固有名詞 | 記事に登場する人名/企業名（#Apple #DeepSeek等） | **必須 1〜2個** | NEOが選ぶ |
| 合計 | 3〜4個 | | |

### 禁止

- ❌ 内部タクソノミータグ（`#後発逆転` `#プラットフォーム支配` 等）→ Ghost専用
- ❌ 数字タグ（`#17%下落` 等）→ 誰も検索しない。数字は本文に書く
- ❌ 5個以上のハッシュタグ → アルゴリズムがペナルティ

### 例

```
日本語記事: #Nowpattern #ニュース分析 #Apple #Siri
英語記事:   #Nowpattern #NewsAnalysis #Apple #Siri
```

---

## 2. Ghost記事タグルール（コードで強制済み）

### 固定タグ（全記事に自動付与）

| タグ | slug | 用途 |
|------|------|------|
| `nowpattern` | `nowpattern` | ブランド |
| `deep-pattern` | `deep-pattern` | フォーマット |
| `日本語` / `English` | `lang-ja` / `lang-en` | 言語 |

### 3層タクソノミー（taxonomy.json が唯一の定義）

```
ファイル: scripts/nowpattern_taxonomy.json
強制: scripts/article_validator.py（Layer 1）
    + scripts/nowpattern_publisher.py（Layer 2）
```

| レイヤー | 個数 | 1記事あたり | 強制方法 |
|----------|------|-------------|---------|
| **ジャンル** | 13 | 1〜2個 | article_validator.py が検証 |
| **イベント** | 19 | 1〜2個 | article_validator.py が検証 |
| **力学** | 16 | 1〜3個 | article_validator.py が検証 |

リスト外のタグ → article_validator.py が exit(1) でブロック → Telegram通知

---

## 3. 記事フォーマット（Deep Pattern v6.0）

> **v6.0（2026-03-03）**: 13セクション→8セクションに統合。言語別見出し（JA記事=日本語、EN記事=英語）。Cialdini LIKING原則追加。

### 8セクション構成（全文無料）

```
★ 全文無料（Phase 1〜）

  0. FAST READ / ファーストリード
     — 1分要約 + タグバッジ + 3シナリオ確率
     — 見出し: "⚡ FAST READ"（JA/EN共通ブランド名）

  1. シグナル — 何が起きたか / THE SIGNAL
     — 「なぜ重要か」+ 事実リスト + 歴史背景 + Delta（変化点）を統合
     — JA見出し: "📡 シグナル — 何が起きたか"
     — EN見出し: "📡 THE SIGNAL"
     — マーカー: np-signal

  2. 行間を読む / Between the Lines
     — 報道が言っていないこと（インサイダー視点）
     — JA見出し: "🔍 行間を読む — 報道が言っていないこと"
     — EN見出し: "🔍 BETWEEN THE LINES"
     — マーカー: np-between-lines

  3. NOW PATTERN
     — 力学分析 × 2 + 交差点
     — 見出し: "NOW PATTERN"（JA/EN共通）
     — マーカー: np-now-pattern

  4. パターンの歴史 / Pattern History
     — 過去の並行事例 × 2（歴史的基準率）
     — JA見出し: "📚 パターンの歴史"
     — EN見出し: "📚 PATTERN HISTORY"

  5. 次のシナリオ / What's Next
     — 楽観/基本/悲観シナリオ × 確率
     — JA見出し: "🔮 次のシナリオ"
     — EN見出し: "🔮 WHAT'S NEXT"

  6. 追跡ループ / Open Loop
     — 次のトリガー + 追跡テーマ
     — + LIKING要素: "あなたはどう読みますか？ 予測に参加 →"
     — JA見出し: "🔄 追跡ループ"
     — EN見出し: "🔄 OPEN LOOP"
     — マーカー: np-open-loop

  7. オラクル宣言 / Oracle Statement
     — 予測追跡ボックス（prediction_db連動記事は必須）
     — JA見出し: "🎯 オラクル宣言"
     — EN見出し: "🎯 ORACLE STATEMENT"
     — マーカー: np-oracle
```

**Phase 1（月1〜3）= 全文無料。Phase 2（月4〜）で有料化。**

### v6.0 必須マーカー（フォーマットゲートが強制）

```
np-fast-read     — FAST READセクション
np-signal        — シグナルセクション（v6.0新規）
np-between-lines — 行間を読むセクション
np-now-pattern   — NOW PATTERNセクション（v6.0新規）
np-open-loop     — 追跡ループセクション
np-tag-badge     — タグバッジ
```

**これら6マーカーが欠けた記事は `nowpattern_publisher.py` が強制的にDRAFTに降格する。**

### 12. ORACLE STATEMENT — 予測追跡ボックス（必須条件あり）

**prediction_dbに登録した予測がある記事は、記事末尾に必ずこのボックスを挿入すること。**
（予測のない記事はスキップ可。Quick Predictionカードのある記事も必須。）

**フォーマット（コピペ用）:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ORACLE STATEMENT — この予測の追跡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
判定質問: [resolution_question_ja]
Nowpatternの予測: [our_pick] — [our_pick_prob]%確率
市場の予測（Polymarket）: [market_consensus.probability]%（[市場の質問]）
判定日: [triggers[0].date]
的中条件: [hit_condition_ja]
↳ この予測を追跡: nowpattern.com/predictions/#[prediction_id]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**フィールドの埋め方:**

| プレースホルダー | 取得元 |
|----------------|-------|
| `resolution_question_ja` | prediction_db の `resolution_question` 日本語フィールド |
| `our_pick` | prediction_db の `our_pick`（YES/NO/具体的予測） |
| `our_pick_prob` | prediction_db の `our_pick_prob`（0〜100の整数） |
| `market_consensus.probability` | prediction_db の `market_consensus.probability` |
| `triggers[0].date` | prediction_db の `triggers[0].date` |
| `hit_condition_ja` | prediction_db の `hit_condition` 日本語フィールド |
| `prediction_id` | prediction_db の `prediction_id`（例: NP-2026-0042） |

**⚠️ 必須ルール（このルールを破ると読者が迷子になる）:**
- リンクは必ず `nowpattern.com/predictions/#[prediction_id_lowercase]` の形式にする
- `prediction_id` は **必ず小文字** に変換してアンカーIDとして使う（ページHTML側が `.lower()` でID生成するため）
  - DBの値: `NP-2026-0042` → リンクで使う値: `np-2026-0042`（小文字）
  - ✅ 正: `nowpattern.com/predictions/#np-2026-0042`
  - ❌ 誤: `nowpattern.com/predictions/#NP-2026-0042`（大文字はアンカー不一致で404）
- ❌ 禁止: `nowpattern.com/predictions/` のみ（ページトップに飛ぶだけで何も見つからない）
- ❌ 禁止: `prediction_id` を省略または推測で書く

**Polymarket情報がない場合:** 「市場の予測（Polymarket）: 未取得」と書く。
**複数予測がある場合:** ボックスを複数並べる（それぞれ異なる prediction_id を使う）。

**prediction_id の確認方法:**
```bash
# VPSで実行
python3 -c "import json; db=json.load(open('/opt/shared/scripts/prediction_db.json')); [print(p['prediction_id'], p.get('title','')[:40]) for p in db['predictions'][-10:]]"
```

---

## 4. X投稿ルール — X Swarm Strategy

> **原則: Qを下げるな。フォーマットを分散させて100投稿をスパムではなく情報シャワーにする。**
> 強制: `x_swarm_dispatcher.py` が比率を物理制御。

### Content Portfolio（4フォーマット × 100投稿/日）

| フォーマット | 比率 | 件数/日 | 目的 | Xアルゴリズム効果 |
|-------------|------|---------|------|------------------|
| **LINK** | 20% | 20件 | nowpattern.comへの誘導 | クリック=いいねの11倍 |
| **NATIVE** | 30% | 30件 | リンクなし長文/スレッド。滞在時間特化 | 滞在時間→Grok評価↑ |
| **RED-TEAM** | 20% | 20件 | NEO同士の討論をそのまま投稿 | 会話=いいねの150倍 |
| **REPLY/QRT** | 30% | 30件 | トレンドニュースへの引用/分析リプライ | プロフィールクリック=12倍 |

### フォーマット詳細

**LINK型（20件/日）:**
- Ghost記事リンク + 力学分析の1行フック
- 予測確率を含む投稿には**Poll自動付与**（「AIは70%と予測。あなたは？」）
- `x_quote_repost.py` が処理

**NATIVE型（30件/日）:**
- リンクなし。予測の力学と結論だけを長文 or スレッド（3〜5ツイート）で展開
- スレッドは単発ツイートの**3倍のエンゲージメント**
- 画像付き（サムネイル/チャート）= テキストonly比+30%リーチ

**RED-TEAM型（20件/日）:**
- 2つの立場でシナリオを論じるスレッド形式
- 「予測は70%でYES — しかし30%のNOシナリオはこうだ」
- 読者の反論リプライを誘発 → 会話スコア150倍ブースト
- **Poll併用**: 「あなたはどちら？ YES / NO」

**REPLY/QRT型（30件/日）:**
- トレンドニュースへの高度な分析引用リポスト
- 有力アカウントへの賛同リプライ（議論禁止）
- Grokが検出する「建設的な会話への貢献」= リーチ向上

### コンテンツパターン（3種、フォーマットと組み合わせ）

| パターン | 使うとき | 最適フォーマット |
|----------|---------|----------------|
| P1 好奇心ギャップ型 | 新規トピック（デフォルト） | NATIVE, LINK |
| P2 差分提示型 | 前回記事あり、確率が変わった | RED-TEAM, LINK+Poll |
| P3 損失回避型 | 投資/行動判断直結 | NATIVE(スレッド), REPLY |

### Poll自動付与ルール（x_swarm_dispatcher.pyが強制）

```
条件: prediction_db.json に紐づく予測がある投稿
形式: X API v2 POST /2/tweets { poll: { options: [...], duration_minutes: 1440 } }
選択肢: 最大4つ（楽観/基本/悲観 + 「記事で確認」）
時間: 24時間（1440分）
```

### ボット対策（Swarm版）

- ランダム間隔 **5〜15分**（フォーマット混在がスパム相殺）
- 深夜投稿禁止（22:00-08:00 JST）
- **4フォーマットの混在が最大の防御**（同一パターンの連続投稿を禁止）
- 連続3投稿以上の同一フォーマット → 自動でフォーマット切替
- Rate Limit 429 → DLQ（Dead Letter Queue）に退避、次サイクルで再試行
- X Premium+を前提（アルゴリズム優遇 + Rate Limit緩和）

### DLQ（Dead Letter Queue）再試行

```
失敗投稿 → /opt/shared/scripts/x_dlq.json に保存
次のcronサイクル（5分後）で最大3件ずつ再試行
3回失敗 → Telegram通知（手動確認）
429 Rate Limit → 30分クールダウン後に再試行
```

---

## 5. 配信ルール

| 配信先 | 件数/日 | 備考 |
|--------|---------|------|
| **Ghost** | **200本**（JP100+EN100） | JP書いたら自動翻訳でEN。翻訳はOpus 4.6（Max内） |
| **X** | **100投稿** | 拡声器 |
| **note** | **3〜5本** | シャドバン対策、投稿間隔4時間以上 |
| **Substack** | **1〜2本** | メール配信、多すぎると解除される |

---

## 6. 強制の仕組み（5層防御）

```
Layer 0: NEO指示書（プロンプト — 無視される可能性あり）
Layer 1: article_validator.py（コード — Ghost記事タグを物理ブロック）
Layer 2: publisher.py STRICT（コード — 投稿時に二重チェック）
Layer 3: x-auto-post.py MANDATORY_HASHTAGS（コード — Xハッシュタグを自動追加）
Layer 4: 投稿後監査cron（コード — 漏れた場合の安全網）
```

**ドキュメント（プロンプト）は忘れられる。コードは忘れない。**
**全てのルールはコードで強制する。ドキュメントは「なぜそうなっているか」の説明だけ。**

---

## 8. Xアルゴリズム自動監視（コードで強制）

### 仕組み

```
スクリプト: scripts/x-algorithm-monitor.py
cron: 毎朝 09:00 JST（自動実行、忘れようがない）
保存先: /opt/shared/x-analytics/tactics.json
```

| 監視項目 | 方法 | コスト |
|----------|------|--------|
| @nowpatternの投稿パフォーマンス | Grok API検索 | $5クレジット内 |
| 同ジャンルのバズ投稿パターン | Grok API検索 | 同上 |
| Xアルゴリズム変更情報 | RSS（4ブログ監視） | 無料 |

### 出力

1. **tactics.json** — 最新の投稿戦術（x-auto-post.pyが参照）
2. **Telegramレポート** — 毎朝Naotoのスマホに自動送信
3. **history/YYYY-MM-DD.json** — 日次データ蓄積（週次分析用）

### 2026年Xアルゴリズム基本ルール（常時適用）

| ルール | 理由 |
|--------|------|
| リプライ = いいねの150倍の重み | 会話を生む投稿が最優先 |
| テキスト+画像 > ビデオ（30%差） | アルゴリズムがテキスト優遇 |
| 外部リンクは本文に入れない | ペナルティ。リプライに置く |
| ポジティブ/建設的なトーン | Grokがトーン監視、攻撃的=抑制 |
| 投稿後1時間のエンゲージメントが最重要 | 初速で拡散が決まる |
| ベスト時間: 9:00-12:00, 18:00-21:00 JST | 平日のゴールデンタイム |
| X Premium必須 | 無料アカウントはリーチ激減 |

---

## 7. このファイルの参照元

| ファイル | 何を参照しているか |
|----------|-------------------|
| `.claude/FLASH_CARDS.md` | Xハッシュタグルール → ここのセクション1 |
| `docs/PIPELINE_ARCHITECTURE.md` | 全ルール → ここを参照 |
| `docs/NEO_INSTRUCTIONS_V2.md` | タグ/X投稿 → ここのセクション1-4 |
| `docs/AGENT_WISDOM.md` | ハッシュタグ → ここのセクション1 |
| `docs/NOWPATTERN_OPERATIONS_MANUAL.md` | X投稿テンプレ → ここのセクション1,4 |

**矛盾を見つけたら → このファイルが正しい → 他を修正する**

---

*最終更新: 2026-02-23 — ルール統合 + Xアルゴリズム監視追加*
