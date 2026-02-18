"""
Nowpattern Publisher v1.0
Ghost投稿 + X引用リポスト + 記事インデックス更新を担当する。

責務: 記事の外部公開とインデックス管理。HTML生成は nowpattern_article_builder.py が担当。

使い方:
  from nowpattern_publisher import publish_deep_pattern, publish_speed_log

  result = publish_deep_pattern(
      article_id="dp-2026-0218-001",
      title="EUがAppleに2兆円の制裁金を課した構造",
      html=html,  # nowpattern_article_builder.py で生成
      genre_tags=["テクノロジー", "経済・金融"],
      event_tags=["司法・制裁", "標準化・独占"],
      dynamics_tags=["プラットフォーム支配", "規制の捕獲"],
      source_urls=["https://ec.europa.eu/..."],
      related_article_ids=["dp-2026-0215-003"],
      ghost_url="https://nowpattern.com",
      admin_api_key="KEY_ID:SECRET",
  )
"""

import json
import hashlib
import hmac
import time
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Ghost API integration (moved from old builder.py)
# ---------------------------------------------------------------------------

def make_ghost_jwt(admin_api_key: str) -> str:
    """Ghost Admin API用のJWTトークンを生成する"""
    import base64

    key_id, secret = admin_api_key.split(":")
    iat = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": iat, "exp": iat + 300, "aud": "/admin/"}

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    h = b64url(json.dumps(header).encode())
    p = b64url(json.dumps(payload).encode())
    signing_input = f"{h}.{p}"
    secret_bytes = bytes.fromhex(secret)
    sig = hmac.new(secret_bytes, signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(sig)}"


def post_to_ghost(
    title: str,
    html: str,
    tags: list[str],
    ghost_url: str = "https://nowpattern.com",
    admin_api_key: str = "",
    status: str = "published",
    featured: bool = False,
) -> dict:
    """Ghost Admin APIに記事を投稿する（?source=html でGhostがlexical変換）"""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        import requests
    except ImportError:
        print("ERROR: requests library not installed. Run: pip install requests")
        return {}

    token = make_ghost_jwt(admin_api_key)
    # Ghost 5.x: ?source=html を付けるとGhostがHTMLをlexical形式に自動変換する
    url = f"{ghost_url}/ghost/api/admin/posts/?source=html"
    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
    }
    body = {
        "posts": [
            {
                "title": title,
                "html": html,
                "tags": [{"name": t} for t in tags],
                "status": status,
                "featured": featured,
            }
        ]
    }

    resp = requests.post(url, json=body, headers=headers, verify=False, timeout=30)
    if resp.status_code == 201:
        post_data = resp.json()["posts"][0]
        print(f"OK: Published '{title}' -> {ghost_url}/{post_data.get('slug', '')}/")
        return post_data
    else:
        print(f"ERROR {resp.status_code}: {resp.text[:500]}")
        return {"error": resp.status_code, "detail": resp.text[:500]}


def update_ghost_post(
    post_id: str,
    html: str,
    updated_at: str,
    ghost_url: str = "https://nowpattern.com",
    admin_api_key: str = "",
) -> dict:
    """既存のGhost記事のコンテンツをlexical HTML cardで更新する"""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        import requests
    except ImportError:
        print("ERROR: requests library not installed. Run: pip install requests")
        return {}

    token = make_ghost_jwt(admin_api_key)
    url = f"{ghost_url}/ghost/api/admin/posts/{post_id}/?source=html"
    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
    }
    body = {
        "posts": [
            {
                "html": html,
                "updated_at": updated_at,
            }
        ]
    }

    resp = requests.put(url, json=body, headers=headers, verify=False, timeout=30)
    if resp.status_code == 200:
        post_data = resp.json()["posts"][0]
        print(f"OK: Updated post {post_id} (html length: {len(post_data.get('html', ''))})")
        return post_data
    else:
        print(f"ERROR {resp.status_code}: {resp.text[:500]}")
        return {"error": resp.status_code, "detail": resp.text[:500]}


# ---------------------------------------------------------------------------
# Article Index management
# ---------------------------------------------------------------------------

DEFAULT_INDEX_PATH = "/opt/shared/nowpattern_article_index.json"


def load_index(index_path: str = DEFAULT_INDEX_PATH) -> dict:
    """記事インデックスを読み込む"""
    p = Path(index_path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "meta": {
            "version": "1.0",
            "last_updated": "",
            "total_articles": 0,
            "total_deep_patterns": 0,
            "total_speed_logs": 0,
        },
        "articles": [],
        "dynamics_index": {
            "プラットフォーム支配": [], "規制の捕獲": [], "物語の覇権": [],
            "対立の螺旋": [], "同盟の亀裂": [], "経路依存": [],
            "制度の劣化": [], "協調の失敗": [], "モラルハザード": [],
            "危機便乗": [], "後発逆転": [], "勝者総取り": [],
        },
        "genre_index": {
            "政治・政策": [], "地政学・安全保障": [], "経済・金融": [],
            "ビジネス・企業": [], "テクノロジー": [], "暗号資産・Web3": [],
            "科学・医療": [], "エネルギー・環境": [], "社会・人口": [],
            "文化・メディア": [], "スポーツ": [], "エンタメ": [],
        },
    }


def save_index(index: dict, index_path: str = DEFAULT_INDEX_PATH) -> None:
    """記事インデックスを保存する"""
    index["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    p = Path(index_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: Index updated at {index_path}")


def add_article_to_index(
    index: dict,
    article_id: str,
    mode: str,
    title_ja: str,
    title_en: str = "",
    slug: str = "",
    url: str = "",
    ghost_id: str = "",
    genre_tags: list[str] | None = None,
    event_tags: list[str] | None = None,
    dynamics_tags: list[str] | None = None,
    dynamics_tags_en: list[str] | None = None,
    word_count_ja: int = 0,
    word_count_en: int = 0,
    related_article_ids: list[str] | None = None,
    source_urls: list[str] | None = None,
    pattern_history_cases: list[dict] | None = None,
) -> dict:
    """記事をインデックスに追加する"""
    genre_tags = genre_tags or []
    event_tags = event_tags or []
    dynamics_tags = dynamics_tags or []
    dynamics_tags_en = dynamics_tags_en or []
    related_article_ids = related_article_ids or []
    source_urls = source_urls or []
    pattern_history_cases = pattern_history_cases or []

    article_entry = {
        "id": article_id,
        "mode": mode,
        "title_ja": title_ja,
        "title_en": title_en,
        "slug": slug,
        "url": url,
        "ghost_id": ghost_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "genre_tags": genre_tags,
        "event_tags": event_tags,
        "dynamics_tags": dynamics_tags,
        "dynamics_tags_en": dynamics_tags_en,
        "word_count_ja": word_count_ja,
        "word_count_en": word_count_en,
        "related_article_ids": related_article_ids,
        "source_urls": source_urls,
        "pattern_history_cases": pattern_history_cases,
    }

    index["articles"].append(article_entry)

    # Update counts
    index["meta"]["total_articles"] = len(index["articles"])
    index["meta"]["total_deep_patterns"] = sum(1 for a in index["articles"] if a["mode"] == "deep_pattern")
    index["meta"]["total_speed_logs"] = sum(1 for a in index["articles"] if a["mode"] == "speed_log")

    # Update dynamics_index
    for tag in dynamics_tags:
        if tag in index["dynamics_index"]:
            if article_id not in index["dynamics_index"][tag]:
                index["dynamics_index"][tag].append(article_id)

    # Update genre_index
    for tag in genre_tags:
        if tag in index["genre_index"]:
            if article_id not in index["genre_index"][tag]:
                index["genre_index"][tag].append(article_id)

    return index


def find_related_articles(index: dict, dynamics_tags: list[str], exclude_id: str = "") -> list[dict]:
    """同じ力学タグを持つ過去記事を検索する（自己参照ナレッジグラフ用）"""
    related = []
    seen_ids = set()
    for tag in dynamics_tags:
        for article_id in index.get("dynamics_index", {}).get(tag, []):
            if article_id != exclude_id and article_id not in seen_ids:
                seen_ids.add(article_id)
                for article in index["articles"]:
                    if article["id"] == article_id:
                        related.append(article)
                        break
    return related


def generate_article_id(mode: str) -> str:
    """記事IDを生成する"""
    now = datetime.now(timezone.utc)
    prefix = "dp" if mode == "deep_pattern" else "sl"
    date_part = now.strftime("%Y-%m%d")
    # Simple counter based on timestamp
    counter = int(now.strftime("%H%M%S")[-3:])
    return f"{prefix}-{date_part}-{counter:03d}"


# ---------------------------------------------------------------------------
# High-level publish functions
# ---------------------------------------------------------------------------

def publish_deep_pattern(
    article_id: str,
    title: str,
    html: str,
    genre_tags: list[str],
    event_tags: list[str],
    dynamics_tags: list[str],
    dynamics_tags_en: list[str] | None = None,
    source_urls: list[str] | None = None,
    related_article_ids: list[str] | None = None,
    pattern_history_cases: list[dict] | None = None,
    word_count_ja: int = 0,
    title_en: str = "",
    ghost_url: str = "https://nowpattern.com",
    admin_api_key: str = "",
    status: str = "published",
    index_path: str = DEFAULT_INDEX_PATH,
) -> dict:
    """Deep Pattern記事をGhostに投稿し、インデックスを更新する"""

    all_tags = genre_tags + event_tags + dynamics_tags

    # Step 1: Ghost投稿
    ghost_result = post_to_ghost(
        title=title,
        html=html,
        tags=all_tags,
        ghost_url=ghost_url,
        admin_api_key=admin_api_key,
        status=status,
        featured=True,
    )

    slug = ghost_result.get("slug", "")
    ghost_id = ghost_result.get("id", "")
    url = f"{ghost_url}/{slug}/" if slug else ""

    # Step 2: インデックス更新
    index = load_index(index_path)
    index = add_article_to_index(
        index=index,
        article_id=article_id,
        mode="deep_pattern",
        title_ja=title,
        title_en=title_en,
        slug=slug,
        url=url,
        ghost_id=ghost_id,
        genre_tags=genre_tags,
        event_tags=event_tags,
        dynamics_tags=dynamics_tags,
        dynamics_tags_en=dynamics_tags_en,
        word_count_ja=word_count_ja,
        related_article_ids=related_article_ids,
        source_urls=source_urls,
        pattern_history_cases=pattern_history_cases,
    )
    save_index(index, index_path)

    print(f"OK: Deep Pattern '{title}' published + indexed as {article_id}")
    return {
        "article_id": article_id,
        "ghost_result": ghost_result,
        "url": url,
        "index_updated": True,
    }


def publish_speed_log(
    article_id: str,
    title: str,
    html: str,
    genre_tags: list[str],
    event_tags: list[str],
    dynamics_tags: list[str],
    source_urls: list[str] | None = None,
    ghost_url: str = "https://nowpattern.com",
    admin_api_key: str = "",
    status: str = "published",
    index_path: str = DEFAULT_INDEX_PATH,
) -> dict:
    """Speed Log記事をGhostに投稿し、インデックスを更新する"""

    all_tags = genre_tags + event_tags + dynamics_tags + ["Speed Log"]

    ghost_result = post_to_ghost(
        title=title,
        html=html,
        tags=all_tags,
        ghost_url=ghost_url,
        admin_api_key=admin_api_key,
        status=status,
    )

    slug = ghost_result.get("slug", "")
    ghost_id = ghost_result.get("id", "")
    url = f"{ghost_url}/{slug}/" if slug else ""

    index = load_index(index_path)
    index = add_article_to_index(
        index=index,
        article_id=article_id,
        mode="speed_log",
        title_ja=title,
        slug=slug,
        url=url,
        ghost_id=ghost_id,
        genre_tags=genre_tags,
        event_tags=event_tags,
        dynamics_tags=dynamics_tags,
        source_urls=source_urls,
    )
    save_index(index, index_path)

    print(f"OK: Speed Log '{title}' published + indexed as {article_id}")
    return {
        "article_id": article_id,
        "ghost_result": ghost_result,
        "url": url,
        "index_updated": True,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== Nowpattern Publisher v1.0 ===")
    print("Ghost投稿 + インデックス更新")
    print()
    print("利用可能な関数:")
    print("  publish_deep_pattern()  - Deep Pattern記事投稿+インデックス更新")
    print("  publish_speed_log()     - Speed Log記事投稿+インデックス更新")
    print("  find_related_articles() - 同じ力学タグの過去記事検索")
    print("  generate_article_id()   - 記事ID自動生成")
    print()
    print("HTML生成は nowpattern_article_builder.py を使用してください。")
