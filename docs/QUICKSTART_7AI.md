# 🎯 7 AI社員 クイックリファレンス

> **月額$140で7人のAI社員を雇う方法**
> （旧$240 → $100削減）

## 今すぐ使う：タスク別ガイド

### 「コードを書きたい」
```
日常的なコード → VS Code で Codex が自動補完 (ChatGPT+ $20)
複雑な実装     → ターミナルで `claude` コマンド (Claude Code $100)
非同期タスク   → Jules でバックグラウンド開発 (Google AI Pro ¥2,900)
```

### 「調べ物をしたい」
```
深い調査 → Google AI Studio → Deep Research (62+サイト同時巡回)
軽い検索 → Gemini アプリで聞く
技術調査 → Claude Code で claude に聞く
```

### 「記事・ドキュメントを書きたい」
```
高品質な記事 → Google Antigravity (Claude Opus 4.5/4.6品質)
技術文書     → Claude Code で生成
SNS投稿     → Gemini アプリで素早く
```

### 「セキュリティチェック」
```
コードレビュー → Claude Code (Sonnet 4.5が最適)
脆弱性スキャン → ./scripts/security_scan.sh
戦略的分析    → Claude Code (Opus 4で総合判断)
```

### 「データ処理・自動化」
```
自動バッチ処理 → OpenClaw (Gemini 2.5 Flash / 無料API)
ワークフロー   → N8N + OpenClaw 連携
ログ分析      → OpenClaw Scout エージェント
```

### 「デザイン・画像」
```
画像生成   → Google AI Studio (Gemini 3 Pro Image / Imagen 4)
UI設計    → Claude Code + Codex で実装
デザイン案 → Gemini アプリで相談
```

---

## 📋 サービス早見表

| やりたいこと | 使うサービス | エージェント名 | コスト |
|-------------|-------------|--------------|--------|
| 戦略判断・指揮 | Claude Code CLI | 🎯 Jarvis | $100/月に含む |
| Web調査・分析 | Google Deep Research | 🔍 Alice | ¥2,900に含む |
| コーディング | VS Code Codex | 💻 CodeX | $20/月に含む |
| 難しいコード | Claude Code | 💻 CodeX+ | $100/月に含む |
| デザイン・画像 | Google AI Studio | 🎨 Pixel | ¥2,900に含む |
| 記事執筆 | Google Antigravity | ✍️ Luna | ¥2,900に含む |
| データ処理 | OpenClaw→Gemini API | 📊 Scout | **無料** |
| セキュリティ | Claude Code | 🛡️ Guard | $100/月に含む |

---

## 🔑 セットアップチェックリスト

### ✅ Claude Code ($100/月)
- [ ] Anthropicで$100プランに変更: https://console.anthropic.com
- [ ] VS Codeで `claude` コマンドが使えることを確認
- [ ] MCP設定（GitHub, Filesystem）を確認

### ✅ ChatGPT Plus ($20/月)
- [ ] VS Code Codex が有効化されていることを確認
- [ ] 設定 → Codex の自動補完がON

### ✅ Google AI Pro (¥2,900/月)
- [ ] Google AI Studio でAPIキーを発行: https://aistudio.google.com/apikey
- [ ] OpenClawの `.env` に `GOOGLE_AI_API_KEY` を設定
- [ ] Antigravity を試す: Geminiアプリ内で確認
- [ ] NotebookLM でプロジェクト資料を登録

---

## 🔄 OpenClaw 設定更新

```bash
# .env に追加するキー
GOOGLE_AI_API_KEY=your-google-ai-studio-api-key

# OpenClaw設定は更新済み:
# config/openclaw/openclaw.json
#   - Scout (Gemini 2.5 Flash) = デフォルト、無料
#   - Alice (Gemini 2.5 Pro) = 分析用、無料
#   - Pixel (Gemini 3 Flash) = クリエイティブ
```

---

## 💡 コスパ最大化のコツ

1. **日常作業はCodex（$20内）** — 自動補完に任せる
2. **考える作業はClaude Code（$100内）** — Opusの推論力を活用
3. **調べ物はDeep Research（¥2,900内）** — 手動検索不要
4. **自動化はOpenClaw+Gemini Flash（無料）** — バッチ処理を自動化
5. **執筆はAntigravity（¥2,900内）** — Opus品質を追加費用なし

**Google AI Pro (¥2,900) が最もお得。$200+相当の価値が含まれている。**
