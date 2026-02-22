# Nowpattern Article Format Specification v4.0

> **このファイルは記事フォーマットの唯一の真実源（Single Source of Truth）です。**
> 全エージェント（NEO-ONE, NEO-TWO, Jarvis, ローカルClaude Code）はこのファイルに従うこと。
> フォーマット変更はこのファイルを更新し、他のファイルはこのファイルを参照する。
>
> 最終更新: 2026-02-21 — v4.0 Flywheel Format

---

## 必須フィールド一覧（JSONキー名）

記事JSONには以下のフィールドが**全て**必要です。空欄は公開拒否されます。

### v4.0 新規フィールド（必須）

| フィールド | 説明 | 例 |
|---|---|---|
| `bottom_line` | 記事の核心を1文で要約（3秒で理解できるレベル） | 「FRB内部のステーブルコイン推進派と反対派の権力闘争が、制度化の方向性を決める」 |
| `bottom_line_pattern` | 力学パターン名の要約 | 「通貨主権の防衛戦 × 制度化のパラドックス」 |
| `bottom_line_scenario` | 基本シナリオの一文要約 | 「制度化は進むがFRBの開放は先送り（50%）」 |
| `bottom_line_watch` | 次の注目イベント+日付 | 「2026年2月27日のウォーレン議員回答期限」 |
| `between_the_lines` | 報道が「言っていないこと」を1段落で分析 | 裏の力学、隠された意図、メディアが触れない構造的問題 |
| `open_loop_trigger` | 次にこのストーリーが動くトリガー+日付 | 「2026年5月のFRB議長交代」 |
| `open_loop_series` | このパターンの続きとして追跡すべきテーマ | 「通貨主権シリーズ: 次はECBのデジタルユーロ決定」 |

### 既存フィールド（必須）

| フィールド | 説明 |
|---|---|
| `title` | 記事タイトル（60字以内、[固有名詞+出来事] — [独自視点]形式） |
| `language` | "ja" または "en" |
| `why_it_matters` | なぜ重要か（2-3文） |
| `facts` | 事実のリスト `[["ラベル", "内容"], ...]` |
| `big_picture_history` | 歴史的背景（300語の段落テキスト） |
| `stakeholder_map` | 利害関係者 `[["アクター", "建前", "本音", "得るもの", "リスク"], ...]` |
| `data_points` | 数字で見る構造 `[["数字", "意味"], ...]` |
| `dynamics_tags` | 力学タグ（"タグ1 × タグ2"形式） |
| `dynamics_summary` | 力学を一文で説明 |
| `dynamics_sections` | 力学分析セクション（各300-500語） |
| `dynamics_intersection` | 力学の交差分析（200語） |
| `pattern_history` | 歴史的類似事例（2-3件） |
| `history_pattern_summary` | パターン史の総括 |
| `scenarios` | 3シナリオ `[["楽観", "30%", "内容", "示唆"], ["基本", "50%", ...], ["悲観", "20%", ...]]` |
| `triggers` | 注目トリガー `[["トリガー名", "日付"], ...]` |
| `genre_tags` | ジャンルタグ |
| `event_tags` | イベントタグ |
| `source_urls` | ソース `[["名前", "URL"], ...]` |
| `x_comment` | X引用リポスト用コメント（200字以内） |

---

## 記事構造（HTML出力順序）

```
1. BOTTOM LINE（TL;DR）    ← v4.0 新規
   - 1文の核心
   - パターン名
   - 基本シナリオ要約
   - 次の注目ポイント

2. タグバッジ（ジャンル/イベント/力学）

3. Why it matters（2-3文）

4. What happened（事実要約、300語）

5. The Big Picture
   - 歴史的文脈
   - 利害関係者マップ
   - データで見る構造

6. Between the Lines         ← v4.0 新規
   - 報道が「言っていないこと」
   - 裏の力学、隠された意図

7. NOW PATTERN（力学分析）
   - 力学タグ × 力学タグ
   - 各力学の詳細分析（300-500語）
   - 力学の交差点

8. Pattern History（歴史的並行事例 2-3件）

9. What's Next
   - 楽観シナリオ（確率%）+ 投資示唆
   - 基本シナリオ（確率%）+ 投資示唆
   - 悲観シナリオ（確率%）+ 投資示唆
   - 注目トリガー

10. Open Loop                ← v4.0 新規
    - 次のトリガーイベント+日付
    - 追跡テーマ（シリーズ）
```

---

## 文体ルール

### 太字強調（必須）
- dynamics_sections の analysis 内で、**最重要フレーズを太字**にすること
- 1段落あたり1-2箇所の太字が目安
- Markdown形式: `**太字テキスト**`

### 会話調（Matt Levine スタイル）
- 堅い報告書口調ではなく、読者に話しかけるように書く
- 「ここが面白いのだが」「要するに」「これは何を意味するか」等の接続を使う
- ただし分析の深さは犠牲にしない

### シナリオのラベル形式
- 「楽観」「基本」「悲観」の短いラベルを使う（「楽観シナリオ」は冗長 — ビルダーが自動で付加する）
- 確率は必ず合計100%にする

---

## バリデーションルール

以下のフィールドが空の場合、記事は**公開拒否**されます:

```python
REQUIRED_V4_FIELDS = [
    "bottom_line",
    "bottom_line_pattern",
    "bottom_line_scenario",
    "bottom_line_watch",
    "between_the_lines",
    "open_loop_trigger",
    "open_loop_series",
]
```

公開前に `article_validator.py` が自動チェックします。
不合格の場合はTelegram通知が送られ、修正を求められます。

---

## 予測追跡（Flywheel）

- 全記事の `scenarios` + `triggers` は自動で `prediction_db.json` に記録される
- 予測ID（NP-YYYY-XXXX）が自動付与される
- トリガー日が到来すると `prediction_verifier.py` がAI判定を提案
- Brier Score で予測精度を追跡（Superforecaster基準: 0.15未満）

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v4.0 | 2026-02-21 | Bottom Line, Between the Lines, Open Loop 追加。予測追跡統合 |
| v3.2 | 2026-02-18 | Deep Pattern 専用化（Speed Log廃止） |
| v3.0 | 2026-02-18 | 2モード制（Deep Pattern + Speed Log）、3層タクソノミー |
