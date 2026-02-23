# NEO-GPT 引継書（完全版）

> **作成日**: 2026-02-20 15:53 JST
> **作成者**: Antigravity セッション 4bc41945
> **目的**: 別の Antigravity エージェントが NEO-GPT のセットアップを完了するための引継書

---

## 1. NEO-GPT とは何か

NEO-GPT は、NEO-1/2（Claude Code SDK ベース）のバックアップとして構築する **Telegram bot**。
バックエンドに **OpenAI Codex CLI** を使い、**ChatGPT Pro サブスク**（$200/月）の枠内で動作する（追加API課金なし）。

| 項目 | 値 |
|------|-----|
| Bot名 | NEO-GPT |
| Telegram ユーザー名 | `@neogpt_nn_bot` |
| Bot Token | `8403014876:AAHZOPGq1lsvfh_Wgncu5YzEpfdb6WHc9L0` |
| VPS IP | `163.44.124.123` |
| VPS ユーザー | `root` |
| VPS パスワード | `MySecurePass2026!` |
| SSH鍵 | このPCにはSSH鍵がない。パスワード認証で接続する |
| インストール先 | `/opt/neo3-codex/` |
| systemd サービス名 | `neo3-telegram.service` |
| Codex CLI バージョン | v0.104.0（インストール済み） |
| ChatGPT アカウント | `marketingilyone@gmail.com` |

---

## 2. 完了済みの作業（触る必要なし）

以下はすべて完了しています。再実行しないでください。

### 2-1. ファイル作成・Git push 済み
- `scripts/neo3_orchestrator.py` — Telegram bot 本体（Codex CLI バックエンド）
- `scripts/setup_neo3.sh` — VPS セットアップスクリプト
- `deploy/neo3-telegram.service` — systemd サービス定義
- `CLAUDE_CODE_SETUP.md` — NEO-GPT セクション追記済み

### 2-2. VPS 上で完了済み
- ✅ Node.js v22.22.0 インストール済み
- ✅ Codex CLI v0.104.0 インストール済み（`/usr/bin/codex`）
- ✅ python-telegram-bot パッケージ インストール済み
- ✅ `/opt/neo3-codex/` ディレクトリ作成済み
- ✅ `/opt/neo3-codex/neo3_orchestrator.py` 配置済み
- ✅ `/opt/neo3-codex/.env` 作成済み
- ✅ `/opt/neo3-codex/workspace/` Git初期化済み
- ✅ `/opt/neo3-codex/logs/` ディレクトリ作成済み
- ✅ `/etc/systemd/system/neo3-telegram.service` 登録済み
- ✅ `systemctl daemon-reload` 実行済み
- ✅ ChatGPT セキュリティ設定でデバイスコード認証 **有効化済み**

---

## 3. 残りの作業（これをやってほしい）

### 作業A: Codex CLI の認証（最重要）

**状況**: `codex login --device-auth` を複数回実行したため、レート制限（429 Too Many Requests）になった。5〜10分以上経過しているので、再試行可能なはず。

**手順**:

```bash
# Step 1: VPSにSSH接続
ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password root@163.44.124.123
# パスワード: MySecurePass2026!

# Step 2: codex login 実行
codex login --device-auth
```

**codex login が表示するもの**:
```
Welcome to Codex [v0.104.0]

Follow these steps to sign in with ChatGPT using device code authorization:

1. Open this link in your browser and sign in to your account
   https://auth.openai.com/codex/device

2. Enter this one-time code (expires in 15 minutes)
   XXXX-XXXXX     ← ★このコードをコピーする
```

**ユーザーに伝えること**:
1. ブラウザで https://auth.openai.com/codex/device を開く
2. 表示されたコード（`XXXX-XXXXX`）を入力する
3. ChatGPT アカウント（`marketingilyone@gmail.com`）でログイン済みの状態で「続行」を押す
4. 承認完了するとターミナルに `Successfully logged in` のようなメッセージが出る

**429エラーが再度出た場合**: 5分待ってから再試行する。

**重要**: ChatGPT のセキュリティ設定で以下が有効になっていることを事前確認：
- 「Codex CLI」→ 有効
- 「Codex に対してデバイスコード認証を有効にする」→ ON
- 設定URL: https://chatgpt.com/settings#settings/Security

### 作業B: ALLOWED_USERS の設定

認証が完了したら、`.env` の `ALLOWED_USERS` にオーナーの Telegram User ID を設定する。

```bash
# オーナーの Telegram User ID を取得
# 方法1: @userinfobot にメッセージを送ると自分のIDが返ってくる
# 方法2: 既存の NEO-1/2 の .env から取得
cat /opt/claude-code-telegram/.env | grep ALLOWED_USERS

# .env を編集
nano /opt/neo3-codex/.env
# ALLOWED_USERS= の行にIDを記入（例: ALLOWED_USERS=123456789）
```

### 作業C: サービス起動

```bash
# サービス有効化 & 起動
systemctl enable neo3-telegram
systemctl start neo3-telegram

# 起動確認
systemctl status neo3-telegram

# ログ確認（リアルタイム）
journalctl -u neo3-telegram -f
```

### 作業D: 動作テスト

1. Telegram で `@neogpt_nn_bot` を検索してチャットを開く
2. `/start` を送信 → ウェルカムメッセージが返ってくればOK
3. `/status` を送信 → Codex CLI バージョンとモデル情報が表示される
4. 「Hello, what can you do?」を送信 → Codex CLI が処理して結果が返ってくる

**テスト失敗時のデバッグ**:
```bash
# ログを確認
journalctl -u neo3-telegram --no-pager -n 50

# 手動で orchestrator を起動してエラーを確認
cd /opt/neo3-codex
source .env && export TELEGRAM_BOT_TOKEN ALLOWED_USERS CODEX_TIMEOUT CODEX_MODEL CODEX_WORK_DIR LOG_DIR
python3 neo3_orchestrator.py

# Codex CLI 単体テスト
codex exec "echo hello world" --full-auto --model o4-mini
```

---

## 4. アーキテクチャ図

```
┌─────────────────────────────────────────────────┐
│                    VPS (163.44.124.123)          │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │  neo3-telegram.service (systemd)         │    │
│  │                                          │    │
│  │  neo3_orchestrator.py                    │    │
│  │    ├─ Telegram Bot (polling)             │    │
│  │    │   └─ @neogpt_nn_bot                 │    │
│  │    │                                     │    │
│  │    └─ codex exec (subprocess)            │    │
│  │        ├─ --full-auto                    │    │
│  │        ├─ --model o4-mini                │    │
│  │        └─ auth: ~/.codex/auth.json       │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  /opt/neo3-codex/                                │
│    ├─ neo3_orchestrator.py                       │
│    ├─ .env                                       │
│    ├─ workspace/  (codex の作業ディレクトリ)       │
│    └─ logs/neo3.log                              │
└─────────────────────────────────────────────────┘
         ▲                    ▲
         │ Telegram API       │ OpenAI API
         │ (polling)          │ (ChatGPT Pro)
         ▼                    ▼
    📱 ユーザー          🤖 OpenAI Codex
    (Telegram)           (o4-mini model)
```

---

## 5. NEO-1/2 との切替

```bash
# NEO-1/2 停止 → NEO-GPT 起動
systemctl stop claude-telegram && systemctl start neo3-telegram

# NEO-GPT 停止 → NEO-1/2 復帰  
systemctl stop neo3-telegram && systemctl start claude-telegram
```

---

## 6. トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `codex: command not found` | PATHにない | `npm i -g @openai/codex` を再実行 |
| `429 Too Many Requests` | レート制限 | 5〜10分待って再試行 |
| `続行ボタンがグレー` | セキュリティ設定未完了 | ChatGPT設定でCodex CLIとデバイスコード認証を有効化 |
| Bot が無反応 | サービス未起動 | `systemctl start neo3-telegram` |
| `TELEGRAM_BOT_TOKEN が設定されていません` | .env読み込み失敗 | `/opt/neo3-codex/.env` の内容を確認 |
| Codex タイムアウト | 処理が300秒超過 | `.env` の `CODEX_TIMEOUT` を増やす |
| `auth.json not found` | 認証未完了 | `codex login --device-auth` を実行 |

---

## 7. ファイル一覧（リポジトリ内）

```
vps-automation-openclaw-main/
├── scripts/
│   ├── neo3_orchestrator.py     ← Telegram bot 本体
│   └── setup_neo3.sh            ← VPS セットアップスクリプト
├── deploy/
│   └── neo3-telegram.service    ← systemd サービスファイル
└── CLAUDE_CODE_SETUP.md         ← NEO-GPT ドキュメント追記済み
```

---

## 8. 作業チェックリスト（次のエージェント用）

```
[ ] codex login --device-auth を実行（429が出たら5分待つ）
[ ] ユーザーにURLとコードを伝える
[ ] ユーザーがブラウザで認証を完了
[ ] ALLOWED_USERS を .env に設定
[ ] systemctl enable --now neo3-telegram
[ ] Telegram で /start テスト
[ ] Telegram で簡単なプロンプトテスト
[ ] 結果をユーザーに報告
```

---

**以上。この引継書に従えば、NEO-GPT の残り作業は 10〜15分で完了できます。**
