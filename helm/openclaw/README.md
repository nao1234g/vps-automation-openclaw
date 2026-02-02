# OpenClaw Helm Chart

## 概要

このHelm ChartはOpenClaw VPSをKubernetesにデプロイするためのものです。

## 前提条件

- Kubernetes 1.24+
- Helm 3.8+
- PersistentVolume provisioner (ストレージクラス)
- Ingress Controller (nginx推奨)
- Cert-Manager (SSL/TLS証明書自動発行)

## インストール方法

### 1. Helmリポジトリの追加

```bash
# 依存チャートのリポジトリを追加
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

### 2. values.yaml のカスタマイズ

```bash
# values.yaml をコピー
cp values.yaml my-values.yaml

# 設定を編集
vim my-values.yaml
```

**必須設定**:
- `ingress.hosts[0].host`: ドメイン名
- `secrets.anthropicApiKey`: Anthropic APIキー
- `postgresql.auth.password`: PostgreSQLパスワード
- `grafana.adminPassword`: Grafana管理者パスワード

### 3. 依存チャートの更新

```bash
helm dependency update
```

### 4. インストール

```bash
# ネームスペースを作成
kubectl create namespace openclaw

# Helm Chartをインストール
helm install openclaw ./openclaw \
  --namespace openclaw \
  --values my-values.yaml
```

### 5. デプロイ確認

```bash
# Pod の状態確認
kubectl get pods -n openclaw

# Service の確認
kubectl get svc -n openclaw

# Ingress の確認
kubectl get ingress -n openclaw
```

## アップグレード

```bash
helm upgrade openclaw ./openclaw \
  --namespace openclaw \
  --values my-values.yaml
```

## アンインストール

```bash
helm uninstall openclaw --namespace openclaw
```

## 設定オプション

### 基本設定

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `replicaCount` | レプリカ数 | `2` |
| `image.repository` | イメージリポジトリ | `openclaw/openclaw` |
| `image.tag` | イメージタグ | `1.1.0` |
| `image.pullPolicy` | イメージプルポリシー | `IfNotPresent` |

### サービス設定

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `service.type` | サービスタイプ | `ClusterIP` |
| `service.port` | サービスポート | `3000` |

### Ingress設定

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `ingress.enabled` | Ingress有効化 | `true` |
| `ingress.className` | Ingressクラス名 | `nginx` |
| `ingress.hosts[0].host` | ホスト名 | `openclaw.example.com` |
| `ingress.tls[0].secretName` | TLSシークレット名 | `openclaw-tls` |

### リソース制限

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `resources.limits.cpu` | CPU制限 | `1000m` |
| `resources.limits.memory` | メモリ制限 | `2Gi` |
| `resources.requests.cpu` | CPU要求 | `500m` |
| `resources.requests.memory` | メモリ要求 | `1Gi` |

### オートスケーリング

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `autoscaling.enabled` | オートスケーリング有効化 | `true` |
| `autoscaling.minReplicas` | 最小レプリカ数 | `2` |
| `autoscaling.maxReplicas` | 最大レプリカ数 | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | CPU使用率目標 | `80` |

### 永続化

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `persistence.enabled` | 永続化有効化 | `true` |
| `persistence.size` | ボリュームサイズ | `10Gi` |
| `persistence.storageClass` | ストレージクラス | `""` |

### PostgreSQL

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `postgresql.enabled` | PostgreSQL有効化 | `true` |
| `postgresql.auth.username` | ユーザー名 | `openclaw` |
| `postgresql.auth.password` | パスワード | `""` |
| `postgresql.auth.database` | データベース名 | `openclaw` |

### Redis

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `redis.enabled` | Redis有効化 | `true` |
| `redis.auth.enabled` | 認証有効化 | `true` |
| `redis.auth.password` | パスワード | `""` |

### N8N

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `n8n.enabled` | N8N有効化 | `true` |
| `n8n.replicaCount` | レプリカ数 | `1` |
| `n8n.ingress.enabled` | Ingress有効化 | `true` |

### Prometheus

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `prometheus.enabled` | Prometheus有効化 | `true` |
| `prometheus.server.retention` | データ保持期間 | `30d` |

### Grafana

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| `grafana.enabled` | Grafana有効化 | `true` |
| `grafana.adminUser` | 管理者ユーザー名 | `admin` |
| `grafana.adminPassword` | 管理者パスワード | `""` |

## トラブルシューティング

### Podが起動しない

```bash
# Pod の詳細確認
kubectl describe pod <pod-name> -n openclaw

# ログ確認
kubectl logs <pod-name> -n openclaw
```

### Ingressが機能しない

```bash
# Ingress の確認
kubectl describe ingress openclaw -n openclaw

# Ingress Controller のログ確認
kubectl logs -n ingress-nginx <ingress-controller-pod>
```

### データベース接続エラー

```bash
# PostgreSQL Pod の確認
kubectl get pods -n openclaw | grep postgresql

# PostgreSQL ログ確認
kubectl logs <postgresql-pod> -n openclaw
```

## ベストプラクティス

### セキュリティ

1. **Secretsの管理**: 本番環境ではExternal Secrets Operatorなどを使用
2. **Network Policy**: 有効化してPod間通信を制限
3. **RBAC**: 最小権限の原則に従う
4. **Pod Security Standards**: Restrictedレベルを適用

### 可用性

1. **レプリカ数**: 最低2レプリカを維持
2. **Pod Disruption Budget**: 有効化
3. **リソース制限**: 適切に設定
4. **ヘルスチェック**: liveness/readiness probeを設定

### パフォーマンス

1. **オートスケーリング**: HPAを有効化
2. **リソース最適化**: CPUとメモリの要求/制限を調整
3. **キャッシング**: Redisを有効化
4. **データベース**: 適切なサイズとリソースを割り当て

## 高度な設定

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
  password: "your-password"
```

### カスタムドメイン設定

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
```

### マルチリージョンデプロイ

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/name
              operator: In
              values:
                - openclaw
        topologyKey: "topology.kubernetes.io/zone"
```

## 参考資料

- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [OpenClaw VPS Documentation](https://github.com/nao1234g/vps-automation-openclaw)

## サポート

問題が発生した場合は、[GitHub Issues](https://github.com/nao1234g/vps-automation-openclaw/issues)で報告してください。
