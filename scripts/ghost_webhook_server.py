#!/usr/bin/env python3
"""
ghost_webhook_server.py — Unified Ghost Webhook Server v1.0
port 8765 で待機。Ghost CMSからのwebhookを受信して即座にQA+アラートを実行。

処理:
  post.published        → 新規公開記事の即時QA + 自動修正 + NEO委譲 + 処刑（DRAFT降格）
  post.published.edited → 既存記事の即時QA（ページ更新含む）
  post.edited           → タグ変更検知 → lang-ja/lang-en 整合性チェック → アラート
  page.published.edited → /predictions/ ページ改ざん検知 → Telegram警告

起動: python3 /opt/shared/scripts/ghost_webhook_server.py
"""

import json, os, sys, time, re, hashlib, sqlite3, subprocess, tempfile
import urllib.request, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

from article_release_guard import evaluate_release_blockers

# ── 環境変数 ─────────────────────────────────────────────────────────────

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
GEN_THUMB   = "/opt/shared/scripts/gen_thumbnail.py"
PRED_DB     = "/opt/shared/scripts/prediction_db.json"

PROTECTED_SLUGS  = {"predictions", "en-predictions"}
REQUIRED_MARKERS = ["np-fast-read", "np-signal", "np-between-lines", "np-open-loop"]
MIN_LEN_JA = 5000
MIN_LEN_EN = 3000
CJK_MAX_EN = 50

# ── Helpers ───────────────────────────────────────────────────────────────

def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx

def ghost_jwt():
    import hmac, hashlib, base64, time as _t
    kid, secret = ADMIN_API_KEY.split(":")
    header  = base64.urlsafe_b64encode(
        json.dumps({"alg":"HS256","kid":kid,"typ":"JWT"}).encode()
    ).rstrip(b"=").decode()
    now     = int(_t.time())
    payload = base64.urlsafe_b64encode(
        json.dumps({"iat":now,"exp":now+300,"aud":"/admin/"}).encode()
    ).rstrip(b"=").decode()
    sig = hmac.new(bytes.fromhex(secret), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"

def send_telegram(msg, level="alert"):
    """
    Alert Triage:
      level='alert' (default): 緊急事態 → Telegramに実際に送信
      level='info'           : 正常動作  → ログのみ（Telegramには送らない）
    """
    if level != "alert":
        print(f"  [INFO-LOG] {msg[:120].replace(chr(10), ' | ')}")
        return
    if not BOT_TOKEN or not CHAT_ID:
        print(f"[Telegram] {msg[:100]}")
        return
    data = json.dumps({"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}).encode()
    req  = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data, headers={"Content-Type":"application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"Telegram error: {e}")

def ghost_get_post(post_id):
    jwt = ghost_jwt()
    url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/?fields=id,slug,title,updated_at,tags,html,feature_image"
    req = urllib.request.Request(url, headers={"Authorization":f"Ghost {jwt}"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            return json.loads(r.read())["posts"][0]
    except Exception as e:
        print(f"  ghost_get_post failed: {e}")
        return None

def ghost_update_feature_image(post_id, updated_at, new_url):
    jwt = ghost_jwt()
    put_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/"
    payload = json.dumps({"posts":[{"feature_image":new_url,"updated_at":updated_at}]}).encode()
    req = urllib.request.Request(put_url, data=payload, method="PUT", headers={
        "Authorization":f"Ghost {jwt}", "Content-Type":"application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            return r.getcode() == 200
    except Exception as e:
        print(f"  update_feature_image failed: {e}")
        return False

def ghost_add_tags(post_id, existing_slugs, add_slugs, updated_at):
    jwt = ghost_jwt()
    all_slugs = list(existing_slugs) + [s for s in add_slugs if s not in existing_slugs]
    put_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/"
    payload = json.dumps({"posts":[{
        "tags":[{"slug":s} for s in all_slugs],
        "updated_at":updated_at
    }]}).encode()
    req = urllib.request.Request(put_url, data=payload, method="PUT", headers={
        "Authorization":f"Ghost {ghost_jwt()}","Content-Type":"application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            return r.getcode() == 200
    except Exception as e:
        print(f"  add_tags failed: {e}")
        return False

def fix_prediction_link(html):
    return re.sub(r'(href=["\'])(/predictions/)(["\'])', r'\1/en/predictions/\3', html)

def ghost_update_html(post_id, updated_at, new_html):
    jwt = ghost_jwt()
    put_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/"
    payload = json.dumps({"posts":[{"html":new_html,"updated_at":updated_at}]}).encode()
    req = urllib.request.Request(put_url, data=payload, method="PUT", headers={
        "Authorization":f"Ghost {ghost_jwt()}","Content-Type":"application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            return r.getcode() == 200
    except Exception as e:
        print(f"  update_html failed: {e}")
        return False

def upload_image(image_path):
    jwt      = ghost_jwt()
    boundary = "GhostUploadBoundary"
    with open(image_path, "rb") as f:
        img_data = f.read()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"thumb.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n"
    ).encode() + img_data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{GHOST_URL}/ghost/api/admin/images/upload/",
        data=body, method="POST", headers={
            "Authorization":f"Ghost {jwt}",
            "Content-Type":f"multipart/form-data; boundary={boundary}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as r:
            return json.loads(r.read()).get("images",[{}])[0].get("url","")
    except Exception as e:
        print(f"  upload_image error: {e}")
        return None

def count_cjk(text):
    max_run = run = 0
    for ch in text:
        cp = ord(ch)
        if (0x3000 <= cp <= 0x9FFF) or (0xF900 <= cp <= 0xFAFF):
            run += 1; max_run = max(max_run, run)
        else:
            run = 0
    return max_run

def get_text(html):
    return re.sub(r"<[^>]+>", "", html or "")

def load_pred_slugs():
    try:
        with open(PRED_DB) as f:
            db = json.load(f)
        slugs = set()
        for p in db.get("predictions", []):
            url = p.get("ghost_url", "")
            if url:
                s = url.rstrip("/").rsplit("/", 1)[-1]
                if s: slugs.add(s)
        return slugs
    except Exception:
        return set()

def load_neo_queue():
    if os.path.exists(NEO_QUEUE):
        try:
            with open(NEO_QUEUE) as f: return json.load(f)
        except Exception: pass
    return {"tasks": []}

def save_neo_queue(q):
    with open(NEO_QUEUE, "w") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)

def enqueue_neo_with_prompt(queue, post_id, slug, title, lang, issue, fix_prompt, priority=1):
    """詳細な修正プロンプト付きでNEOキューに追加"""
    existing = {(t["post_id"], t["issue"]) for t in queue["tasks"] if t.get("status") != "done"}
    if (post_id, issue) in existing:
        return False
    queue["tasks"].append({
        "task_id":    f"{slug[:25]}_{issue[:15]}_{int(time.time())}",
        "post_id":    post_id,
        "slug":       slug,
        "title":      title[:80],
        "lang":       lang,
        "issue":      issue,
        "fix_prompt": fix_prompt,
        "priority":   priority,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status":     "pending",
        "source":     "webhook_qa",
    })
    return True

def build_fix_prompt(slug, title, lang, issues):
    """NEOが即実行できる修正プロンプトを生成"""
    lang_str  = "日本語" if lang == "ja" else "英語"
    issue_str = "\n".join(f"  - {iss}" for iss in issues)
    prompt    = (
        f"【QA Sentinel 自動委譲タスク】\n"
        f"記事スラッグ: {slug}\n"
        f"タイトル: {title}\n"
        f"言語: {lang_str}\n"
        f"検出された問題:\n{issue_str}\n\n"
        f"以下の手順で修正せよ:\n"
        f"1. Ghost Admin APIで記事を取得: GET /ghost/api/admin/posts/?filter=slug:{slug}\n"
        f"2. 問題を修正（セクション追加/翻訳補完/文字数補強）\n"
        f"3. Ghost Admin APIで更新: PUT /ghost/api/admin/posts/{{post_id}}/\n"
        f"4. 修正完了後、/opt/shared/neo_task_queue.json の task_id をstatusをdoneに更新\n"
        f"優先度: HIGH — 完了後Telegramで報告"
    )
    return prompt

def update_health_db(post_id, slug, lang, checks):
    """Article Health DBをupsert"""
    try:
        con = sqlite3.connect(HEALTH_DB)
        con.execute("""
            INSERT OR REPLACE INTO article_health (
                post_id, slug, title, lang, checked_at,
                image_ok, image_fixed, tags_ok, tags_fixed, missing_tags,
                content_len, length_ok, sections_ok, missing_sections,
                cjk_ok, cjk_char_count, oracle_ok, oracle_needed,
                pred_link_ok, pred_link_fixed, neo_queued, neo_issue, overall_ok
            ) VALUES (
                :post_id,:slug,:title,:lang,:checked_at,
                :image_ok,:image_fixed,:tags_ok,:tags_fixed,:missing_tags,
                :content_len,:length_ok,:sections_ok,:missing_sections,
                :cjk_ok,:cjk_char_count,:oracle_ok,:oracle_needed,
                :pred_link_ok,:pred_link_fixed,:neo_queued,:neo_issue,:overall_ok
            )
        """, checks)
        con.commit()
        con.close()
    except Exception as e:
        print(f"  health_db update failed: {e}")

# ── QA Logic for Single Post ──────────────────────────────────────────────

def run_qa_on_post(post_id, event_type="post.published"):
    """単一記事のQA + 自動修正 + NEO委譲"""
    print(f"  [QA] {post_id} ({event_type})")

    # Ghost APIから最新データ取得
    post = ghost_get_post(post_id)
    if not post:
        print(f"  [QA] post not found: {post_id}")
        return

    slug  = post.get("slug", "")
    title = post.get("title", "")
    html  = post.get("html", "") or ""
    fi    = post.get("feature_image", "")
    tags  = {t["slug"] for t in post.get("tags", [])}
    updated_at = post.get("updated_at", "")
    lang  = "en" if "lang-en" in tags else "ja"
    text  = get_text(html)
    content_len = len(text)

    # Ghost DBからJA画像セット（画像重複チェック用）
    ja_images = set()
    try:
        gcon = sqlite3.connect(GHOST_DB)
        for row in gcon.execute("""
            SELECT p.feature_image FROM posts p
            JOIN posts_tags pt ON p.id = pt.post_id
            JOIN tags t ON pt.tag_id = t.id
            WHERE t.slug='lang-ja' AND p.type='post' AND p.status='published'
              AND p.feature_image IS NOT NULL
        """).fetchall():
            ja_images.add(row[0])
        gcon.close()
    except Exception as e:
        print(f"  ja_images fetch failed: {e}")

    pred_slugs = load_pred_slugs()
    neo_queue  = load_neo_queue()

    rec = {
        "post_id": post_id, "slug": slug, "title": title[:120], "lang": lang,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "content_len": content_len,
        "image_ok": 1, "image_fixed": 0,
        "tags_ok": 1, "tags_fixed": 0, "missing_tags": "",
        "length_ok": 1, "sections_ok": 1, "missing_sections": "",
        "cjk_ok": 1, "cjk_char_count": 0,
        "oracle_ok": 1, "oracle_needed": 0,
        "pred_link_ok": 1, "pred_link_fixed": 0,
        "neo_queued": 0, "neo_issue": "", "overall_ok": 0,
    }
    neo_issues = []
    fixes_done = []

    # Check 1: feature_image
    if lang == "en" and fi and fi in ja_images:
        rec["image_ok"] = 0
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            tmp_path = tf.name
        try:
            clean_title = title.replace('\x00','').replace('\x05','').strip()
            r = subprocess.run([
                "python3", GEN_THUMB, "--title", clean_title,
                "--lang", "en", "--output", tmp_path, "--size", "1200x675"
            ], capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                new_url = upload_image(tmp_path)
                if new_url and ghost_update_feature_image(post_id, updated_at, new_url):
                    rec["image_fixed"] = 1
                    fixes_done.append("EN画像を再生成")
        finally:
            if os.path.exists(tmp_path): os.unlink(tmp_path)

    # Check 2: required tags
    required = {"nowpattern","deep-pattern"} | ({"lang-ja"} if lang=="ja" else {"lang-en"})
    missing_tags = required - tags
    if missing_tags:
        rec["tags_ok"]      = 0
        rec["missing_tags"] = ",".join(sorted(missing_tags))
        if ghost_add_tags(post_id, tags, list(missing_tags), updated_at):
            rec["tags_fixed"] = 1
            fixes_done.append(f"タグ追加:{','.join(missing_tags)}")

    # Check 3: prediction link (EN)
    bad_pred_link = bool(re.search(r'href=["\'](?!https?://)[^"\']*?(?<!/en)/predictions/["\']', html))
    if lang == "en" and bad_pred_link:
        rec["pred_link_ok"] = 0
        new_html = fix_prediction_link(html)
        if ghost_update_html(post_id, updated_at, new_html):
            rec["pred_link_fixed"] = 1
            fixes_done.append("/predictions/ → /en/predictions/")

    # Check 4: content length
    min_len = MIN_LEN_JA if lang == "ja" else MIN_LEN_EN
    if content_len < min_len:
        rec["length_ok"] = 0
        neo_issues.append(f"article_too_short:{content_len}chars(min:{min_len})")

    # Check 5: section markers
    missing_secs = [m for m in REQUIRED_MARKERS if m not in html]
    if missing_secs:
        rec["sections_ok"]      = 0
        rec["missing_sections"] = ",".join(missing_secs)
        neo_issues.append(f"missing_sections:{','.join(missing_secs)}")

    # Check 6: CJK contamination (EN)
    if lang == "en":
        cjk = count_cjk(text)
        rec["cjk_char_count"] = cjk
        if cjk > CJK_MAX_EN:
            rec["cjk_ok"] = 0
            neo_issues.append(f"cjk_contamination:{cjk}chars")

    # Check 7: Oracle
    if slug in pred_slugs:
        rec["oracle_needed"] = 1
        if "np-oracle" not in html:
            rec["oracle_ok"] = 0
            neo_issues.append("missing_oracle_statement")

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


    # Check 8: JA-EN pairing — 公開時に対訳の存在を即時確認（URLルール強制）
    rec["pair_ok"] = 1
    rec["pair_queued"] = 0
    try:
        _pcon = sqlite3.connect(GHOST_DB)
        if lang == "ja":
            _pair_slug = "en-" + slug
            _pair_row = _pcon.execute(
                "SELECT id FROM posts WHERE slug=? AND status='published' AND type='post'",
                (_pair_slug,)
            ).fetchone()
            if not _pair_row:
                rec["pair_ok"] = 0
                _pair_lines = [
                    "【EN翻訳生成タスク】",
                    "JA記事 \"" + title + "\" (" + slug + ") が公開されましたが EN翻訳がありません。",
                    "以下の手順で EN 翻訳を作成・公開してください:",
                    "1. Ghost Admin API で JA 記事を取得: GET /ghost/api/admin/posts/?filter=slug:" + slug,
                    "2. 本文を英語に翻訳（Deep Pattern v6.0 フォーマット維持）",
                    "3. nowpattern_publisher.py の publish_deep_pattern() で投稿:",
                    "   language='en', ja_slug='" + slug + "' を指定",
                    "   ENスラッグ: en-" + slug + " / 公開URL: https://nowpattern.com/en/" + slug + "/",
                    "4. 完了後 Telegram で報告",
                ]
                _pair_prompt = "\n".join(_pair_lines)
                _pair_neo_queue = load_neo_queue()
                enqueue_neo_with_prompt(
                    _pair_neo_queue, post_id, slug, title, "en",
                    "missing_en_translation", _pair_prompt
                )
                save_neo_queue(_pair_neo_queue)
                rec["pair_queued"] = 1
                send_telegram(
                    "🔄 *EN翻訳なし* `" + slug[:45] + "`\n→ NEO に EN 翻訳生成を依頼しました（DRAFT降格なし）",
                    level="info"
                )
        elif lang == "en" and slug.startswith("en-"):
            _pair_slug = slug[3:]
            _pair_row = _pcon.execute(
                "SELECT id FROM posts WHERE slug=? AND status='published' AND type='post'",
                (_pair_slug,)
            ).fetchone()
            if not _pair_row:
                rec["pair_ok"] = 0
                send_telegram(
                    "⚠️ *JA原文なし* EN記事 `" + slug[:45] + "`\nJA版 `" + _pair_slug + "` が未公開です（要確認）",
                    level="info"
                )
        _pcon.close()
    except Exception as _pe:
        print("  [QA] pairing check failed: " + str(_pe))

    # NEO委譲 + 処刑権（QA不合格→即DRAFT降格）
    if neo_issues:
        rec["neo_queued"] = 1
        rec["neo_issue"]  = "|".join(neo_issues)
        fix_prompt = build_fix_prompt(slug, title, lang, neo_issues)
        enqueue_neo_with_prompt(neo_queue, post_id, slug, title, lang, neo_issues[0], fix_prompt)
        save_neo_queue(neo_queue)
        # 処刑: 修正されるまで非公開
        ghost_force_draft(post_id, slug)

    rec["overall_ok"] = 1 if (
        (rec["image_ok"] or rec["image_fixed"]) and
        (rec["tags_ok"]  or rec["tags_fixed"])  and
        (rec["pred_link_ok"] or rec["pred_link_fixed"]) and
        rec["length_ok"] and rec["sections_ok"] and rec["cjk_ok"] and rec["oracle_ok"]
    ) else 0

    update_health_db(post_id, slug, lang, rec)

    # レポート生成
    status = "✅ PASS" if rec["overall_ok"] else "⚠️ ISSUES"
    msg_parts = [f"🛡 *[QA Sentinel] 記事公開検知*", f"{status} `{slug[:45]}`"]
    if fixes_done:
        msg_parts.append(f"🔧 自動修正: {', '.join(fixes_done)}")
    if neo_issues:
        msg_parts.append(f"📬 NEO委譲: {', '.join(neo_issues[:2])}")
        msg_parts.append(f"⚰️ DRAFT降格（修正まで非公開）")

    result_msg = "\n".join(msg_parts)
    print(f"  {result_msg.replace(chr(10), ' | ')[:120]}")
    # Alert Triage: 失敗/DRAFT降格のみTelegram。完全PASSはログのみ
    _triage_level = "alert" if (rec.get("overall_ok") == 0 or neo_issues) else "info"
    send_telegram(result_msg, level=_triage_level)

    # Zero-Touch X Distribution: QA合格記事を自動X投稿（idempotent）
    if rec.get("overall_ok") == 1:
        try:
            x_post_on_qa_pass(post_id, slug, title, lang)
        except Exception as _xe:
            print(f"  [X] x_post_on_qa_pass error: {_xe}")

    # Visual E2E: ブラウザレベルの DOM + console.error チェック
    if rec.get("overall_ok") == 1:
        # 合格記事のみE2E確認（不合格はDRAFTになるのでスキップ）
        try:
            import subprocess as _sp
            article_url = f"https://nowpattern.com/{slug}/" if not slug.startswith("en-") else f"https://nowpattern.com/en/{slug[3:]}/"
            _sp.Popen(
                ["python3", "/opt/shared/scripts/site_playwright_check.py",
                 "--article-url", article_url],
                stdout=open("/opt/shared/logs/e2e_visual.log", "a"),
                stderr=subprocess.STDOUT,
            )
        except Exception as e:
            print(f"  [E2E] launch failed: {e}")

    # AI Red-Teaming: np-oracle のある予測記事のみキューに追加（定額サブスク NEO が実行）
    if rec.get("overall_ok") == 1 and "np-oracle" in html:
        try:
            import sys as _sys_rt
            if "/opt/shared/scripts" not in _sys_rt.path:
                _sys_rt.path.insert(0, "/opt/shared/scripts")
            from ai_redteam import _enqueue_redteam as _enqueue_rt
            _rt_enqueued = _enqueue_rt(neo_queue, post_id, slug, title, html, lang)
            if _rt_enqueued:
                save_neo_queue(neo_queue)
                print(f"  [RedTeam] queued for NEO: {slug[:45]}")
            else:
                print(f"  [RedTeam] already in queue (skip): {slug[:45]}")
        except Exception as _rte:
            print(f"  [RedTeam] enqueue error: {_rte}")

    return rec



# ── Zero-Touch X Distribution: QA合格後自動X投稿 ──────────────────────────

def x_post_on_qa_pass(post_id, slug, title, lang):
    """QA合格記事をX(Twitter)に自動投稿（冪等・OAuth1.0a）"""

    # x_posted_at カラムが存在しなければ作成（冪等）
    try:
        _con = sqlite3.connect(HEALTH_DB)
        _con.execute("ALTER TABLE article_health ADD COLUMN x_posted_at TEXT")
        _con.commit()
        _con.close()
    except Exception:
        pass  # カラム既存ならエラー無視

    # 冪等チェック: すでに投稿済みならスキップ
    try:
        _con = sqlite3.connect(HEALTH_DB)
        _row = _con.execute(
            "SELECT x_posted_at FROM article_health WHERE slug=?", (slug,)
        ).fetchone()
        _con.close()
        if _row and _row[0]:
            print(f"  [X] skip (already posted at {_row[0]}): {slug}")
            return
    except Exception:
        pass

    # X API 認証情報（cron-env.sh 経由で環境変数に注入済み）
    tw_key     = ENV.get("TWITTER_API_KEY", "")
    tw_secret  = ENV.get("TWITTER_API_SECRET", "")
    tw_token   = ENV.get("TWITTER_ACCESS_TOKEN", "")
    tw_tsecret = ENV.get("TWITTER_ACCESS_SECRET", "")

    if not all([tw_key, tw_secret, tw_token, tw_tsecret]):
        print("  [X] Twitter credentials missing — skip")
        return

    # ツイート本文を生成
    article_url = (
        f"https://nowpattern.com/en/{slug[3:]}/"
        if lang == "en" and slug.startswith("en-")
        else f"https://nowpattern.com/{slug}/"
    )
    hashtags = "#Nowpattern #NewsAnalysis" if lang == "en" else "#Nowpattern #ニュース分析"
    clean_title = title.replace("\n", " ").strip()
    if len(clean_title) > 85:
        clean_title = clean_title[:82] + "..."
    tweet_text = f"{clean_title}\n\n{hashtags}\n\n{article_url}"

    # DLQ: タスクキューに追加（Exponential Backoffで自動再試行）
    try:
        import sys as _sys
        if "/opt/shared/scripts" not in _sys.path:
            _sys.path.insert(0, "/opt/shared/scripts")
        import task_queue as _tq
        _dlq_payload = {
            "slug": slug,
            "title": title,
            "lang": lang,
            "tweet_text": tweet_text,
            "article_url": article_url,
        }
        _dlq_key = f"xpost:{slug}"
        _enqueued = _tq.enqueue(
            task_type="x_post",
            payload=_dlq_payload,
            idempotency_key=_dlq_key,
        )
        if _enqueued:
            print(f"  [X→DLQ] ENQUEUED: {slug}")  # INFO: ログのみ
        else:
            print(f"  [X→DLQ] SKIP: {slug} already in queue or processed")
    except Exception as _e:
        print(f"  [X→DLQ] enqueue failed: {_e}")
        send_telegram(f"❌ *[X→DLQ エラー]* `{slug[:45]}`\n`{str(_e)[:100]}`")


# ── Circuit Breaker: Webhook Rate Limiter ────────────────────────────────────

_CB_DB = "/opt/shared/webhook_rate_limit.db"
_CB_THRESHOLD = 5     # 同一slugへのWebhookがこの回数を超えたら遮断
_CB_WINDOW_SEC = 60   # 監視ウィンドウ（秒）
_CB_COOLDOWN_SEC = 300  # 遮断後の冷却時間（秒）

def _cb_init():
    import sqlite3 as _sq3
    con = _sq3.connect(_CB_DB, timeout=5)
    con.execute("""
        CREATE TABLE IF NOT EXISTS webhook_hits (
            slug TEXT NOT NULL,
            ts   REAL NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS cb_breakers (
            slug       TEXT PRIMARY KEY,
            tripped_at REAL NOT NULL
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_wh_slug_ts ON webhook_hits(slug, ts)")
    con.commit()
    con.close()

_cb_init()

def circuit_breaker_check(slug: str) -> bool:
    """
    Returns True if OK to process, False if circuit is OPEN (should skip).
    Records each webhook hit and trips the breaker if threshold exceeded.
    """
    import sqlite3 as _sq3, time as _t
    now = _t.time()

    con = _sq3.connect(_CB_DB, timeout=5)
    try:
        # クールダウン中か確認
        row = con.execute(
            "SELECT tripped_at FROM cb_breakers WHERE slug=?", (slug,)
        ).fetchone()
        if row:
            if now - row[0] < _CB_COOLDOWN_SEC:
                print(f"  [CB] OPEN circuit for {slug} (cooldown {_CB_COOLDOWN_SEC}s)")
                return False
            else:
                # クールダウン終了 → リセット
                con.execute("DELETE FROM cb_breakers WHERE slug=?", (slug,))
                con.commit()

        # 今回のヒットを記録
        con.execute("INSERT INTO webhook_hits (slug, ts) VALUES (?, ?)", (slug, now))

        # 古いヒットを削除（ウィンドウ外）
        con.execute(
            "DELETE FROM webhook_hits WHERE slug=? AND ts < ?",
            (slug, now - _CB_WINDOW_SEC)
        )
        con.commit()

        # ウィンドウ内のヒット数をカウント
        count = con.execute(
            "SELECT COUNT(*) FROM webhook_hits WHERE slug=? AND ts >= ?",
            (slug, now - _CB_WINDOW_SEC)
        ).fetchone()[0]

        if count > _CB_THRESHOLD:
            # ブレーカーを落とす
            con.execute(
                "INSERT OR REPLACE INTO cb_breakers (slug, tripped_at) VALUES (?, ?)",
                (slug, now)
            )
            con.commit()
            print(f"  [CB] TRIPPED! {slug} hit {count}x in {_CB_WINDOW_SEC}s — blocking for {_CB_COOLDOWN_SEC}s")
            send_telegram(
                f"\u26a1 *[Circuit Breaker 発動]* `{slug[:45]}`\n"
                f"{_CB_WINDOW_SEC}秒以内に{count}回のWebhookを検知\n"
                f"無限ループの可能性あり\u2014{_CB_COOLDOWN_SEC}秒間遺断します"
            )
            return False

        return True

    finally:
        con.close()


# ── Tag Change QA: lang 整合性チェック ────────────────────────────────────

def run_tag_check_on_post(post_id, webhook_post):
    """post.edited イベントでタグ変更を検知し、lang タグ整合性を確認する"""
    slug = webhook_post.get("slug", post_id[:12])
    print(f"  [TAG-CHECK] {slug}")

    # Ghost API から最新のタグを取得
    post = ghost_get_post(post_id)
    if not post:
        print(f"  [TAG-CHECK] post not found: {post_id}")
        return

    tags = {t["slug"] for t in post.get("tags", [])}
    has_lang_ja = "lang-ja" in tags
    has_lang_en = "lang-en" in tags

    issues = []
    # ルール1: 両方あってはいけない
    if has_lang_ja and has_lang_en:
        issues.append("CONFLICT: lang-ja と lang-en が同時に付与されている")
    # ルール2: どちらもない
    if not has_lang_ja and not has_lang_en:
        issues.append("MISSING: lang-ja / lang-en タグが両方ない")
    # ルール3: ENスラッグなのにlang-jaタグ
    if slug.startswith("en-") and has_lang_ja and not has_lang_en:
        issues.append(f"MISMATCH: スラッグ '{slug}' はEN記事だがlang-jaタグが付いている")
    # ルール4: JAスラッグなのにlang-enタグ
    if not slug.startswith("en-") and has_lang_en and not has_lang_ja:
        issues.append(f"MISMATCH: スラッグ '{slug}' はJA記事だがlang-enタグが付いている")

    if issues:
        issue_str = "\n".join(f"  ⚠️ {iss}" for iss in issues)
        msg = (
            f"🏷 *[TAG ALERT] タグ整合性エラー検知*\n"
            f"記事: `{slug}`\n"
            f"現在のタグ: {', '.join(sorted(tags)) or '(なし)'}\n"
            f"{issue_str}\n"
            f"→ Ghost Admin で手動確認"
        )
        print(f"  [TAG-CHECK] ISSUES: {'; '.join(issues)}")
        send_telegram(msg)
    else:
        print(f"  [TAG-CHECK] OK: {slug} tags={tags & {'lang-ja','lang-en'}}")

# ── Webhook Handler ───────────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length) or b"{}"
            body   = json.loads(raw)
        except Exception as e:
            print(f"[Webhook] parse error: {e}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"parse_error"}')
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

        # イベント判定
        post = body.get("post", body.get("page", {}))
        if isinstance(post, dict) and "current" in post:
            post = post["current"]

        post_id = post.get("id", "")
        slug    = post.get("slug", "")
        status  = post.get("status", "")

        print(f"[Webhook] {self.path} | slug={slug} | id={post_id} | status={status}")

        # page.published.edited — predictions改ざん検知
        if slug in PROTECTED_SLUGS:
            editor = post.get("updated_by", {}).get("name", "unknown") if isinstance(post.get("updated_by"), dict) else "unknown"
            msg = (
                f"⚠️ *[ALERT] /{slug}/ ページが変更されました*\n"
                f"編集者: {editor}\n"
                f"時刻: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}\n"
                f"→ 意図しない変更の場合は即確認"
            )
            print(msg)
            send_telegram(msg)
            return

        # post.published / post.published.edited → QA即実行
        if post_id and status in ("published", ""):
            # Circuit Breaker: 同一slugの連続Webhookを遮断
            if not circuit_breaker_check(slug):
                return
            # Semantic QA: Gemini Flash によるコンテンツ品質チェック
            try:
                import sys as _sys2
                if "/opt/shared/scripts" not in _sys2.path:
                    _sys2.path.insert(0, "/opt/shared/scripts")
                import semantic_qa as _sqa
                _sqa_fetch = ghost_request(
                    "GET",
                    f"/posts/{post_id}/?formats=html&fields=id,title,html"
                )
                _sqa_post = (_sqa_fetch.get("posts") or [{}])[0]
                _sqa_passed, _sqa_score, _sqa_reason = _sqa.check(
                    post_id,
                    _sqa_post.get("title", ""),
                    _sqa_post.get("html", ""),
                    slug=slug,
                    lang=lang,
                )
                if not _sqa_passed:
                    print(f"  [SemanticQA] BLOCKED: {slug} score={_sqa_score}/10")
                    return
            except Exception as _sqa_e:
                print(f"  [SemanticQA] Error (skip): {_sqa_e}")
            try:
                run_qa_on_post(post_id, self.path.strip("/"))
            except Exception as e:
                print(f"[Webhook] QA error for {post_id}: {e}")
                import traceback; traceback.print_exc()
            return

        # post.edited → タグ変更の lang 整合性チェック
        # (status = "draft" でも投稿されたタグ変更を検知する)
        if post_id and "/post.edited" in self.path:
            try:
                run_tag_check_on_post(post_id, post)
            except Exception as e:
                print(f"[Webhook] tag-check error for {post_id}: {e}")

    def log_message(self, fmt, *args):
        pass  # アクセスログは静かに

# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port   = int(os.environ.get("WEBHOOK_PORT", "8765"))
    server = HTTPServer(("127.0.0.1", port), WebhookHandler)
    print(f"[Ghost Webhook Server] listening on 127.0.0.1:{port}")
    print(f"  Ghost DB: {GHOST_DB}")
    print(f"  Health DB: {HEALTH_DB}")
    print(f"  NEO Queue: {NEO_QUEUE}")
    server.serve_forever()
