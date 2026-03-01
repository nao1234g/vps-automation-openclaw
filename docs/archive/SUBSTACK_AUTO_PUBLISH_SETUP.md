# Substack自動投稿セットアップガイド

> N8N + Python API サーバーでSubstackに自動投稿する完全ガイド

## 📋 概要

このシステムは以下の構成で動作します：

```
PostgreSQL (AISA reports)
  ↓
N8N (スケジュール実行)
  ↓
Substack API Server (Python + FastAPI + python-substack)
  ↓
Substack.com (自動投稿)
```

---

## 🚀 セットアップ手順

### 1. Substack認証情報を取得

1. Substackにログイン: https://substack.com
2. あなたのパブリケーションURLを確認（例: `https://aisaintel.substack.com`）
3. メールアドレスとパスワードを準備

### 2. 環境変数を設定

`.env` ファイルに以下を追加：

```bash
# Substack Publishing API
SUBSTACK_EMAIL=your-email@example.com
SUBSTACK_PASSWORD=your-substack-password
SUBSTACK_PUBLICATION_URL=https://aisaintel.substack.com
```

**セキュリティ注意**：
- `.env` のパーミッションを 600 に設定: `chmod 600 .env`
- `.env` は絶対にGitにコミットしない

### 3. Dockerコンテナを起動

```bash
# ローカル開発環境
docker compose -f docker-compose.quick.yml up -d --build

# VPS本番環境（SSHでアクセスして実行）
cd /opt/openclaw
docker compose -f docker-compose.quick.yml up -d --build substack-api
```

### 4. APIサーバーの動作確認

```bash
# ヘルスチェック
curl http://localhost:8000/health

# 期待するレスポンス:
{
  "status": "healthy",
  "substack_connection": "ok",
  "authenticated": true,
  "user_id": "12345..."
}
```

### 5. N8Nワークフローをインポート

1. N8Nにアクセス: http://localhost:5678 (SSHトンネル経由の場合)
2. **Workflows** → **Import from File**
3. `n8n-workflows/substack-auto-publish-api.json` を選択
4. インポート完了

### 6. PostgreSQL認証情報を設定

N8Nで「Get Latest Unpublished Report」ノードの認証情報を設定：

- **Host**: `postgres`（Docker内部DNS）
- **Database**: `openclaw`（または `.env` の `POSTGRES_DB`）
- **User**: `openclaw`（または `.env` の `POSTGRES_USER`）
- **Password**: `.env` の `POSTGRES_PASSWORD`

### 7. テスト実行

1. N8Nで「Substack Auto Publish - API方式」ワークフローを開く
2. 右上の **Execute Workflow** をクリック
3. 実行ログを確認

**期待する結果**：
- PostgreSQLから最新の未投稿レポートを取得
- Substack APIサーバーに送信
- Substackに投稿成功
- PostgreSQLの `published_at` カラムが更新される

---

## 🔧 トラブルシューティング

### エラー: `substack_connection: failed`

**原因**: Substack認証情報が間違っている

**解決策**:
1. `.env` の `SUBSTACK_EMAIL`, `SUBSTACK_PASSWORD` を確認
2. Substackにログインできるか確認
3. コンテナを再起動: `docker restart openclaw-substack-api`

### エラー: `Connection refused to substack-api:8000`

**原因**: Substack APIコンテナが起動していない

**解決策**:
```bash
# コンテナの状態を確認
docker ps | grep substack-api

# ログを確認
docker logs openclaw-substack-api

# 再起動
docker restart openclaw-substack-api
```

### エラー: `No unpublished report found`

**原因**: `aisa.generated_reports` テーブルに未投稿のレポートがない

**解決策**:
```sql
-- PostgreSQLで確認
SELECT * FROM aisa.generated_reports WHERE published_at IS NULL;

-- テストデータを挿入
INSERT INTO aisa.generated_reports (title, content)
VALUES ('Test Post', '<h1>Test Content</h1><p>This is a test.</p>');
```

---

## 📊 APIエンドポイント

### `POST /publish`

Substackに記事を投稿します。

**リクエスト例**:
```json
{
  "title": "AISA Newsletter - 2026-02-14",
  "content": "<h1>今日のAIニュース</h1><p>本文...</p>",
  "subtitle": "AIトレンドレポート",
  "is_draft": false
}
```

**レスポンス例**:
```json
{
  "success": true,
  "message": "Post published successfully",
  "post_id": "123456",
  "post_url": "https://aisaintel.substack.com/p/your-post-slug"
}
```

**パラメータ**:
- `title` (必須): 記事タイトル
- `content` (必須): 記事本文（HTML形式）
- `subtitle` (任意): サブタイトル
- `is_draft` (デフォルト: false):
  - `true`: 下書きとして保存
  - `false`: 即座に公開

### `GET /health`

APIサーバーのヘルスチェック

**レスポンス例**:
```json
{
  "status": "healthy",
  "substack_connection": "ok",
  "authenticated": true,
  "user_id": "12345..."
}
```

---

## ⏰ スケジュール設定

### N8Nスケジュールトリガーの変更

デフォルトは「毎日24時間ごと」ですが、特定の時刻に変更できます：

1. N8Nワークフローの「Schedule」ノードを開く
2. **Trigger Times** → **Custom** を選択
3. **Cron Expression** に以下を入力：

```
0 9 * * *   # 毎日 午前9時（JST）
0 9,18 * * * # 毎日 午前9時と午後6時
0 9 * * 1-5  # 平日のみ 午前9時
```

---

## 🔒 セキュリティ

### 本番環境での注意事項

1. **Substackパスワードは強力なものを使用**
2. **`.env` ファイルのパーミッションを 600 に設定**
   ```bash
   chmod 600 /opt/openclaw/.env
   ```
3. **Substack APIサーバーのポートは外部公開しない**
   - docker-compose.quick.yml では `127.0.0.1:8000:8000` に設定済み
   - N8Nからのみアクセス可能

4. **定期的にパスワードをローテーション**

---

## 📝 ログ確認

### Substack APIサーバーのログ

```bash
# リアルタイムログ
docker logs -f openclaw-substack-api

# 最新100行
docker logs openclaw-substack-api --tail 100
```

### N8Nワークフローの実行履歴

N8N Web UI → **Executions** → 対象ワークフロー → 詳細

---

## 🎯 次のステップ

1. ✅ Substack APIサーバー起動
2. ✅ N8Nワークフローインポート
3. ✅ テスト実行成功
4. ⏰ スケジュール設定（毎日自動実行）
5. 📊 AISA レポート生成の自動化
6. 🔔 Telegram通知（成功/失敗）

---

## 📚 参考資料

- [python-substack GitHub](https://github.com/ma2za/python-substack)
- [FastAPI公式ドキュメント](https://fastapi.tiangolo.com/)
- [N8N公式ドキュメント](https://docs.n8n.io/)
- [Substack公式サポート](https://support.substack.com/)

---

*最終更新: 2026-02-14*
