#!/usr/bin/env python3
"""
patch_stakeholder_table.py
Ghost上の既存記事の利害関係者マップ（カード形式）を
5列スティッキーテーブル形式に一括置換する。

使い方:
  python3 /opt/shared/scripts/patch_stakeholder_table.py --dry-run
  python3 /opt/shared/scripts/patch_stakeholder_table.py
"""
import re
import sys
import json
import hmac
import hashlib
import time
import base64
import argparse
import urllib.request
import ssl

GHOST_URL = "https://nowpattern.com"
GHOST_ADMIN_API_KEY = "6995030a3b8c7ab6f20bfe27:c071ad0cfe5b40b44a57890899d3edda40f6caede282ca2eda66a82980634d2c"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def _make_jwt() -> str:
    key_id, secret_hex = GHOST_ADMIN_API_KEY.split(":")
    secret = bytes.fromhex(secret_hex)
    iat = int(time.time())
    exp = iat + 300
    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    header = b64url(json.dumps({"alg": "HS256", "kid": key_id, "typ": "JWT"}).encode())
    payload = b64url(json.dumps({"iat": iat, "exp": exp, "aud": "/admin/"}).encode())
    sig = b64url(hmac.new(secret, f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def _api_get(path):
    url = f"{GHOST_URL}/ghost/api/admin/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Ghost {_make_jwt()}"})
    with urllib.request.urlopen(req, context=SSL_CTX) as r:
        return json.loads(r.read())


def _api_put(post_id, payload):
    url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/?source=html"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"Ghost {_make_jwt()}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, context=SSL_CTX) as r:
        return json.loads(r.read())


def extract_grid_block(html: str, start: int) -> tuple[str, int] | None:
    """
    html[start] から始まる <div class="np-stakeholder-grid"> ブロック全体を抽出。
    divタグの深さをカウントして正しい閉じタグを特定する。
    returns: (block_html, end_index) or None
    """
    # start が np-stakeholder-grid の開始位置であることを確認
    if not html[start:].startswith('<div class="np-stakeholder-grid">'):
        return None

    depth = 0
    i = start
    while i < len(html):
        open_m = re.search(r'<div', html[i:])
        close_m = re.search(r'</div>', html[i:])

        if open_m is None and close_m is None:
            break

        open_pos = i + open_m.start() if open_m else len(html)
        close_pos = i + close_m.start() if close_m else len(html)

        if open_pos < close_pos:
            depth += 1
            i = open_pos + 4  # len("<div")
        else:
            depth -= 1
            end = close_pos + 6  # len("</div>")
            if depth == 0:
                return html[start:end], end
            i = end

    return None


def parse_actor_card(card_html: str) -> tuple[str, str, str, str, str] | None:
    """np-actor-card HTML から (actor, public, private, gains, loses) を抽出"""
    name_m = re.search(r'<div class="np-actor-name">(.*?)</div>', card_html)
    if not name_m:
        return None
    actor = name_m.group(1).strip()

    def get_attr(data_type):
        m = re.search(
            rf'data-type="{data_type}"[^>]*>.*?<span class="np-actor-value">(.*?)</span>',
            card_html,
        )
        return m.group(1).strip() if m else ""

    return (actor, get_attr("public"), get_attr("private"), get_attr("gains"), get_attr("loses"))


def parse_grid(grid_html: str) -> list | None:
    """np-stakeholder-grid ブロックから全アクターデータを抽出"""
    # np-actor-card ブロックを抽出（深さカウント方式）
    actors = []
    i = 0
    while True:
        idx = grid_html.find('<div class="np-actor-card">', i)
        if idx < 0:
            break
        # この actor-card ブロックを抽出
        result = extract_grid_block.__wrapped__(grid_html, idx) if hasattr(extract_grid_block, '__wrapped__') else _extract_div_block(grid_html, idx)
        if result is None:
            i = idx + 1
            continue
        card_html, end = result
        data = parse_actor_card(card_html)
        if data:
            actors.append(data)
        i = end

    return actors if actors else None


def _extract_div_block(html: str, start: int) -> tuple[str, int] | None:
    """html[start] の <div...> から対応する </div> までを抽出"""
    depth = 0
    i = start
    while i < len(html):
        open_m = re.search(r'<div', html[i:])
        close_m = re.search(r'</div>', html[i:])

        if open_m is None and close_m is None:
            break
        open_pos = i + open_m.start() if open_m else len(html)
        close_pos = i + close_m.start() if close_m else len(html)

        if open_pos < close_pos:
            depth += 1
            i = open_pos + 4
        else:
            depth -= 1
            end = close_pos + 6
            if depth == 0:
                return html[start:end], end
            i = end
    return None


def build_sticky_table(actors: list) -> str:
    """5列スティッキーテーブルHTMLを生成"""
    TH_BASE = "padding:9px 12px;font-size:0.78em;font-weight:600;letter-spacing:.05em;text-transform:uppercase;white-space:nowrap;border-bottom:2px solid #dde4ed"
    TH_ACTOR = f'{TH_BASE};position:sticky;left:0;z-index:2;background:#1a2940;color:#e8d5b7;text-align:left;min-width:90px'
    TH_PUBLIC = f'{TH_BASE};background:#1e3050;color:#c4d4e8;text-align:left;min-width:140px'
    TH_PRIVATE = f'{TH_BASE};background:#2a1f0e;color:#d4a853;text-align:left;min-width:140px'
    TH_GAINS = f'{TH_BASE};background:#0e2a1a;color:#6ec88a;text-align:left;min-width:140px'
    TH_LOSES = f'{TH_BASE};background:#2a0e0e;color:#e88a8a;text-align:left;min-width:140px'

    header = (
        f'<tr>'
        f'<th style="{TH_ACTOR}">アクター</th>'
        f'<th style="{TH_PUBLIC}">建前</th>'
        f'<th style="{TH_PRIVATE}">本音</th>'
        f'<th style="{TH_GAINS}">&#x2705; 得るもの</th>'
        f'<th style="{TH_LOSES}">&#x274c; 失うもの</th>'
        f'</tr>'
    )

    TD_BASE = "padding:10px 12px;border-bottom:1px solid #eeeae4;vertical-align:top;line-height:1.5"
    rows = []
    for i, (actor, public_pos, private_int, gains, loses) in enumerate(actors):
        bg_row = "#faf9f7" if i % 2 == 0 else "#f3f1ee"
        td_actor = f'{TD_BASE};position:sticky;left:0;z-index:1;background:{bg_row};font-weight:700;color:#1a2940;white-space:nowrap;font-size:0.92em'
        td_public = f'{TD_BASE};background:{bg_row};color:#2c3e55'
        td_private = f'{TD_BASE};background:{bg_row};color:#7a5a1a'
        td_gains = f'{TD_BASE};background:{bg_row};color:#1a6b35'
        td_loses = f'{TD_BASE};background:{bg_row};color:#8b2a2a'
        rows.append(
            f'<tr>'
            f'<td style="{td_actor}">{actor}</td>'
            f'<td style="{td_public}">{public_pos}</td>'
            f'<td style="{td_private}">{private_int}</td>'
            f'<td style="{td_gains}">{gains}</td>'
            f'<td style="{td_loses}">{loses}</td>'
            f'</tr>'
        )

    return (
        f'<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:8px;border:1px solid #dde4ed;margin:12px 0">'
        f'<table style="width:100%;border-collapse:collapse;table-layout:auto;font-size:0.88em">'
        f'<thead>{header}</thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
        f'</div>'
    )


def convert_html(html: str) -> tuple[str, int]:
    """HTMLのnp-stakeholder-gridブロックをテーブルに変換。変換数を返す"""
    new_html = html
    count = 0
    offset = 0

    while True:
        idx = new_html.find('<div class="np-stakeholder-grid">', offset)
        if idx < 0:
            break

        result = _extract_div_block(new_html, idx)
        if result is None:
            offset = idx + 1
            continue

        block_html, end = result
        actors = parse_grid(block_html)
        if not actors:
            offset = end
            continue

        table_html = build_sticky_table(actors)
        new_html = new_html[:idx] + table_html + new_html[end:]
        offset = idx + len(table_html)
        count += 1

    return new_html, count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="変換確認のみ（Ghost更新なし）")
    args = parser.parse_args()

    print("Ghost記事を取得中...")
    all_posts = []
    page = 1
    while True:
        data = _api_get(f"posts/?limit=50&page={page}&fields=id,title,html,updated_at&formats=html")
        posts = data.get("posts", [])
        if not posts:
            break
        all_posts.extend(posts)
        meta = data.get("meta", {}).get("pagination", {})
        if page >= meta.get("pages", 1):
            break
        page += 1

    print(f"取得: {len(all_posts)}件")

    updated = 0
    skipped = 0
    for post in all_posts:
        html = post.get("html") or ""
        if "np-stakeholder-grid" not in html:
            skipped += 1
            continue

        new_html, n = convert_html(html)
        if n == 0:
            print(f"  SKIP (パース失敗): {post['title'][:55]}")
            skipped += 1
            continue

        print(f"  {'[DRY] ' if args.dry_run else ''}PATCH ({n}ブロック): {post['title'][:60]}")

        if not args.dry_run:
            try:
                _api_put(post["id"], {
                    "posts": [{
                        "html": new_html,
                        "updated_at": post["updated_at"],
                    }]
                })
                updated += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"    ERROR: {e}")
        else:
            updated += 1

    print(f"\n完了: 更新={updated}件 スキップ={skipped}件")
    if args.dry_run:
        print("(--dry-run: 実際の変更なし)")


if __name__ == "__main__":
    main()
