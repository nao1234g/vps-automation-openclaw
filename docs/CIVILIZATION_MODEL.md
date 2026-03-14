# AI Civilization Model — Nowpattern の予測知性アーキテクチャ

> このドキュメントは AI Civilization OS の設計哲学と構造を説明する。
> 実装は各 Python モジュールを参照すること。

---

## なぜ「文明」と呼ぶか

単体のAIエージェントは「一人の専門家」だ。
AI Civilizationは「文明」——複数の専門家が互いに批判し合い、
より精度の高い予測を生成するための協調システムだ。

```
一人の専門家の予測精度: 65〜70%
文明（6エージェントのディベート）の予測精度: 目標 75〜85%
```

この差を生むのが「悪魔の代弁者（監査官）」の存在だ。
全員が賛成している時に反論する役割がなければ、集合知は機能しない。

---

## 7層アーキテクチャ

```
Layer 7: Board Meeting         — 経営判断（Geneen逆算原則）
Layer 6: Decision Engine       — 戦略・資本・実行プラン
Layer 5: Apps + Loops          — Nowpatternとの統合・定期実行
Layer 4: Agent Civilization    — 6専門エージェントの議論
Layer 3: Knowledge Engine      — 知識グラフ・歴史パターン
Layer 2: Prediction Engine     — 確率推定・シナリオ生成
Layer 1: Truth Engine          — 事実検証・Brier Score追跡
```

各層は上位層にサービスを提供し、下位層から情報を取得する。
**単方向依存**（上位→下位への依存のみ）を守ることで循環参照を防ぐ。

---

## 6専門エージェントの役割と特性

| エージェント | 専門領域 | 確率バイアス | 主要メソッド |
|------------|---------|-----------|------------|
| **Historian** | 歴史的パターン・基準率 | 0（中立） | `find_parallels()` |
| **Scientist** | 論理・因果・証拠品質 | -3（保守的） | `evaluate_causality()` |
| **Economist** | 市場・金融・Polymarket | 0（市場追従） | `compare_to_market()` |
| **Strategist** | 地政学・権力構造 | +5（強気） | `get_strategic_scenarios()` |
| **Builder** | 実装可能性・実行障壁 | 0（現実的） | `estimate_resources()` |
| **Auditor** | リスク・バイアス検出 | -5（悲観的） | `audit_prediction()` |

### バイアス設計の哲学

各エージェントのバイアスは「欠陥」ではなく「役割」だ。

- **Strategist (+5)**: 楽観的な計画者がいなければ実行が起きない
- **Auditor (-5)**: 悲観的な批判者がいなければリスクを見落とす
- **合成**: ±10の幅が打ち消し合い、コンセンサスは中央値に収束する

---

## ディベートプロセス

```
1. 議題設定（AgentDebateLoop.enqueue()）
   → topic, tags, base_probability を設定

2. 各エージェントが独立分析（AgentManager.debate()）
   → 6つの独立した確率推定

3. 加重平均でコンセンサス計算（DebateEngine.calculate_consensus()）
   → confidence × agent_weight で重み付け平均

4. 監査官が最終チェック（AuditorAgent.audit_prediction()）
   → PASS / WARN / FAIL で品質保証

5. 結果をprediction_dbに記録
   → OTSタイムスタンプで改ざん防止
```

---

## 予測精度の計測（Brier Score）

```python
Brier Score = (予測確率 - 実際の結果)²

例:
  予測: 70%（0.70）
  結果: YES（1.0）
  Brier = (0.70 - 1.0)² = 0.09  ← 低いほど良い

Brier評価グレード:
  EXCEPTIONAL: < 0.05  （超人的な精度）
  EXCELLENT:   < 0.10
  GOOD:        < 0.15
  DECENT:      < 0.20
  AVERAGE:     < 0.25
  POOR:        >= 0.25  ← ここを超えるとBoardがアラート
```

---

## Moat Strength（競争優位の測定）

```
Moat Score = resolved_count × hit_rate

SEED:     score < 1.0    （開始直後）
EARLY:    score < 5.0    （初期トラックレコード）
BUILDING: score < 15.0   （信頼構築中）
STRONG:   score < 30.0   （競合が追いつけない段階）
FORTRESS: score >= 30.0  （3年分の実績 = 翌日には作れない壁）
```

---

## 自己進化メカニズム（EvolutionLoop）

```
毎週日曜 JST 09:00:
  1. 解決済み予測 → なぜ外れたか分析
  2. 力学タグ別のミスパターンを特定
  3. 次回予測への指示事項を自動生成
  4. AGENT_WISDOM.md の「## 自己学習ログ」に追記
  5. 全エージェントが次のセッションから使用
```

これはDSPy原理の実装:
**「人間が書いたプロンプトよりAIがA/Bテストで導いたプロンプトの方が精度が高い」**

---

## 制約（AIへの命令）

- `prediction_db.json` のデータを直接変更することは禁止
- `NORTH_STAR.md` / `CLAUDE.md` への自律的書き込みは禁止
- `AGENT_WISDOM.md` の `## 自己学習ログ` セクションへの追記のみ許可
- Polymarket市場データとの乖離が20%超の場合、Market Agentのレビューを必須化

---

*最終更新: 2026-03-14 — AI Civilization OS 初版実装に合わせて作成*
