# OpenClaw Control UI ペアリング問題 解決ガイド

## 問題の概要

OpenClaw GatewayとブラウザベースのControl UIを接続する際、「disconnected (1008): pairing required」エラーが発生する問題。

## 原因

OpenClaw Gatewayはデフォルトでデバイスペアリングを要求しますが、ブラウザからの接続時にはペアリングプロセスが完了できないため、接続が拒否されます。

## 解決策

### 1. ペアリング無効化（推奨）

**手順:**

1. `.env` ファイルに以下を追加:
   ```bash
   OPENCLAW_DISABLE_PAIRING=true
   ```

2. OpenClawコンテナを再起動:
   ```bash
   docker compose -f docker-compose.quick.yml restart openclaw
   ```

3. ブラウザで `http://localhost:3000` にアクセス

4. パスワード入力を求められたら、`.env` の `OPENCLAW_GATEWAY_TOKEN` を入力

### 2. ペアリング状態確認

**専用スクリプト:**
```bash
./scripts/check_openclaw_pairing.sh
```

**確認項目:**
- コンテナ起動状態
- `OPENCLAW_DISABLE_PAIRING` 環境変数
- Gatewayプロセスの `--no-pairing` オプション
- HTTP/WebSocket接続テスト

**詳細モード:**
```bash
./scripts/check_openclaw_pairing.sh --verbose
```

## 設定詳細

### 環境変数

| 変数名 | 説明 | デフォルト値 | 推奨値 |
|--------|------|--------------|--------|
| `OPENCLAW_DISABLE_PAIRING` | ペアリング無効化 | `false` | `true` |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway認証トークン | - | 強力なランダム文字列 |

### Gatewayコマンドオプション

```bash
openclaw gateway run \
    --port 3000 \
    --bind lan \
    --password "${OPENCLAW_GATEWAY_TOKEN}" \
    --no-pairing \
    --verbose
```

## トラブルシューティング

### エラー: "pairing required"

**症状:**
- ブラウザで接続時にWebSocketが即座に切断される
- コンソールに `disconnected (1008): pairing required` エラー

**解決方法:**
1. `.env` に `OPENCLAW_DISABLE_PAIRING=true` を追加
2. コンテナ再起動: `docker compose restart openclaw`
3. ブラウザキャッシュをクリア
4. 再度接続を試みる

### エラー: "authentication failed"

**症状:**
- パスワード入力後に認証エラー

**解決方法:**
1. `.env` の `OPENCLAW_GATEWAY_TOKEN` を確認
2. トークンをコピーして正確に入力
3. トークンに特殊文字が含まれる場合はエスケープを確認

### コンテナが起動しない

**確認項目:**
```bash
# コンテナログ確認
docker logs openclaw-agent

# 環境変数確認
docker exec openclaw-agent env | grep OPENCLAW

# ヘルスチェック
curl -sf http://localhost:3000/ || echo "Failed"
```

## セキュリティ考慮事項

### ペアリング無効化のリスク

**低リスク（内部ネットワーク）:**
- Dockerネットワーク内部のみで使用
- `127.0.0.1` へのバインド
- Nginxリバースプロキシ経由でのみ外部公開

**推奨設定:**
- ペアリング無効化 (`OPENCLAW_DISABLE_PAIRING=true`)
- 強力なGatewayトークン（32文字以上のランダム文字列）
- HTTPSによる通信の暗号化
- ファイアウォールでポート制限

### ペアリング有効化が必要な場合

**シナリオ:**
- インターネット経由で直接公開
- 複数のユーザーが異なるデバイスから接続
- 最高レベルのセキュリティが必要

**設定:**
```bash
OPENCLAW_DISABLE_PAIRING=false
```

**ペアリング手順:**
1. OpenClaw CLIツールを使用してデバイスを登録
2. ペアリングコードを生成
3. ブラウザでペアリングコードを入力
4. デバイス承認を完了

## 検証方法

### 1. 基本接続テスト

```bash
# HTTP接続
curl -I http://localhost:3000/

# 期待される応答: HTTP/1.1 200 OK または 302 Found
```

### 2. WebSocket接続テスト

```bash
# wscatがインストールされている場合
npm install -g wscat
wscat -c ws://localhost:3000/

# 接続成功時: "Connected" メッセージ
```

### 3. Control UI ブラウザテスト

1. ブラウザで `http://localhost:3000` を開く
2. 開発者ツール（F12）でConsoleタブを確認
3. WebSocket接続のステータスを確認
   - 成功: `WebSocket connection established`
   - 失敗: `disconnected (1008): pairing required`

### 4. 自動診断スクリプト

```bash
./scripts/check_openclaw_pairing.sh
```

**正常時の出力:**
```
========================================
  診断結果まとめ
========================================

✅ 確認項目:
  1. コンテナ状態: 起動中
  2. ペアリング設定: true
  3. Gateway プロセス: 実行中
  4. HTTP接続: HTTP 200

[SUCCESS] OpenClaw Gateway は正常に動作しています！

🌐 Control UI アクセス方法:
  1. ブラウザで http://localhost:3000 を開く
  2. パスワード入力を求められたら、.env の OPENCLAW_GATEWAY_TOKEN を入力
  3. ペアリングは不要です（自動的にスキップ）
```

## 関連ファイル

### 実装ファイル

- [docker/openclaw/entrypoint.sh](docker/openclaw/entrypoint.sh) - Gateway起動スクリプト
- [docker-compose.quick.yml](docker-compose.quick.yml) - Docker Compose設定
- [.env.example](.env.example) - 環境変数テンプレート
- [scripts/check_openclaw_pairing.sh](scripts/check_openclaw_pairing.sh) - 診断スクリプト

### ドキュメント

- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - コマンドクイックリファレンス
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - トラブルシューティング全般
- [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) - 運用ガイド

## 更新履歴

### 2026-02-04
- **問題解決:** Control UIペアリング問題の修正
- **追加:** `OPENCLAW_DISABLE_PAIRING` 環境変数
- **追加:** `--no-pairing` Gatewayオプション
- **追加:** `check_openclaw_pairing.sh` 診断スクリプト
- **更新:** ドキュメント整備

## サポート

問題が解決しない場合:

1. **ログ確認:**
   ```bash
   docker logs -f openclaw-agent
   ```

2. **診断スクリプト実行:**
   ```bash
   ./scripts/check_openclaw_pairing.sh --verbose
   ```

3. **Issue報告:**
   - [GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues)
   - エラーメッセージとログを添付

4. **コミュニティサポート:**
   - プロジェクトのDiscussionsセクション
   - 関連フォーラム

---

**OpenClaw VPS Automation Project**  
Documentation updated: 2026-02-04
