# MODEL_ROUTING_POLICY.md — モデルルーティングポリシー

> **どのタスクにどのモデルを使うかの唯一の定義。**
> 課金上限: Claude Max $200/月（定額）— Anthropic API従量課金は使用禁止。
> 更新: 変更時は末尾のCHANGELOGに1行追記。

---

## 基本原則

```
① Claude Max定額の範囲内でのみ使う（Anthropic API従量課金禁止）
② 能力が十分なら低コストモデルを選ぶ（コスト最小化）
③ 予測・翻訳・記事執筆 = Opusレベル必須（精度が収益に直結）
④ 分析・検索・モニタリング = 無料モデルで十分
⑤ 課金モデルは「承認が必要な提案のみ」Naotoへ提示する
```

---

## モデル別の役割マップ

### Claude Opus 4.6（NEO-ONE / NEO-TWO経由）

**コスト**: Claude Max $200/月定額内（無限使用）
**使用経路**: VPS `neo-telegram.service` / `neo2-telegram.service`

| タスク | 理由 |
|--------|------|
| 記事執筆（Deep Pattern v6.0） | 力学分析・シナリオ構造化に最高精度必要 |
| 予測分析（YES/NO判定） | Brier Scoreに直結。外れると信頼が下がる |
| 英語翻訳（JP→EN） | バイリンガルプラットフォームの品質 |
| prediction_auto_verifier.py の判定 | 解決日の予測結果判定（Unshakeable facts必要） |
| evolution_loop.py の wisdom生成 | 自己進化ループの核心 |
| AGENT_WISDOM.md への自己追記 | 知識更新の精度 |

**禁止使用**:
- ❌ Anthropic API（従量課金）経由での呼び出し
- ❌ OpenClaw の `anthropic/` モデル経由（同じく従量課金）

---

### Claude Sonnet 4.6（ローカルClaude Code）

**コスト**: Claude Max $200/月定額内
**使用経路**: ローカル VSCode Extension / Claude Code CLI

| タスク | 理由 |
|--------|------|
| ローカルファイル編集・コード作成 | 現在のセッションがこれ |
| Hook・スクリプトのデバッグ | ローカル環境での作業 |
| CLAUDE.md / NORTH_STAR.md の参照・読み取り | ドキュメント確認 |
| settings.local.json の更新 | フック設定変更 |
| Git操作（commit / push） | バージョン管理 |

---

### Gemini 2.5 Pro（無料枠）

**コスト**: Google AIのAPIキーで無料枠利用
**使用経路**: VPS cron スクリプト直接呼び出し

| タスク | 理由 |
|--------|------|
| evolution_loop.py のメタ分析 | 週次バッチ処理。無料でOK |
| llm-judge.py の意味レベル検知 | PreToolUse hook。低コスト要求 |
| Hey Loop の情報収集分析 | 1日4回。コスト積み上がる |
| 技術トレンド分析（研究ダイジェスト） | 要約・分類に向いている |
| X アルゴリズム変化の分析 | 無料枠で十分 |

**制限**: 無料枠のリクエスト数制限に注意。超えたら「無料枠超過」をNaotoに報告。

---

### Grok 4.1 API（$5クレジット内）

**コスト**: X AI APIクレジット。$5/月のバジェット管理
**使用経路**: VPS スクリプトから HTTP直接呼び出し

| タスク | 理由 |
|--------|------|
| prediction_auto_verifier.py の検索フェーズ | Xのリアルタイムデータが必要 |
| x-algorithm-monitor.py の分析 | X投稿パフォーマンス把握 |
| 予測の解決情報収集 | 最新ニュース検索（Grok検索機能） |
| @nowpattern の分析 | 自アカウントのデータ取得 |

**コスト管理ルール**:
- 毎月の使用量を追跡（$5超過前にNaotoへ通知）
- 検索は朝1回（毎朝09:00 JST）に集約してバースト避ける
- バッチ処理でリクエスト数を最小化

---

### OpenAI Codex（NEO-GPT）

**コスト**: NEO-GPTのバックエンド
**使用経路**: VPS `neo3-telegram.service`（`/opt/neo3-codex/`）

| タスク | 理由 |
|--------|------|
| NEO-ONE/TWOのバックアップ | OAuthトークン切れや障害時の代替 |
| コーディングタスク | Codexはコード生成が得意 |

**優先度**: NEO-ONE/TWOが正常稼働中はNEO-GPTは待機。
バックアップ専用のため積極的には使わない。

---

## タスク別の推奨モデル早見表

| タスク | 推奨モデル | 理由 |
|--------|-----------|------|
| 記事執筆 | Opus 4.6 (NEO) | 品質最優先 |
| 翻訳（JP→EN） | Opus 4.6 (NEO) | 品質最優先 |
| 予測判定 | Opus 4.6 (NEO) | 精度がBrierに直結 |
| コード作成（ローカル） | Sonnet 4.6 (local) | 定額内・速い |
| ログ分析・要約 | Gemini 2.5 Pro | 無料枠OK |
| Xアルゴリズム分析 | Gemini 2.5 Pro | 無料枠OK |
| X検索・最新情報 | Grok 4.1 | X特化 |
| 予測解決情報収集 | Grok 4.1 | リアルタイム検索 |
| バックアップ処理 | Codex (NEO-GPT) | 障害時のみ |

---

## コスト超過時の対応

```
① Gemini無料枠超過
   → Naotoに通知 → 次月まで待機 または 有料プランへの移行判断はNaotoが行う

② Grok $5クレジット枯渇
   → Naotoに通知 → $5追加チャージ（Type 2判断 = Naoto承認後実施）
   → それまでは予測検証をスキップ（予測解決のみ遅延）

③ Claude Max使用量90%超過
   → .claude.json で確認 → Naotoにアカウント切り替えを提案
   → marketingiiyone@gmail.com ↔ nakamura-ai@ewg.co.jp を切り替え
```

---

## 禁止事項

```
❌ Anthropic API（api.anthropic.com）への直接呼び出し（従量課金発生）
❌ OpenClaw の anthropic/ モデル（同じく従量課金）
❌ Gemini 1.0/1.5 Pro（旧モデル。Gemini 2.5 Proを使う）
❌ GPT-4o / GPT-4 への直接課金（NEO-GPT経由のCodexのみ可）
```

---

## 将来の検討（Naoto承認後のみ実施）

```
候補: DeepSeek R1 Distill Qwen 32B
  input $0.29/1M, output $0.29/1M
  提案者: model-intel-bot (2026-03-08)
  状況: pending_approvals.json ID=7aa06939 で承認待ち
  ROI: 現在Claude Max定額内なので急ぎではない
```

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-03-14 | 初版。5モデルの役割定義。コスト管理ルール。禁止事項。将来候補（DeepSeek）。 |
