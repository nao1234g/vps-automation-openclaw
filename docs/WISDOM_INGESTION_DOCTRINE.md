# WISDOM_INGESTION_DOCTRINE.md — 知恵の摂取ドクトリン

> 制定: 2026-03-14
> 典拠: Charlie Munger「Mental Models」/ Philip Tetlock「Superforecasting」(2015) / Kahneman「Thinking Fast and Slow」
> このファイルは「どこから学ぶか」の行動規範。違反は判断精度の劣化として記録される。

---

## 核心原則

> "You've got to have models in your head. And you've got to array your experience
>  —both vicarious and direct—on this latticework of models."
> — Charlie Munger, USC Business School Commencement (1994)

**知恵の源泉は2種類ある:**

| 種類 | 定義 | 劣化のリスク |
|------|------|-------------|
| **直接経験** | 自分が試みて得た成果・失敗 | サンプルサイズが小さい。バイアスが強い |
| **代理経験** | 他者の事例から学んだパターン | 文脈が異なる可能性。過信のリスク |

**解決策: 「多様なモデルのラティス（格子）」を意識的に構築する**

---

## 5つの知恵階層

すべての学習インプットをこの階層で分類し、上位から優先させること。

| 階層 | 種類 | 例 | 信頼度 |
|------|------|-----|--------|
| L1 | **実測値・ログ・実験結果** | Brier Score, エラーログ, A/Bテスト | 最高（数値が語る） |
| L2 | **同分野の古典・一次文献** | Tetlock "Superforecasting", Geneen "Managing" | 高（時間の篩にかかった） |
| L3 | **世界最高水準の現役実践者の証言** | 公開インタビュー, X/noteの一次発言 | 中（コンテキスト確認必要） |
| L4 | **二次文献・要約・解説** | ブログ記事, YouTube解説, 本の要約 | 低（原典と照合するまで使わない） |
| L5 | **AIが推測で生成した情報** | 「〜のはずです」「一般的に〜」 | 最低（使用禁止 = Wishful Fact） |

**実装ルール: L4以下は単体で判断の根拠にしない。必ずL1〜L3と組み合わせる。**

---

## Superforecaster の思考プロセス（Tetlock 7原則）

予測精度（Brier Score）を上げるための具体的行動規範。

```
1. 外側の視点（Outside View）から始める:
   類似事例の歴史的基準率を最初に確認してから、今回のケースに戻る。
   例: 「この政権が1年以内に崩壊する確率は？」→ まず過去50年の基準率を確認

2. 内側の視点（Inside View）で更新する:
   今回のケース固有の要因でベースレートを上下に調整する。
   「この政権はX要因があるため、基準率より+10%高い」

3. 粒度のある確率を使う:
   「かなり可能性がある」ではなく「63%」。
   数値は5刻みで表現（5%, 10%, ... 95%）。端値（0%, 100%）は禁止。

4. クロスカッティング:
   複数の独立したアプローチで同じ問いに答える。
   3つのアプローチが同じ結論を出したら確信度が上がる。

5. 情報更新:
   新しいシグナルが入ったら即座に確率を更新する（ベイズ更新）。
   「以前の予測と変わらない」は情報怠慢。

6. 校正（Calibration）を意識する:
   「80%と言ったことが実際80%の頻度で起きているか」を追跡する。
   過信バイアス（実際より高い確率をつける）は Brier Score で検出可能。

7. エラーから学ぶ:
   外れた予測を分析する。「なぜ外れたか」に答えられなければ次も外れる。
```

---

## 世界標準の情報摂取サイクル

Nowpatternが世界基準の予測プラットフォームになるためには、
AIエージェントが「毎週この情報を消化している」状態が必要。

### 週次摂取プロトコル（VPS自動化推奨）

| 頻度 | ソース | 目的 |
|------|--------|------|
| 毎日 | Polymarket / Metaculus オープン予測 | 市場コンセンサスとの比較校正 |
| 毎日 | Reuters / AP / Bloomberg 一次記事 | シグナル検出 |
| 週1回 | Superforecaster ブログ / GJP レポート | 力学パターンの学習 |
| 週1回 | 解決済み予測のBrierレビュー（evolution_loop.py） | 自己校正 |
| 月1回 | 古典文献1章読了（下記リスト） | メンタルモデル拡張 |

### 推奨古典リスト（Nowpatternの文脈で有用）

```
予測・判断精度:
  - Tetlock, P. (2015). Superforecasting. Crown.  ← 最優先
  - Kahneman, D. (2011). Thinking, Fast and Slow. Farrar, Straus.
  - Silver, N. (2012). The Signal and the Noise. Penguin.

経営・意思決定:
  - Geneen, H. (1984). Managing. Doubleday.
  - Bezos, J. (2016). Amazon Shareholder Letters (2004-present).
  - Grove, A. (1996). Only the Paranoid Survive. Doubleday.

競争優位・モート:
  - Munger, C. (2005). Poor Charlie's Almanack. Donning.
  - Morningstar (2016). Why Moats Matter.

メディア・プラットフォーム:
  - Christensen, C. (1997). The Innovator's Dilemma. HBS Press.
  - Anderson, C. (2006). The Long Tail. Hyperion.
```

---

## 「世界一」のベンチマーク定義

> 「世界一の予測プラットフォーム」は定性的スローガンではなく、測定可能な数値目標である。

| 指標 | 現在（2026-03） | Year 1 目標 | Year 3 目標（世界基準） |
|------|-----------------|-------------|------------------------|
| Brier Score（全予測平均） | 測定中 | 0.18以下 | 0.13以下（GJPトップ10%水準） |
| オープン予測数 | 12 | 50+ | 200+ |
| 予測解決率（1年以内） | 測定中 | 60%以上 | 75%以上 |
| JA+EN記事数 | 165 | 500 | 3,000 |
| 読者投票参加率 | 測定中 | 月1,000票 | 月50,000票 |
| キャリブレーション精度 | 未測定 | ±5%以内 | ±3%以内 |

**GJP（Good Judgment Project）のトップSuperforecasterは Brier Score 0.13前後。**
**これが「世界基準」の数値的定義。Nowpatternはここを目指す。**

---

## 知識の陳腐化ルール

```
情報の鮮度管理:
- 6ヶ月以上前の市場データ → 最新値で上書きするまで使用禁止
- 1年以上前のAI技術情報 → 「古い情報」とフラグを立てる
- 解決済み予測の教訓 → AGENT_WISDOM.mdに永続記録（陳腐化しない）
- 古典文献の原則 → 不変（Munger/Geneen/Tetlockの核心は10年後も有効）
```

---

*典拠: Munger, C. (1994). USC Business School Commencement Address. | Tetlock, P. & Gardner, D. (2015). Superforecasting. | Kahneman, D. (2011). Thinking, Fast and Slow.*
