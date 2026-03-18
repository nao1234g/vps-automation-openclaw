# インフラ構成（NEO / Docker / Hey Loop 統合）
<!-- [Nowpattern固有] — VPS・NEO・Dockerの具体的構成。Nowpatternプロジェクト層のインフラ仕様。 -->

## VPS・Docker

- **VPS**: ConoHa 163.44.124.123（Caddy リバースプロキシ）
- **Compose**: `docker-compose.quick.yml`（現在使用中、`/opt/openclaw/`）
- **DB**: PostgreSQL 16 / `openclaw_secure_2026`
- **OpenClaw設定**: `config/openclaw/openclaw.json`（CLIフラグは不可）

### Docker Compose ファイル使い分け

| ファイル | 用途 |
|---|---|
| `docker-compose.quick.yml` | **本番（現在使用中）** |
| `docker-compose.dev.yml` | フル開発環境 |
| `docker-compose.minimal.yml` | 開発テスト用（PostgreSQL + OpenNotebook + N8N） |

### Docker セキュリティルール
- 全コンテナ: 非root実行（UID 1001）+ `no-new-privileges:true`
- ポートバインド: `127.0.0.1` のみ（Caddy以外）
- 変更後の検証: `docker compose config` → `docker compose up -d --build` → `docker logs --tail 20`

---

## NEO アーキテクチャ（Telegram Claude Code Dual Agent）

**重要: Claude Max（$200/月定額）経由。Anthropic API（従量課金）は使用しない。**

| サービス | Bot | systemd | 役割 |
|---|---|---|---|
| NEO-ONE | `@claude_brain_nn_bot` | `neo-telegram.service` | CTO・戦略・記事執筆 |
| NEO-TWO | `@neo_two_nn2026_bot` | `neo2-telegram.service` | 補助・並列タスク |
| NEO-GPT | OpenAI Codex CLI | `neo3-telegram.service` | バックアップ |

- 作業ディレクトリ: `/opt`（`APPROVED_DIRECTORY`環境変数）
- permission_mode: `bypassPermissions`（両方）
- OAuthトークン: ローカルPC → VPS SCPコピー（Windowsタスクスケジューラ、4時間ごと）
- **制約**: OpenClawの`anthropic/`モデルはAPI課金 → NEOをOpenClawに追加してはいけない

### ローカルClaude Code との役割分担
- **Neo（VPS）**: VPSファイル操作、Docker操作、記事執筆
- **ローカルClaude Code**: ローカルファイル編集、CLAUDE.md更新、git操作
- **衝突回避**: 両者が同時に同じVPSファイルを触らない

---

## Hey Loop（インテリジェンス収集 + Telegram報告）

**スケジュール（1日4回 JST）**: 00:00 / 06:00 / 12:00 / 18:00

| データソース | 内容 | コスト |
|---|---|---|
| Reddit (Infra/Revenue) | r/selfhosted, r/SaaS等 | 無料 |
| Hacker News | トップ50記事 | 無料 |
| Gemini + Google Search | 14トピックローテーション | 無料 |
| Grok + X | AIビルダー収益報告 | $5クレジット（朝1回のみ） |

**共有知識**: `/opt/shared/AGENT_WISDOM.md` — タスク開始前に全エージェントが読む
**タスクログ**: `/opt/shared/task-log/YYYY-MM-DD_agent_タスク名.md`

---

## 主要パス

| パス | 用途 |
|---|---|
| `/opt/claude-code-telegram/CLAUDE.md` | NEO-ONE 実効指示書（46KB、neocloop所有） |
| `/opt/claude-code-telegram-neo2/CLAUDE.md` | NEO-TWO 実効指示書（38KB、neocloop所有） |
| ~~`/opt/CLAUDE.md`~~ | 退役済み (2026-03-14) → `.retired-20260314` に移動 |
| `/opt/shared/SHARED_STATE.md` | 30分ごと自動更新（最新状態の真実） |
| `/opt/shared/AGENT_WISDOM.md` | 全エージェント共有知識 |
| `/var/www/nowpattern/content/data/ghost.db` | Ghost CMS SQLite DB |
| `config/openclaw/openclaw.json` | OpenClaw設定（CLIフラグではなくここで変更） |
