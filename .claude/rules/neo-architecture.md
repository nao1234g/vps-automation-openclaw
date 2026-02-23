# NEO アーキテクチャ（Telegram経由 Claude Code Dual Agent）

## 概要
NEO-ONE/NEO-TWOの2つのClaude Code Telegramサービスが独立稼働。
**重要: Claude Max（$200/月定額）経由。Anthropic API（従量課金）は使用しない。**

| サービス | Bot | systemd | 役割 |
|---|---|---|---|
| NEO-ONE | `@claude_brain_nn_bot` | `neo-telegram.service` | CTO・戦略・記事執筆 |
| NEO-TWO | `@neo_two_nn2026_bot` | `neo2-telegram.service` | 補助・並列タスク |

## 重要な設定
- NEO-ONE: `/opt/claude-code-telegram/` + `neo-telegram.service`
- NEO-TWO: `/opt/claude-code-telegram-neo2/` + `neo2-telegram.service`
- 作業ディレクトリ: `/opt`（`APPROVED_DIRECTORY`環境変数）
- CLAUDE.md: `/opt/CLAUDE.md` → `/opt/claude-code-telegram/CLAUDE.md` シンボリックリンク
- permission_mode: `bypassPermissions`（両方、2026-02-23設定済み）
- OAuthトークン: ローカルPC → VPS SCPコピー（Windowsタスクスケジューラ、4時間ごと）

## Jarvis↔Neo 通信
- 共有フォルダ: `/opt/shared/reports/`（ホスト）= `/shared/reports/`（コンテナ内）
- Jarvis → `/shared/reports/YYYY-MM-DD_タスク名.md` に書き込み
- Neo → `/opt/shared/reports/` を読んでユーザーに報告

## ローカルClaude Code との役割分担
- **Neo（VPS）**: VPSファイル操作、Docker操作、N8N操作、戦略立案
- **ローカルClaude Code**: ローカルファイル編集、CLAUDE.md更新、git操作、設計レビュー
- **衝突回避**: 両者が同時に同じVPSファイルを触らない

## 制約（絶対に守ること）
- OpenClawの`anthropic/`モデルはAPI課金 → NEOをOpenClawに追加してはいけない
- NEOはClaude Code Telegramサービスとして独立運用（OpenClawと完全分離）

## エージェント構成（10人）
| # | 名前 | 役割 | モデル | プラットフォーム |
|---|------|------|--------|-----------------|
| 1 | Jarvis | 実行・投稿・翻訳 | GLM-5 (zai/) | OpenClaw |
| 2 | Alice | リサーチ | GLM-5 (zai/) | OpenClaw |
| 3 | CodeX | 開発 | Gemini 2.5 Pro | OpenClaw |
| 4 | Pixel | デザイン | Gemini 2.5 Pro | OpenClaw |
| 5 | Luna | 補助執筆 | GLM-5 (zai/) | OpenClaw |
| 6 | Scout | データ処理 | Gemini 2.5 Pro | OpenClaw |
| 7 | Guard | セキュリティ | Gemini 2.5 Pro | OpenClaw |
| 8 | Hawk | X/SNSリサーチ | grok-4.1 | OpenClaw |
| 9 | NEO-ONE | CTO・戦略・執筆 | claude-opus-4.6 | Telegram (Max) |
| 10 | NEO-TWO | 補助・並列タスク | claude-opus-4.6 | Telegram (Max) |

## NEO OAuthトークン自動同期（2026-02-23設定済み）
- スクリプト: `C:\Users\user\AppData\Local\Temp\sync-neo-token.ps1`
- タスク名: `NEO-TokenSync`（Windowsタスクスケジューラ、4時間ごと）
- ログ: `C:\Users\user\AppData\Local\Temp\neo-token-sync.log`
