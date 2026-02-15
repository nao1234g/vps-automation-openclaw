# Substack Publishing API - Dockerfile
FROM python:3.12-slim

# セキュリティ: 非rootユーザーで実行
RUN groupadd -r appuser && useradd -r -g appuser -u 1001 appuser

# 作業ディレクトリ
WORKDIR /app

# 依存関係をコピー
COPY requirements.txt .

# Pythonパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app.py .

# 権限設定
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# ポート公開
EXPOSE 8000

# アプリケーション起動
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
