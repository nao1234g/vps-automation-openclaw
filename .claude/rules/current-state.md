# 現在の状態（Current State）

> ⚠️ このファイルは古くなりやすい。セッション開始時は優先してVPSを確認:
> - `cat /opt/shared/SYSTEM_BRIEFING.md`（毎時更新）
> - `cat /opt/shared/SHARED_STATE.md`（30分更新）
> VPSのファイルと矛盾がある場合は**VPSのファイルが正しい**。

---

## 動作中の構成（2026-02-23時点）

- **VPS**: ConoHa 163.44.124.123（Caddy リバースプロキシ）
- **Compose**: `docker-compose.quick.yml`（`/opt/openclaw/`）
- **コンテナ**: openclaw-agent, postgres, n8n, substack-api, opennotebook
- **Gateway**: ws://127.0.0.1:3000（トークン認証 + デバイスペアリング済み）
- **Telegram bot**: `@openclaw_nn2026_bot` = Jarvis（OpenClaw）
- **NEO-ONE**: `@claude_brain_nn_bot` = Claude Opus 4.6（`neo-telegram.service`）
- **NEO-TWO**: `@neo_two_nn2026_bot` = Claude Opus 4.6（`neo2-telegram.service`）
- **DBパスワード**: `openclaw_secure_2026`（静的設定済み）
- **OpenClawエージェント**: Jarvis 1体のみ（Gemini 2.5 Pro）。Alice/Luna/CodeX/Pixel/Scout/Guard/Hawk は廃止済み
- **VPSデスクトップ**: XFCE4 + xrdp（SSHトンネル経由、`neocloop/AYfnhKtist6M`）

## ⚠️ 廃止済み・存在しないもの（間違えないこと）

- **@aisaintel** — X(Twitter)アカウント **廃止。存在しない。**
- **AISAコンテンツパイプライン（RSS→X→note→Substack）** — **SUSPENDED**。復活予定なし。
- **AISA ブランド** — Nowpatternに統合済み。

## 現在のコンテンツ戦略

**唯一の本命: nowpattern.com**

```
NEO-ONE / NEO-TWO（記事執筆）
  ↓
nowpattern.com / Ghost CMS（メインハブ）
  - 日本語記事 (lang-ja): 23本
  - 英語記事 (lang-en): 16本
  ↓
配信（現在稼働中）
  note    — キュー3件 pending（note-auto-post.py）
  Substack — substack-api コンテナ稼働中
  X       — アカウントなし・投稿なし
```

## Nowpattern.com 詳細

- Ghost CMS（`ghost-nowpattern.service`、SQLite、port 2368）
- SSL: Let's Encrypt（Caddy自動更新）✅
- Admin: `https://nowpattern.com/ghost/`
- Admin API: `/opt/cron-env.sh`の`NOWPATTERN_GHOST_ADMIN_API_KEY`
- `/etc/hosts`に`127.0.0.1 nowpattern.com`追加済み
- **タクソノミー v3.0**: Deep Pattern一択（Speed Log廃止）
  - 3層: ジャンル(13) × イベントタグ(19) × 力学タグ(16)
  - 力学は4×4構造: 支配×対立×崩壊×転換

## Nowpatternスクリプト群（ローカル）

| スクリプト | 説明 |
|---|---|
| `scripts/nowpattern_article_builder.py` | Deep Pattern HTML生成 |
| `scripts/nowpattern_publisher.py` | Ghost投稿 + 記事インデックス管理 |
| `scripts/gen_dynamics_diagram.py` | 力学ダイアグラムSVG自動生成 |
| `docs/NEO_INSTRUCTIONS_V2.md` | NEO執筆指示書v2.0 |

## news-analyst-pipeline（稼働中）

- スクリプト: `/opt/shared/scripts/news-analyst-pipeline.py`
- cron: 1日3回（JST 10:00 / 16:00 / 22:00）
- 投稿先: Ghost(英語ドラフト) + note(日本語ドラフト) — X投稿は無効
- ⚠️ AISAの遺産。Nowpatternとの統合・整理が未完了。

## コスト状況

| 項目 | コスト |
|---|---|
| Gemini API | 無料枠で運用中 |
| xAI API | $5購入済み（Grok Web検索 + intelligence-feed-v2 X収集） |
| Claude Max | $200/月（NEO-ONE + NEO-TWO + ローカルClaude Code） |
| Google AI Pro | ¥2,900/月（Antigravity用） |

## 未解決の課題（openな項目のみ）

- [ ] **NAVER Blog** — SMS認証が必要なため手動アカウント作成が必要
- [ ] **Medium MEDIUM_TOKEN** — medium.com/me/settings → Integration tokensから手動取得
- [ ] **noteアカウント刷新** — noindex問題、新アカウントで自然な投稿から開始
- [ ] **X APIキーローテーション** — developer.x.com → Keys再生成（要手動）
