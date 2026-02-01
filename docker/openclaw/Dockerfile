# OpenClaw AI Agent - Secure Production Build
# Multi-stage build for security and minimal footprint

# ============================================
# Build Stage
# ============================================
FROM node:20-alpine AS builder

# セキュリティアップデート + ビルド依存関係
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
    git \
    python3 \
    make \
    g++ && \
    rm -rf /var/cache/apk/*

WORKDIR /build

# OpenClawのクローンとビルド
RUN git clone https://github.com/Sh-Osakana/open-claw.git . && \
    npm ci && \
    npm run build && \
    npm cache clean --force

# ============================================
# Production Stage
# ============================================
FROM node:20-alpine

LABEL maintainer="OpenClaw VPS Project"
LABEL description="OpenClaw AI Agent - Secure Production"
LABEL version="1.0.0"

# セキュリティアップデート + 実行時依存関係のみ
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
    dumb-init \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    curl && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

# 非rootユーザー作成
RUN addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

# Chromiumのパス設定（Puppeteer用）
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# 作業ディレクトリ
WORKDIR /app
RUN chown -R appuser:appgroup /app

# ビルドステージからコピー
COPY --from=builder --chown=appuser:appgroup /build/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /build/package*.json ./
COPY --from=builder --chown=appuser:appgroup /build/dist ./dist
COPY --from=builder --chown=appuser:appgroup /build/src ./src

# データ・ログ・キャッシュディレクトリ
RUN mkdir -p /app/data /app/logs /app/skills /app/.cache && \
    chown -R appuser:appgroup /app/data /app/logs /app/skills /app/.cache

# 非rootユーザーに切り替え
USER appuser

# ポート公開
EXPOSE 3000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})" || exit 1

# dumb-init使用（PID 1問題回避）
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# アプリケーション起動
CMD ["npm", "start"]

