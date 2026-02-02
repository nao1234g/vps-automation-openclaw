# 貢献ガイドライン

OpenClaw VPS プロジェクトへの貢献を歓迎します！このドキュメントでは、貢献方法とガイドラインを説明します。

## 📋 目次

1. [行動規範](#行動規範)
2. [始め方](#始め方)
3. [開発プロセス](#開発プロセス)
4. [コミット規約](#コミット規約)
5. [プルリクエスト](#プルリクエスト)
6. [コードスタイル](#コードスタイル)
7. [テスト](#テスト)
8. [ドキュメント](#ドキュメント)

---

## 行動規範

### 私たちの約束

オープンで歓迎的な環境を作るため、私たちは以下を約束します：

- 年齢、体型、障害、民族性、性別、経験レベル、国籍、外見、人種、宗教、性的指向に関わらず、すべての人を歓迎します
- 建設的なフィードバックを提供し、受け入れます
- プロフェッショナルで礼儀正しい態度を保ちます

### 受け入れられない行動

以下の行動は受け入れられません：

- 荒らし行為、侮辱的/軽蔑的なコメント
- ハラスメント（公的または私的）
- 他者の個人情報の公開
- その他、プロフェッショナルでない行為

---

## 始め方

### 1. リポジトリをフォーク

GitHub上で[リポジトリ](https://github.com/nao1234g/vps-automation-openclaw)をフォークします。

### 2. ローカルにクローン

```bash
git clone https://github.com/YOUR_USERNAME/vps-automation-openclaw.git
cd vps-automation-openclaw
```

### 3. 開発環境のセットアップ

```bash
# 環境変数設定
make setup-env
nano .env

# 開発環境起動
make dev
```

詳細は [DEVELOPMENT.md](DEVELOPMENT.md) を参照してください。

---

## 開発プロセス

### ブランチ戦略

```
main          # 本番環境用、安定版
develop       # 開発ブランチ
feature/*     # 新機能
bugfix/*      # バグ修正
hotfix/*      # 緊急修正
docs/*        # ドキュメント
```

### ワークフロー

1. **Issue作成**
   - バグ報告または機能提案のIssueを作成
   - 既存のIssueを確認して重複を避ける

2. **ブランチ作成**
   ```bash
   git checkout -b feature/awesome-feature
   ```

3. **開発**
   - コードを書く
   - テストを追加
   - ドキュメントを更新

4. **ローカルテスト**
   ```bash
   make dev
   make test
   make validate
   ```

5. **コミット**
   ```bash
   git add .
   git commit -m "feat: Add awesome feature"
   ```

6. **プッシュ**
   ```bash
   git push origin feature/awesome-feature
   ```

7. **プルリクエスト作成**
   - GitHub上でPRを作成
   - テンプレートに従って記入

8. **レビュー対応**
   - フィードバックに対応
   - 必要に応じて修正

9. **マージ**
   - レビュー承認後、マージ

---

## コミット規約

### Conventional Commits形式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

| Type | 説明 | 例 |
|------|------|-----|
| `feat` | 新機能 | feat: Add backup notification |
| `fix` | バグ修正 | fix: Resolve database connection issue |
| `docs` | ドキュメント | docs: Update README |
| `style` | コードスタイル | style: Format with prettier |
| `refactor` | リファクタリング | refactor: Simplify health check logic |
| `test` | テスト | test: Add integration tests |
| `chore` | その他 | chore: Update dependencies |
| `perf` | パフォーマンス | perf: Optimize database queries |
| `ci` | CI/CD | ci: Add security scan workflow |

### Scope（オプション）

- `docker`: Docker関連
- `nginx`: Nginx設定
- `postgres`: PostgreSQL
- `monitoring`: 監視スタック
- `security`: セキュリティ

### 例

```bash
# 良い例
feat(monitoring): Add Grafana dashboard for containers
fix(nginx): Resolve SSL certificate renewal issue
docs: Add troubleshooting guide for database issues

# 悪い例
Update stuff
Fixed bug
WIP
```

---

## プルリクエスト

### チェックリスト

PR作成前に以下を確認：

- [ ] コードが動作する
- [ ] テストが追加されている
- [ ] すべてのテストがパスする
- [ ] ドキュメントが更新されている
- [ ] コミットメッセージが規約に従っている
- [ ] コードスタイルが統一されている
- [ ] セキュリティ問題がない
- [ ] 関連Issueが参照されている

### PR テンプレート

```markdown
## 概要
この変更の概要を記述

## 変更内容
- 変更点1
- 変更点2

## 関連Issue
Closes #123

## テスト方法
1. ステップ1
2. ステップ2

## スクリーンショット（該当する場合）
[スクリーンショットを添付]

## チェックリスト
- [ ] テストを追加した
- [ ] ドキュメントを更新した
- [ ] セキュリティチェックを実施した
```

---

## コードスタイル

### JavaScript/Node.js

```javascript
// ESLint + Prettier 使用
// セミコロン使用
// 2スペースインデント

// 良い例
const result = await fetchData();
if (result.success) {
  console.log('Success');
}

// 悪い例
const result=await fetchData()
if(result.success){console.log('Success')}
```

### Shell Script

```bash
#!/bin/bash
# ShellCheck準拠
# 関数でコードを整理
# エラーハンドリング必須

# 良い例
set -euo pipefail

log_info() {
    echo "[INFO] $1"
}

main() {
    log_info "Starting process"
    # ...
}

main "$@"

# 悪い例
echo "Starting"
command1
command2
```

### Docker

```dockerfile
# マルチステージビルド推奨
# 非rootユーザー実行
# レイヤー最小化

# 良い例
FROM node:20-alpine AS builder
WORKDIR /build
RUN npm ci && npm run build

FROM node:20-alpine
COPY --from=builder /build/dist ./dist
USER appuser
CMD ["npm", "start"]

# 悪い例
FROM node:20
COPY . .
RUN npm install
CMD node server.js
```

---

## テスト

### テスト要件

すべての新機能には以下のテストが必要：

1. **ユニットテスト**
   - 個別機能のテスト
   - カバレッジ80%以上

2. **統合テスト**
   - コンポーネント間の連携
   - データベース接続

3. **E2Eテスト**（該当する場合）
   - ユーザーフロー全体

### テスト実行

```bash
# すべてのテスト
make test
make validate

# 開発環境テスト
make dev
# 手動テスト

# セキュリティテスト
make scan
```

---

## ドキュメント

### ドキュメント更新が必要な場合

- 新機能追加
- APIの変更
- 設定変更
- トラブルシューティング手順

### 更新すべきドキュメント

| 変更内容 | 更新ドキュメント |
|---------|---------------|
| 新機能 | README.md, OPERATIONS_GUIDE.md |
| セキュリティ | SECURITY_CHECKLIST.md |
| トラブルシューティング | TROUBLESHOOTING.md |
| パフォーマンス | PERFORMANCE.md |
| 開発 | DEVELOPMENT.md |
| スキル | skills/README.md |

---

## Issue報告

### バグ報告

以下の情報を含めてください：

```markdown
## 環境
- OS: Ubuntu 22.04
- Docker: 20.10.21
- Docker Compose: v2.13.0

## 再現手順
1. ステップ1
2. ステップ2

## 期待される動作
正常に動作すべき

## 実際の動作
エラーが発生

## ログ
```
エラーログを貼り付け
```

## スクリーンショット
[該当する場合]
```

### 機能提案

```markdown
## 提案内容
機能の概要

## 動機
なぜこの機能が必要か

## 実装案
どのように実装するか

## 代替案
他に考えられる方法
```

---

## レビュープロセス

### レビュー観点

1. **機能性**
   - 要件を満たしているか
   - バグがないか

2. **コード品質**
   - 可読性
   - 保守性
   - パフォーマンス

3. **セキュリティ**
   - 脆弱性がないか
   - ベストプラクティスに従っているか

4. **テスト**
   - 適切なテストがあるか
   - カバレッジは十分か

5. **ドキュメント**
   - 必要なドキュメントが更新されているか

### レビュー時間

- 小さなPR（< 100行）: 24時間以内
- 中規模PR（100-500行）: 48時間以内
- 大規模PR（> 500行）: 1週間以内

---

## 質問・サポート

- **GitHub Issues**: バグ報告・機能提案
- **GitHub Discussions**: 質問・議論
- **Discord**: リアルタイムチャット（TODO: リンク追加）

---

## ライセンス

貢献により、あなたのコードはプロジェクトと同じ[MITライセンス](LICENSE)の下でライセンスされることに同意したものとみなされます。

---

**💡 Tip**: 初めての貢献の場合は、`good first issue`ラベルのIssueから始めることをお勧めします。

---

**ありがとうございます！** あなたの貢献がOpenClaw VPSプロジェクトをより良いものにします。🎉
