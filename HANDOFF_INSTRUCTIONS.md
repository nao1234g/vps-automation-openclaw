# 🔄 プロジェクト引き継ぎ指示書
**作成日時:** 2026-02-06 04:26 UTC  
**最終確認:** 2026-02-06 04:36 UTC  
**現在のステータス:** ✅ 全サービス正常稼働中

> 続き作業は `NEXT_STEPS_IDE.md` を最優先で参照

---

## 📊 現在の環境状態

### 起動中のサービス（docker compose）

| サービス | コンテナ名 | ステータス | ポート | ヘルスチェック |
|---------|-----------|-----------|-------|--------------|
| PostgreSQL | `openclaw-postgres` | ✅ Healthy | 5432 | OK |
| OpenNotebook | `openclaw-opennotebook` | ✅ Healthy | 8080 | OK (DBコネクテッド) |
| N8N | `openclaw-n8n` | ✅ Running | 5678 | OK |
| OpenClaw Agent | `openclaw-agent` | ✅ Healthy | 3000 | OK |
| Nginx | `openclaw-nginx` | ✅ Running | 80 | OK |

**起動コマンド:** `docker compose up -d` (メインの docker-compose.yml 使用)

**アクセスURL（2026-02-06 04:36 UTC時点）:**
- OpenNotebook: http://localhost:8080
- N8N: http://localhost:5678
- OpenClaw: http://localhost:3000
- Nginx: http://localhost:80

---

## 🔧 直前に解決した問題

### 問題1: OpenNotebookが unhealthy 状態
**症状:**
```bash
curl http://localhost:8080/health
# → 503 Service Unavailable
# → {"status":"error","database":"disconnected"}
```

**根本原因:**
1. **opennotebookスキーマ未作成**
   - PostgreSQL初期化スクリプト（`docker/postgres/init/01-init.sql`）が途中までしか実行されていなかった
   - 存在するスキーマ: `n8n` のみ
   - 不足: `opennotebook`, `openclaw` スキーマ

2. **ネットワーク分離**
   - OpenNotebook: `minimal-network` に接続
   - PostgreSQL: `openclaw-network` に接続
   - 異なるネットワークでDNS解決不可

3. **パスワード不一致**
   - PostgreSQLの実設定値と、OpenNotebookの `DATABASE_URL` の認証情報が不一致
   - 固定値の直書きではなく `.env` を単一の正とする運用に統一

**解決方法:**
```bash
# 1. SQLスキーマを手動作成
cat /workspaces/vps-automation-openclaw/docker/postgres/init/01-init.sql | \
  docker exec -i openclaw-postgres psql -U openclaw -d openclaw

# 2. 環境をクリーンに再起動（パスワードと接ネットワーク修正）
docker compose down
docker compose up -d
```

**結果:** ✅ 全サービス正常稼働

### 問題2: OpenClaw Agent が Restarting する
**症状:**
```bash
docker ps
# → openclaw-agent Restarting
docker compose logs openclaw
# → Gateway auth is set to token, but no token is configured.
```

**根本原因:**
- `.env` に `OPENCLAW_GATEWAY_TOKEN` は存在していたが、`docker-compose.yml` の `openclaw.environment` に変数を渡していなかった

**解決方法:**
```yaml
# docker-compose.yml (openclaw.environment)
OPENCLAW_GATEWAY_TOKEN: ${OPENCLAW_GATEWAY_TOKEN}
OPENCLAW_PASSWORD: ${OPENCLAW_PASSWORD:-}
```

```bash
docker compose up -d --force-recreate openclaw
```

**結果:** ✅ `openclaw-agent` が healthy で安定

---

## 🗄️ データベース情報

### PostgreSQL接続情報
```bash
ホスト: postgres (Dockerネットワーク内) / localhost:5432 (ホストから)
ユーザー: openclaw
パスワード: .env の POSTGRES_PASSWORD を参照（この文書に平文記載しない）
データベース: openclaw
```

### スキーマ構成
```sql
-- 存在するスキーマ（確認済み）
\dn
         List of schemas
     Name     |       Owner       
--------------+-------------------
 n8n          | openclaw
 openclaw     | openclaw
 opennotebook | openclaw
 public       | pg_database_owner
```

### OpenNotebookテーブル
```sql
-- notebooks テーブル
opennotebook.notebooks (id, title, content, created_at, updated_at, deleted_at)

-- notes テーブル
opennotebook.notes (id, notebook_id, title, content, tags, created_at, updated_at)
```

### OpenClawテーブル
```sql
-- conversations テーブル
openclaw.conversations (id, telegram_chat_id, title, context, created_at, updated_at)

-- messages テーブル
openclaw.messages (id, conversation_id, role, content, metadata, created_at)
```

---

## 📁 重要なファイル・ディレクトリ

### 環境設定
- **`.env`** - 環境変数（gitignore対象、パスワード含む）
- **`.env.example`** - 環境変数テンプレート
- **`.env.development.example`** - 開発環境用
- **`.env.production.example`** - 本番環境用

### Docker Compose設定
- **`docker-compose.yml`** - メイン設定（現在使用中）
- **`docker-compose.dev.yml`** - 開発環境オーバーライド
- **`docker-compose.minimal.yml`** - 最小構成テスト用
- **`docker-compose.production.yml`** - 本番環境用（SSL/Nginx完全版）

### 初期化スクリプト
- **`docker/postgres/init/01-init.sql`** - PostgreSQL初期化SQL
  - ⚠️ 注意: 初回起動時のみ実行される
  - 再実行するには: `docker volume rm` でボリューム削除が必要

### サービス別ディレクトリ
```
docker/
├── openclaw/          # OpenClaw Dockerfile & entrypoint
├── opennotebook/      # OpenNotebook Dockerfile & アプリケーション
│   └── app/
│       ├── server.js  # Expressサーバー
│       └── package.json
├── postgres/
│   ├── init/          # 初期化SQL
│   └── migrations/    # マイグレーションSQL（未使用）
├── nginx/             # Nginx設定（リバースプロキシ）
└── n8n/workflows/     # N8Nワークフロー定義
```

### データ永続化
```
data/
├── postgres/          # PostgreSQLデータ（Dockerボリューム）
├── openclaw/          # OpenClawデータ
├── n8n/               # N8Nデータ
├── opennotebook/      # OpenNotebookデータ
└── opennotebook_uploads/  # アップロードファイル

logs/
├── openclaw/          # OpenClawログ
├── n8n/               # N8Nログ
└── opennotebook/      # OpenNotebookログ
```

---

## 🚀 Makefileコマンド（開発用）

### 基本コマンド
```bash
# ヘルプ表示
make help

# 環境セットアップ
make setup-dirs        # ディレクトリ作成
make setup-env         # .env作成
make validate-env      # 環境変数チェック

# 最小構成（開発・テスト用）
make minimal           # PostgreSQL + OpenNotebook + N8N
make minimal-logs      # ログ表示
make minimal-down      # 停止
make minimal-clean     # 完全削除

# 開発環境
make dev               # 全サービス + Adminer起動
make dev-logs          # ログ表示
make dev-down          # 停止

# 本番環境
make prod              # 本番環境起動（Nginx SSL含む）
make prod-logs         # ログ表示

# ヘルスチェック
make health            # 全サービスヘルスチェック

# バックアップ・リストア
make backup            # データバックアップ
make restore           # データリストア

# セキュリティ
make scan              # セキュリティスキャン（Trivy）

# クリーンアップ
make clean             # 停止 + コンテナ削除
make clean-volumes     # ボリューム削除（⚠️データ消失）
```

---

## 🔍 トラブルシューティング

### OpenClaw Agent が Restarting する（発生時の対処）

`docker compose logs openclaw` で以下が出る場合:
```text
Gateway auth is set to token, but no token is configured.
Set gateway.auth.token (or OPENCLAW_GATEWAY_TOKEN), or pass --token.
```

対処:
```bash
# 1) .env にトークンを設定（32文字以上推奨）
OPENCLAW_GATEWAY_TOKEN=REPLACE_WITH_LONG_RANDOM_TOKEN

# 2) コンテナ再作成
docker compose up -d --force-recreate openclaw

# 3) 起動確認
docker ps --format "table {{.Names}}\t{{.Status}}" | grep openclaw-agent
curl -I http://localhost:3000/ | head -n 1
```

### ヘルスチェックコマンド

```bash
# 全コンテナの状態確認
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 個別サービスヘルスチェック
curl http://localhost:8080/health  # OpenNotebook
curl -I http://localhost:3000/ | head -n 1  # OpenClaw
curl http://localhost:5678/        # N8N

# PostgreSQL接続確認
docker exec openclaw-postgres psql -U openclaw -c "SELECT 1;"

# スキーマ確認
docker exec openclaw-postgres psql -U openclaw -c "\dn"

# テーブル確認
docker exec openclaw-postgres psql -U openclaw -c "\dt opennotebook.*"
```

### ログ確認

```bash
# 全サービスのログ
docker compose logs -f

# 個別サービス
docker compose logs -f opennotebook
docker compose logs -f postgres
docker compose logs -f openclaw
docker compose logs -f n8n

# エラーのみ
docker compose logs | grep -i error
```

### ネットワーク問題

```bash
# ネットワーク一覧
docker network ls

# ネットワーク詳細（接続コンテナ確認）
docker network inspect vps-automation-openclaw_openclaw-network

# コンテナのネットワーク接続確認
docker inspect openclaw-opennotebook | jq '.[0].NetworkSettings.Networks | keys'

# DNS解決テスト
docker exec openclaw-opennotebook ping -c 2 postgres

# 手動でネットワークに接続
docker network connect vps-automation-openclaw_openclaw-network <container_name>
```

### データベース問題

```bash
# データベース初期化スクリプトの再実行
cat docker/postgres/init/01-init.sql | \
  docker exec -i openclaw-postgres psql -U openclaw -d openclaw

# 接続文字列確認
docker exec openclaw-opennotebook printenv DATABASE_URL

# PostgreSQLのパスワード確認
docker inspect openclaw-postgres | jq '.[0].Config.Env[] | select(startswith("POSTGRES_PASSWORD="))'
```

### 完全リセット（最終手段）

```bash
# すべて停止・削除
docker compose down -v  # ⚠️ ボリュームも削除（データ消失）

# クリーン起動
docker compose up -d --build
```

---

## 📝 環境変数の重要ポイント

### .envファイルの必須変数

```bash
# Database（現在の設定）
POSTGRES_USER=openclaw
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD   # ⚠️ 重要（実値は .env のみ）
POSTGRES_DB=openclaw

# LLM API Keys
ANTHROPIC_API_KEY=sk-ant-CHANGE_ME           # Claude API
OPENAI_API_KEY=sk-proj-CHANGE_ME            # OpenAI API
ZHIPUAI_API_KEY=CHANGE_ME                   # ZhipuAI API（オプション）

# OpenClaw
OPENCLAW_GATEWAY_TOKEN=CHANGE_ME_TO_RANDOM_TOKEN
TELEGRAM_BOT_TOKEN=0000000000:CHANGE_ME

# N8N
N8N_USER=admin
N8N_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD
N8N_ENCRYPTION_KEY=CHANGE_ME_32_RANDOM_CHARACTERS

# OpenNotebook
OPENNOTEBOOK_API_KEY=CHANGE_ME_TO_YOUR_API_KEY
```

### パスワード不一致に注意

docker-compose.ymlとdocker-compose.minimal.ymlで異なるデフォルトパスワードを使用：
- **minimal.yml:** `dev_password`
- **メインyml:** `.env` から読み込み（`POSTGRES_PASSWORD`）

**⚠️ 混在させるとDB接続エラーになります！**

---

## 🎯 次のステップ（優先順位順）

### 即座に実行すべきこと
1. **全サービスのヘルスチェック**
   ```bash
   docker ps
   curl http://localhost:8080/health | jq .
   curl -I http://localhost:3000/ | head -n 1
   ```

2. **ログ監視（エラー確認）**
   ```bash
   docker compose logs -f --tail=100
   ```

3. **OpenClawトークン未設定の確認**
   ```bash
   grep '^OPENCLAW_GATEWAY_TOKEN=' .env
   docker compose logs --tail=80 openclaw
   ```

4. **環境変数の確認**
   ```bash
   ./scripts/validate_env.sh
   ```

### 開発継続の場合
1. **OpenClawのスキル開発**
   - `skills/` ディレクトリに新しいスキルを追加
   - 既存: `n8n-integration.js`, `opennotebook-integration.js`, `vps-maintenance.js`

2. **N8Nワークフロー作成**
   - N8N UI: http://localhost:5678
   - ユーザー: `admin` / パスワード: `.env` の `N8N_PASSWORD`

3. **E2Eテスト実行**
   ```bash
   cd tests/e2e
   npm test
   ```

4. **セキュリティスキャン**
   ```bash
   ./scripts/security_scan.sh --all
   ```

### 本番デプロイの場合
1. **環境変数を本番用に変更**
   ```bash
   cp .env.production.example .env
   # .envを編集（強力なパスワード、本番APIキー）
   ```

2. **SSL証明書セットアップ**
   ```bash
   ./scripts/setup_ssl.sh
   ```

3. **本番環境起動**
   ```bash
   docker compose -f docker-compose.production.yml up -d
   ```

4. **バックアップ設定**
   ```bash
   ./scripts/setup_cron_jobs.sh  # 定期バックアップ有効化
   ```

---

## 📚 参考ドキュメント（優先順）

1. **QUICK_REFERENCE.md** - よく使うコマンド集
2. **DEVELOPMENT.md** - 開発ガイド
3. **ARCHITECTURE.md** - システム設計
4. **SECURITY_CHECKLIST.md** - セキュリティ対策リスト
5. **OPERATIONS_GUIDE.md** - 運用ガイド
6. **TROUBLESHOOTING.md** - トラブルシューティング
7. **CHANGELOG.md** - 変更履歴（v1.2.0が最新）

---

## ⚠️ 重要な注意事項

### セキュリティ
- ❌ `.env` ファイルを**絶対にgitにコミットしない**
- ❌ 引き継ぎ文書・Issue・PRに**実パスワード/実トークンを記載しない**
- ✅ SSH鍵認証を必ず設定
- ✅ UFW/Fail2ban を本番環境で有効化
- ✅ 定期的にセキュリティスキャン実行

### データバックアップ
- PostgreSQLデータは `data/postgres/` に永続化
- **ボリューム削除前に必ずバックアップ**
  ```bash
  make backup  # または
  ./scripts/backup.sh
  ```

### OpenClaw権限
- OpenClawは**非常に強力な権限**を持つ
- メインPCへのインストールは危険
- **専用VPS環境での運用を強く推奨**

---

## 🔄 引き継ぎ時のチェックリスト

**次の担当者は以下を確認してください:**

- [ ] 全コンテナが起動している (`docker ps`)
- [ ] OpenNotebook healthyステータス (`curl localhost:8080/health`)
- [ ] PostgreSQL接続可能 (`docker exec openclaw-postgres psql -U openclaw -c "\dn"`)
- [ ] ログにエラーがない (`docker compose logs --tail=100`)
- [ ] .envファイルが存在し、パーミッション600 (`ls -la .env`)
- [ ] データディレクトリが存在 (`ls -la data/`)
- [ ] この引き継ぎ文書を読んだ ✅

---

## 💬 よくある質問

**Q: OpenNotebookが unhealthy になる**  
A: このドキュメントの「トラブルシューティング > データベース問題」参照

**Q: docker compose up でネットワークエラー**  
A: `docker compose down && docker compose up -d` でクリーンに再起動

**Q: PostgreSQL初期化スクリプトが実行されない**  
A: 初回起動時のみ実行。再実行するには `docker volume rm vps-automation-openclaw_postgres_data` 後に起動

**Q: パスワード認証エラー**  
A: .env の `POSTGRES_PASSWORD` とdocker-composeのDATABASE_URLが一致するか確認

---

## 📞 サポート情報

- **Issues:** GitHub Issues で報告
- **ドキュメント:** プロジェクトルートの `*.md` ファイル参照
- **ログ:** `logs/` ディレクトリ
- **セキュリティ報告:** セキュリティ問題は非公開で報告

---

**引き継ぎ完了条件:**
✅ 全サービスがhealthy状態  
✅ このドキュメントを理解  
✅ 緊急時の対処方法を把握  

**現在の状態:** ✅ すべて正常稼働中（最終確認: 2026-02-06 04:36 UTC）

---

**作成者:** GitHub Copilot (Claude Sonnet 4.5)  
**最終更新:** 2026-02-06 04:26 UTC
