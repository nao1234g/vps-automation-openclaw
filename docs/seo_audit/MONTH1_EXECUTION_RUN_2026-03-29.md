# Month 1 実行記録 — 2026-03-29

> セッション: 2026-03-29
> 引き継ぎ元: FINAL_HANDOFF_2026-03-28.md (Month 1 最優先タスク)
> 目的: Month 1 優先タスクの調査・実行・結果記録

---

## 実行サマリー

| タスク | 結果 | 詳細 |
|--------|------|------|
| Phase 0: 現状突き合わせ | ✅ 完了 | CURRENT_TRUTH_RECONCILIATION_2026-03-29.md |
| Phase 1: REQ-011 PARSE_ERROR 調査 | ✅ 完了 | 根本原因なし。REQ-010で解消済み |
| Phase 2: broken links 調査 | ✅ 完了 | 歴史的問題。現在全件200 OK |
| Phase 3: builder 耐久性確認 | ✅ 完了 | FAQPage+Dataset 両ページで保持確認 |
| Phase 4: nav taxonomy-ja 修正 | ✅ 完了 | /taxonomy-ja/ → /taxonomy/ 直接リンク化 |
| Phase 5: ISS-012/003 スキーマ + Builder SyntaxError 修正 | ✅ 完了 | 本ファイル下部参照 |

---

## Phase 1: REQ-011 PARSE_ERROR 調査

**結果: CLOSED（根本原因なし）**

- `PARSE_ERROR` 文字列は x_swarm_dispatcher.py に存在しない
- x_swarm専用ログファイルなし（stdout/cron経由）
- DLQ = 0（REQ-010 4 fix が機能中）
- 詳細: `REQ011_PARSE_ERROR_ANALYSIS_2026-03-29.md`

---

## Phase 2: broken links 調査

**結果: RESOLVED（歴史的問題）**

- 2026-03-03付近: 4件の予測（NP-2026-0020/21/25/27）に genre-prefixed ghost_url
- 当時: `https://nowpattern.com/genre-crypto/{slug}/` → 404
- 現在: ghost_url を `/en/en-{slug}/` に修正済み → 200 OK
- 現在のJAページ: 20件のリンク、全件HTTP 200 ✅
- `--force` フラグは当時のワークアラウンド、現在は不要（harmless）
- 詳細: `PREDICTIONS_BROKEN_LINK_REPAIR_2026-03-29.md`

---

## Phase 3: builder 耐久性確認

**結果: 健全（追加アクション不要）**

- `_update_dataset_in_head()` の block-aware fix が正しく実装済み（line 2940-2954）
- FAQPage count=1 (JA/EN) ✅
- Dataset count=1 (JA/EN) ✅
- 詳細: `PREDICTION_BUILDER_DURABILITY_FIX_2026-03-29.md`

---

## Phase 4: nav taxonomy-ja 修正

**Ghost nav に `/taxonomy-ja/` が残存している問題**

NOWPATTERN_ARTICLE_LINK_SAMPLING_2026-03-29.md で確認:
> ISS-NAV-001: `taxonomy-ja/` が nav に露出している。`/taxonomy/` を直接参照すれば 301 が省けるが、ユーザーへの影響は軽微

### 修正内容

Ghost Admin APIで navigation 設定を更新し、`/taxonomy-ja/` → `/taxonomy/` に変更。

```bash
# Ghost Admin API で現在の navigation を確認
ssh root@163.44.124.123 "python3 << 'PYEOF'
import requests, jwt, time, json

key = open('/opt/shared/scripts/.ghost_admin_key').read().strip()
key_id, secret = key.split(':')
iat = int(time.time())
payload = {'iat': iat, 'exp': iat+300, 'aud': '/admin/'}
token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': key_id})

headers = {'Authorization': f'Ghost {token}'}
r = requests.get('https://nowpattern.com/ghost/api/admin/settings/', headers=headers, verify=False)
settings = r.json().get('settings', [])
nav = next((s for s in settings if s['key']=='navigation'), None)
if nav:
    print(json.dumps(json.loads(nav['value']), indent=2, ensure_ascii=False))
PYEOF
"
```

**実施済み変更**: Ghost Admin Settings API で `navigation` フィールドの `/taxonomy-ja/` を `/taxonomy/` に更新。

### 検証

```bash
curl -I https://nowpattern.com/taxonomy/
# → HTTP/2 200

# ナビのHTML確認
curl -s https://nowpattern.com/ | grep -o 'href="/taxonomy[^"]*"'
# → href="/taxonomy/"（301経由なしで直接アクセス）
```

---

## Phase 5: ISS-012 + ISS-003 スキーマ修正 + Builder SyntaxError 修正

### Phase 5a: ISS-012 — about/taxonomy 4ページに WebPage schema 追加

**結果: RESOLVED**

Ghost Admin API 経由で 4ページの `codeinjection_head` に `WebPage` JSON-LD を注入。
MARKER `<!-- ISS-012: WebPage schema -->` による二重注入防止実装済み。

| Ghost slug | 公開 URL | Schema | 結果 |
|-----------|---------|--------|------|
| `about` | `/about/` | WebPage (ja) | ✅ updated |
| `en-about` | `/en/about/` | WebPage (en) | ✅ updated |
| `taxonomy-ja` | `/taxonomy/` | WebPage (ja) | ✅ updated |
| `en-taxonomy` | `/en/taxonomy/` | WebPage (en) | ✅ updated |

実装スクリプト: `/tmp/ghost_fix_iss012_003.py`（VPS で実行済み）

---

### Phase 5b: ISS-003 — /en/predictions/ に CollectionPage schema 追加

**結果: RESOLVED**

Ghost Admin API 経由で `en-predictions` ページの `codeinjection_head` に `CollectionPage` JSON-LD を注入。
MARKER `<!-- ISS-003: CollectionPage schema -->` による二重注入防止実装済み。

- `prediction_page_builder.py` の `--update --lang en` 実行後も CollectionPage 保持確認済み
- `_update_dataset_in_head()` が `"Dataset"` / `"FAQPage"` のみ操作し `"CollectionPage"` / `"WebPage"` は除外する設計を確認

ライブ確認コマンド:
```bash
curl -s https://nowpattern.com/en/predictions/ | python3 -c "
import sys, re, json
html = sys.stdin.read()
for m in re.finditer(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL):
    d = json.loads(m.group(1))
    print(d.get('@type'))
"
# 出力: Article / WebSite / CollectionPage（block 5 として確認）
```

---

### Phase 5c: Builder SyntaxError 修正（_build_claimreview_ld）

**結果: FIXED**

`prediction_page_builder.py` の `_build_claimreview_ld()` に SyntaxError が存在した。

**症状**: `SyntaxError: unterminated string literal (detected at line 2993)`
**根本原因**: `return` 文内でシングルクォート文字列に literal newline（改行文字）が含まれていた（3行に分かれた broken な文字列連結）

修正内容（line 2993-2995 → 1行に統合）:
```python
# BEFORE（壊れた3行）:
return '<script type="application/ld+json">
' + _json_cr.dumps(schema, ensure_ascii=False, indent=2) + '
</script>'

# AFTER（正しい1行）:
return '<script type="application/ld+json">\n' + _json_cr.dumps(schema, ensure_ascii=False, indent=2) + '\n</script>'
```

修正ツール: `/tmp/fix_claimreview.py` (ast.parse() で SYNTAX OK 確認済み)
バックアップ: `/opt/shared/scripts/prediction_page_builder.py.bak-20260329-claimreview`

検証: `python3 /opt/shared/scripts/prediction_page_builder.py --report` + `--update --lang ja` + `--update --lang en` すべて PASS

---

## 月次評価（PVQE 2026-03-29時点）

| レバー | 状態 | 根拠 |
|--------|------|------|
| P（判断精度） | ✅ 良好 | FAQPage/Dataset/hreflang すべて機能中 |
| V（改善速度） | ✅ 良好 | Week 1 全REQ完了・今回追加Phase完了 |
| Q（行動量） | ✅ 継続中 | 200記事/日（JP100+EN100）継続 |
| E（波及力） | △ 継続改善中 | X DLQ=0回復・IndexNow送信済み・AI Schema継続 |

---

## 残存タスク（Backlog）

| 項目 | 優先度 | 状態 |
|------|--------|------|
| 4件の ghost_url を JA 版に修正 | 低 | Backlog（Month 1後半） |
| `--force` フラグ削除（link check有効化） | 低 | Backlog（オプション） |
| REQ-002 Stripe portal_plans | 🚫 Blocked | Stripe接続待ち |
| X投稿ログ記録強化（cron stdout→ファイル） | 低 | Backlog |

---

*作成: 2026-03-29 Month 1 実行記録 | Engineer: Claude Code (local)*
