#!/usr/bin/env python3
"""
qa_sentinel.py — Autonomous QA Sentinel v1.0
毎日 JST 03:00 (UTC 18:00) に全記事を監査し、自動修正 + NEO委譲を実行する。

自動修正（サイレント）:
  - feature_image: EN記事がJA画像を使用している場合 → EN用thumbnail再生成
  - required_tags: nowpattern/deep-pattern/lang-ja/lang-en 欠落 → Ghost APIで追加
  - prediction_links: EN記事の /predictions/ → /en/predictions/ 修正

NEOキュー委譲（AIが必要な修正）:
  - article_too_short: JA<5000文字 / EN<3000文字
  - missing_sections: np-fast-read/np-signal/np-between-lines 欠落
  - cjk_contamination: EN記事に日本語50文字超
  - missing_oracle: prediction_db記事でOracleボックスなし

実行: python3 /opt/shared/scripts/qa_sentinel.py [--dry-run] [--report-only]
"""

import os, sys, json, sqlite3, subprocess, tempfile, time, urllib.request, ssl, re, hashlib
from datetime import datetime, timezone

from article_release_guard import evaluate_release_blockers

DRY_RUN     = "--dry-run" in sys.argv
REPORT_ONLY = "--report-only" in sys.argv

# ── 環境変数 ────────────────────────────────────────────────────────────────

def load_env():
    env = {}
    try:
        for line in open("/opt/cron-env.sh"):
            if line.startswith("export "):
                k, _, v = line[7:].strip().partition("=")
                env[k] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    env.update(os.environ)
    return env

ENV           = load_env()
GHOST_URL     = ENV.get("NOWPATTERN_GHOST_URL", "https://nowpattern.com")
ADMIN_API_KEY = ENV.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
BOT_TOKEN     = ENV.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID       = ENV.get("TELEGRAM_CHAT_ID", "")

GHOST_DB    = "/var/www/nowpattern/content/data/ghost.db"
HEALTH_DB   = "/opt/shared/article_health.db"
NEO_QUEUE   = "/opt/shared/neo_task_queue.json"
REPORTS_DIR = "/opt/shared/reports"
GEN_THUMB   = "/opt/shared/scripts/gen_thumbnail.py"
PRED_DB     = "/opt/shared/scripts/prediction_db.json"

# 必須タグ slug
REQUIRED_TAGS_ALL = ["nowpattern", "deep-pattern"]
REQUIRED_TAGS_JA  = ["lang-ja"]
REQUIRED_TAGS_EN  = ["lang-en"]

# 必須セクションマーカー
REQUIRED_MARKERS = ["np-fast-read", "np-signal", "np-between-lines", "np-open-loop"]

# コンテンツ長しきい値
MIN_LEN_JA = 5000
MIN_LEN_EN = 3000

# CJK汚染しきい値（EN記事で連続日本語50文字超）
CJK_MAX_EN = 50

# ── Ghost JWT ─────────────────────────────────────────────────────────────

def ghost_jwt():
    import hmac, hashlib, base64, time as _t
    kid, secret = ADMIN_API_KEY.split(":")
    header  = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "kid": kid, "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    now     = int(_t.time())
    payload = base64.urlsafe_b64encode(
        json.dumps({"iat": now, "exp": now + 300, "aud": "/admin/"}).encode()
    ).rstrip(b"=").decode()
    sig = hmac.new(bytes.fromhex(secret), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"

def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx

# ── Ghost API ──────────────────────────────────────────────────────────────

def ghost_get_post(post_id):
    jwt     = ghost_jwt()
    url     = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/?fields=id,slug,title,updated_at,tags,html,lexical"
    req     = urllib.request.Request(url, headers={"Authorization": f"Ghost {jwt}"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            return json.loads(r.read())["posts"][0]
    except Exception as e:
        print(f"  GET post failed ({post_id}): {e}")
        return None

def ghost_add_tags(post_id, existing_tag_slugs, slugs_to_add):
    """existing_tag_slugsにslugs_to_addを追加してPUT"""
    post = ghost_get_post(post_id)
    if not post:
        return False
    jwt = ghost_jwt()
    all_slugs = list(existing_tag_slugs) + [s for s in slugs_to_add if s not in existing_tag_slugs]
    tags_payload = [{"slug": s} for s in all_slugs]
    put_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/"
    payload = json.dumps({"posts": [{
        "tags": tags_payload,
        "updated_at": post["updated_at"]
    }]}).encode()
    req2 = urllib.request.Request(put_url, data=payload, method="PUT", headers={
        "Authorization": f"Ghost {ghost_jwt()}",
        "Content-Type":  "application/json",
    })
    try:
        with urllib.request.urlopen(req2, timeout=15, context=_ssl_ctx()) as r:
            return r.getcode() == 200
    except Exception as e:
        print(f"  PUT tags failed ({post_id}): {e}")
        return False

def ghost_update_html(post_id, new_html):
    """HTMLコンテンツのみ更新"""
    post = ghost_get_post(post_id)
    if not post:
        return False
    jwt = ghost_jwt()
    put_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/"
    payload = json.dumps({"posts": [{
        "html": new_html,
        "updated_at": post["updated_at"]
    }]}).encode()
    req = urllib.request.Request(put_url, data=payload, method="PUT", headers={
        "Authorization": f"Ghost {ghost_jwt()}",
        "Content-Type":  "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            return r.getcode() == 200
    except Exception as e:
        print(f"  PUT html failed ({post_id}): {e}")
        return False

def ghost_update_feature_image(post_id, new_url):
    post = ghost_get_post(post_id)
    if not post:
        return False
    jwt = ghost_jwt()
    put_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/"
    payload = json.dumps({"posts": [{
        "feature_image": new_url,
        "updated_at": post["updated_at"]
    }]}).encode()
    req = urllib.request.Request(put_url, data=payload, method="PUT", headers={
        "Authorization": f"Ghost {ghost_jwt()}",
        "Content-Type":  "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            return r.getcode() == 200
    except Exception as e:
        print(f"  PUT feature_image failed ({post_id}): {e}")
        return False

def upload_image_to_ghost(image_path):
    jwt      = ghost_jwt()
    url      = f"{GHOST_URL}/ghost/api/admin/images/upload/"
    boundary = "GhostUploadBoundary"
    with open(image_path, "rb") as f:
        img_data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="thumb.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + img_data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Ghost {jwt}",
        "Content-Type":  f"multipart/form-data; boundary={boundary}",
    })
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as r:
            resp = json.loads(r.read())
            return resp.get("images", [{}])[0].get("url", "")
    except Exception as e:
        print(f"  Upload error: {e}")
        return None

# ── Article Health DB ─────────────────────────────────────────────────────

def init_health_db():
    os.makedirs(os.path.dirname(HEALTH_DB), exist_ok=True)
    con = sqlite3.connect(HEALTH_DB)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS article_health (
            post_id          TEXT PRIMARY KEY,
            slug             TEXT NOT NULL,
            title            TEXT,
            lang             TEXT,
            checked_at       TEXT,
            -- image
            image_ok         INTEGER DEFAULT 0,
            image_fixed      INTEGER DEFAULT 0,
            -- tags
            tags_ok          INTEGER DEFAULT 0,
            tags_fixed       INTEGER DEFAULT 0,
            missing_tags     TEXT,
            -- length
            content_len      INTEGER DEFAULT 0,
            length_ok        INTEGER DEFAULT 0,
            -- sections
            sections_ok      INTEGER DEFAULT 0,
            missing_sections TEXT,
            -- CJK contamination (EN only)
            cjk_ok           INTEGER DEFAULT 1,
            cjk_char_count   INTEGER DEFAULT 0,
            -- oracle
            oracle_ok        INTEGER DEFAULT 1,
            oracle_needed    INTEGER DEFAULT 0,
            -- prediction link (EN only)
            pred_link_ok     INTEGER DEFAULT 1,
            pred_link_fixed  INTEGER DEFAULT 0,
            -- neo queue
            neo_queued       INTEGER DEFAULT 0,
            neo_issue        TEXT,
            -- overall
            overall_ok       INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS qa_runs (
            run_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at       TEXT,
            total        INTEGER,
            passed       INTEGER,
            auto_fixed   INTEGER,
            neo_queued   INTEGER,
            dry_run      INTEGER
        );
    """)
    con.commit()
    return con

# ── Quality Checks ────────────────────────────────────────────────────────

def count_cjk(text):
    """日本語・CJK文字の連続最大長を返す"""
    max_run = 0
    run     = 0
    for ch in text:
        cp = ord(ch)
        if (0x3000 <= cp <= 0x9FFF) or (0xF900 <= cp <= 0xFAFF) or (0xAC00 <= cp <= 0xD7AF):
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return max_run

def get_html_text(html):
    """HTMLタグを除いてプレーンテキストを返す"""
    if not html:
        return ""
    return re.sub(r"<[^>]+>", "", html)

def check_missing_markers(html):
    """欠落マーカーのリストを返す"""
    if not html:
        return list(REQUIRED_MARKERS)
    return [m for m in REQUIRED_MARKERS if m not in html]

def check_prediction_link(html, lang):
    """EN記事で /predictions/ (非 /en/predictions/) が存在すれば True（要修正）"""
    if lang != "en" or not html:
        return False
    # /en/predictions/ は OK。/predictions/ のみ（/en/なし）はNG
    bad_pattern = re.compile(r'href=["\'](?!https?://)[^"\']*?(?<!/en)/predictions/["\']')
    return bool(bad_pattern.search(html))

def fix_prediction_link(html):
    """EN記事の /predictions/ URL を /en/predictions/ に修正"""
    result = html
    # __GHOST_URL__/predictions/ および /predictions/ を /en/predictions/ に変換
    # すでに /en/predictions/ になっているものはスキップ
    i = 0
    while True:
        idx = result.find("/predictions/", i)
        if idx == -1:
            break
        # /en/predictions/ はスキップ
        if result[max(0,idx-3):idx] == "/en":
            i = idx + 1
            continue
        result = result[:idx] + "/en/predictions/" + result[idx+len("/predictions/"):]
        i = idx + len("/en/predictions/")
    return result


def load_prediction_slugs():
    """prediction_db.jsonから記事slugセットを返す"""
    try:
        with open(PRED_DB) as f:
            db = json.load(f)
        slugs = set()
        for p in db.get("predictions", []):
            url = p.get("ghost_url", "")
            if url:
                slug = url.rstrip("/").rsplit("/", 1)[-1]
                if slug:
                    slugs.add(slug)
        return slugs
    except Exception:
        return set()

# ── NEO Task Queue ────────────────────────────────────────────────────────

def load_neo_queue():
    if os.path.exists(NEO_QUEUE):
        try:
            with open(NEO_QUEUE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"tasks": []}

def save_neo_queue(q):
    with open(NEO_QUEUE, "w") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)


def build_fix_prompt(slug, title, lang, issues):
    """NEOが即実行できる詳細修正プロンプトを生成"""
    lang_str  = "日本語" if lang == "ja" else "英語"
    issue_str = "\n".join(f"  - {iss}" for iss in issues)
    prompt    = (
        f"【QA Sentinel 自動委譲タスク】\n"
        f"記事スラッグ: {slug}\n"
        f"タイトル: {title}\n"
        f"言語: {lang_str}\n"
        f"検出された問題:\n{issue_str}\n\n"
        f"修正手順:\n"
        f"1. Ghost Admin API で記事取得: GET /ghost/api/admin/posts/?filter=slug:{slug}\n"
        f"2. 問題に応じて修正（セクション追加/文字数補強/翻訳改善）\n"
        f"3. Ghost Admin API で更新: PUT /ghost/api/admin/posts/{{post_id}}/\n"
        f"4. /opt/shared/neo_task_queue.json の該当task_idをstatus=doneに変更\n"
        f"優先度: HIGH"
    )
    return prompt

def enqueue_neo(queue, post_id, slug, title, lang, issue, priority=2):
    """NEOキューに追加（同じpost_id+issueが未完了なら重複追加しない）"""
    existing = {(t["post_id"], t["issue"]) for t in queue["tasks"] if t.get("status") != "done"}
    key = (post_id, issue)
    if key in existing:
        return False
    queue["tasks"].append({
        "task_id":    f"{slug[:30]}_{issue[:20]}_{int(time.time())}",
        "post_id":    post_id,
        "slug":       slug,
        "title":      title[:80],
        "lang":       lang,
        "issue":      issue,
        "priority":   priority,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status":     "pending",
    })
    return True


# ── Ghost 強制DRAFT降格 ────────────────────────────────────────────────────

def ghost_force_draft(post_id, slug):
    """QA不合格記事を強制的にDRAFT（非公開）に降格する"""
    post = ghost_get_post(post_id)
    if not post:
        print(f"  [DRAFT] fetch failed: {slug}")
        return False
    jwt = ghost_jwt()
    put_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/"
    payload = json.dumps({"posts": [{
        "status": "draft",
        "updated_at": post["updated_at"]
    }]}).encode()
    req = urllib.request.Request(put_url, data=payload, method="PUT", headers={
        "Authorization": f"Ghost {ghost_jwt()}",
        "Content-Type":  "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            ok = r.getcode() == 200
            if ok:
                print(f"  [DRAFT] DEMOTED: {slug}")
            return ok
    except Exception as e:
        print(f"  [DRAFT] PUT failed ({slug}): {e}")
        return False

# ── Telegram ──────────────────────────────────────────────────────────────


def enqueue_neo_with_prompt(queue, post_id, slug, title, lang, issue, fix_prompt, priority=2):
    """詳細プロンプト付きでNEOキューに追加"""
    existing = {(t["post_id"], t["issue"]) for t in queue["tasks"] if t.get("status") != "done"}
    if (post_id, issue) in existing:
        return False
    queue["tasks"].append({
        "task_id":    f"{slug[:25]}_{issue[:15]}_{__import__('time').time():.0f}",
        "post_id":    post_id,
        "slug":       slug,
        "title":      title[:80],
        "lang":       lang,
        "issue":      issue,
        "fix_prompt": fix_prompt,
        "priority":   priority,
        "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        "status":     "pending",
        "source":     "batch_sentinel",
    })
    return True

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("[Telegram] no token/chat_id — printing instead:")
        print(msg)
        return
    data = json.dumps({"chat_id": CHAT_ID, "text": msg}).encode()
    req  = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"Telegram error: {e}")

# ── Main ──────────────────────────────────────────────────────────────────

def main():
    run_label = "(DRY RUN)" if DRY_RUN else ("(REPORT ONLY)" if REPORT_ONLY else "")
    print(f"[QA Sentinel] 開始 {run_label} — {datetime.now().strftime('%Y-%m-%d %H:%M JST')}")

    if not os.path.exists(GHOST_DB):
        print(f"ERROR: Ghost DB not found: {GHOST_DB}")
        return

    # DBセットアップ
    health_con = init_health_db()
    health_cur = health_con.cursor()

    # Ghost DBから全公開記事を取得
    ghost_con = sqlite3.connect(GHOST_DB)
    ghost_con.row_factory = sqlite3.Row

    posts = ghost_con.execute("""
        SELECT DISTINCT p.id, p.slug, p.title, p.html, p.feature_image,
               MAX(CASE WHEN t.slug = 'lang-en' THEN 'en' ELSE 'ja' END) as lang
        FROM posts p
        JOIN posts_tags pt ON p.id = pt.post_id
        JOIN tags t ON pt.tag_id = t.id
        WHERE t.slug IN ('lang-ja', 'lang-en')
          AND p.type = 'post'
          AND p.status = 'published'
        GROUP BY p.id, p.slug, p.title
        ORDER BY p.published_at DESC
    """).fetchall()

    # 全記事のタグを一括取得
    all_post_tags = {}
    for row in ghost_con.execute("""
        SELECT pt.post_id, t.slug
        FROM posts_tags pt
        JOIN tags t ON pt.tag_id = t.id
    """).fetchall():
        all_post_tags.setdefault(row[0], set()).add(row[1])

    # JA画像URLセット（EN記事の画像重複チェック用）
    ja_images = set()
    for row in ghost_con.execute("""
        SELECT p.feature_image
        FROM posts p
        JOIN posts_tags pt ON p.id = pt.post_id
        JOIN tags t ON pt.tag_id = t.id
        WHERE t.slug = 'lang-ja'
          AND p.type = 'post'
          AND p.status = 'published'
          AND p.feature_image IS NOT NULL
    """).fetchall():
        ja_images.add(row[0])

    ghost_con.close()

    pred_slugs = load_prediction_slugs()
    neo_queue  = load_neo_queue()

    print(f"  対象: {len(posts)}件 / 予測連動slug: {len(pred_slugs)}件")

    # カウンタ
    total         = len(posts)
    passed        = 0
    auto_fixed    = 0
    neo_queued_n  = 0
    draft_demoted = 0  # 処刑権: DRAFT降格件数
    issues_detail = []

    for i, post in enumerate(posts, 1):
        post_id = post["id"]
        slug    = post["slug"]
        title   = post["title"] or ""
        html    = post["html"] or ""
        lang    = post["lang"]
        fi      = post["feature_image"]
        tags    = all_post_tags.get(post_id, set())
        text    = get_html_text(html)
        content_len = len(text)

        if i % 20 == 0:
            print(f"  [{i}/{total}] 処理中...")

        rec = {
            "post_id":         post_id,
            "slug":            slug,
            "title":           title[:120],
            "lang":            lang,
            "checked_at":      datetime.now(timezone.utc).isoformat(),
            "content_len":     content_len,
            "image_ok":        1,
            "image_fixed":     0,
            "tags_ok":         1,
            "tags_fixed":      0,
            "missing_tags":    "",
            "length_ok":       1,
            "sections_ok":     1,
            "missing_sections":"",
            "cjk_ok":          1,
            "cjk_char_count":  0,
            "oracle_ok":       1,
            "oracle_needed":   0,
            "pred_link_ok":    1,
            "pred_link_fixed": 0,
            "neo_queued":      0,
            "neo_issue":       "",
            "overall_ok":      0,
        }
        neo_issues = []

        # ── Check 1: feature_image (EN記事がJA画像を使用) ──────────────────
        if lang == "en" and fi and fi in ja_images:
            rec["image_ok"] = 0
            if not DRY_RUN and not REPORT_ONLY:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                    tmp_path = tf.name
                try:
                    clean_title = title.replace('\x00','').replace('\x05','').strip()
                    r = subprocess.run([
                        "python3", GEN_THUMB,
                        "--title", clean_title,
                        "--lang", "en",
                        "--output", tmp_path,
                        "--size", "1200x675"
                    ], capture_output=True, text=True, timeout=30)
                    if r.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                        new_url = upload_image_to_ghost(tmp_path)
                        if new_url and ghost_update_feature_image(post_id, new_url):
                            rec["image_fixed"] = 1
                            auto_fixed += 1
                            print(f"  [IMG FIX] {slug[:40]}")
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

        # ── Check 2: required tags ─────────────────────────────────────────
        required = set(REQUIRED_TAGS_ALL + (REQUIRED_TAGS_JA if lang == "ja" else REQUIRED_TAGS_EN))
        missing_tags = required - tags
        if missing_tags:
            rec["tags_ok"]      = 0
            rec["missing_tags"] = ",".join(sorted(missing_tags))
            if not DRY_RUN and not REPORT_ONLY:
                ok = ghost_add_tags(post_id, tags, list(missing_tags))
                if ok:
                    rec["tags_fixed"] = 1
                    auto_fixed += 1
                    print(f"  [TAG FIX] {slug[:40]} +{','.join(missing_tags)}")

        # ── Check 3: prediction link (EN記事) ──────────────────────────────
        if lang == "en" and check_prediction_link(html, lang):
            rec["pred_link_ok"] = 0
            if not DRY_RUN and not REPORT_ONLY:
                new_html = fix_prediction_link(html)
                if ghost_update_html(post_id, new_html):
                    rec["pred_link_fixed"] = 1
                    auto_fixed += 1
                    print(f"  [LINK FIX] {slug[:40]}")

        # ── Check 4: content length ─────────────────────────────────────────
        min_len = MIN_LEN_JA if lang == "ja" else MIN_LEN_EN
        if content_len < min_len:
            rec["length_ok"] = 0
            neo_issues.append(f"article_too_short:{content_len}chars(min:{min_len})")

        # ── Check 5: required section markers ──────────────────────────────
        missing_secs = check_missing_markers(html)
        if missing_secs:
            rec["sections_ok"]      = 0
            rec["missing_sections"] = ",".join(missing_secs)
            neo_issues.append(f"missing_sections:{','.join(missing_secs)}")

        # ── Check 6: CJK contamination (EN only) ───────────────────────────
        if lang == "en":
            cjk_count = count_cjk(text)
            rec["cjk_char_count"] = cjk_count
            if cjk_count > CJK_MAX_EN:
                rec["cjk_ok"] = 0
                neo_issues.append(f"cjk_contamination:{cjk_count}chars")

        # ── Check 7: Oracle Statement ──────────────────────────────────────
        if slug in pred_slugs or (lang == "en" and slug.replace("en-","") in pred_slugs):
            rec["oracle_needed"] = 1
            if "np-oracle" not in html:
                rec["oracle_ok"] = 0
                neo_issues.append("missing_oracle")

        # ── NEO委譲 ─────────────────────────────────────────────────────────
        release_block = evaluate_release_blockers(
            title=title,
            html=html,
            tags=list(tags),
            site_url=GHOST_URL,
            status="published",
            channel="public",
            require_external_sources=True,
            check_source_fetchability=True,
        )
        if release_block["errors"]:
            neo_issues.append("release_blocker:" + ",".join(release_block["errors"][:3]))

        if neo_issues:
            rec["neo_queued"] = 1
            rec["neo_issue"]  = "|".join(neo_issues)
            if not DRY_RUN and not REPORT_ONLY:
                fix_prompt = build_fix_prompt(slug, title, lang, neo_issues)
                for issue in neo_issues:
                    if enqueue_neo_with_prompt(neo_queue, post_id, slug, title, lang,
                                               issue, fix_prompt):
                        neo_queued_n += 1

        # ── 処刑権: QA不合格記事をDRAFTに降格 ──────────────────────────────
        # NEOが修正するまで公開しない。修正完了後NEOがre-publishする。
        if neo_issues and not DRY_RUN and not REPORT_ONLY:
            if ghost_force_draft(post_id, slug):
                draft_demoted += 1

        # ── overall OK? ────────────────────────────────────────────────────
        fixable_ok = (
            (rec["image_ok"] or rec["image_fixed"]) and
            (rec["tags_ok"]  or rec["tags_fixed"])  and
            (rec["pred_link_ok"] or rec["pred_link_fixed"])
        )
        structural_ok = (rec["length_ok"] and rec["sections_ok"] and
                         rec["cjk_ok"]    and rec["oracle_ok"])
        rec["overall_ok"] = 1 if (fixable_ok and structural_ok) else 0
        if rec["overall_ok"]:
            passed += 1
        else:
            issues_detail.append({
                "slug": slug[:50],
                "lang": lang,
                "neo_issues": neo_issues,
                "tags_missing": rec["missing_tags"],
                "secs_missing": rec["missing_sections"],
            })

        # DB upsert
        health_cur.execute("""
            INSERT OR REPLACE INTO article_health (
                post_id, slug, title, lang, checked_at,
                image_ok, image_fixed,
                tags_ok, tags_fixed, missing_tags,
                content_len, length_ok,
                sections_ok, missing_sections,
                cjk_ok, cjk_char_count,
                oracle_ok, oracle_needed,
                pred_link_ok, pred_link_fixed,
                neo_queued, neo_issue,
                overall_ok
            ) VALUES (
                :post_id, :slug, :title, :lang, :checked_at,
                :image_ok, :image_fixed,
                :tags_ok, :tags_fixed, :missing_tags,
                :content_len, :length_ok,
                :sections_ok, :missing_sections,
                :cjk_ok, :cjk_char_count,
                :oracle_ok, :oracle_needed,
                :pred_link_ok, :pred_link_fixed,
                :neo_queued, :neo_issue,
                :overall_ok
            )
        """, rec)

        time.sleep(0.05)  # DB負荷軽減

    # NEOキューを保存
    if not DRY_RUN and not REPORT_ONLY:
        save_neo_queue(neo_queue)

    # Visual E2E: 不合格記事のサンプル（最大3件）をブラウザチェック
    if not DRY_RUN and not REPORT_ONLY:
        e2e_targets = [d for d in issues_detail if d.get("neo_issues")][:3]
        if e2e_targets:
            print(f"  [E2E] {len(e2e_targets)}件のブラウザ検証を非同期起動...")
            for d in e2e_targets:
                _slug = d["slug"]
                _lang = d["lang"]
                if _lang == "en":
                    _url = f"https://nowpattern.com/en/{_slug[3:]}/" if _slug.startswith("en-") else f"https://nowpattern.com/{_slug}/"
                else:
                    _url = f"https://nowpattern.com/{_slug}/"
                import subprocess as _sp
                _sp.Popen(
                    ["python3", "/opt/shared/scripts/site_playwright_check.py",
                     "--article-url", _url],
                    stdout=open("/opt/shared/logs/e2e_visual.log", "a"),
                    stderr=open("/opt/shared/logs/e2e_visual.log", "a"),
                )

    # qa_runs に記録
    health_cur.execute("""
        INSERT INTO qa_runs (run_at, total, passed, auto_fixed, neo_queued, dry_run)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now(timezone.utc).isoformat(), total, passed, auto_fixed, neo_queued_n, int(DRY_RUN or REPORT_ONLY)))
    health_con.commit()
    health_con.close()

    # ── JSON レポート ──────────────────────────────────────────────────────
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"qa_sentinel_{datetime.now().strftime('%Y-%m-%d')}.json")
    report_data = {
        "run_at":     datetime.now().strftime("%Y-%m-%d %H:%M JST"),
        "total":      total,
        "passed":     passed,
        "failed":     total - passed,
        "pass_rate":  f"{passed/total*100:.1f}%" if total else "0%",
        "auto_fixed": auto_fixed,
        "neo_queued": neo_queued_n,
        "dry_run":    DRY_RUN or REPORT_ONLY,
        "issues":     issues_detail[:50],  # 最大50件
    }
    with open(report_path, "w") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    # ── Telegram レポート ─────────────────────────────────────────────────
    pass_icon  = "✅" if passed == total else ("⚠️" if passed / total >= 0.8 else "🚨")
    fail_count = total - passed
    msg = (
        f"🛡 *[QA Sentinel] 監査完了* {run_label}\n"
        f"{pass_icon} 合格: {passed}/{total} ({passed/total*100:.1f}%)\n"
        f"🔧 自動修正: {auto_fixed}件\n"
        f"📬 NEO委譲: {neo_queued_n}タスク\n"
        f"⚰️ 処刑（DRAFT降格）: {draft_demoted}件\n"
    )
    if fail_count > 0:
        # 不合格のトップ5をサマリー
        neo_issues_top = [d for d in issues_detail if d["neo_issues"]][:5]
        if neo_issues_top:
            msg += "\nNEO委譲例:\n"
            for d in neo_issues_top:
                msg += f"  • [{d['lang']}] {d['slug'][:35]}\n    ↳ {d['neo_issues'][0]}\n"

    print(msg)
    if not DRY_RUN:
        send_telegram(msg)

    print(f"\n[QA Sentinel] 完了 — 合格 {passed}/{total}, 自動修正 {auto_fixed}件, NEO委譲 {neo_queued_n}件")
    print(f"  レポート: {report_path}")
    print(f"  HealthDB: {HEALTH_DB}")

if __name__ == "__main__":
    main()
