# VPS & Docker セキュリティチェックリスト

このドキュメントは、VPSにDockerをインストールして運用する際のセキュリティチェックリストです。

## 📋 初期セットアップ

### システムセキュリティ

- [ ] システムを最新にアップデート
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```

- [ ] UFWファイアウォールの設定
  ```bash
  sudo ./scripts/setup_vps_security.sh
  ```
  - [ ] デフォルトポリシー: Incoming拒否、Outgoing許可
  - [ ] 必要なポート（SSH, HTTP, HTTPS）のみ開放
  - [ ] UFW有効化確認

- [ ] Fail2banのインストールと設定
  - [ ] SSHブルートフォース攻撃対策
  - [ ] バン時間: 3600秒以上
  - [ ] リトライ上限: 3回以下

- [ ] 自動セキュリティアップデートの有効化
  - [ ] unattended-upgradesインストール済み
  - [ ] 自動再起動設定（オプション）

### SSH強化

- [ ] SSH設定の変更 (`/etc/ssh/sshd_config`)
  - [ ] `PermitRootLogin no`
  - [ ] `PasswordAuthentication no` （鍵認証設定後）
  - [ ] `PubkeyAuthentication yes`
  - [ ] `MaxAuthTries 3`
  - [ ] `Port 2222` （オプション: デフォルトポート変更）

- [ ] SSH鍵認証の設定
  - [ ] 公開鍵を `~/.ssh/authorized_keys` に追加
  - [ ] パーミッション確認: `chmod 600 ~/.ssh/authorized_keys`
  - [ ] パスワード認証を無効化する前に鍵認証をテスト

- [ ] SSH設定の反映
  ```bash
  sudo systemctl restart sshd
  ```

## 🐳 Docker セキュリティ

### Dockerインストール

- [ ] 古いDockerバージョンの削除
- [ ] 公式リポジトリからインストール
  ```bash
  sudo ./scripts/setup_docker_security.sh
  ```
- [ ] Docker、Docker Compose最新版の確認
  ```bash
  docker --version
  docker compose version
  ```

### Docker Daemon設定

- [ ] `/etc/docker/daemon.json` の作成と設定
  - [ ] `live-restore: true` - デーモン停止時にコンテナ継続
  - [ ] `userland-proxy: false` - パフォーマンス向上
  - [ ] `no-new-privileges: true` - 特権昇格防止
  - [ ] `icc: false` - コンテナ間通信制限
  - [ ] ログローテーション設定
  - [ ] `userns-remap: default` - ユーザーネームスペース分離

- [ ] Dockerサービスの再起動
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl restart docker
  ```

### Docker Socketセキュリティ

- [ ] Docker socketパーミッション設定
  ```bash
  sudo chmod 660 /var/run/docker.sock
  ```

- [ ] Rootlessモードの検討（推奨）
  - [ ] 非rootユーザーでDockerデーモンを実行
  - [ ] セキュリティリスクの最小化

## 🛡️ コンテナセキュリティ

### Docker Composeでのベストプラクティス

- [ ] `security_opt`:
  - [ ] `no-new-privileges:true` - 全コンテナに設定
  - [ ] `apparmor=docker-default` - AppArmorプロファイル

- [ ] `read_only: true` - 可能な限り読み取り専用ファイルシステム

- [ ] Capabilities制限:
  - [ ] `cap_drop: ALL` - 全権限を削除
  - [ ] `cap_add` - 必要最小限の権限のみ追加

- [ ] 非rootユーザーで実行:
  - [ ] `user: "1000:1000"` または適切なUID/GID

- [ ] リソース制限:
  - [ ] CPU制限設定
  - [ ] メモリ制限設定

- [ ] ネットワーク分離:
  - [ ] 内部ネットワークは `internal: true`
  - [ ] 不要なポート公開を避ける

- [ ] ヘルスチェック設定:
  - [ ] 全サービスにヘルスチェック実装

- [ ] ログ設定:
  - [ ] ログローテーション設定（max-size, max-file）

### Dockerfileベストプラクティス

- [ ] 最小限のベースイメージ使用（Alpine推奨）
- [ ] マルチステージビルドでイメージサイズ最小化
- [ ] 非rootユーザーの作成と使用
  ```dockerfile
  RUN addgroup -g 1000 appgroup && \
      adduser -u 1000 -S appuser -G appgroup
  USER appuser
  ```
- [ ] 最新パッケージにアップデート
- [ ] 不要なパッケージをインストールしない
- [ ] dumb-init使用（PID 1問題対策）
- [ ] ヘルスチェック実装
- [ ] .dockerignoreファイルの作成

## 🔍 イメージセキュリティ

### 脆弱性スキャン

- [ ] Trivyのインストール
  ```bash
  # setup_docker_security.sh で自動インストール済み
  ```

- [ ] イメージスキャンの実施
  ```bash
  trivy image <イメージ名>
  ```

- [ ] 定期的なスキャン（週1回推奨）
  ```bash
  ./scripts/security_scan.sh
  ```

- [ ] HIGH/CRITICAL脆弱性の対処
  - [ ] パッケージのアップデート
  - [ ] ベースイメージの変更
  - [ ] 代替パッケージの検討

### イメージ管理

- [ ] 信頼できるソースからのみイメージを取得
- [ ] タグに `latest` を使用しない（バージョン固定）
- [ ] 定期的なイメージの更新
- [ ] 未使用イメージの削除

## 🔐 シークレット管理

- [ ] 環境変数ファイル (`.env`) でシークレット管理
  ```bash
  chmod 600 .env
  echo ".env" >> .gitignore
  ```

- [ ] `.env.example` の作成（値はプレースホルダー）

- [ ] ハードコードされたシークレットの確認と削除

- [ ] Docker Secrets の検討（Swarmモード）

- [ ] シークレットのローテーション計画

## 🌐 ネットワークセキュリティ

- [ ] カスタムブリッジネットワークの使用
  ```bash
  docker network create --driver bridge isolated_network
  ```

- [ ] デフォルトブリッジネットワークを使用しない

- [ ] 内部通信のみのサービスは外部公開しない

- [ ] リバースプロキシ（Nginx/Traefik）の使用
  - [ ] SSL/TLS証明書の設定
  - [ ] セキュリティヘッダーの設定

## 📊 監視とロギング

### セキュリティ監査

- [ ] Docker Bench Securityの定期実行
  ```bash
  sudo /opt/docker-bench-security/docker-bench-security.sh
  ```

- [ ] 監査結果の確認と対処

- [ ] セキュリティスキャンの自動化（cron設定推奨）
  ```cron
  0 2 * * 0 /path/to/security_scan.sh
  ```

### ログ監視

- [ ] Dockerログの確認
  ```bash
  docker logs <コンテナ名>
  ```

- [ ] システムログの確認
  ```bash
  sudo journalctl -u docker.service -f
  ```

- [ ] 異常なアクセスパターンの監視

- [ ] ログ集約ツールの検討（ELKスタック等）

## 🔧 定期メンテナンス

### 週次タスク

- [ ] セキュリティスキャンの実施
  ```bash
  ./scripts/security_scan.sh
  ```

- [ ] ログの確認

- [ ] ディスク使用状況の確認

### 月次タスク

- [ ] システムメンテナンス
  ```bash
  sudo ./scripts/maintenance.sh
  ```

- [ ] Docker Bench Securityの実施

- [ ] バックアップの確認

- [ ] シークレットのローテーション検討

### 随時タスク

- [ ] セキュリティアップデートの適用

- [ ] 脆弱性情報のチェック

- [ ] インシデント対応計画の見直し

## 🚨 インシデント対応

### セキュリティインシデント発生時

1. [ ] 影響範囲の特定
2. [ ] 該当コンテナ/サービスの隔離
3. [ ] ログの保存
4. [ ] 脆弱性の修正
5. [ ] シークレットのローテーション
6. [ ] 再デプロイとテスト
7. [ ] 事後レビューと改善

### 連絡先

- システム管理者: `[連絡先を記入]`
- セキュリティ担当: `[連絡先を記入]`
- インシデント報告: `[連絡先を記入]`

## 📚 参考リンク

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)

## 🛠️ 作成したスクリプト

### セットアップスクリプト

- [scripts/setup_vps_security.sh](scripts/setup_vps_security.sh) - VPS初期セキュリティ設定
- [scripts/setup_docker_security.sh](scripts/setup_docker_security.sh) - Dockerセキュリティ設定

### 運用スクリプト

- [scripts/security_scan.sh](scripts/security_scan.sh) - セキュリティスキャン実行
- [scripts/maintenance.sh](scripts/maintenance.sh) - 定期メンテナンス

### テンプレート

- [docker/docker-compose.secure.template.yml](docker/docker-compose.secure.template.yml) - セキュアなDocker Compose設定
- [docker/Dockerfile.secure.template](docker/Dockerfile.secure.template) - セキュアなDockerfile

## ✅ 最終チェック

導入完了前の最終確認:

- [ ] 全てのスクリプトが実行可能
- [ ] セキュリティスキャンでCRITICAL脆弱性なし
- [ ] Docker Bench Securityで重大な警告なし
- [ ] SSH鍵認証のみでアクセス可能
- [ ] ファイアウォールが有効
- [ ] 全コンテナが非rootユーザーで実行
- [ ] シークレットが適切に管理されている
- [ ] バックアップ計画が確立
- [ ] 監視とアラート設定完了
- [ ] ドキュメント整備完了

---

**重要**: このチェックリストは定期的に見直し、セキュリティ情勢の変化に応じて更新してください。
