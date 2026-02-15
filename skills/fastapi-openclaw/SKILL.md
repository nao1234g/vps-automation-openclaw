---
name: fastapi-openclaw
description: "FastAPI で高性能REST APIサーバーを構築：非同期処理、Pydanticバリデーション、Docker統合"
source: community
risk: safe
tags:
  - fastapi
  - python
  - api
  - async
  - docker
  - openclaw
related_skills:
  - @api-design-principles
  - @docker-integration
  - @n8n-openclaw-integration
---

# FastAPI 実践ガイド for OpenClaw

## Overview

FastAPIを使って高性能なREST APIサーバーを構築します。非同期処理、Pydanticによる型安全なバリデーション、自動生成されるOpenAPI仕様書、Docker統合まで、実戦的なノウハウをカバーします。OpenClawプロジェクトでは、Substack自動投稿APIサーバーでFastAPIを活用しています。

## When to Use This Skill

このスキルを使用する場面：

- ✅ 高速なREST APIサーバーが必要
- ✅ 非公式APIをラップして独自APIを提供したい（例: Substack）
- ✅ N8Nワークフローから呼び出せるカスタムエンドポイントが欲しい
- ✅ 型安全なリクエスト/レスポンス処理が必要
- ✅ 自動生成されるAPIドキュメントが欲しい（Swagger UI）

Trigger keywords: `fastapi`, `rest api`, `async python`, `api server`, `pydantic`

## How It Works

### Step 1: FastAPI プロジェクト構築

基本的なFastAPIアプリケーションを作成します。

```python
# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="OpenClaw Custom API",
    description="Custom API server for OpenClaw automation",
    version="1.0.0"
)

# リクエストモデル（Pydanticで型定義）
class PublishRequest(BaseModel):
    title: str
    content: str
    subtitle: Optional[str] = None
    is_draft: bool = False

# レスポンスモデル
class PublishResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 投稿エンドポイント（非同期処理）
@app.post("/publish", response_model=PublishResponse)
async def publish_post(request: PublishRequest):
    try:
        # 実際の処理（例: Substack APIを呼び出す）
        post_id = await create_post(request.title, request.content)

        return PublishResponse(
            success=True,
            post_id=post_id,
            url=f"https://example.substack.com/p/{post_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# サーバー起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 2: 環境変数管理

`pydantic-settings` で環境変数を型安全に管理：

```python
# config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API認証
    api_key: str
    api_secret: Optional[str] = None

    # サービス設定
    substack_cookies: Optional[str] = None
    substack_publication_url: str

    # アプリケーション設定
    debug: bool = False
    log_level: str = "info"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# シングルトンとして使用
settings = Settings()
```

使用例：

```python
from config import settings

@app.post("/publish")
async def publish_post(request: PublishRequest):
    # 環境変数から読み込んだ設定を使用
    api = Api(cookies_string=settings.substack_cookies)
    # ...
```

### Step 3: エラーハンドリング

カスタム例外ハンドラーでエラーを統一管理：

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# カスタム例外クラス
class SubstackAPIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

# 例外ハンドラー
@app.exception_handler(SubstackAPIError)
async def substack_error_handler(request: Request, exc: SubstackAPIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.message,
            "detail": "Substack API returned an error"
        }
    )

# 使用例
@app.post("/publish")
async def publish_post(request: PublishRequest):
    if not request.title:
        raise SubstackAPIError("Title is required", status_code=400)
    # ...
```

### Step 4: ミドルウェアでログとCORS設定

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番では特定のオリジンのみ許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエストログ
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response
```

### Step 5: Dockerファイル作成

マルチステージビルドで軽量なイメージを作成：

```dockerfile
# docker/substack-api/Dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 本番イメージ
FROM python:3.11-slim

# 非rootユーザー作成
RUN useradd -m -u 1000 appuser

WORKDIR /app

# ビルダーから依存関係をコピー
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

# PATH設定
ENV PATH=/home/appuser/.local/bin:$PATH

USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# サーバー起動
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

requirements.txt:

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-substack==0.1.0  # 例: Substack用
requests==2.31.0
```

### Step 6: Docker Compose 統合

```yaml
# docker-compose.quick.yml
services:
  substack-api:
    build:
      context: ./docker/substack-api
      dockerfile: Dockerfile
    container_name: openclaw-substack-api
    restart: unless-stopped

    ports:
      - "127.0.0.1:8000:8000"  # ローカルのみアクセス可

    environment:
      SUBSTACK_COOKIES: ${SUBSTACK_COOKIES:-}
      SUBSTACK_PUBLICATION_URL: ${SUBSTACK_PUBLICATION_URL}
      LOG_LEVEL: ${LOG_LEVEL:-info}

    networks:
      - openclaw-network

    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Step 7: API テスト

```bash
# ヘルスチェック
curl http://localhost:8000/health

# APIドキュメント（Swagger UI）
open http://localhost:8000/docs

# ReDoc形式のドキュメント
open http://localhost:8000/redoc

# 投稿テスト
curl -X POST http://localhost:8000/publish \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Post",
    "content": "This is a test post.",
    "is_draft": true
  }'
```

## Examples

### Example 1: Substack 自動投稿 API

```python
# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from substack import Api
from substack.post import Post
from config import settings

app = FastAPI(title="Substack Publishing API")

class PublishRequest(BaseModel):
    title: str
    content: str
    subtitle: str = ""
    is_draft: bool = False

class PublishResponse(BaseModel):
    success: bool
    post_id: str = None
    url: str = None

@app.post("/publish", response_model=PublishResponse)
async def publish_post(request: PublishRequest):
    try:
        # Substack API初期化（Cookie認証）
        api = Api(
            cookies_string=settings.substack_cookies,
            publication_url=settings.substack_publication_url
        )

        # ユーザーID取得
        user = api.get_user()
        user_id = user.get("id")

        # 投稿作成
        post = Post(user_id=user_id, title=request.title, subtitle=request.subtitle)
        post.add(request.content)

        # ドラフト保存
        draft_result = api.post_draft(post)

        # 公開（is_draft=False の場合）
        if not request.is_draft:
            prepublish_result = api.prepublish_draft(draft_result)
            publish_result = api.publish_draft(prepublish_result)
            post_id = publish_result.get("id")
        else:
            post_id = draft_result.get("id")

        return PublishResponse(
            success=True,
            post_id=str(post_id),
            url=f"{settings.substack_publication_url}/p/{post_id}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish: {str(e)}")

@app.get("/health")
async def health_check():
    # 認証確認
    try:
        api = Api(cookies_string=settings.substack_cookies)
        user = api.get_user()
        return {
            "status": "healthy",
            "authenticated": True,
            "user_id": user.get("id")
        }
    except:
        return {
            "status": "healthy",
            "authenticated": False
        }
```

### Example 2: N8N から FastAPI を呼び出す

N8N HTTP Request Node の設定：

```json
{
  "name": "Publish to Substack via API",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "http://substack-api:8000/publish",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Content-Type",
          "value": "application/json"
        }
      ]
    },
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {
          "name": "title",
          "value": "={{$json.title}}"
        },
        {
          "name": "content",
          "value": "={{$json.content}}"
        },
        {
          "name": "is_draft",
          "value": false
        }
      ]
    }
  }
}
```

### Example 3: 非同期処理とバックグラウンドタスク

```python
from fastapi import BackgroundTasks

# バックグラウンドタスク
async def send_notification(post_id: str):
    # Telegram通知を送信
    import requests
    requests.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={
            "chat_id": settings.telegram_chat_id,
            "text": f"✅ 投稿完了: Post ID {post_id}"
        }
    )

@app.post("/publish")
async def publish_post(request: PublishRequest, background_tasks: BackgroundTasks):
    # 投稿処理
    post_id = await create_post(request.title, request.content)

    # バックグラウンドで通知送信
    background_tasks.add_task(send_notification, post_id)

    return {"success": True, "post_id": post_id}
```

## Best Practices

### ✅ Do This

- **型安全なモデル**: PydanticでリクエストとレスポンスをすべてModelで定義
- **非同期処理**: I/O待機が発生する処理は `async def` で定義
- **環境変数管理**: `pydantic-settings` で型安全に管理
- **エラーハンドリング**: `HTTPException` と カスタム例外ハンドラーを使用
- **ヘルスチェック**: `/health` エンドポイントを必ず実装
- **APIドキュメント**: 自動生成されるSwagger UIを活用（`/docs`）
- **マルチステージビルド**: Dockerイメージを軽量化
- **非rootユーザー**: セキュリティのためコンテナは非rootで実行

### ❌ Avoid This

- **同期処理の濫用**: `def` ではなく `async def` を使う（I/O処理）
- **型なしリクエスト**: `dict` ではなく Pydantic Model を使う
- **ハードコードされた設定**: 環境変数で管理する
- **エラーの握りつぶし**: `try-except` で捕捉したら必ずログ出力
- **ポート公開**: 外部からアクセスする必要がなければ `127.0.0.1:port` にバインド
- **rootユーザー**: Dockerコンテナは必ず非rootで実行

## Common Pitfalls

### Problem: `asyncio` エラー: Event loop is closed

**Root Cause:** 非同期関数内で同期ライブラリを使用している

**Solution:**
```python
# ❌ Wrong: 同期ライブラリを async内で使用
@app.post("/publish")
async def publish_post(request: PublishRequest):
    result = requests.post("https://api.example.com", json=request.dict())  # 同期処理

# ✅ Correct: 非同期ライブラリを使用
import httpx

@app.post("/publish")
async def publish_post(request: PublishRequest):
    async with httpx.AsyncClient() as client:
        result = await client.post("https://api.example.com", json=request.dict())
```

**Prevention:** I/O処理には `httpx`, `aiofiles`, `asyncpg` 等の非同期ライブラリを使用

---

### Problem: Pydantic ValidationError

**Root Cause:** リクエストボディのフィールド型が一致しない

**Symptoms:**
```json
{
  "detail": [
    {
      "loc": ["body", "is_draft"],
      "msg": "value is not a valid boolean",
      "type": "type_error.bool"
    }
  ]
}
```

**Solution:**
```python
# リクエストモデルで適切な型を定義
class PublishRequest(BaseModel):
    title: str  # 必須
    content: str  # 必須
    is_draft: bool = False  # デフォルト値あり

    # カスタムバリデーション
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title must not be empty')
        return v
```

**Prevention:** Pydantic Model で型とバリデーションルールを明確に定義

---

### Problem: CORS エラー（ブラウザから呼び出し時）

**Root Cause:** CORS ミドルウェアが未設定

**Symptoms:**
```
Access to fetch at 'http://localhost:8000/api' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

**Solution:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 許可するオリジン
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Prevention:** フロントエンドから呼び出す場合は必ずCORS設定を追加

## Configuration Reference

### Uvicorn 起動オプション

```bash
# 開発環境: ホットリロード有効
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 本番環境: ワーカー複数起動
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# ログレベル指定
uvicorn app:app --log-level info

# SSL/TLS対応
uvicorn app:app --ssl-keyfile=./key.pem --ssl-certfile=./cert.pem
```

### 環境変数

```bash
# アプリケーション設定
DEBUG=false
LOG_LEVEL=info

# Uvicorn設定
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_WORKERS=4
```

## Related Skills

- `@api-design-principles` - REST API設計のベストプラクティス
- `@n8n-openclaw-integration` - N8Nワークフローとの連携
- `@docker-performance-tuning` - Dockerコンテナ最適化
- See also: `docker/substack-api/` - Substack API実装例

## Troubleshooting

### Issue 1: ImportError: No module named 'fastapi'

**Solution:**
```bash
# コンテナ内で依存関係を再インストール
docker exec -it openclaw-substack-api pip install -r requirements.txt

# またはDockerイメージを再ビルド
docker compose -f docker-compose.quick.yml up -d --build substack-api
```

### Issue 2: Uvicorn が起動しない

**Symptoms:**
```
Error loading ASGI app. Could not import module "app".
```

**Diagnosis:**
```bash
# アプリケーションファイルの存在確認
docker exec openclaw-substack-api ls -la /app/app.py

# Pythonパスを確認
docker exec openclaw-substack-api python -c "import sys; print(sys.path)"
```

**Fix:**
- `app.py` が `/app/` 直下にあるか確認
- Dockerfileの `COPY` コマンドを確認

## Advanced Usage

### Dependency Injection

FastAPIの依存性注入システムを活用：

```python
from fastapi import Depends

# 依存関数
async def get_api_client():
    api = Api(cookies_string=settings.substack_cookies)
    yield api
    # クリーンアップ処理

# エンドポイントで使用
@app.post("/publish")
async def publish_post(
    request: PublishRequest,
    api: Api = Depends(get_api_client)  # 依存性注入
):
    user = api.get_user()
    # ...
```

### OpenAPI カスタマイズ

API仕様書をカスタマイズ：

```python
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="OpenClaw Custom API",
        version="1.0.0",
        description="Powerful API for OpenClaw automation",
        routes=app.routes,
    )

    # カスタムフィールド追加
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## References

- [FastAPI Official Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Async Python Guide](https://realpython.com/async-io-python/)
- Related: `docker/substack-api/app.py` - 実装例

---

*最終更新: 2026-02-15 — FastAPI実践ガイドを作成（Substack API実装を反映）*
