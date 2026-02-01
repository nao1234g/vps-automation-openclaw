FROM node:20-alpine

WORKDIR /app

# システム依存関係
RUN apk add --no-cache \
    git \
    python3 \
    make \
    g++

# OpenNotebookのクローン（仮のリポジトリURL - 実際のものに置き換え）
# NOTE: 実際のOpenNotebookリポジトリが存在する場合はそちらを使用
RUN git clone https://github.com/open-notebook/open-notebook.git . || \
    echo "OpenNotebook placeholder" > README.md

# 依存関係のインストール（リポジトリが存在する場合）
RUN if [ -f package.json ]; then npm install && npm run build; fi

# データディレクトリ
RUN mkdir -p /app/data /app/uploads

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:8080/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})" || exit 0

# ポート公開
EXPOSE 8080

# 起動コマンド
CMD if [ -f package.json ]; then npm start; else echo "OpenNotebook not configured" && sleep infinity; fi

