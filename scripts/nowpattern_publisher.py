"""
Nowpattern Publisher v3.0
Ghost投稿 + 記事インデックス更新を担当する。

責務: 記事の外部公開とインデックス管理。HTML生成は nowpattern_article_builder.py が担当。
タクソノミーバリデーション: taxonomy.json駆動のSTRICTバリデーション。不正タグは投稿をブロックする。

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
    body = {
        "posts": [
            {
                "title": title,
                "lexical": json.dumps(lexical_doc),
                "tags": ghost_tags,
                "status": status,
                "featured": featured,
                "email_segment": "none",
            }
        ]
    }

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
) -> dict:
    """Deep Pattern記事をGhostに投稿し、インデックスを更新する

    v3.0変更点:
    - タグはtaxonomy.jsonに基づいてSTRICTバリデーション（不正タグ→投稿ブロック）
    - Ghost APIにslug指定でタグ送信（不正なauto-slugを防止）
    - 実際のGhost APIレスポンスURLを使用（slug truncationによる404を防止）
    """

    # --- v4.0 フォーマットゲート（最終出口バリデーション） ---
    v4_markers = ["np-bottom-line", "np-between-lines", "np-open-loop"]
    missing = [m for m in v4_markers if m not in html]
    if missing:
        print(f"  BLOCK v4.0 validation: HTML missing {', '.join(missing)}")
        print(f"     -> See ARTICLE_FORMAT_SPEC.md to add v4.0 fields")
        raise ValueError(f"v4.0 format validation failed: missing {', '.join(missing)}")

    # --- タクソノミーバリデーション + 正規化（STRICT: 不正タグ→投稿ブロック） ---
    print("  Taxonomy validation (STRICT)...")
    genre_resolved = resolve_tag_list(genre_tags, "genre")
    event_resolved = resolve_tag_list(event_tags, "event")
    dynamics_resolved = resolve_tag_list(dynamics_tags, "dynamics")

    # 固定タグ追加
    tag_objects = (
        [{"name": "Nowpattern", "slug": "nowpattern"}, {"name": "Deep Pattern", "slug": "deep-pattern"}]
        + genre_resolved + event_resolved + dynamics_resolved
    )

    # Step 1: Ghost投稿（slug指定方式）
    ghost_result = post_to_ghost(
        title=title,
        html=html,
        tag_objects=tag_objects,
        ghost_url=ghost_url,
        admin_api_key=admin_api_key,
        status=status,
        featured=True,
    )

    # 実際のGhost URLを使用（slug truncationによる404を防止）
    slug = ghost_result.get("slug", "")
    ghost_id = ghost_result.get("id", "")
    url = ghost_result.get("url", "")
    if not url and slug:
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
