#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ghost記事タイトルを一括更新 + 重複記事を削除するスクリプト。
"""
import json, os, sys, time, hashlib, hmac, base64
import urllib3; urllib3.disable_warnings()
import requests

API_KEY = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
GHOST_URL = "https://nowpattern.com"

def make_jwt(key):
    kid, secret = key.split(":")
    iat = int(time.time())
    def b64u(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    h = b64u(json.dumps({"alg":"HS256","typ":"JWT","kid":kid}).encode())
    p = b64u(json.dumps({"iat":iat,"exp":iat+300,"aud":"/admin/"}).encode())
    s = f"{h}.{p}"
    sig = hmac.new(bytes.fromhex(secret), s.encode(), hashlib.sha256).digest()
    return f"{s}.{b64u(sig)}"

def hdrs():
    return {"Authorization": f"Ghost {make_jwt(API_KEY)}", "Content-Type": "application/json"}

# -------------------------------------------------------------------------
# 更新するタイトル一覧: (post_id, new_title)
# -------------------------------------------------------------------------
TITLE_UPDATES = [
    (
        "699793255850354f44049bc9",
        "HyperliquidがDCにロビー団体設立 — DeFiが「規制される側」から「規制を書く側」へ"
    ),
    (
        "699779e45850354f44049bbe",
        "ミュンヘン安全保障会議2026 — 米欧同盟の亀裂が構造的になった5つの兆候"
    ),
    (
        "699779e05850354f44049bb1",
        "米史上最大の下水流出事故 — 連邦政府が原因施設を所有する構造的皮肉"
    ),
    (
        "699779dd5850354f44049ba8",
        "ジュネーブ停戦交渉の直前にロシアが過去最大規模のドローン攻撃 — 交渉カードとしての暴力"
    ),
    (
        "699779d95850354f44049b9d",
        "「トランプが1年でNATOを壊した」— 上院議員が公言する同盟崩壊の実態"
    ),
    # [6] slug末尾-2 → 重複なので削除対象
    # [7] 元記事 → こちらにタイトルを付与
    (
        "6997259e5850354f44049b8b",
        "核軍縮条約「新START」が失効 — 後継交渉ゼロ、トランプ外交が作る核の空白"
    ),
    (
        "69967ce55850354f44049b80",
        "暗号資産市場が1兆ドル縮小する中、現実資産トークン化（RWA）が13.5%成長した理由"
    ),
    (
        "69967cdf5850354f44049b77",
        "ビットコインマイナーは「電力の無駄遣い」ではなく「柔軟な電力需要」— Paradigmの反論"
    ),
    (
        "69967cdc5850354f44049b6a",
        "ブンデスバンク総裁がユーロステーブルコイン支持 — ドル支配への欧州の対抗軸"
    ),
    (
        "69967cce5850354f44049b5f",
        "ロシア財務省が認めた日650億円超の暗号資産取引 — 制裁回避の実態"
    ),
    # [12] slug末尾-2 → 重複削除対象
    # [13] 元記事 → こちらにタイトルを付与
    (
        "6996289d5850354f44049b3d",
        "「NATOはかつてなく強い」の裏メッセージ — 欧州は自力防衛せよ、米は引く"
    ),
    (
        "6995d42c5850354f44049b32",
        "現職大統領の企業がBTC・ETH・CROのETFをSECに申請 — 利益相反と規制緩和の象徴"
    ),
    (
        "6995d4285850354f44049b25",
        "トランプが排ガス規制を撤廃 — EV義務化消滅でトヨタが有利、テスラは逆風"
    ),
    (
        "6995d4255850354f44049b1c",
        "トランプ「イラン体制転換が最善」— 空母2隻配備で2003年以来最大の中東緊張"
    ),
    (
        "6995d4215850354f44049b13",
        "ルビオ＝王毅会談の裏側 — 関税・台湾・半導体、米中「取引外交」の優先順位"
    ),
    (
        "6995d4165850354f44049b08",
        "米・イスラエルのイラン制裁強化 — 焦点は中国への原油遮断と米中経済戦争の新戦線"
    ),
]

# 重複記事: 削除するID ([6]と[12]の-2重複版)
DELETE_IDS = [
    "699779d55850354f44049b94",  # [6] New START -2 (重複)
    "69967cca5850354f44049b56",  # [12] Colby NATO -2 (重複)
]

def get_updated_at(post_id):
    r = requests.get(
        f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/?fields=updated_at",
        headers=hdrs(), verify=False, timeout=15)
    return r.json().get("posts", [{}])[0].get("updated_at", "")

def update_title(post_id, new_title):
    updated_at = get_updated_at(post_id)
    body = {"posts": [{"title": new_title, "updated_at": updated_at}]}
    r = requests.put(
        f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/",
        json=body, headers=hdrs(), verify=False, timeout=20)
    return r.status_code == 200, r.text[:200]

def delete_post(post_id):
    r = requests.delete(
        f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/",
        headers=hdrs(), verify=False, timeout=15)
    return r.status_code == 204

# ---- 実行 ----
print("=== タイトル更新 ===")
ok_count = 0
for pid, new_title in TITLE_UPDATES:
    ok, msg = update_title(pid, new_title)
    status = "OK" if ok else "ERROR"
    print(f"[{status}] {new_title[:50]}...")
    if ok:
        ok_count += 1
    else:
        print(f"       {msg}")

print(f"\n=== 重複記事削除 ===")
for pid in DELETE_IDS:
    ok = delete_post(pid)
    status = "DELETED" if ok else "ERROR"
    print(f"[{status}] {pid}")

print(f"\n完了: {ok_count}/{len(TITLE_UPDATES)} 件更新, {len(DELETE_IDS)} 件削除")
