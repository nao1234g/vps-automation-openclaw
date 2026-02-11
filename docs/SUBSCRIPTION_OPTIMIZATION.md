# サブスクリプション最適化プラン - 7 AI社員システム

## 💰 コスト概要

### 現在の支出
| サービス | 月額 | 備考 |
|----------|------|------|
| Claude Code | $200 | Max plan |
| ChatGPT Plus | $20 | Codex含む |
| Google AI Pro | ¥2,900 (~$20) | Antigravity含む |
| **合計** | **~$240/月** | |

### 最適化後
| サービス | 月額 | 変更点 |
|----------|------|--------|
| Claude Code | **$100** | $100プランに変更 |
| ChatGPT Plus | $20 | 変更なし |
| Google AI Pro | ¥2,900 (~$20) | 変更なし |
| **合計** | **~$140/月** | **▼$100 削減（42%減）** |

---

## 🏗️ 3サブスクリプション × 7エージェント 対応表

### サブスクリプション別の提供機能

#### 1. Claude Code ($100/月)
| 機能 | 用途 |
|------|------|
| Claude Opus 4 | 戦略的思考、複雑な推論 |
| Claude Sonnet 4.5 | コーディング、レビュー |
| Claude Haiku 4 | 高速な軽量タスク |
| IDE統合 | VS Code / ターミナルで直接使用 |
| MCP対応 | GitHub、ファイルシステム等のツール連携 |

#### 2. OpenAI ChatGPT Plus ($20/月)
| 機能 | 用途 |
|------|------|
| Codex | VS Code内でのコード生成・デバッグ |
| GPT-4o | 一般的なチャット、ブレスト |
| DALL-E 3 | 画像生成 |
| Deep Research | 調査レポート生成 |

#### 3. Google AI Pro (¥2,900/月)
| 機能 | 用途 |
|------|------|
| **Google Antigravity** | Claude Opus 4.5/4.6へのエージェントリクエスト |
| Gemini 3 Pro | 最高性能マルチモーダル |
| Gemini 2.5 Pro/Flash | コーディング・推論 |
| Deep Research | 62+ Webサイト同時調査 |
| NotebookLM | 資料分析・学習 |
| Jules | 非同期コーディングエージェント |
| Gemini Code Assist & CLI | コード補助 |
| Google Cloud $10/月クレジット | API追加利用分 |
| **Gemini API (無料枠)** | OpenClawからの自動呼び出し |

---

## 🤖 エージェント × サービス マッピング

```
┌─────────────────────────────────────────────────────────┐
│                     人間（指揮官）                        │
│            タスクに応じてツールを選択                       │
├──────────┬──────────────────┬────────────────────────────┤
│ Claude   │   OpenAI         │   Google AI Pro            │
│ Code     │   ChatGPT+       │                            │
│ $100/月  │   $20/月         │   ¥2,900/月               │
├──────────┼──────────────────┼────────────────────────────┤
│ Jarvis   │ CodeX            │ Alice (Deep Research)      │
│ (Opus4)  │ (Codex/VS Code)  │ Pixel (Gemini 3 Pro Image)│
│ Guard    │                  │ Luna (Antigravity→Opus4.6) │
│ (Sonnet) │                  │ Scout (Flash API/無料)     │
└──────────┴──────────────────┴────────────────────────────┘
```

### 各エージェントの詳細

| # | Agent | 役割 | 使うサービス | モデル | 使い方 |
|---|-------|------|-------------|--------|--------|
| 1 | 🎯 Jarvis | 戦略・指揮 | Claude Code | Opus 4 | ターミナル/IDEで直接対話。複雑な意思決定 |
| 2 | 🔍 Alice | リサーチ | Google AI Pro | Deep Research + Gemini | Google AI Studioで調査。62+サイト同時巡回 |
| 3 | 💻 CodeX | 開発 | Codex + Claude Code | Codex / Opus 4 | VS Code Codexで日常開発。難問はClaude Code |
| 4 | 🎨 Pixel | デザイン | Google AI Pro | Gemini 3 Pro Image | 画像生成・UI設計。Geminiの視覚能力活用 |
| 5 | ✍️ Luna | 執筆 | Google Antigravity | Opus 4.5/4.6 | 高品質な記事・ドキュメント生成 |
| 6 | 📊 Scout | データ処理 | Google AI Pro(API) | Gemini 2.5 Flash | **OpenClawから自動呼び出し（無料枠）** |
| 7 | 🛡️ Guard | セキュリティ | Claude Code | Sonnet 4.5 | コードレビュー・脆弱性分析 |

---

## ⚡ OpenClaw自動化のポイント

### OpenClawで自動化できるエージェント（API経由）

Google AI StudioのGemini APIは**無料枠**があるため、OpenClawから直接呼び出せます：

| モデル | 無料枠 | 有料API |
|--------|--------|---------|
| Gemini 3 Flash | ✅ 無料 | $0.50/M入力 |
| Gemini 2.5 Flash | ✅ 無料 | $0.30/M入力 |
| Gemini 2.5 Pro | ✅ 無料 | $1.25/M入力 |
| Gemini 3 Pro | ❌ 有料のみ | $2.00/M入力 |

**推奨**: OpenClawのデフォルトエージェントを Gemini 2.5 Flash（無料）に設定。
複雑なタスクのみ Gemini 2.5 Pro（無料）にルーティング。

### 手動で使うエージェント（サブスク経由）

| エージェント | ツール | 操作方法 |
|-------------|--------|----------|
| Jarvis | Claude Code CLI | `claude` コマンドでターミナルから |
| CodeX | VS Code Codex | エディタ内で自動補完・生成 |
| Guard | Claude Code | コードレビューをclaude codeに依頼 |
| Alice | Google AI Studio | Deep Researchで調査依頼 |
| Luna | Google Antigravity | エージェントリクエストで執筆依頼 |
| Pixel | Google AI Studio | 画像生成・デザインレビュー |

---

## 🔧 実際のワークフロー

### 日常的な開発作業
```
1. VS Code を開く
2. Codex (ChatGPT+) が自動でコード補完
3. 複雑な実装 → Claude Code (claude コマンド) に聞く
4. コードレビュー → Claude Code でGuard役
5. ドキュメント生成 → Google Antigravity (Luna役)
```

### リサーチ → 記事作成フロー
```
1. Google Deep Research (Alice役) で62+サイト調査
2. NotebookLM で資料をまとめる
3. Google Antigravity (Luna役) でClaude Opus品質の記事生成
4. Scout (OpenClaw→Gemini Flash) でデータ処理・フォーマット
5. N8N ワークフローで自動投稿
```

### セキュリティ監査フロー
```
1. Claude Code (Guard役) でコードレビュー
2. scripts/security_scan.sh で自動スキャン
3. Claude Code (Jarvis役) で結果分析・改善提案
```

### 自動化バッチ処理（OpenClaw + N8N）
```
1. N8N スケジュールトリガー (毎朝8時)
2. OpenClaw → Gemini 2.5 Flash (Scout役/無料) でデータ収集
3. OpenClaw → Gemini 2.5 Pro (無料) で分析
4. 結果をPostgreSQLに保存
5. Telegram通知
```

---

## 📊 コスト効率分析

### 従量課金API vs サブスクリプション

| 方式 | 月額 | 利用制限 | メリット |
|------|------|---------|---------|
| API従量課金 | $59~$181+ | 使った分だけ | 柔軟、予算超過リスク |
| **サブスクリプション** | **$140固定** | **実質無制限** | **予測可能、使い放題** |

### ROI（投資対効果）
- **Claude Code $100**: 1日あたり~$3.3。Opus 4による戦略的意思決定を無制限に = 価値∞
- **ChatGPT Plus $20**: Codex + GPT-4o無制限。開発効率3~5倍向上
- **Google AI Pro ¥2,900**: Gemini全モデル + Antigravity + Deep Research + NotebookLM + Jules + $10 GCPクレジット = **最もコスパ良い**

### Google AI Pro の価値分解
```
Google AI Pro ¥2,900/月 に含まれるもの:
├── Gemini 3 Pro/Flash (最新モデル)
├── Gemini 2.5 Pro/Flash  
├── Google Antigravity (Claude Opus 4.5/4.6アクセス!)
├── Deep Research (62+サイト同時調査)
├── NotebookLM (上位アクセス)
├── Jules (コーディングエージェント)
├── Gemini Code Assist & CLI
├── Google Cloud $10/月クレジット
├── 2TB ストレージ
├── 100万トークン コンテキストウィンドウ
└── Gemini API 無料枠 (OpenClaw用)

→ 個別に契約すると$200+相当の価値
```

---

## 🚀 実装ステップ

### Phase 1: 即日実行
1. [ ] Claude Code を $200 → $100 プランに変更
2. [ ] Google AI Studio で API キーを発行（Gemini用）
3. [ ] OpenClaw の `openclaw.json` を Gemini API で設定

### Phase 2: 1週間以内
4. [ ] VS Code Codex の活用を最大化（設定最適化）
5. [ ] Google Antigravity でのClaude Opus利用を試す
6. [ ] N8N ワークフローを Gemini API（無料枠）で自動化

### Phase 3: 2週間以内
7. [ ] 全サービスの使用量モニタリング開始
8. [ ] Deep Research → NotebookLM → Antigravity のリサーチパイプライン構築
9. [ ] 月次コストレポートの自動化

---

## 📁 関連ファイル
- `config/openclaw/openclaw.json` - OpenClaw基本設定（Gemini API用に更新）
- `config/openclaw/openclaw-multiagent.json` - マルチエージェント設定
- `scripts/cost_monitor_multiagent.sh` - コスト監視
- `n8n-workflows/` - 自動化ワークフロー
