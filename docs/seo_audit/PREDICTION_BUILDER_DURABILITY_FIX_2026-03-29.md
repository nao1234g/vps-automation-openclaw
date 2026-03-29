# prediction_page_builder.py 耐久性確認 — 2026-03-29

> Phase 3: cron 再実行後もFAQPage+Dataset が保持されるか確認

---

## 確認サマリー

| 項目 | 状態 |
|------|------|
| FAQPage in `/predictions/` | **✅ 存在（count=1）** |
| FAQPage in `/en/predictions/` | **✅ 存在（count=1）** |
| Dataset in `/predictions/` | **✅ 存在（count=1）** |
| Dataset in `/en/predictions/` | **✅ 存在（count=1）** |
| `_update_dataset_in_head()` の greedy regex bug | **✅ 修正済み（block-aware実装）** |
| cron再実行後の FAQPage 消失 | **✅ 発生しない（block-aware fixが機能中）** |

---

## 前回セッションとの差異

### 前回セッション（2026-03-28 FINAL_HANDOFF）の記録

> 「BUILDER BUG FIX: `_update_dataset_in_head()` regex: greedy→block-aware。FAQPageが毎cron消えるバグを修正（2026-03-29）」
> バックアップ: `.bak-20260328-faq`

前回セッションでこのバグが修正されたと記録されていたが、今セッションで実際のコードを確認し、**修正が正しく適用されていること**を検証した。

### 今セッションの確認結果

`_update_dataset_in_head()` の実装（line 2940-2954付近）:

```python
# block-aware implementation（修正後）
_ld_blocks = list(_re.finditer(
    r'<script[^>]*application/ld\+json[^>]*>[\s\S]*?</script>',
    head, _re.IGNORECASE,
))
head_clean = head
for _m in reversed(_ld_blocks):
    if '"Dataset"' in _m.group():
        head_clean = head_clean[:_m.start()] + head_clean[_m.end():]
head_clean = head_clean.strip()
```

**旧実装（greedy regex）との比較:**

```python
# OLD（破壊的）: FAQPage開始タグから Dataset 終了タグまで丸ごと削除
head_clean = _re.sub(
    r'<script[^>]*application/ld[+]json[^>]*>[\s\S]*?"@type"\s*:\s*"Dataset"[\s\S]*?</script>',
    "", head, flags=_re.IGNORECASE,
).strip()

# NEW（block-aware）: Dataset ブロックのみ削除、FAQPage は保持
```

**結論**: block-aware 実装が正しく適用されており、cron 再実行でも FAQPage は消えない。

---

## Live 検証

```bash
curl -s https://nowpattern.com/predictions/ | grep -c 'FAQPage'
# → 1

curl -s https://nowpattern.com/en/predictions/ | grep -c 'FAQPage'
# → 1

curl -s https://nowpattern.com/predictions/ | grep -c 'Dataset'
# → 1

curl -s https://nowpattern.com/en/predictions/ | grep -c 'Dataset'
# → 1
```

**4/4 PASS** ✅

---

## codeinjection_head 現状

| Page | ci_len | hreflang | FAQPage | Dataset |
|------|--------|----------|---------|---------|
| JA `/predictions/` | ~2079 chars | ✅ | ✅ (4 Q&As) | ✅ (12 fields) |
| EN `/en/predictions/` | ~2699 chars | ✅ | ✅ (4 Q&As) | ✅ (12 fields) |

---

## cron 定義確認

```bash
crontab -l | grep prediction_page_builder
# → 0 22 * * * python3 /opt/shared/scripts/prediction_page_builder.py --force --update >> /opt/shared/polymarket/prediction_page.log 2>&1
# JST 07:00 毎日実行
```

---

## Phase 3 ステータス: DONE（追加アクション不要）

- builder 耐久性: 確認済み ✅
- FAQPage / Dataset: 両ページで保持確認済み ✅
- 追加修正: 不要

---

*作成: 2026-03-29 Phase 3 確認 | Engineer: Claude Code (local)*
