# OpenNotebook - Secure Production Build
# Multi-stage build for security

# ============================================
# Build Stage
# ============================================
FROM node:20-alpine AS builder

# セキュリティアップデート
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
    git \
    python3 \
    make \
    g++ && \
    rm -rf /var/cache/apk/*

WORKDIR /build

# プレースホルダーアプリをコピー（実際のアプリがある場合は置き換え）
COPY app/ ./

# 依存関係のインストール
RUN if [ -f package.json ]; then \
    npm ci && \
    npm run build 2>/dev/null || true && \
    npm cache clean --force; \
    fi

# ============================================
# Production Stage
# ============================================
FROM node:20-alpine

LABEL maintainer="OpenClaw VPS Project"
LABEL description="OpenNotebook - Secure Production"
LABEL version="1.0.0"

# セキュリティアップデート
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
    dumb-init \
    curl && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

# 非rootユーザー作成
RUN addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

# 作業ディレクトリ
WORKDIR /app
RUN chown -R appuser:appgroup /app

# ビルドステージからコピー
COPY --from=builder --chown=appuser:appgroup /build ./

# データ・ログディレクトリ
RUN mkdir -p /app/data /app/uploads /app/logs /app/.cache && \
    chown -R appuser:appgroup /app/data /app/uploads /app/logs /app/.cache

# 非rootユーザーに切り替え
USER appuser

# ポート公開
EXPOSE 8080

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# dumb-init使用
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# アプリケーション起動
CMD ["node", "server.js"]

