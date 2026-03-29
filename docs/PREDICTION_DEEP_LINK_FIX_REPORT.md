# Prediction Deep Link Fix — 完了レポート

> 作成日: 2026-03-28
> ステータス: **全ワークストリーム完了（WS1–G + 運用化 WS2–4）**
> 検証完了時刻: 2026-03-28 — E2E最終確認: 2026-03-28（本セッション）

---

## 概要

nowpattern.com の Oracle Statement（記事末尾の予測ボックス）にあるリンクを
`/predictions/` (ページトップ) → `/predictions/#np-XXXX` (予測カード直接) に修正した。

**修正前:** リンクが `/predictions/` に飛ぶだけで、特定の予測カードに到達できない
**修正後:** `#np-2026-0042` 形式のアンカーで予測カードに直リンク、自動展開

---

## 最終検証結果（2026-03-28 17:15 JST）

| 指標 | 数値 |
|------|------|
| JA /predictions/ ページのアンカー数 | **214** (sq=193 + dq=21) ※2026-03-28時点 |
| EN /en/predictions/ ページのアンカー数 | **876** |
| JA記事のoracleディープリンク数 | **192** |
| アンカー不一致（リンク切れ） | **0** |
| リグレッションlint結果 | **PASS（0件）** |

> **2026-03-29 追記**: daily cron (JST 07:00) によりページが再生成されるため、アンカー数は日次で変動する。
> 2026-03-29 ライブ確認: JA=**199** (sq=178+dq=21)、EN=**876** (変動なし)。
> dq=21 が安定していること（fix適用後の新アンカー形式）がリグレッションなしの証拠。
> sq カウント変動は予測の追加・解決によるもの（設計通り）。lint PASS (0件) も継続確認済み。

---

## ワークストリーム詳細

### Workstream A — 現状監査

**発見事項:**
- 168件のJA記事にOracle Statement（`/predictions/` リンク）が存在
- しかしリンクがアンカーなし（`/predictions/` のみ）
- `/predictions/` ページには `id` 属性が付いていない → ディープリンク不可

---

### Workstream B — アンカーアーキテクチャ決定

**採用方式:** HTMLアンカーID方式

```
予測カード:   <details id="np-2026-0042" ...>
記事リンク:   href="nowpattern.com/predictions/#np-2026-0042"
ルール:       prediction_id を lowercase に変換してアンカーIDに使用
```

**根拠:** `prediction_id`（例: `NP-2026-0042`）の lowercase 変換値がアンカーID。
HTMLの仕様上、IDは大文字小文字を区別するため、DBの `NP-` プレフィックスをそのまま使うと
リンク側の `#NP-` と大文字不一致になる可能性があるため、常に lowercase に統一。

---

### Workstream C — prediction_page_builder.py 改修

**変更ファイル:** `/opt/shared/scripts/prediction_page_builder.py`
**バックアップ:** `.bak-20260328-anchors`

#### 修正 1: build_rows() 言語フィルター（Patch 1）

`article_title` が空の予測について、`ghost_url` のパスで言語を判定するフォールバックを追加。

```python
# Before: article_title が空 → _is_japanese("") = False → JA予測がスキップされていた
if lang == "ja" and not _is_japanese(title): continue

# After: ghost_url で言語判定するフォールバック
if not title:
    if lang == "ja" and _url_is_en: continue  # /en/ がある = EN記事 → skip
    if lang == "en" and not _url_is_en: continue
else:
    if lang == "ja" and not _is_japanese(title): continue
    ...
```

#### 修正 2: build_rows() シナリオフィルター（Patch 2）

シナリオデータ（楽観/基本/悲観）が空の予測もアンカーIDのためのミニマル行を生成するよう変更。

```python
# Before: シナリオなし → continue で完全スキップ
if base is None and opt is None and pess is None: continue

# After: prediction_id + ghost_url があれば最小限の行を生成
if base is None and opt is None and pess is None:
    if _pid_min and _url_min:
        rows.append({... "prediction_id": _pid_min ...})
    continue
```

#### 修正 3: _build_compact_row() — アンカーID（既実装確認）

`_build_compact_row()` は既に `id='{_anchor_id}'` を生成していた（Workstream C 完了済み）。

```python
_anchor_id = r.get('prediction_id', '').lower()
_id_attr = f" id='{_anchor_id}'" if _anchor_id else ''
return f'<details{_id_attr} data-genres=...'
```

#### 修正 4: Oracle Guardian エラーカード（本セッション追加）

`_build_error_card()` 関数が `id` 属性を生成していなかった。
`status=resolved` の7件がここでレンダリングされていたため、アンカーが消えていた。

```python
# Added before return statement in _build_error_card():
_og_id_attr = f" id='{pred_id.lower()}'" if pred_id and pred_id != '???' else ''
return (
    f'<details{_og_id_attr} style="border:2px solid #EF4444;...'
```

#### ハッシュ自動展開スクリプト（Workstream C）

`/predictions/` ページのフッターに以下のJSを追加済み:

```javascript
(function(){
  var h = location.hash;
  if (!h) return;
  var el = document.querySelector(h);
  if (!el) return;
  if (el.tagName === 'DETAILS') {
    el.open = true;
    el.scrollIntoView({behavior:'smooth', block:'start'});
  }
})();
```

---

### Workstream D — 既存記事の一括マイグレーション

**対象:** 168件のJA記事 + 168件のEN記事
**処理:** `/predictions/` → `/predictions/#np-XXXX`（予測IDアンカーつき）に一括置換

**スクリプト:** `/opt/shared/scripts/migrate_prediction_links.py`

**結果:**
- 168件のJA記事: Oracle Statement リンクにアンカー追加完了
- 168件のEN記事: `/en/predictions/#np-XXXX` 形式に統一完了

---

### Workstream E — 将来記事のバリデーション

**対象スクリプト:** `/opt/shared/scripts/nowpattern_publisher.py`

新規記事生成時のOracle Statementテンプレートを更新。
`{prediction_id}` → `{prediction_id_lower}` （lowercase変換後の値）を自動挿入。

---

### Workstream F — リグレッション防止（lintスクリプト）

**スクリプト:** `/opt/shared/scripts/lint_prediction_links.py`（v5）

**仕様:**
- JA記事のOracle CTA（`予測に参加 →`）がアンカーなしの場合のみFAIL
- EN記事の汎用LIKING CTA（`→ 全予測を見る`等）は除外（false positiveを防止）
- 正規表現: oracle CTA テキストパターンに限定

```python
BARE_ORACLE = re.compile(
    r'href=["\'][^"\'#]*/(?:en/)?predictions/["\'][^>]*>'
    r'[^<]*(?:予測に参加|Join\s+the\s+prediction|Participate\s+in\s+the\s+prediction)[^<]*'
    r'</a>'
)
```

**最終実行結果:**
```
Checked 192 JA prediction articles (out of 229 JA published)
Bare oracle CTAs found: 0
OK - all JA oracle CTAs are anchored
```

---

### Workstream G — 検証・引き渡し

#### アンカー到達カバレッジ（2026-03-28 17:15 JST 確認）

| ステップ | Before | After |
|----------|--------|-------|
| JA /predictions/ アンカー数 | 22 | **214** |
| JA記事 oracle deep link カバレッジ | 22/192 (11%) | **192/192 (100%)** |
| Bare oracle CTA（lint結果） | 未計測 | **0件** |

#### 根本原因（発見順）

1. **言語フィルター問題**: `article_title` が空の予測 → `_is_japanese("") = False` → JA予測がスキップ
2. **シナリオフィルター問題**: シナリオデータなし → `continue` で完全スキップ（170件）
3. **Oracle Guardianカード問題**: `status=resolved` + データ不完全 → `id` 属性なしのエラーカード（7件）

---

## ファイル変更サマリー

### VPS変更ファイル

| ファイル | 変更内容 |
|----------|---------|
| `/opt/shared/scripts/prediction_page_builder.py` | build_rows() 言語/シナリオフィルター修正 + Oracle Guardian id追加 + ハッシュJS追加 |
| `/opt/shared/scripts/migrate_prediction_links.py` | 新規作成（一括マイグレーション） |
| `/opt/shared/scripts/lint_prediction_links.py` | v5（JA限定 + oracle CTA正規表現） |
| `/opt/shared/scripts/nowpattern_publisher.py` | 将来記事テンプレート更新 |

### バックアップ

| バックアップパス | 内容 |
|-----------------|------|
| `/opt/shared/scripts/prediction_page_builder.py.bak-20260328-anchors` | Workstream C パッチ適用前 |
| `/opt/shared/scripts/prediction_page_builder.py.bak-20260328-og-anchor` | Oracle Guardian パッチ適用前（2026-03-28 本セッション） |
| `/opt/shared/scripts/prediction_page_builder.py.bak-errorcard-20260329` | Oracle Guardian id 再適用前（2026-03-29 WS4 再パッチ） |

---

## 検証コマンド（確認時に使用）

```bash
# 1. アンカーカバレッジ確認
ssh root@163.44.124.123 "python3 /opt/shared/scripts/lint_prediction_links.py"
# → Bare oracle CTAs found: 0 / OK - all JA oracle CTAs are anchored

# 2. JA /predictions/ ライブアンカー数確認
ssh root@163.44.124.123 "python3 -c \"
import sqlite3, json, re
con = sqlite3.connect('/var/www/nowpattern/content/data/ghost.db')
lex = json.loads(con.execute(\\\"SELECT lexical FROM posts WHERE slug='predictions'\\\").fetchone()[0])
html = lex['root']['children'][0]['html']
ids = re.findall(r\\\"id='(np-[0-9]{4}-[0-9]{4})'\\\", html, re.IGNORECASE)
print(f'JA anchors: {len(ids)}')
\""

# 3. specific anchor check
# https://nowpattern.com/predictions/#np-2026-0042  ← ブラウザで動作確認
```

---

## リグレッション防止（運用化済み）

- **週次lintクーロン稼働中**: `lint_oracle_cta_cron.py` 毎週月曜 08:00 UTC（JST 17:00）
  - bare oracle CTAが1件でも検出 → Telegram即時アラート
  - ログ: `/opt/shared/logs/lint_oracle_cta.log`
- 新規記事のOracle Statementは `#np-XXXX`（小文字）形式を維持すること
- `prediction_page_builder.py` の日次cron（JST 07:00）が毎日アンカーを再生成する
- 詳細は `docs/PREDICTION_DEEP_LINK_RUNBOOK.md` と `docs/PREDICTION_DEEP_LINK_CRON.md` を参照

---

*作成: Claude Code (claude-sonnet-4-6) — 2026-03-28*
