# Antigravity完結型 7人のAI社員アーキテクチャ

> **月額 ¥2,900（Google AI Pro）のみで、7人のAI社員を運用する設計書**
> 作成日: 2025年7月 / 更新: 2026年2月

---

## 概要

3つのサブスクリプション（$140/月）を **Google AI Pro 1本（¥2,900/月）** に統合。
Antigravity内の複数モデル + Google AI Proの付帯サービスで全エージェントを実現する。

---

## エージェント配置表

| # | Agent | 役割 | モデル/ツール | 使う場所 | 選定理由 |
|---|-------|------|-------------|---------|---------|
| 1 | 🎯 **Jarvis** | 戦略・指揮 | Claude Opus 4.6 | Antigravity | 最高の推論力 |
| 2 | 🔍 **Alice** | リサーチ | Deep Research | ブラウザ（gemini.google.com） | 62+サイト同時巡回 |
| 3 | 💻 **CodeX** | 開発 | Claude Opus 4.6 | Antigravity | 最高のコード品質 |
| 4 | 🎨 **Pixel** | デザイン | Gemini 3 Pro Image | Antigravity / Gemini Advanced | 画像生成特化 |
| 5 | ✍️ **Luna** | 執筆 | Claude Opus 4.6 | Antigravity | 最高の文章力 |
| 6 | 📊 **Scout** | データ処理 | Sonnet 4.5 | Antigravity | 定型処理。Opus枠を温存 |
| 7 | 🛡️ **Guard** | セキュリティ | Sonnet 4.5 | Antigravity | スキャン実行は軽量で十分 |

---

## Opus枠の戦略的配分

**Opus 4.6（高価値）**: Jarvis / CodeX / Luna — 判断力・創造力が必要なタスク
**Sonnet 4.5（効率重視）**: Scout / Guard — 定型的・反復的なタスク
**専用ツール**: Alice（Deep Research）/ Pixel（画像生成）

→ Opusのエージェントリクエスト枠を温存しつつ、全体の品質を最大化

---

## コスト比較

| プラン | 月額 |
|-------|------|
| 旧: 3サブスク分散型 | 約¥21,000（$140） |
| **新: Antigravity完結型** | **¥2,900** |
| **削減率** | **86%** |

---

## 使い方

### Antigravity内（5人）

Antigravityのモデル選択で適切なモデルを選び、依頼する：

| タスク | モデル選択 | 依頼例 |
|-------|-----------|--------|
| 戦略判断 | Opus 4.6 | 「来月のプロジェクト戦略を提案して」 |
| コーディング | Opus 4.6 | 「entrypoint.shのバグを修正して」 |
| 記事執筆 | Opus 4.6 | 「READMEを日英で書いて」 |
| ログ分析 | Sonnet 4.5 | 「Dockerログを分析して」 |
| セキュリティ | Sonnet 4.5 | 「セキュリティスキャンを実行して」 |

### ブラウザ（2人）

| タスク | サービス | URL |
|-------|---------|-----|
| 深いリサーチ | Deep Research | gemini.google.com → Deep Research |
| 画像生成 | Gemini Advanced | gemini.google.com → 画像生成 |

---

## ワークフロー（スラッシュコマンド）

Antigravity内でスラッシュコマンドとして呼び出し可能：

- `/jarvis` — 戦略モード起動
- `/guard` — セキュリティスキャン実行
- `/scout` — データ処理・ログ分析

---

## 制限事項と対策

| 制限 | 対策 |
|------|------|
| エージェントリクエスト上限（非公開） | Scout/GuardをSonnet 4.5にしてOpus枠を温存 |
| Deep Researchはブラウザのみ | 結果をAntigravityにコピペして分析を続行 |
| 画像生成の品質差 | 必要に応じてGemini Advancedのブラウザ版を利用 |
| 日次上限に達した場合 | 翌日リセット。将来的にはClaude Code CLI追加も検討 |

---

## 将来の拡張オプション

| 条件 | 追加サービス | コスト |
|------|------------|--------|
| Antigravityの制限が厳しい場合 | Claude Code CLI | +$100/月 |
| コード補完が欲しい場合 | ChatGPT Plus (Codex) | +$20/月 |
| より多くのリクエストが必要な場合 | Google AI Ultra (¥30,000/月) | +¥27,100/月 |
