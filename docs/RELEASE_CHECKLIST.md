# Release Checklist

OpenClaw VPS プロジェクトのリリース前チェックリスト

このドキュメントは、新しいバージョンをリリースする前に確認すべき項目をまとめています。

## 📋 リリース前チェックリスト

### 1. コードの品質

#### コード変更
- [ ] 全ての新機能がテストされている
- [ ] 既存機能に破壊的変更がない（または CHANGELOG に記載）
- [ ] コードレビューが完了している
- [ ] セキュリティスキャンに合格している
- [ ] パフォーマンステストに合格している

#### テスト
- [ ] 手動テストが完了している
- [ ] エッジケースのテストが完了している
- [ ] エラーハンドリングが適切
- [ ] ロールバック手順が確認されている

### 2. ドキュメント

#### 更新必須
- [ ] CHANGELOG.md が更新されている
- [ ] バージョン番号が正しい（Semantic Versioning）
- [ ] 新機能がドキュメント化されている
- [ ] 破壊的変更が明記されている
- [ ] 移行ガイドが更新されている（必要な場合）

#### ドキュメント確認
- [ ] README.md が最新の状態
- [ ] 全てのリンクが有効
- [ ] スクリーンショットが最新（該当する場合）
- [ ] コマンド例が動作する
- [ ] FAQ が更新されている（必要な場合）

### 3. セキュリティ

#### セキュリティチェック
- [ ] 依存パッケージに既知の脆弱性がない
- [ ] 機密情報がコミットされていない
- [ ] .env.example に新しい環境変数が追加されている
- [ ] セキュリティスキャンに合格
  ```bash
  ./scripts/security_scan.sh --all
  ```

#### アクセス制御
- [ ] デフォルトパスワードが変更されている
- [ ] 不要なポートが閉じられている
- [ ] ファイアウォール設定が適切
- [ ] SSL/TLS設定が適切

### 4. 設定ファイル

#### Docker関連
- [ ] docker-compose.production.yml が動作する
- [ ] docker-compose.dev.yml が動作する
- [ ] docker-compose.monitoring.yml が動作する
- [ ] docker-compose.minimal.yml が動作する
- [ ] リソース制限が適切に設定されている

#### 環境変数
- [ ] .env.example が最新
- [ ] 必須環境変数が全て記載されている
- [ ] デフォルト値が適切
- [ ] 環境変数のバリデーションが実装されている

### 5. デプロイメント

#### 自動化スクリプト
- [ ] setup.sh が動作する
- [ ] backup.sh が動作する
- [ ] restore.sh が動作する
- [ ] health_check.sh が動作する
- [ ] security_scan.sh が動作する
- [ ] maintenance.sh が動作する
- [ ] benchmark.sh が動作する

#### Makefile
- [ ] 全てのMakeターゲットが動作する
  ```bash
  make prod
  make dev
  make monitoring
  make minimal
  make clean
  make health
  ```

### 6. CI/CD

#### GitHub Actions
- [ ] セキュリティスキャンワークフローが成功
- [ ] Docker Composeテストワークフローが成功
- [ ] 全てのワークフローがグリーン
- [ ] バッジが最新の状態

#### 自動化
- [ ] Pre-commitフックが動作
- [ ] Linterが成功
- [ ] フォーマッターが適用されている

### 7. データベース

#### マイグレーション
- [ ] データベースマイグレーションが正常に動作
- [ ] ロールバックスクリプトが用意されている
- [ ] サンプルデータが最新
- [ ] インデックスが最適化されている

#### バックアップ
- [ ] バックアップスクリプトが動作
- [ ] リストアスクリプトが動作
- [ ] バックアップからの復元がテスト済み

### 8. 監視とログ

#### Grafana ダッシュボード
- [ ] 全てのダッシュボードが表示される
- [ ] メトリクスが正しく収集されている
- [ ] アラートルールが動作する

#### ログ
- [ ] ログレベルが適切
- [ ] センシティブ情報がログに記録されていない
- [ ] ログローテーションが設定されている

### 9. パフォーマンス

#### ベンチマーク
- [ ] パフォーマンステストが実行されている
  ```bash
  ./scripts/benchmark.sh --full
  ```
- [ ] 前バージョンと比較して劣化していない
- [ ] ボトルネックが特定・解消されている

#### リソース使用量
- [ ] メモリ使用量が許容範囲内
- [ ] CPU使用量が許容範囲内
- [ ] ディスクI/Oが最適化されている

### 10. ユーザーエクスペリエンス

#### インストール
- [ ] クリーンな環境でインストールが成功する
- [ ] セットアップ時間が15分以内
- [ ] エラーメッセージがわかりやすい

#### ドキュメント
- [ ] クイックスタートガイドが動作する
- [ ] トラブルシューティングガイドが充実している
- [ ] FAQ が充実している

### 11. バージョン管理

#### Git
- [ ] コミットメッセージがConventional Commitsに準拠
- [ ] 全ての変更がコミットされている
- [ ] マージ競合が解決されている
- [ ] タグが適切に付けられている

#### バージョン番号
- [ ] Semantic Versioningに準拠
  - MAJOR: 破壊的変更
  - MINOR: 後方互換性のある機能追加
  - PATCH: 後方互換性のあるバグ修正
- [ ] 全ての該当ファイルでバージョン番号が更新されている
  - CHANGELOG.md
  - README.md バッジ

### 12. コミュニティ

#### オープンソース
- [ ] LICENSE ファイルが最新
- [ ] CONTRIBUTING.md が最新
- [ ] CODE_OF_CONDUCT.md が存在（該当する場合）
- [ ] CODEOWNERS が設定されている

#### Issue/PR テンプレート
- [ ] Issue テンプレートが最新
- [ ] PR テンプレートが最新
- [ ] 全てのテンプレートが機能する

---

## 🚀 リリース手順

### Step 1: 最終確認

```bash
# 1. ブランチを最新の状態に
git checkout main
git pull origin main

# 2. 全ての変更がコミット済みか確認
git status

# 3. ビルドテスト
docker compose -f docker-compose.production.yml build

# 4. 統合テスト
make prod
./scripts/health_check.sh
./scripts/benchmark.sh --quick
```

### Step 2: CHANGELOG更新

```bash
# CHANGELOG.md を編集
nano CHANGELOG.md
```

フォーマット:
```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- 新機能1
- 新機能2

### Changed
- 変更点1
- 変更点2

### Fixed
- バグ修正1
- バグ修正2

### Security
- セキュリティ修正1
```

### Step 3: バージョン番号更新

```bash
# README.md のバッジ更新
sed -i 's/version-[0-9.]*-blue/version-X.Y.Z-blue/' README.md

# 他の該当ファイルも更新
```

### Step 4: コミット&タグ

```bash
# コミット
git add CHANGELOG.md README.md
git commit -m "chore: Release vX.Y.Z"

# タグ作成
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# プッシュ
git push origin main
git push origin vX.Y.Z
```

### Step 5: GitHub Release作成

1. GitHub リポジトリページにアクセス
2. "Releases" → "Draft a new release"
3. タグを選択: `vX.Y.Z`
4. リリースタイトル: `Version X.Y.Z`
5. 説明に CHANGELOG の該当バージョンセクションをコピー
6. "Publish release" をクリック

### Step 6: リリース後確認

```bash
# 1. GitHub Actionsが成功しているか確認
# https://github.com/YOUR_USERNAME/vps-automation-openclaw/actions

# 2. タグが正しくプッシュされているか確認
git ls-remote --tags origin

# 3. リリースページを確認
# https://github.com/YOUR_USERNAME/vps-automation-openclaw/releases
```

### Step 7: コミュニケーション

- [ ] リリースノートをSNSでシェア（該当する場合）
- [ ] ドキュメントサイトを更新（該当する場合）
- [ ] コミュニティに通知（該当する場合）

---

## 🔧 緊急修正（Hotfix）手順

緊急のバグ修正が必要な場合:

```bash
# 1. Hotfixブランチ作成
git checkout main
git checkout -b hotfix/vX.Y.Z+1

# 2. バグ修正

# 3. テスト
make prod
./scripts/health_check.sh

# 4. CHANGELOG更新（### Fixed セクションに追加）

# 5. コミット
git commit -am "fix: 緊急バグ修正の説明"

# 6. mainにマージ
git checkout main
git merge hotfix/vX.Y.Z+1

# 7. タグ作成
git tag -a vX.Y.Z+1 -m "Hotfix version X.Y.Z+1"

# 8. プッシュ
git push origin main
git push origin vX.Y.Z+1

# 9. ブランチ削除
git branch -d hotfix/vX.Y.Z+1
```

---

## 📊 リリース後のモニタリング

### 監視項目

```bash
# 1. エラーログ確認
docker compose -f docker-compose.production.yml logs --tail=100

# 2. リソース使用状況
docker stats --no-stream

# 3. セキュリティスキャン
./scripts/security_scan.sh --all

# 4. パフォーマンス測定
./scripts/benchmark.sh --quick
```

### 問題発生時

1. 影響範囲の特定
2. ロールバックの検討
3. 修正版の準備
4. ユーザーへの通知

---

## 📝 リリースノートテンプレート

```markdown
# Release vX.Y.Z

## 🎉 Highlights

このリリースの主な変更点を簡潔に説明

## ✨ New Features

- 機能1の説明
- 機能2の説明

## 🐛 Bug Fixes

- バグ1の修正
- バグ2の修正

## 📚 Documentation

- ドキュメント1の追加/更新
- ドキュメント2の追加/更新

## 🔒 Security

- セキュリティ修正1
- セキュリティ修正2

## ⚡ Performance

- パフォーマンス改善1
- パフォーマンス改善2

## 🔄 Migration Guide

破壊的変更がある場合の移行手順

## 🙏 Contributors

このリリースに貢献してくださった方々（該当する場合）

## 📖 Full Changelog

https://github.com/YOUR_USERNAME/vps-automation-openclaw/compare/vX.Y.Z-1...vX.Y.Z
```

---

## 🎯 品質基準

リリース可能な状態の最低基準:

### 必須項目（MUST）
✅ 全てのテストが成功
✅ セキュリティスキャンに合格
✅ ドキュメントが最新
✅ CHANGELOG が更新されている
✅ 既知のクリティカルバグがない

### 推奨項目（SHOULD）
⭐ パフォーマンスが前バージョンより劣化していない
⭐ コードレビューが完了している
⭐ ユーザーフィードバックが反映されている

### オプション（MAY）
💡 新機能のデモ動画がある
💡 ブログ記事が公開されている

---

## 🤝 サポート

リリースプロセスに関する質問:
- [GitHub Discussions](https://github.com/nao1234g/vps-automation-openclaw/discussions)
- [CONTRIBUTING.md](../CONTRIBUTING.md)

---

<div align="center">

**🚀 品質の高いリリースをお届けしましょう！ ✨**

</div>
