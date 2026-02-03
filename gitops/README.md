# GitOps Configuration

## 概要

このディレクトリには、OpenClaw VPSのGitOps設定が含まれています。ArgoCDを使用して、Gitリポジトリをソースオブトゥルースとした継続的デリバリーを実現します。

## ディレクトリ構造

```
gitops/
├── argocd/
│   ├── application.yaml      # 単一アプリケーション定義
│   ├── applicationset.yaml   # 複数環境の自動生成
│   ├── project.yaml          # プロジェクト設定
│   └── notifications.yaml    # 通知設定
└── README.md
```

## 前提条件

### 1. ArgoCD のインストール

```bash
# ネームスペース作成
kubectl create namespace argocd

# ArgoCD インストール
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# ArgoCD CLI インストール (macOS)
brew install argocd

# ArgoCD CLI インストール (Linux)
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
```

### 2. 初期設定

```bash
# ArgoCD サーバーへのポートフォワード
kubectl port-forward svc/argocd-server -n argocd 8080:443

# 初期パスワード取得
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# ログイン
argocd login localhost:8080 --username admin --password <password>

# パスワード変更
argocd account update-password
```

## セットアップ

### 1. プロジェクトの作成

```bash
kubectl apply -f gitops/argocd/project.yaml
```

### 2. 単一環境のデプロイ

```bash
kubectl apply -f gitops/argocd/application.yaml
```

### 3. 複数環境の自動デプロイ（ApplicationSet）

```bash
kubectl apply -f gitops/argocd/applicationset.yaml
```

### 4. 通知設定

```bash
# Slack/Telegram トークンを設定
kubectl edit secret argocd-notifications-secret -n argocd

# 通知設定を適用
kubectl apply -f gitops/argocd/notifications.yaml
```

## 環境構成

### Production

- **ブランチ**: `main`
- **ネームスペース**: `openclaw`
- **レプリカ数**: 3
- **自動同期**: 有効
- **values**: `values-production.yaml`

### Staging

- **ブランチ**: `develop`
- **ネームスペース**: `openclaw-staging`
- **レプリカ数**: 2
- **自動同期**: 有効
- **values**: `values-production.yaml`

### Development

- **ブランチ**: `develop`
- **ネームスペース**: `openclaw-dev`
- **レプリカ数**: 1
- **自動同期**: 無効（手動）
- **values**: `values-development.yaml`

## ワークフロー

### デプロイメントフロー

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   開発者     │────▶│   GitHub    │────▶│   ArgoCD    │
│  git push   │     │  (main/dev) │     │  (sync)     │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                    ┌─────────────────────────────────────┐
                    │         Kubernetes Cluster          │
                    │                                     │
                    │  ┌─────────┐  ┌─────────┐  ┌────┐ │
                    │  │Production│  │Staging │  │Dev │ │
                    │  └─────────┘  └─────────┘  └────┘ │
                    └─────────────────────────────────────┘
```

### ブランチ戦略

1. **Feature Branch**: 機能開発
   ```bash
   git checkout -b feature/new-feature
   # 開発・テスト
   git push origin feature/new-feature
   # PR作成 → develop へマージ
   ```

2. **Staging デプロイ**: develop ブランチへのマージで自動

3. **Production デプロイ**: main ブランチへのマージで自動
   ```bash
   git checkout main
   git merge develop
   git push origin main
   # 自動的に本番環境にデプロイ
   ```

## 同期ポリシー

### 自動同期

```yaml
syncPolicy:
  automated:
    prune: true      # 削除されたリソースを自動削除
    selfHeal: true   # ドリフトを自動修復
```

### 同期ウィンドウ

- **平日**: 22:00-08:00（営業時間外）のみ自動同期
- **週末**: 常に自動同期許可
- **手動同期**: 常に可能

### 同期オプション

```yaml
syncOptions:
  - CreateNamespace=true        # ネームスペース自動作成
  - PrunePropagationPolicy=foreground  # 削除順序制御
  - ApplyOutOfSyncOnly=true     # 変更があるリソースのみ適用
```

## 通知設定

### Slack

以下のチャンネルに通知が送信されます:

- **#openclaw-deployments**: デプロイ成功、同期開始
- **#openclaw-alerts**: デプロイ失敗、ヘルス低下

### Telegram

- デプロイ成功/失敗の通知

### 設定方法

```bash
# Slack Bot Token を設定
kubectl create secret generic argocd-notifications-secret \
  --from-literal=slack-token=xoxb-your-token \
  --from-literal=telegram-token=your-telegram-token \
  -n argocd
```

## 管理コマンド

### アプリケーション一覧

```bash
argocd app list
```

### 手動同期

```bash
argocd app sync openclaw
```

### 強制同期（すべてのリソースを再適用）

```bash
argocd app sync openclaw --force
```

### ロールバック

```bash
# 履歴確認
argocd app history openclaw

# 特定のリビジョンにロールバック
argocd app rollback openclaw <revision>
```

### 差分確認

```bash
argocd app diff openclaw
```

### ログ確認

```bash
argocd app logs openclaw
```

## トラブルシューティング

### 同期が失敗する

```bash
# 詳細なエラー確認
argocd app get openclaw

# リソースの状態確認
argocd app resources openclaw

# 同期エラーの詳細
argocd app sync openclaw --dry-run
```

### ヘルスチェックが失敗する

```bash
# Pod の状態確認
kubectl get pods -n openclaw

# Pod のログ確認
kubectl logs -f <pod-name> -n openclaw

# イベント確認
kubectl get events -n openclaw --sort-by='.lastTimestamp'
```

### 自動同期が動作しない

1. 同期ウィンドウを確認
2. プロジェクト設定を確認
3. リポジトリへのアクセス権限を確認

```bash
argocd proj get openclaw
argocd repo list
```

## ベストプラクティス

### セキュリティ

1. **RBAC**: 最小権限の原則
2. **GPG署名**: コミットの署名検証
3. **シークレット管理**: Sealed Secrets または External Secrets

### 運用

1. **段階的デプロイ**: dev → staging → production
2. **自動ロールバック**: ヘルスチェック失敗時
3. **通知**: 重要なイベントをSlack/Telegramに通知

### パフォーマンス

1. **同期間隔**: デフォルト3分（調整可能）
2. **並列同期**: ApplicationSetで複数環境を効率的に管理
3. **差分適用**: 変更があるリソースのみ適用

## 参考資料

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
- [ApplicationSet Documentation](https://argo-cd.readthedocs.io/en/stable/user-guide/application-set/)
- [Notifications Documentation](https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/)

---

## まとめ

GitOpsにより、以下を実現:

✅ **宣言的デプロイ**: Gitをソースオブトゥルースとして
✅ **自動同期**: コミットで自動的にデプロイ
✅ **マルチ環境**: 開発/ステージング/本番を統一管理
✅ **ロールバック**: 簡単に以前のバージョンに戻る
✅ **監査**: すべての変更がGit履歴に記録
✅ **通知**: デプロイ状況をリアルタイムで把握
