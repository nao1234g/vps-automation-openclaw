# Helm Charts for OpenClaw

## 概要

このディレクトリには、OpenClaw VPSをKubernetesクラスターにデプロイするためのHelm Chartsが含まれています。

## ディレクトリ構造

```
helm/
├── openclaw/              # メインのHelm Chart
│   ├── Chart.yaml         # Chartメタデータ
│   ├── values.yaml        # デフォルト値
│   ├── values-production.yaml   # 本番環境用設定
│   ├── values-development.yaml  # 開発環境用設定
│   ├── templates/         # Kubernetesマニフェストテンプレート
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   ├── configmap.yaml
│   │   ├── secret.yaml
│   │   ├── pvc.yaml
│   │   ├── hpa.yaml
│   │   ├── pdb.yaml
│   │   ├── networkpolicy.yaml
│   │   ├── servicemonitor.yaml
│   │   └── _helpers.tpl
│   └── README.md          # Chart固有のドキュメント
└── README.md              # このファイル
```

## クイックスタート

### 前提条件

1. **Kubernetes クラスター** (1.24+)
   ```bash
   kubectl version
   ```

2. **Helm** (3.8+)
   ```bash
   helm version
   ```

3. **Ingress Controller** (nginx推奨)
   ```bash
   # nginx-ingress のインストール
   helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
   helm install nginx-ingress ingress-nginx/ingress-nginx
   ```

4. **Cert-Manager** (SSL/TLS証明書自動発行)
   ```bash
   # cert-manager のインストール
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

### インストール手順

#### 1. Helmリポジトリの追加

```bash
# 依存チャートのリポジトリを追加
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

#### 2. ネームスペースの作成

```bash
kubectl create namespace openclaw
```

#### 3. Secretsの作成

```bash
# Anthropic API Key
kubectl create secret generic openclaw-secrets \
  --from-literal=anthropic-api-key="sk-ant-..." \
  --from-literal=session-secret="$(openssl rand -hex 32)" \
  --from-literal=jwt-secret="$(openssl rand -hex 32)" \
  --namespace openclaw

# PostgreSQL パスワード
kubectl create secret generic openclaw-postgresql \
  --from-literal=postgres-password="$(openssl rand -hex 32)" \
  --namespace openclaw

# Grafana 管理者パスワード
kubectl create secret generic openclaw-grafana \
  --from-literal=admin-password="$(openssl rand -hex 16)" \
  --namespace openclaw
```

#### 4. values.yaml のカスタマイズ

```bash
cd helm/openclaw
cp values.yaml my-values.yaml
vim my-values.yaml
```

**必須設定**:
```yaml
ingress:
  hosts:
    - host: openclaw.your-domain.com  # あなたのドメインに変更
      paths:
        - path: /
          pathType: Prefix

secrets:
  anthropicApiKey: "sk-ant-..."  # あなたのAPIキー
```

#### 5. 依存チャートの更新

```bash
helm dependency update
```

#### 6. デプロイ

**開発環境**:
```bash
helm install openclaw . \
  --namespace openclaw \
  --values values-development.yaml
```

**本番環境**:
```bash
helm install openclaw . \
  --namespace openclaw \
  --values values-production.yaml \
  --values my-values.yaml
```

#### 7. デプロイ確認

```bash
# Podの状態確認
kubectl get pods -n openclaw

# Serviceの確認
kubectl get svc -n openclaw

# Ingressの確認
kubectl get ingress -n openclaw

# アプリケーションログ確認
kubectl logs -f deployment/openclaw -n openclaw
```

## 環境別デプロイ

### 開発環境

```bash
helm install openclaw-dev ./openclaw \
  --namespace openclaw-dev \
  --create-namespace \
  --values openclaw/values-development.yaml
```

**特徴**:
- レプリカ数: 1
- リソース制限: 低
- 永続化: 最小限
- 監視: 無効
- ネットワークポリシー: 無効

### 本番環境

```bash
helm install openclaw-prod ./openclaw \
  --namespace openclaw-prod \
  --create-namespace \
  --values openclaw/values-production.yaml \
  --values my-production-secrets.yaml
```

**特徴**:
- レプリカ数: 3+
- オートスケーリング: 有効
- 永続化: 完全
- 監視: 完全（Prometheus + Grafana）
- ネットワークポリシー: 有効
- PodDisruptionBudget: 有効

## 管理コマンド

### アップグレード

```bash
helm upgrade openclaw ./openclaw \
  --namespace openclaw \
  --values my-values.yaml
```

### ロールバック

```bash
# リリース履歴の確認
helm history openclaw -n openclaw

# 前のバージョンにロールバック
helm rollback openclaw -n openclaw

# 特定のリビジョンにロールバック
helm rollback openclaw 1 -n openclaw
```

### アンインストール

```bash
# Chartをアンインストール（PVCは保持）
helm uninstall openclaw -n openclaw

# PVCも削除
kubectl delete pvc -n openclaw --all
```

### デバッグ

```bash
# テンプレートのレンダリング確認
helm template openclaw ./openclaw --values my-values.yaml

# Dry-run（実際にはデプロイしない）
helm install openclaw ./openclaw \
  --namespace openclaw \
  --values my-values.yaml \
  --dry-run --debug

# 設定値の確認
helm get values openclaw -n openclaw
```

## カスタマイズ

### カスタムドメインの設定

```yaml
ingress:
  enabled: true
  hosts:
    - host: openclaw.your-domain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: openclaw-tls
      hosts:
        - openclaw.your-domain.com

n8n:
  ingress:
    hosts:
      - host: n8n.your-domain.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: n8n-tls
        hosts:
          - n8n.your-domain.com
```

### 外部データベースの使用

```yaml
postgresql:
  enabled: false

externalDatabase:
  enabled: true
  host: "postgres.example.com"
  port: 5432
  database: "openclaw"
  user: "openclaw"
  password: ""  # Secretから取得
```

### リソースのカスタマイズ

```yaml
resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
```

## ベストプラクティス

### セキュリティ

1. **Secretsの管理**
   - External Secrets Operatorを使用
   - Sealed Secretsでバージョン管理
   - values.yamlに平文で保存しない

2. **ネットワークポリシー**
   - 本番環境では必ず有効化
   - 最小権限の原則に従う

3. **Pod Security Standards**
   - Restrictedレベルを適用
   - 非rootユーザーで実行

### 可用性

1. **レプリカ数**
   - 本番環境: 最低3レプリカ
   - 開発環境: 1レプリカ

2. **Pod Disruption Budget**
   - 本番環境では必ず有効化
   - minAvailable: 2以上

3. **ヘルスチェック**
   - liveness/readiness probeを適切に設定
   - タイムアウトを調整

### パフォーマンス

1. **リソース最適化**
   - 適切なrequests/limitsを設定
   - オートスケーリングを有効化

2. **永続化**
   - 高速ストレージクラスを使用
   - 適切なサイズを設定

3. **キャッシング**
   - Redisを有効化
   - 適切なTTLを設定

## トラブルシューティング

### Podが起動しない

```bash
# Pod の詳細確認
kubectl describe pod <pod-name> -n openclaw

# ログ確認
kubectl logs <pod-name> -n openclaw

# イベント確認
kubectl get events -n openclaw --sort-by='.lastTimestamp'
```

### Ingressが機能しない

```bash
# Ingress の詳細確認
kubectl describe ingress openclaw -n openclaw

# Ingress Controller のログ
kubectl logs -n ingress-nginx deployment/nginx-ingress-controller

# DNS確認
nslookup openclaw.your-domain.com
```

### データベース接続エラー

```bash
# PostgreSQL の状態確認
kubectl get pods -n openclaw | grep postgresql

# PostgreSQL に接続テスト
kubectl exec -it <postgresql-pod> -n openclaw -- psql -U openclaw -d openclaw
```

### 証明書の問題

```bash
# Cert-Manager のログ確認
kubectl logs -n cert-manager deployment/cert-manager

# Certificate の状態確認
kubectl get certificate -n openclaw
kubectl describe certificate openclaw-tls -n openclaw
```

## マイグレーション

### Docker ComposeからKubernetesへ

1. **データのエクスポート**
   ```bash
   # Docker Compose環境でバックアップ
   ./scripts/backup.sh
   ```

2. **Kubernetesにデプロイ**
   ```bash
   helm install openclaw ./openclaw -n openclaw
   ```

3. **データのインポート**
   ```bash
   # PVCにバックアップをコピー
   kubectl cp backup.tar.gz openclaw/<pod-name>:/tmp/

   # リストアスクリプト実行
   kubectl exec -it <pod-name> -n openclaw -- /app/scripts/restore.sh /tmp/backup.tar.gz
   ```

## 参考資料

- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [OpenClaw VPS Documentation](https://github.com/nao1234g/vps-automation-openclaw)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)

## サポート

問題が発生した場合:

1. [トラブルシューティングガイド](../TROUBLESHOOTING.md)を確認
2. [GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues)で報告
3. [GitHub Discussions](https://github.com/nao1234g/vps-automation-openclaw/discussions)で質問

---

## まとめ

Helm Chartsにより、OpenClaw VPSを:

✅ **Kubernetes対応**: エンタープライズグレードのオーケストレーション
✅ **スケーラブル**: 自動スケーリングで需要に対応
✅ **高可用性**: マルチレプリカとPDB
✅ **セキュア**: ネットワークポリシーとPod Security Standards
✅ **監視**: Prometheus + Grafana統合
✅ **バックアップ**: 自動バックアップとリストア

KubernetesとHelmにより、本格的なクラウドネイティブデプロイメントを実現できます。
