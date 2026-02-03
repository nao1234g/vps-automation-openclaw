# OpenClaw AI Agent - Secure Production Build
# Debian-based image for better compatibility

FROM node:22-slim

LABEL maintainer="OpenClaw VPS Project"
LABEL description="OpenClaw AI Agent - Production"
LABEL version="1.0.0"

# セキュリティアップデート + 依存関係
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    dumb-init \
    chromium \
    curl \
    git \
    jq \
    ca-certificates \
    cmake \
    build-essential \
    python3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Chromiumのパス設定（Puppeteer用）
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    NODE_ENV=production

# OpenClawをグローバルにインストール
RUN npm install -g openclaw@latest && \
    npm cache clean --force

# ビルドツールを削除（容量削減）
RUN apt-get purge -y build-essential python3 cmake && \
    apt-get autoremove -y && \
    apt-get clean

# 非rootユーザー作成
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m appuser

# 作業ディレクトリ
WORKDIR /app
RUN chown -R appuser:appgroup /app

# データ・ログ・キャッシュディレクトリ
RUN mkdir -p /app/data /app/logs /app/skills /app/.cache && \
    chown -R appuser:appgroup /app/data /app/logs /app/skills /app/.cache

# 非rootユーザーに切り替え
USER appuser

# OpenClaw設定ディレクトリを作成
RUN mkdir -p /home/appuser/.openclaw

# 起動スクリプトを作成
COPY --chown=appuser:appgroup entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# ポート公開
EXPOSE 3000

# ヘルスチェック（WebSocket用に変更）
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -sf http://localhost:3000/ || exit 1

# dumb-init使用（PID 1問題回避）
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# エントリポイントスクリプトで起動
CMD ["/app/entrypoint.sh"]
