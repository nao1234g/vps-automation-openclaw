FROM node:20-alpine

# 作業ディレクトリ
WORKDIR /app

# システム依存関係
RUN apk add --no-cache \
    git \
    python3 \
    make \
    g++ \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont

# Chromiumのパス設定（Puppeteer用）
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# OpenClawのクローン
RUN git clone https://github.com/Sh-Osakana/open-claw.git . && \
    npm install && \
    npm run build

# カスタムスキルディレクトリ
RUN mkdir -p /app/skills

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# ポート公開
EXPOSE 3000

# 起動コマンド
CMD ["npm", "start"]

