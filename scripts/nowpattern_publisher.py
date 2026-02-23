"""
Nowpattern Publisher v3.1
Ghost投稿 + 記事インデックス更新を担当する。

責務: 記事の外部公開とインデックス管理。HTML生成は nowpattern_article_builder.py が担当。
タクソノミーバリデーション: taxonomy.json駆動のSTRICTバリデーション。不正タグは投稿をブロックする。
フォーマットゲート: v5.3準拠チェック（FAST READ, TAG_BADGE, SUMMARY, Between the Lines, OPEN LOOP）

v3.1 changes:
  - genre slugプレフィックス廃止（genre-geopolitics → geopolitics）
  - v5.3フォーマットゲート（np-tag-badge, np-summary 必須追加）
  - speakable JSONLD更新（np-bottom-line廃止 → np-fast-read, np-summary, np-why-box）

Ghostタグルール（v3.0）:
  - 全タグは英語name_en + taxonomy slugで統一（日本語名はbuilder側で表示翻訳）
  - 入力がJA/EN/slugどれでも自動で正規化される
  - タクソノミー外のタグは投稿を拒否する（安全ネット）

使い方:
  from nowpattern_publisher import publish_deep_pattern

  result = publish_deep_pattern(
      article_id="dp-2026-0218-001",
      title="EUがAppleに2兆円の制裁金を課した構造",
      html=html,  # nowpattern_article_builder.py で生成
      genre_tags=["Technology", "Economy & Trade"],  # name_en推奨（name_jaも可）
      event_tags=["Judicial Action", "Structural Shift"],
      dynamics_tags=["Platform Power", "Regulatory Capture"],
      source_urls=["https://ec.europa.eu/..."],
      related_article_ids=["dp-2026-0215-003"],
      ghost_url="https://nowpattern.com",
      admin_api_key="KEY_ID:SECRET",
  )
"""

import json
import hashlib
import hmac
import os
import time
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Genre-based URL structure (v4.0: routes.yaml collection routing)
# ---------------------------------------------------------------------------

# Routes.yaml collection priority order — determines URL for multi-genre articles.
# The first matching genre in this order becomes the article's URL genre.
GENRE_PRIORITY_ORDER = [
    "geopolitics", "finance", "economy", "technology",
    "crypto", "energy", "environment", "governance",
    "business", "culture", "health", "media", "society",
]


def get_primary_genre_url(genre_slugs: list[str]) -> str:
    """記事のジャンルスラッグリストから、URLに使うプライマリジャンルのパスを返す。

    Args:
        genre_slugs: ["crypto", "governance"] etc.
    Returns:
        "crypto" (routes.yamlの優先順位で最初にマッチしたジャンル)
    """
    for g in GENRE_PRIORITY_ORDER:
        if g in genre_slugs:
            return g
    return ""


# ---------------------------------------------------------------------------
# Taxonomy-driven tag resolution (v3.0: taxonomy.json single source of truth)
# ---------------------------------------------------------------------------

_TAXONOMY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nowpattern_taxonomy.json")
_TAG_LOOKUP = {}  # any_name_or_slug -> {"name": name_en, "slug": slug, "type": "genre"|"event"|"dynamics"}
_TAXONOMY_LOADED = False


def _load_taxonomy():
    """taxonomy.jsonを読み込み、あらゆる入力形式から正規タグへの逆引きテーブルを構築する。"""
    global _TAG_LOOKUP, _TAXONOMY_LOADED
    if _TAXONOMY_LOADED:
        return

    try:
        with open(_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
    except FileNotFoundError:
        print(f"WARNING: {_TAXONOMY_PATH} not found. Tag validation disabled.")
        _TAXONOMY_LOADED = True
        return

    # Fixed tags
    for ft in tax.get("fixed_tags", []):
        entry = {"name": ft["name"], "slug": ft["slug"], "type": "fixed"}
        _TAG_LOOKUP[ft["name"]] = entry
        _TAG_LOOKUP[ft["name"].lower()] = entry
        _TAG_LOOKUP[ft["slug"]] = entry

    # Genres
    for g in tax.get("genres", []):
        entry = {"name": g["name_en"], "slug": g["slug"], "type": "genre"}
        _TAG_LOOKUP[g["name_en"]] = entry
        _TAG_LOOKUP[g["name_en"].lower()] = entry
        _TAG_LOOKUP[g["name_ja"]] = entry
        _TAG_LOOKUP[g["slug"]] = entry

    # Events
    for e in tax.get("events", []):
        entry = {"name": e["name_en"], "slug": e["slug"], "type": "event"}
        _TAG_LOOKUP[e["name_en"]] = entry
        _TAG_LOOKUP[e["name_en"].lower()] = entry
        _TAG_LOOKUP[e["name_ja"]] = entry
        _TAG_LOOKUP[e["slug"]] = entry

    # Dynamics
    for d in tax.get("dynamics", []):
        entry = {"name": d["name_en"], "slug": d["slug"], "type": "dynamics"}
        _TAG_LOOKUP[d["name_en"]] = entry
        _TAG_LOOKUP[d["name_en"].lower()] = entry
        _TAG_LOOKUP[d["name_ja"]] = entry
        _TAG_LOOKUP[d["slug"]] = entry

    _TAXONOMY_LOADED = True
    print(f"  Taxonomy loaded: {len(tax.get('genres', []))} genres, {len(tax.get('events', []))} events, {len(tax.get('dynamics', []))} dynamics")


def resolve_tag(input_tag: str) -> dict | None:
    """任意の入力（name_en, name_ja, slug）を正規タグに解決する。

    Returns: {"name": name_en, "slug": slug, "type": ...} or None if not found.
    """
    _load_taxonomy()
    if input_tag in _TAG_LOOKUP:
        return _TAG_LOOKUP[input_tag]
    if input_tag.lower() in _TAG_LOOKUP:
        return _TAG_LOOKUP[input_tag.lower()]
    return None


def resolve_tag_list(tags: list[str], tag_type: str) -> list[dict]:
    """タグリストを正規化する。不正タグがあればValueErrorを送出。

    Args:
        tags: 入力タグリスト（name_en, name_ja, slugのいずれか）
        tag_type: "genre", "event", "dynamics" — タイプ一致も検証

    Returns: [{"name": name_en, "slug": slug}, ...] — Ghost API送信用
    """
    resolved = []
    errors = []

    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue

        result = resolve_tag(tag)
        if result is None:
            errors.append(f"  REJECT '{tag}' — タクソノミーに存在しません")
        elif result["type"] != tag_type and result["type"] != "fixed":
            errors.append(f"  REJECT '{tag}' — タイプ不一致（期待: {tag_type}, 実際: {result['type']}）")
        else:
            if tag != result["name"]:
                print(f"  AUTO-FIX: '{tag}' -> '{result['name']}' (slug: {result['slug']})")
            resolved.append({"name": result["name"], "slug": result["slug"]})

    if errors:
        print("TAXONOMY VALIDATION FAILED:")
        print("\n".join(errors))
        raise ValueError(
            f"タクソノミーバリデーション失敗: {len(errors)}個の不正タグ。"
            f"タクソノミーに登録されたタグのみ使用してください。\n"
            + "\n".join(errors)
        )

    return resolved


def validate_tags(
    dynamics_tags: list[str],
    event_tags: list[str],
    genre_tags: list[str],
    strict: bool = True,
    auto_fix: bool = True,
) -> list[str]:
    """タクソノミーバリデーション（v3.0: STRICT by default）。

    strict=True（デフォルト）: 不正タグがあれば ValueError で投稿をブロック。
    auto_fix=True: 入力がJA/slugでも自動でname_enに正規化する。
    """
    _load_taxonomy()
    warnings = []

    for i, tag in enumerate(dynamics_tags):
        result = resolve_tag(tag)
        if result and result["type"] == "dynamics":
            if auto_fix and tag != result["name"]:
                print(f"  AUTO-FIX dynamics: '{tag}' -> '{result['name']}'")
                dynamics_tags[i] = result["name"]
        else:
            warnings.append(f"REJECT dynamics: '{tag}'")

    for i, tag in enumerate(event_tags):
        result = resolve_tag(tag)
        if result and result["type"] == "event":
            if auto_fix and tag != result["name"]:
                print(f"  AUTO-FIX event: '{tag}' -> '{result['name']}'")
                event_tags[i] = result["name"]
        else:
            warnings.append(f"REJECT event: '{tag}'")

    for i, tag in enumerate(genre_tags):
        result = resolve_tag(tag)
        if result and result["type"] == "genre":
            if auto_fix and tag != result["name"]:
                print(f"  AUTO-FIX genre: '{tag}' -> '{result['name']}'")
                genre_tags[i] = result["name"]
        else:
            warnings.append(f"REJECT genre: '{tag}'")

    if warnings:
        msg = "TAXONOMY VALIDATION FAILED:\n" + "\n".join(warnings)
        print(msg)
        if strict:
            raise ValueError(msg)

    return warnings


# Legacy compatibility aliases (for external scripts)
VALID_DYNAMICS_TAGS = set()
VALID_EVENT_TAGS = set()
VALID_GENRE_TAGS = set()

def _init_legacy_sets():
    """旧APIの互換用: VALID_*_TAGS セットを初期化"""
    global VALID_DYNAMICS_TAGS, VALID_EVENT_TAGS, VALID_GENRE_TAGS
    _load_taxonomy()
    VALID_DYNAMICS_TAGS = {v["name"] for v in _TAG_LOOKUP.values() if v["type"] == "dynamics"}
    VALID_EVENT_TAGS = {v["name"] for v in _TAG_LOOKUP.values() if v["type"] == "event"}
    VALID_GENRE_TAGS = {v["name"] for v in _TAG_LOOKUP.values() if v["type"] == "genre"}


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


def generate_organization_jsonld(
    ghost_url: str = "https://nowpattern.com",
) -> str:
    """Nowpattern サイト全体の Organization JSON-LD を生成する。

    Ghost 管理画面 → Settings → Code injection → Site Header に貼り付ける。
    E-E-A-T シグナルとして機能し、AIアシスタントがサイトを「信頼できる情報源」として認識する。

    generate_ghost_header_script() を呼び出すか、
    ローカルで python -c "from nowpattern_publisher import generate_organization_jsonld; print(generate_organization_jsonld())"
    を実行して Ghost に貼り付ける。
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": f"{ghost_url}/#organization",
        "name": "Nowpattern",
        "url": ghost_url,
        "logo": {
            "@type": "ImageObject",
            "url": f"{ghost_url}/content/images/2026/02/nowpattern_logo_profile.svg",
            "width": 512,
            "height": 512,
        },
        "sameAs": [
            "https://x.com/nowpattern",
        ],
        "description": (
            "Nowpattern analyzes global geopolitical and macro events through structural dynamics. "
            "Each article maps historical patterns, stakeholder conflicts, and 3-scenario probability forecasts."
        ),
        "knowsAbout": [
            "Geopolitics", "Macroeconomics", "Platform Economics",
            "Structural Pattern Analysis", "Scenario Forecasting",
            "Regulatory Capture", "Power Transition Theory",
            "Geopolitical Risk", "Economic Warfare",
        ],
        "publishingPrinciples": f"{ghost_url}/about/",
        "diversityPolicy": f"{ghost_url}/about/",
        "foundingDate": "2026",
        "inLanguage": ["ja", "en"],
    }
    jsonld_str = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{jsonld_str}</script>'


def generate_article_jsonld(
    title: str,
    excerpt: str,
    url: str,
    published_at: str,
    image_url: str = "",
    dynamics_tags: list[str] | None = None,
    language: str = "ja",
    ghost_url: str = "https://nowpattern.com",
) -> str:
    """記事ごとのJSONLDを生成する（SpeculativeArticle + speakable）。

    AIO最適化の要:
    - `SpeculativeArticle`: nowpatternの3シナリオ予測をGoogleがAI予測記事として認識
    - `speakable`: BOTTOM LINE / Why it matters がGoogleAIOに直接引用される
    - `author.knowsAbout`: 力学タグを専門知識シグナルとして登録

    Ghost APIの`codeinjection_foot`フィールドに文字列として渡す。
    """
    keywords = [t.replace(" ", "-").lower() for t in (dynamics_tags or [])]

    schema = {
        "@context": "https://schema.org",
        "@type": ["NewsArticle", "SpeculativeArticle"],
        "headline": title[:110],  # Googleは110文字以内を推奨
        "description": excerpt[:200],
        "url": url,
        "datePublished": published_at,
        "dateModified": published_at,
        "author": {
            "@type": "Organization",
            "name": "Nowpattern",
            "url": f"{ghost_url}/about/",
            "knowsAbout": keywords or [
                "Geopolitics", "Economic Analysis", "Platform Economics",
                "Structural Pattern Analysis", "Scenario Forecasting",
            ],
        },
        "publisher": {
            "@type": "Organization",
            "name": "Nowpattern",
            "logo": {
                "@type": "ImageObject",
                "url": f"{ghost_url}/content/images/2026/02/nowpattern_logo_profile.svg",
            },
        },
        "inLanguage": "ja" if language == "ja" else "en",
        "keywords": keywords,
        # speakable: これらのCSSセレクタの内容をAI/音声が直接引用する
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".np-fast-read", ".np-summary", ".np-why-box"],
        },
    }
    if image_url:
        schema["image"] = {
            "@type": "ImageObject",
            "url": image_url,
            "width": 1200,
            "height": 630,
        }

    jsonld_str = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{jsonld_str}</script>'


def post_to_ghost(
    title: str,
    html: str,
    tags: list[str] | list[dict] | None = None,
    ghost_url: str = "https://nowpattern.com",
    admin_api_key: str = "",
    status: str = "published",
    featured: bool = False,
    language: str = "ja",
    tag_objects: list[dict] | None = None,
    codeinjection_foot: str = "",
) -> dict:
    """Ghost Admin APIに記事を投稿する（lexical HTML card方式 — CSSを保持）

    NOTE: ?source=html はGhostがHTMLをlexical変換する際にCSS付きdiv/spanのスタイルを
    剥がしてしまうため使用禁止。lexical HTML card方式で直接送信すること。

    タグの指定方法（v3.0）:
      tag_objects（推奨）: [{"name": "Escalation Spiral", "slug": "p-escalation"}, ...]
        → slugを明示的に指定するため、Ghostが不正なslugを生成しない
      tags（旧API互換）: ["Escalation Spiral", ...] → name only, Ghost auto-generates slug

    language="ja" → lang-ja タグ自動付与
    language="en" → lang-en タグ自動付与
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        import requests
    except ImportError:
        print("ERROR: requests library not installed. Run: pip install requests")
        return {}

    token = make_ghost_jwt(admin_api_key)

    # lexical HTML card方式: CSSインラインスタイルを保持する
    lexical_doc = {
        "root": {
            "children": [{"type": "html", "version": 1, "html": html}],
            "direction": None, "format": "", "indent": 0,
            "type": "root", "version": 1,
        }
    }

    # タグを構築（v3.0: slug指定方式を優先）
    _load_taxonomy()
    if tag_objects:
        # 新API: slug指定済みオブジェクト
        ghost_tags = list(tag_objects)
    elif tags:
        # 旧API互換: name文字列リスト → resolve_tagでslugを付与
        ghost_tags = []
        for t in tags:
            resolved = resolve_tag(t)
            if resolved:
                ghost_tags.append({"name": resolved["name"], "slug": resolved["slug"]})
            else:
                ghost_tags.append({"name": t})  # fallback（バリデーション通過済みのはず）
    else:
        ghost_tags = []

    # 言語タグを自動付与（slug指定で確実にマッチ）
    if language == "ja":
        ghost_tags.append({"name": "日本語", "slug": "lang-ja"})
    else:
        ghost_tags.append({"name": "English", "slug": "lang-en"})

    url = f"{ghost_url}/ghost/api/admin/posts/"
    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
    }
    post_payload: dict = {
        "title": title,
        "lexical": json.dumps(lexical_doc),
        "tags": ghost_tags,
        "status": status,
        "featured": featured,
        "email_segment": "none",
    }
    if codeinjection_foot:
        post_payload["codeinjection_foot"] = codeinjection_foot

    body = {"posts": [post_payload]}

    resp = requests.post(url, json=body, headers=headers, verify=False, timeout=30)
    if resp.status_code == 201:
        post_data = resp.json()["posts"][0]
        actual_url = post_data.get("url", "")
        actual_slug = post_data.get("slug", "")
        print(f"OK: Published '{title}' -> {actual_url or ghost_url + '/' + actual_slug + '/'}")
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
    """既存のGhost記事のコンテンツをlexical HTML card方式で更新する。

    NOTE: ?source=html はCSSインラインスタイルを剥がすため使用禁止。
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        import requests
    except ImportError:
        print("ERROR: requests library not installed. Run: pip install requests")
        return {}

    token = make_ghost_jwt(admin_api_key)

    # lexical HTML card方式: CSSインラインスタイルを保持する
    lexical_doc = {
        "root": {
            "children": [{"type": "html", "version": 1, "html": html}],
            "direction": None, "format": "", "indent": 0,
            "type": "root", "version": 1,
        }
    }

    url = f"{ghost_url}/ghost/api/admin/posts/{post_id}/"
    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json",
    }
    body = {
        "posts": [
            {
                "lexical": json.dumps(lexical_doc),
                "updated_at": updated_at,
            }
        ]
    }

    resp = requests.put(url, json=body, headers=headers, verify=False, timeout=30)
    if resp.status_code == 200:
        post_data = resp.json()["posts"][0]
        print(f"OK: Updated post {post_id} (lexical: {len(post_data.get('lexical', ''))} chars)")
        return post_data
    else:
        print(f"ERROR {resp.status_code}: {resp.text[:500]}")
        return {"error": resp.status_code, "detail": resp.text[:500]}


# ---------------------------------------------------------------------------
# Article Index management
# ---------------------------------------------------------------------------

DEFAULT_INDEX_PATH = "/opt/shared/nowpattern_article_index.json"
DEFAULT_SITEMAP_PATH = "/opt/shared/sitemap-news.xml"
DEFAULT_LLMS_TXT_PATH = "/opt/shared/llms.txt"


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
        "dynamics_index": {tag: [] for tag in VALID_DYNAMICS_TAGS},
        "genre_index": {tag: [] for tag in VALID_GENRE_TAGS},
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
    # v5.0: Delta support
    bottom_line: str = "",
    scenario_summary: list[dict] | None = None,
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
        # v5.0: Delta support — future articles can reference this
        "bottom_line": bottom_line,
        "scenario_summary": scenario_summary or [],
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
# X (Twitter) API v2 posting
# ---------------------------------------------------------------------------

_X_MAX_CHARS = 1400


def post_to_x(
    text: str,
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
) -> dict:
    """X API v2 でツイートを投稿する（OAuth1.0a / requests_oauthlib）。

    認証情報は環境変数から渡すこと（コードに直書き禁止）:
        TWITTER_API_KEY, TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
    """
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("  SKIP X: API credentials not set")
        return {"skipped": True, "reason": "Missing X API credentials"}

    try:
        from requests_oauthlib import OAuth1
        import requests as req
    except ImportError:
        print("  ERROR X: requests_oauthlib not installed. Run: pip install requests-oauthlib")
        return {"error": "requests_oauthlib not installed"}

    auth = OAuth1(api_key, api_secret, access_token, access_token_secret)
    resp = req.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json={"text": text[:_X_MAX_CHARS]},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        tweet_id = resp.json().get("data", {}).get("id", "")
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
        print(f"  OK X: published → {tweet_url}")
        return {"tweet_id": tweet_id, "url": tweet_url}
    else:
        print(f"  ERROR X {resp.status_code}: {resp.text[:300]}")
        return {"error": resp.status_code, "detail": resp.text[:300]}


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
    # v5.0: Delta support
    bottom_line: str = "",
    scenario_summary: list[dict] | None = None,
    # v5.1: X posting (JP + EN 同時投稿)
    # build_x_post_texts() で生成したテキストを渡す。空文字ならX投稿スキップ
    x_post_ja: str = "",
    x_post_en: str = "",
    x_api_key: str = "",
    x_api_secret: str = "",
    x_access_token: str = "",
    x_access_token_secret: str = "",
    # v5.2: JSONLD excerpt (指定しなければ bottom_line にフォールバック)
    excerpt: str = "",
    # v5.2: 投稿後に sitemap を自動再生成するか
    auto_sitemap: bool = True,
    sitemap_output_path: str = DEFAULT_SITEMAP_PATH,
) -> dict:
    """Deep Pattern記事をGhostに投稿し、インデックスを更新する

    v3.0変更点:
    - タグはtaxonomy.jsonに基づいてSTRICTバリデーション（不正タグ→投稿ブロック）
    - Ghost APIにslug指定でタグ送信（不正なauto-slugを防止）
    - 実際のGhost APIレスポンスURLを使用（slug truncationによる404を防止）
    """

    # --- v5.3 フォーマットゲート（最終出口バリデーション） ---
    # v5.3: TAG_BADGE (np-tag-badge) + SUMMARY (np-summary) 必須追加
    v5_markers = ["np-fast-read", "np-between-lines", "np-open-loop", "np-tag-badge", "np-summary"]
    missing = [m for m in v5_markers if m not in html]
    if missing:
        print(f"  BLOCK v5.3 validation: HTML missing {', '.join(missing)}")
        print(f"     -> See docs/ARTICLE_FORMAT.md for required sections")
        raise ValueError(f"v5.3 format validation failed: missing {', '.join(missing)}")

    # --- タクソノミーバリデーション + 正規化（STRICT: 不正タグ→投稿ブロック） ---
    print("  Taxonomy validation (STRICT)...")
    genre_resolved = resolve_tag_list(genre_tags, "genre")
    event_resolved = resolve_tag_list(event_tags, "event")
    dynamics_resolved = resolve_tag_list(dynamics_tags, "dynamics")

    # --- ジャンル数バリデーション（1〜2個必須） ---
    if len(genre_resolved) < 1:
        raise ValueError("ジャンルタグが0個です。最低1個のジャンルタグが必要です。")
    if len(genre_resolved) > 2:
        raise ValueError(f"ジャンルタグが{len(genre_resolved)}個です。最大2個までです: {[t['name'] for t in genre_resolved]}")

    # --- ジャンルタグをroutes.yaml優先順位でソート（URL決定に影響） ---
    genre_resolved.sort(
        key=lambda t: GENRE_PRIORITY_ORDER.index(t["slug"]) if t["slug"] in GENRE_PRIORITY_ORDER else 99
    )

    # タグ構築: ジャンルを先頭に（Ghost primary_tag = 最初のタグ → URL決定に使用）
    tag_objects = (
        genre_resolved
        + [{"name": "Nowpattern", "slug": "nowpattern"}, {"name": "Deep Pattern", "slug": "deep-pattern"}]
        + event_resolved + dynamics_resolved
    )

    # Step 1: Ghost投稿（slug指定方式）
    # JSONLD事前生成（published_atは暫定値。Ghost APIレスポンスのURLが確定後に使う）
    published_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    # excerpt: 明示指定 > bottom_line > title の優先順
    _excerpt = excerpt or bottom_line or title
    jsonld = generate_article_jsonld(
        title=title,
        excerpt=_excerpt,
        url="",  # Ghost投稿前はURLが不明 — 投稿後に update_ghost_post でURLを更新できるが
                 # 初回投稿時はtitleベースのslugで十分（AIOはクロール後に拾う）
        published_at=published_at,
        dynamics_tags=dynamics_tags,
        language="ja" if not title_en else ("en" if title_en == title else "ja"),
        ghost_url=ghost_url,
    )

    ghost_result = post_to_ghost(
        title=title,
        html=html,
        tag_objects=tag_objects,
        ghost_url=ghost_url,
        admin_api_key=admin_api_key,
        status=status,
        featured=True,
        codeinjection_foot=jsonld,
    )

    # 実際のGhost URLを使用（slug truncationによる404を防止）
    slug = ghost_result.get("slug", "")
    ghost_id = ghost_result.get("id", "")
    url = ghost_result.get("url", "")
    if not url and slug:
        # フォールバック: routes.yamlのジャンルベースURL構造に合わせる
        genre_slugs = [t["slug"] for t in genre_resolved]
        primary_genre = get_primary_genre_url(genre_slugs)
        lang = "ja" if not title_en else ("en" if title_en == title else "ja")
        if lang == "en" and primary_genre:
            url = f"{ghost_url}/en/{primary_genre}/{slug}/"
        elif lang == "en":
            url = f"{ghost_url}/en/{slug}/"
        elif primary_genre:
            url = f"{ghost_url}/{primary_genre}/{slug}/"
        else:
            url = f"{ghost_url}/{slug}/"

    # 正規化後のタグ名をリストに書き戻す（インデックス用）
    genre_names = [t["name"] for t in genre_resolved]
    event_names = [t["name"] for t in event_resolved]
    dynamics_names = [t["name"] for t in dynamics_resolved]

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
        genre_tags=genre_names,
        event_tags=event_names,
        dynamics_tags=dynamics_names,
        dynamics_tags_en=dynamics_tags_en or dynamics_names,
        word_count_ja=word_count_ja,
        related_article_ids=related_article_ids,
        source_urls=source_urls,
        pattern_history_cases=pattern_history_cases,
        bottom_line=bottom_line,
        scenario_summary=scenario_summary,
    )
    save_index(index, index_path)

    # Step 3: X 投稿（JP + EN 同時投稿）
    # x_post_ja / x_post_en は build_x_post_texts() で事前生成して渡す
    x_results = {}
    x_creds = dict(
        api_key=x_api_key,
        api_secret=x_api_secret,
        access_token=x_access_token,
        access_token_secret=x_access_token_secret,
    )
    if x_post_ja:
        print("  Posting to X (JA)...")
        x_results["ja"] = post_to_x(text=x_post_ja, **x_creds)
    if x_post_en:
        print("  Posting to X (EN)...")
        x_results["en"] = post_to_x(text=x_post_en, **x_creds)

    # Step 4: Sitemap 自動再生成（投稿後にインデックスが更新された状態で生成）
    sitemap_path = ""
    if auto_sitemap:
        try:
            sitemap_path = generate_news_sitemap(
                index_path=index_path,
                output_path=sitemap_output_path,
                ghost_url=ghost_url,
            )
        except Exception as e:
            print(f"  WARN: sitemap generation failed: {e}")

    print(f"OK: Deep Pattern '{title}' published + indexed as {article_id}")
    return {
        "article_id": article_id,
        "ghost_result": ghost_result,
        "url": url,
        "index_updated": True,
        "x_results": x_results,
        "sitemap_path": sitemap_path,
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
    """【廃止】Speed Log記事をGhostに投稿する関数。Speed Logは廃止済み。代わりに publish_deep_pattern() を使うこと。"""

    # --- タクソノミーバリデーション ---
    validate_tags(dynamics_tags, event_tags, genre_tags)

    all_tags = genre_tags + event_tags + dynamics_tags + ["Deep Pattern"]

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
# News Sitemap generation (Google News Sitemap + llms.txt deployment)
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_news_sitemap(
    index_path: str = DEFAULT_INDEX_PATH,
    output_path: str = DEFAULT_SITEMAP_PATH,
    ghost_url: str = "https://nowpattern.com",
    max_articles: int = 1000,
    news_days: int = 2,
) -> str:
    """Google News Sitemap XML を記事インデックスから生成する。

    Google News Sitemap は直近 2日間 の記事のみ収録可能。
    通常の sitemap.xml は max_articles 件の全記事を収録する。

    出力:
        output_path に sitemap-news.xml を書き込む
        output_path.replace("-news.xml", ".xml") に全記事 sitemap.xml を書き込む

    VPS Caddyでの配信方法（/etc/caddy/Caddyfile に追記）:
        handle /sitemap-news.xml {
            root * /opt/shared
            file_server
        }
        handle /sitemap.xml {
            root * /opt/shared
            file_server
        }
    """
    index = load_index(index_path)
    articles = index.get("articles", [])

    if not articles:
        print("WARN: No articles in index, skipping sitemap generation")
        return ""

    now_utc = datetime.now(timezone.utc)
    cutoff_news = now_utc.timestamp() - (news_days * 86400)

    # ─── Google News Sitemap (直近2日間のみ) ─────────────────────────────
    news_items = []
    for a in sorted(articles, key=lambda x: x.get("published_at", ""), reverse=True):
        url = a.get("url", "")
        if not url:
            slug = a.get("slug", "")
            if slug:
                url = f"{ghost_url}/{slug}/"
            else:
                continue

        pub_at = a.get("published_at", "")
        try:
            dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
            if dt.timestamp() < cutoff_news:
                continue  # 2日以上前の記事はNews Sitemapに含めない
            pub_str = dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        except (ValueError, AttributeError):
            continue

        title = a.get("title_ja") or a.get("title_en", "")
        genre_tags = a.get("genre_tags", [])
        keywords = ", ".join(genre_tags[:3]) if genre_tags else "geopolitics"

        news_items.append(
            f'  <url>\n'
            f'    <loc>{url}</loc>\n'
            f'    <news:news>\n'
            f'      <news:publication>\n'
            f'        <news:name>Nowpattern</news:name>\n'
            f'        <news:language>ja</news:language>\n'
            f'      </news:publication>\n'
            f'      <news:publication_date>{pub_str}</news:publication_date>\n'
            f'      <news:title><![CDATA[{title}]]></news:title>\n'
            f'      <news:keywords>{keywords}</news:keywords>\n'
            f'    </news:news>\n'
            f'  </url>'
        )

    news_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n'
        + ("\n".join(news_items) if news_items else "  <!-- no recent articles -->") + "\n"
        "</urlset>\n"
    )

    # ─── Standard Sitemap (全記事) ────────────────────────────────────────
    all_items = []
    for a in sorted(articles, key=lambda x: x.get("published_at", ""), reverse=True)[:max_articles]:
        url = a.get("url", "")
        if not url:
            slug = a.get("slug", "")
            if slug:
                url = f"{ghost_url}/{slug}/"
            else:
                continue

        pub_at = a.get("published_at", "")
        try:
            dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
            lastmod = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            lastmod = now_utc.strftime("%Y-%m-%d")

        all_items.append(
            f'  <url>\n'
            f'    <loc>{url}</loc>\n'
            f'    <lastmod>{lastmod}</lastmod>\n'
            f'    <changefreq>weekly</changefreq>\n'
            f'    <priority>0.8</priority>\n'
            f'  </url>'
        )

    all_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ("\n".join(all_items) if all_items else "  <!-- no articles -->") + "\n"
        "</urlset>\n"
    )

    # ─── Write files ─────────────────────────────────────────────────────
    p_news = Path(output_path)
    p_news.parent.mkdir(parents=True, exist_ok=True)
    p_news.write_text(news_xml, encoding="utf-8")
    print(f"OK: News sitemap ({len(news_items)} articles) -> {output_path}")

    p_all = Path(output_path.replace("-news.xml", ".xml"))
    p_all.write_text(all_xml, encoding="utf-8")
    print(f"OK: Full sitemap ({len(all_items)} articles) -> {p_all}")

    return output_path


def deploy_llms_txt(
    output_path: str = DEFAULT_LLMS_TXT_PATH,
) -> str:
    """llms.txt をスクリプトディレクトリから /opt/shared/ にコピーする。

    VPS Caddyでの配信方法（/etc/caddy/Caddyfile に追記）:
        handle /llms.txt {
            root * /opt/shared
            file_server
        }
    """
    src = os.path.join(_SCRIPT_DIR, "llms.txt")
    if not os.path.exists(src):
        print(f"WARN: llms.txt not found at {src}")
        return ""

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(src, output_path)
    print(f"OK: llms.txt deployed -> {output_path}")
    return output_path


def deploy_robots_txt(
    output_path: str = "/opt/shared/robots.txt",
) -> str:
    """robots.txt をスクリプトディレクトリから /opt/shared/ にコピーする。

    Ghost は独自の robots.txt を持つが、Caddy レベルで上書きする方法:
        handle /robots.txt {
            root * /opt/shared
            file_server
        }
    """
    src = os.path.join(_SCRIPT_DIR, "robots.txt")
    if not os.path.exists(src):
        print(f"WARN: robots.txt not found at {src}")
        return ""

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(src, output_path)
    print(f"OK: robots.txt deployed -> {output_path}")
    return output_path


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
    print("  generate_news_sitemap() - Google News + 全記事 sitemap.xml 生成")
    print("  deploy_llms_txt()       - llms.txt を /opt/shared/ にデプロイ")
    print("  deploy_robots_txt()     - robots.txt を /opt/shared/ にデプロイ")
    print()
    print("HTML生成は nowpattern_article_builder.py を使用してください.")
