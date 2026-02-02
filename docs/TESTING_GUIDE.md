# Testing Guide

## Overview

このガイドでは、OpenClaw VPS プロジェクトの包括的なテスト戦略について説明します。

## テストの種類

### 1. E2E (End-to-End) テスト

**目的**: 実際のユーザーフローをシミュレートし、システム全体が正しく動作することを確認

**ツール**: Playwright

**場所**: `tests/e2e/`

**実行方法**:
```bash
cd tests/e2e
npm install
npm test
```

**カバレッジ**:
- ✅ ヘルスチェックエンドポイント
- ✅ API エンドポイント (コスト追跡、システムメトリクス)
- ✅ 監視システム (Prometheus, Grafana, Alertmanager)
- ✅ セキュリティヘッダー
- ✅ レート制限
- ✅ エラーハンドリング

**詳細**: [tests/e2e/README.md](../tests/e2e/README.md)

---

### 2. インテグレーションテスト

**目的**: 複数のコンポーネント間の連携をテスト

**実行方法**:
```bash
# Docker環境でのテスト
docker compose -f docker-compose.minimal.yml up -d
./scripts/health_check.sh

# データベース接続テスト
docker compose exec postgres psql -U openclaw -d openclaw -c "SELECT 1;"

# API統合テスト
curl http://localhost/health
curl http://localhost/api/costs/daily
```

**カバレッジ**:
- ✅ データベース接続
- ✅ コンテナ間通信
- ✅ API エンドポイント
- ✅ 認証・認可
- ✅ N8N ワークフロー実行

---

### 3. ユニットテスト

**目的**: 個別の関数やモジュールの動作を検証

**実行方法**:
```bash
# OpenClaw アプリケーション
cd openclaw
npm test

# OpenNotebook
cd docker/opennotebook/app
npm test
```

**カバレッジ目標**: 80% 以上

**ベストプラクティス**:
- 各関数に対して最低1つのテストケース
- エッジケースのテスト
- エラーハンドリングのテスト
- モックを使用した外部依存の分離

---

### 4. パフォーマンステスト

**目的**: システムのパフォーマンスとスケーラビリティを評価

**ツール**: カスタムベンチマークスクリプト

**実行方法**:
```bash
./scripts/benchmark.sh
```

**ベンチマーク項目**:
- ✅ API レスポンスタイム
- ✅ データベースクエリ性能
- ✅ ストレージ I/O
- ✅ ネットワークスループット

**パフォーマンス目標**:
- ヘルスチェック: < 200ms
- API エンドポイント: < 1000ms
- データベースクエリ: < 100ms
- ページロード: < 3000ms

---

### 5. セキュリティテスト

**目的**: セキュリティ脆弱性の検出と対策確認

**ツール**:
- Trivy (コンテナ脆弱性スキャン)
- Docker Bench Security
- TruffleHog (シークレット検出)
- ShellCheck (スクリプト静的解析)

**実行方法**:
```bash
# 全セキュリティスキャン実行
./scripts/security_scan.sh

# 個別実行
trivy image openclaw:latest
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -v /var/lib:/var/lib -v /var/run/docker.sock:/var/run/docker.sock \
  docker/docker-bench-security
```

**チェック項目**:
- ✅ コンテナイメージの脆弱性
- ✅ シークレット漏洩
- ✅ Docker セキュリティ設定
- ✅ スクリプトの潜在的問題
- ✅ 依存関係の脆弱性

---

### 6. バックアップ検証テスト

**目的**: バックアップの整合性と復元可能性を確認

**実行方法**:
```bash
# クイック検証（ファイル存在確認）
sudo ./scripts/verify_backup.sh --quick

# 完全検証（テスト復元）
sudo ./scripts/verify_backup.sh --full

# データベースのみ検証
sudo ./scripts/verify_backup.sh --database-only
```

**検証項目**:
- ✅ バックアップファイルの存在
- ✅ ファイル整合性（checksum）
- ✅ データベースダンプの構文
- ✅ アーカイブの圧縮整合性
- ✅ テスト復元の成功

---

## テスト戦略

### TDD (Test-Driven Development)

新機能開発時は TDD を推奨:

1. **RED**: テストを先に書く（失敗する）
2. **GREEN**: 最小限の実装でテストを通す
3. **REFACTOR**: コードをリファクタリング

```bash
# テストファースト
1. tests/unit/new-feature.test.ts を作成
2. npm test -- テストが失敗することを確認
3. src/new-feature.ts を実装
4. npm test -- テストが通ることを確認
5. リファクタリング
```

---

## CI/CD パイプライン

### GitHub Actions ワークフロー

#### 1. セキュリティスキャン (`.github/workflows/security-scan.yml`)
- トリガー: プッシュ、PR、スケジュール (毎日 1:00)
- 実行内容: Trivy, TruffleHog, ShellCheck
- 結果: GitHub Security タブに SARIF アップロード

#### 2. Docker Compose テスト (`.github/workflows/docker-compose-test.yml`)
- トリガー: プッシュ、PR
- 実行内容: Docker Compose 起動テスト、ヘルスチェック
- タイムアウト: 10分

#### 3. E2E テスト (`.github/workflows/e2e-tests.yml`)
- トリガー: プッシュ、PR、スケジュール (毎日 2:00)
- 実行内容: Playwright E2E テスト (Chromium, Firefox)
- アーティファクト: スクリーンショット、ビデオ、トレース、レポート

---

## テスト実行フロー

### ローカル開発時

```bash
# 1. 環境起動
docker compose -f docker-compose.development.yml up -d

# 2. ヘルスチェック
./scripts/health_check.sh

# 3. ユニットテスト実行
cd openclaw && npm test

# 4. E2E テスト実行
cd tests/e2e && npm test

# 5. セキュリティスキャン
./scripts/security_scan.sh

# 6. パフォーマンステスト
./scripts/benchmark.sh
```

### デプロイ前

```bash
# 1. 全テスト実行
make test-all

# 2. セキュリティスキャン
make security-scan

# 3. バックアップ検証
make verify-backup

# 4. デプロイバリデーション
./scripts/validate_deployment.sh
```

### 本番環境

```bash
# 1. ヘルスチェック（定期実行）
./scripts/health_check.sh

# 2. バックアップ検証（週次）
sudo ./scripts/verify_backup.sh --full

# 3. セキュリティスキャン（日次）
./scripts/security_scan.sh

# 4. パフォーマンス監視
# Grafana ダッシュボードで常時監視
```

---

## テストデータ管理

### シードデータ生成

```bash
# 開発環境用サンプルデータ生成
./scripts/seed_data.sh

# 内容:
# - サンプルユーザー (10名)
# - サンプルワークフロー (5個)
# - サンプルノートブック (20個)
# - API使用履歴 (30日分)
```

### テストデータクリーンアップ

```bash
# テストデータ削除
docker compose exec postgres psql -U openclaw -d openclaw -c "DELETE FROM api_usage WHERE date < NOW() - INTERVAL '30 days';"

# 全データ削除（開発環境のみ）
docker compose down -v
docker compose up -d
```

---

## トラブルシューティング

### E2E テストが失敗する

**原因**: サービスが起動完了していない

**解決策**:
```bash
# サービスの状態確認
docker compose ps

# ログ確認
docker compose logs

# 再起動
docker compose restart
```

### パフォーマンステストが遅い

**原因**: リソース不足

**解決策**:
```bash
# リソース使用状況確認
docker stats

# 不要なコンテナ停止
docker compose stop <service>

# システムリソース確認
./scripts/status_dashboard.sh
```

### セキュリティスキャンでエラー

**原因**: 古いイメージや脆弱性

**解決策**:
```bash
# イメージ更新
docker compose pull

# 再ビルド
docker compose build --no-cache

# 脆弱性修正後に再スキャン
./scripts/security_scan.sh
```

---

## ベストプラクティス

### ✅ DO

- テストは常に最新に保つ
- CI/CD パイプラインでテストを自動化
- 失敗したテストは即座に修正
- テストカバレッジ 80% 以上を維持
- エッジケースをテスト
- パフォーマンス目標を設定

### ❌ DON'T

- テストをスキップしない
- テストを無効化したままにしない
- フレイキーテスト（不安定なテスト）を放置しない
- 本番データでテストしない
- テストの実行時間を無視しない

---

## メトリクス

### テストカバレッジ目標

| カテゴリ | 目標カバレッジ |
|---------|--------------|
| ユニットテスト | 80%+ |
| インテグレーションテスト | 70%+ |
| E2E テスト | 主要フロー 100% |
| セキュリティテスト | 全コンポーネント |

### テスト実行時間目標

| テスト種別 | 目標時間 |
|-----------|---------|
| ユニットテスト | < 2分 |
| インテグレーションテスト | < 5分 |
| E2E テスト | < 10分 |
| セキュリティスキャン | < 15分 |

---

## 参考資料

- [Playwright Documentation](https://playwright.dev)
- [Testing Best Practices](https://github.com/goldbergyoni/javascript-testing-best-practices)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

## まとめ

包括的なテスト戦略により、以下を実現:

✅ **品質保証**: 高品質なコードとシステムの維持
✅ **早期発見**: バグや脆弱性の早期検出
✅ **自動化**: CI/CD による自動テスト実行
✅ **信頼性**: 本番環境の安定性向上
✅ **ドキュメント**: テストがシステム仕様のドキュメントとして機能

テストは開発プロセスの重要な一部です。継続的にテストを書き、実行し、改善していきましょう。
