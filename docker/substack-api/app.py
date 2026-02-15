#!/usr/bin/env python3
"""
Substack Publishing API Server
N8Nから呼び出してSubstackに自動投稿するための軽量APIサーバー
"""
import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from substack import Api
from substack.post import Post

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Substack Publishing API",
    description="N8N integration for automated Substack publishing",
    version="1.0.0"
)

# 環境変数から認証情報を取得
SUBSTACK_EMAIL = os.getenv("SUBSTACK_EMAIL")
SUBSTACK_PASSWORD = os.getenv("SUBSTACK_PASSWORD")
SUBSTACK_COOKIES = os.getenv("SUBSTACK_COOKIES")  # Cookie認証（CAPTCHA回避）
SUBSTACK_PUBLICATION_URL = os.getenv("SUBSTACK_PUBLICATION_URL")

# Cookie認証またはメール/パスワード認証のいずれかが必要
if not SUBSTACK_PUBLICATION_URL:
    logger.error("SUBSTACK_PUBLICATION_URL is required")
    raise RuntimeError("SUBSTACK_PUBLICATION_URL must be set")

if not SUBSTACK_COOKIES and not all([SUBSTACK_EMAIL, SUBSTACK_PASSWORD]):
    logger.error("Missing authentication credentials")
    raise RuntimeError("Either SUBSTACK_COOKIES or (SUBSTACK_EMAIL + SUBSTACK_PASSWORD) must be set")


class PublishRequest(BaseModel):
    """投稿リクエストのスキーマ"""
    title: str = Field(..., description="記事のタイトル")
    content: str = Field(..., description="記事の本文（HTML）")
    subtitle: Optional[str] = Field(None, description="サブタイトル（任意）")
    is_draft: bool = Field(False, description="下書きとして保存（True）、即公開（False）")


class PublishResponse(BaseModel):
    """投稿レスポンスのスキーマ"""
    success: bool
    message: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None


@app.get("/")
async def root():
    """ヘルスチェック"""
    return {
        "service": "Substack Publishing API",
        "status": "running",
        "publication": SUBSTACK_PUBLICATION_URL
    }


@app.post("/publish", response_model=PublishResponse)
async def publish_post(request: PublishRequest):
    """
    Substackに記事を投稿する

    Args:
        request: PublishRequest（タイトル、本文、サブタイトル等）

    Returns:
        PublishResponse（成功/失敗、投稿URL等）
    """
    try:
        logger.info(f"Publishing post: {request.title}")

        # Substack APIに接続（Cookie認証を優先）
        if SUBSTACK_COOKIES:
            logger.info("Using cookie authentication")
            api = Api(
                cookies_string=SUBSTACK_COOKIES,
                publication_url=SUBSTACK_PUBLICATION_URL
            )
        else:
            logger.info("Using email/password authentication")
            api = Api(
                email=SUBSTACK_EMAIL,
                password=SUBSTACK_PASSWORD,
                publication_url=SUBSTACK_PUBLICATION_URL
            )

        # ユーザーIDを取得
        user_id = api.get_user_id()
        logger.info(f"Authenticated as user: {user_id}")

        # 投稿を作成
        post = Post(
            user_id=user_id,
            title=request.title,
            subtitle=request.subtitle or ""
        )

        # 本文を追加（HTMLとして）
        post.add(request.content)

        # 下書き投稿
        draft_result = api.post_draft(post)
        logger.info(f"Draft created: {draft_result}")

        if request.is_draft:
            # 下書きとして保存のみ
            return PublishResponse(
                success=True,
                message="Draft saved successfully",
                post_id=str(draft_result.get('id')),
                post_url=f"{SUBSTACK_PUBLICATION_URL}/p/{draft_result.get('slug')}"
            )
        else:
            # 即公開
            prepublish_result = api.prepublish_draft(draft_result)
            publish_result = api.publish_draft(prepublish_result)
            logger.info(f"Published: {publish_result}")

            return PublishResponse(
                success=True,
                message="Post published successfully",
                post_id=str(publish_result.get('id')),
                post_url=f"{SUBSTACK_PUBLICATION_URL}/p/{publish_result.get('slug')}"
            )

    except Exception as e:
        logger.error(f"Failed to publish post: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to publish post: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """詳細なヘルスチェック"""
    try:
        # Substack接続テスト（Cookie認証を優先）
        if SUBSTACK_COOKIES:
            api = Api(
                cookies_string=SUBSTACK_COOKIES,
                publication_url=SUBSTACK_PUBLICATION_URL
            )
        else:
            api = Api(
                email=SUBSTACK_EMAIL,
                password=SUBSTACK_PASSWORD,
                publication_url=SUBSTACK_PUBLICATION_URL
            )
        user_id = api.get_user_id()

        return {
            "status": "healthy",
            "substack_connection": "ok",
            "authenticated": True,
            "user_id": user_id
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "substack_connection": "failed",
            "authenticated": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
