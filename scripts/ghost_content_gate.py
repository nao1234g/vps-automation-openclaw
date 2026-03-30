#!/usr/bin/env python3
"""
ghost_content_gate.py v1.0 -- Ghost Content Validator Gate
port 8766 | systemd: ghost-content-gate.service

Ghost post.published/post.published.edited イベントを受信し、
記事内容を検証。FAIL → 即座にDRAFTに戻す + Telegram通知
(NEOがどんなコードを書いても、この門を通った記事は正しい状態に強制される)

検証チェックリスト:
  1. 言語タグ整合性: 英語タイトル→lang-en / CJK→lang-ja
  2. コンテンツ構造: np-signal / np-between-lines / np-open-loop 必須(EN)
  3. コンテンツ長: 8000文字未満 = FAST_READ_ONLY疑い (EN)
  4. リンク整合性: EN記事に /predictions/ などJA専用リンクが混入していないか
"""

import json, re, os, sys, time, urllib.request, ssl, hmac, hashlib, base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from article_release_guard import evaluate_release_blockers


def load_env():
    env = {}
    try:
        with open('/opt/cron-env.sh') as f:
            for line in f:
                if line.startswith('export '):
                    k, _, v = line[7:].partition('=')
                    env[k] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


ENV = load_env()
BOT_TOKEN = ENV.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID   = ENV.get('TELEGRAM_CHAT_ID', '')
API_KEY   = ENV.get('NOWPATTERN_GHOST_ADMIN_API_KEY', '')

LOG_PATH = '/opt/shared/logs/ghost_content_gate.log'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode    = ssl.CERT_NONE


def get_token():
    kid, sec = API_KEY.split(':')
    now = int(time.time())
    h = base64.urlsafe_b64encode(
        ('{"alg":"HS256","kid":"' + kid + '","typ":"JWT"}').encode()
    ).rstrip(b'=')
    p = base64.urlsafe_b64encode(
        ('{"iat":' + str(now) + ',"exp":' + str(now + 300) + ',"aud":"/admin/"}').encode()
    ).rstrip(b'=')
    s = base64.urlsafe_b64encode(
        hmac.new(bytes.fromhex(sec), h + b'.' + p, hashlib.sha256).digest()
    ).rstrip(b'=')
    return (h + b'.' + p + b'.' + s).decode()


def has_cjk(text):
    return bool(re.search(r'[\u3000-\u9fff\u4e00-\u9fff\uff00-\uffef]', text))


def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'a') as f:
        f.write(line + '\n')


def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        data = json.dumps({
            'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'
        }).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            data=data, headers={'Content-Type': 'application/json'}, method='POST')
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f'Telegram error: {e}')


def ghost_get_post(post_id):
    try:
        url = f'https://nowpattern.com/ghost/api/admin/posts/{post_id}/?formats=html&include=tags'
        req = urllib.request.Request(
            url, headers={'Authorization': 'Ghost ' + get_token()})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            return json.loads(r.read()).get('posts', [{}])[0]
    except Exception as e:
        log(f'ghost_get_post error: {e}')
        return {}


def ghost_patch_to_draft(post_id, updated_at):
    try:
        body = json.dumps({'posts': [{
            'id': post_id,
            'status': 'draft',
            'updated_at': updated_at
        }]}).encode()
        url = f'https://nowpattern.com/ghost/api/admin/posts/{post_id}/'
        req = urllib.request.Request(url, data=body, method='PUT', headers={
            'Authorization': 'Ghost ' + get_token(),
            'Content-Type': 'application/json'
        })
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            return True
    except Exception as e:
        log(f'ghost_patch_to_draft error: {e}')
        return False


EN_REQUIRED_MARKERS = ['np-signal', 'np-between-lines', 'np-open-loop', 'np-fast-read']
EN_MIN_LENGTH = 8000
JA_ONLY_PATHS_RE = re.compile(r'href=["\']/((?!en/)(?!ghost/)(?!content/)[a-z][a-z0-9-]+)/["\']')
JA_ALLOWED_PATHS = {'about', 'taxonomy', 'taxonomy-guide', '#', 'predictions', 'en'}


def validate_article(post):
    title  = post.get('title', '') or ''
    html   = post.get('html', '') or ''
    tags   = post.get('tags', []) or []

    tag_slugs  = [t.get('slug', '') for t in tags]
    is_english = not has_cjk(title)
    errors     = []
    should_draft = False

    # Check 1: language tag consistency
    if is_english:
        if 'lang-ja' in tag_slugs and 'lang-en' not in tag_slugs:
            errors.append('LANG ERROR: English title has lang-ja tag (needs lang-en)')
            should_draft = True
        elif 'lang-ja' in tag_slugs and 'lang-en' in tag_slugs:
            errors.append('LANG WARNING: both lang-ja and lang-en present (duplicate)')
    else:
        if 'lang-en' in tag_slugs and 'lang-ja' not in tag_slugs:
            errors.append('LANG ERROR: Japanese title has lang-en tag (needs lang-ja)')
            should_draft = True

    # Check 2: EN article structure (markers)
    if is_english and html:
        missing = [m for m in EN_REQUIRED_MARKERS if m not in html]
        if missing:
            errors.append('STRUCTURE ERROR: EN missing markers: ' + ', '.join(missing))
            should_draft = True

        if len(html) < EN_MIN_LENGTH:
            errors.append(f'LENGTH ERROR: EN article too short ({len(html)} chars < {EN_MIN_LENGTH}) - FAST_READ_ONLY suspected')
            should_draft = True

    # Check 3: EN article link consistency
    if is_english and html:
        matches = JA_ONLY_PATHS_RE.findall(html)
        bad = [m for m in matches if m not in JA_ALLOWED_PATHS]
        if bad:
            errors.append('LINK WARNING: EN article has JA-root links: ' + str(bad[:5]))
            # warning only, do not draft

    release_block = evaluate_release_blockers(
        title=title,
        html=html,
        tags=tag_slugs,
        site_url='https://nowpattern.com',
        status='published',
        channel='public',
        require_external_sources=True,
        check_source_fetchability=True,
    )
    if release_block["errors"]:
        errors.append('RELEASE BLOCKER: ' + ', '.join(release_block["errors"]))
        should_draft = True

    return len(errors) == 0, errors, should_draft


class GateHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or b'{}')
        except Exception:
            return

        post = body.get('post', body.get('page', {}))
        if not post:
            return

        post_id    = post.get('id', '')
        slug       = post.get('slug', '')
        updated_at = post.get('updated_at', '')

        if not post_id:
            return

        log(f'Webhook received: {slug} ({post_id[-8:]})')
        Thread(
            target=self._validate_and_act,
            args=(post, slug, post_id, updated_at),
            daemon=True
        ).start()

    def _validate_and_act(self, post, slug, post_id, updated_at):
        # Fetch full post if HTML not in webhook payload
        html = post.get('html', '')
        if not html or len(html) < 100:
            full = ghost_get_post(post_id)
            if full:
                post = full
                updated_at = post.get('updated_at', updated_at)

        is_valid, errors, should_draft = validate_article(post)

        if is_valid:
            log(f'  PASS: {slug[:60]}')
            return

        log(f'  FAIL ({len(errors)} errors): {slug[:60]}')
        for e in errors:
            log(f'    {e}')

        draft_msg = ''
        if should_draft:
            ok = ghost_patch_to_draft(post_id, updated_at)
            draft_msg = 'Reverted to DRAFT' if ok else 'DRAFT revert FAILED'
            log(f'  {draft_msg}')
        else:
            draft_msg = 'Warning only (not drafted)'

        emoji = 'ALERT' if should_draft else 'WARN'
        msg = (
            f'[{emoji}] Ghost Content Gate FAIL\n'
            f'slug: {slug}\n'
            + '\n'.join(f'  {e}' for e in errors) + '\n'
            f'{draft_msg}\n'
            f'Fix and republish.'
        )
        send_telegram(msg)

    def log_message(self, fmt, *args):
        pass


if __name__ == '__main__':
    if not API_KEY:
        print('[ERROR] NOWPATTERN_GHOST_ADMIN_API_KEY not set')
        sys.exit(1)
    port = 8767
    server = HTTPServer(('127.0.0.1', port), GateHandler)
    log(f'Ghost Content Gate v1.0 on :{port}')
    log(f'Validating: lang_tag | structure(EN) | length(EN) | links(EN)')
    server.serve_forever()
