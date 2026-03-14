# SELF_IMPROVEMENT_LOOP.md — 自己進化ループの設計書

> **Persistent Intelligence OS の第3のミッション: 自律的進化。**
> このファイルはシステムがどのように自らを賢くするかを定義する。
> AIが書き換えてよいのは「戦術（AGENT_WISDOM.md）」のみ。「目的（NORTH_STAR.md）」は不変。
> 更新: 変更時は末尾のCHANGELOGに1行追記。

---

## 概要

```
「3年積み上げたトラックレコードは翌日には作れない。
 これが唯一の堀（Moat）。」— NORTH_STAR.md
```

自己進化ループは予測精度（Brier Score）を自動的に分析し、
AIシステム自身の「思考パターン」を週次で最適化する仕組みである。

---

## 2層の自己改善システム

### Layer A: ECC Pipeline（ミスの根絶 — 毎回実行）

```
① ミスが発生（ツール失敗・ロジックエラー・推測実装）
   ↓
② KNOWN_MISTAKES.md に即記録（failure_capture.py が自動下書き）
   ↓
③ auto-codifier.py がパターンを mistake_patterns.json に登録
   ↓
④ fact-checker.py（Stop hook）がそのパターンを物理ブロック（exit 2）
   ↓
⑤ regression-runner.py で全ガードを毎日テスト（25テスト / PASS確認）
   ↓
⑥ llm-judge.py（Gemini）が未知パターンを意味レベルで検知
   ↓
⑦ 同じミスは技術的に不可能になる → ①に戻る（新しいミスのみ）
```

**原則: 穴を塞ぐだけ。開けない。ガードは追加するだけで削除しない。**

### Layer B: Evolution Loop（予測精度の向上 — 週次実行）

```
① prediction_auto_verifier.py が予測を解決（Grok検索 + Opus判定）
   ↓ Brier Score が計算される
② evolution_loop.py が毎週日曜 JST 09:00 に実行
   ↓ 解決済み予測を収集（週間バッチ）
③ Gemini API でメタ分析:「なぜ外れたか？なぜ当たったか？」
   ↓ miss_patterns / hit_patterns を抽出
④ 「次回の予測精度を上げる指示事項」をMarkdownで生成
   ↓ DSPy形式: 具体的な改善ルール
⑤ AGENT_WISDOM.md の「## 自己学習ログ」セクションに自動追記
   ↓ Telegramで What Changed レポートをNaotoに送信
⑥ 全エージェントが次のセッションから新しい知識を使う
   ↓
⑦ 次の予測の精度が上がる → ①に戻る
```

---

## スクリプト詳細

### evolution_loop.py（VPS: 毎週日曜 JST 09:00）

```
ファイル: loops/evolution_loop.py
クラス: EvolutionLoop(dry_run=False)
依存: PredictionTracker（apps.nowpattern）、LearningLoop（knowledge_engine）
```

**実行フロー:**

```python
class EvolutionLoop:
    def run(self):
        # 1. 解決済み予測を収集
        predictions = self.prediction_tracker.get_resolved_this_week()

        # 2. Brier Score 分析
        scores = [(p, p.brier_score) for p in predictions]
        miss_patterns = [p for p, bs in scores if bs > 0.25]  # 外れ閾値

        # 3. Gemini でメタ分析
        wisdom_update = self._generate_wisdom_update(miss_patterns, hit_patterns)

        # 4. AGENT_WISDOM.md に追記
        self._append_to_wisdom(wisdom_update)

        # 5. evolution_log.json に監査記録
        self._log_evolution(predictions, wisdom_update)

        # 6. Telegram通知
        self._notify(wisdom_update)
```

### prediction_auto_verifier.py（VPS: 毎日自動実行）

```
役割: 予測の自動検証（解決日が来た予測を処理）
手順:
  1. prediction_db.json から "status": "tracking" の予測を取得
  2. Grok API で最新情報を検索（resolution_question）
  3. LLM（最新Claude）で YES/NO 判定
  4. Brier Score 計算: BS = (forecast_prob/100 - outcome)²
  5. prediction_db.json に結果を書き込み（APPEND原則）
```

### data/agent_wisdom_updates.json（52件ローテーション）

```json
{
  "updates": [
    {
      "week": "2026-W11",
      "generated_at": "2026-03-09T00:00:00Z",
      "predictions_analyzed": 4,
      "miss_count": 1,
      "hit_count": 3,
      "avg_brier_score": 0.1688,
      "wisdom_text": "## Nowpattern 次回予測精度向上のための指示\n\n### 1. パターン分析\n..."
    }
  ]
}
```

### evolution_log.json（52週ローテーション）

```
場所: data/evolution_log.json
役割: 自己進化の監査証跡
内容: 週次実行ごとの分析結果（何件分析、何件的中、平均Brier、変更内容）
```

---

## Brier Score の解釈

| Brier Score | 評価 | 意味 |
|-------------|------|------|
| 0.00 | 完璧 | 100%確信で的中 |
| 0.00〜0.10 | 優秀 | Superforecasterレベル |
| 0.10〜0.25 | 良好 | 平均的予測者より上 |
| 0.25〜0.50 | 平均 | ランダムと大差なし |
| 0.50以上 | 要改善 | ランダムより悪い |

**現在のシステム平均（2026-03-09時点）: 0.1688**

---

## 自己改善の制約（AIへの権限境界）

### AIが自律的に書き換えてよいもの

```
✅ AGENT_WISDOM.md の「## 自己学習ログ」セクションへの追記
✅ mistake_patterns.json への新しいパターンの追加
✅ knowledge_timeline.json へのランの記録（APPEND ONLY）
✅ evolution_log.json への週次記録
✅ data/agent_wisdom_updates.json への追記
```

### AIが絶対に書き換えてはいけないもの

```
❌ NORTH_STAR.md（The Eternal Directives を含む）
❌ CLAUDE.md（north-star-guard.py が物理ブロック）
❌ prediction_db.json の既存エントリの変更・削除
❌ OPERATING_PRINCIPLES.md（Eternal Directives）
❌ 既存の予測確率の遡及変更
❌ mistake_patterns.json からのパターン削除
```

---

## ECC Pipeline の実装ファイル

| スクリプト | タイミング | 役割 |
|-----------|-----------|------|
| `scripts/guard/failure_capture.py` | PostToolUseFailure | 失敗の自動記録 |
| `.claude/hooks/auto-codifier.py` | PostToolUse(Edit/Write) | パターン自動生成 |
| `.claude/hooks/fact-checker.py` | Stop hook | パターン物理ブロック |
| `.claude/hooks/llm-judge.py` | PreToolUse(Edit/Write) | 意味レベル検知 |
| `.claude/hooks/regression-runner.py` | 毎日自動 | 全ガードのテスト |
| `.claude/state/mistake_patterns.json` | 常時参照 | 登録済み20パターン |

---

## Hive Mind 双方向同期（ローカル ↔ VPS）

```
ローカルで学んだこと → VPS AGENT_WISDOM.md へ（session-end.sh）
VPSで学んだこと → ローカルに同期（session-start.sh pull）
```

これにより全エージェント（NEO-ONE / NEO-TWO / NEO-GPT / local-claude）が
同一の知識ベースを共有し、片方のミスが全エージェントの改善に繋がる。

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-03-14 | 初版。ECC Pipeline + Evolution Loop の2層システム定義。Brier Score解釈表。自律権限境界。 |
