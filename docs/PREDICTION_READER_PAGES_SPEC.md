# Prediction Platform — Reader-Facing Pages Specification

> Spec for the 6 NEW reader-facing pages to be created (Phase 7).
> These are DIFFERENT from the existing /forecast-rules/, /scoring-guide/, /integrity-audit/ pages.
> Last updated: 2026-03-29

---

## Pages to Create (6 total: 3 JA + 3 EN)

| URL | Ghost slug | Language | Status |
|-----|-----------|----------|--------|
| `/forecasting-methodology/` | `forecasting-methodology` | JA | ⏳ Not created |
| `/en/forecasting-methodology/` | `en-forecasting-methodology` | EN | ⏳ Not created |
| `/forecast-scoring-and-resolution/` | `forecast-scoring-and-resolution` | JA | ⏳ Not created |
| `/en/forecast-scoring-and-resolution/` | `en-forecast-scoring-and-resolution` | EN | ⏳ Not created |
| `/forecast-integrity-and-audit/` | `forecast-integrity-and-audit` | JA | ⏳ Not created |
| `/en/forecast-integrity-and-audit/` | `en-forecast-integrity-and-audit` | EN | ⏳ Not created |

---

## Page Relationship to Existing Pages

These NEW pages are NOT replacements for existing pages:

| Existing page | New page | Difference |
|---------------|----------|------------|
| `/forecast-rules/` | `/forecasting-methodology/` | Rules = "what we do". Methodology = "why and how we do it" |
| `/scoring-guide/` | `/forecast-scoring-and-resolution/` | Guide = reference. Scoring+Resolution = detailed process with examples |
| `/integrity-audit/` | `/forecast-integrity-and-audit/` | Existing = overview. New = technical audit trail with OTS details |

Both sets of pages will coexist. The new pages go deeper and link to the existing ones.

---

## Page Content Specifications

### 1. /forecasting-methodology/ (JA) + /en/forecasting-methodology/ (EN)

**Purpose**: Explain HOW we make predictions — not just what the rules are.

**Sections**:
1. なぜ予測プラットフォームなのか / Why a prediction platform?
2. 予測の5つの条件 / The 5 requirements for a valid prediction
3. 確率の設定方法 / How we set probabilities
4. カテゴリ別の予測手法 / Methodology by category (geopolitics, economics, technology)
5. 予測の改善サイクル / How we improve via EvolutionLoop
6. 外部比較 / Comparison with Superforecasters (Tetlock reference)

**Key content**:
- Link to: PREDICTION_BRIER_SCORE_METHODOLOGY.md (technical details)
- Link to: /predictions/ (see our track record)

### 2. /forecast-scoring-and-resolution/ (JA) + /en/forecast-scoring-and-resolution/ (EN)

**Purpose**: Explain the complete scoring and resolution process with examples.

**Sections**:
1. ブライアスコアとは / What is a Brier Score?
2. 計算式と例 / Formula and worked examples
3. 解決プロセス / Resolution process (from AWAITING_EVIDENCE to RESOLVED)
4. 判定基準 / Resolution criteria (yes/no/void conditions)
5. スコアの精度ティア / Score accuracy tiers (PROVISIONAL, VERIFIED_OFFICIAL, etc.)
6. 暫定スコアの説明 / Why current scores are PROVISIONAL — honest disclosure

**CRITICAL**: Must include the PROVISIONAL tier disclosure prominently:
> "現在のすべての予測スコアは暫定計算値です。ブロックチェーン確認待ちのため。"
> "All current prediction scores are provisional pending blockchain timestamp confirmation."

**Key content**:
- Formula: `BS = (initial_prob/100 - outcome)²`
- Worked examples with real prediction IDs
- Link to: /predictions/ score display
- Link to: /forecast-integrity-and-audit/ for proof details

### 3. /forecast-integrity-and-audit/ (JA) + /en/forecast-integrity-and-audit/ (EN)

**Purpose**: Technical audit trail documentation for sophisticated readers.

**Sections**:
1. 誠実性の誓い / Integrity pledge (we publish all predictions, hits and misses)
2. 改ざん防止の仕組み / Anti-tampering mechanisms
3. initial_prob ロック / initial_prob write-once guarantee
4. OTSタイムスタンプ / OpenTimestamps blockchain anchoring
5. 予測台帳 / Prediction ledger (JSONL append-only)
6. 現在の制限事項 / Current limitations (PROVISIONAL tier explanation)
7. 監査の検証方法 / How readers can independently verify

**CRITICAL**: Must disclose current limitations honestly:
> "現在の予測スコアは、2026年3月29日の後付けバックフィルに基づいています。"

---

## Implementation Requirements

### Ghost Setup (per new page)

1. Create Ghost page with slug as specified above
2. Add `lang-ja` or `lang-en` tag
3. Add `codeinjection_head` with hreflang (JA+EN pairs must be bilateral)
4. Set `canonical_url` to the public URL

### Caddy Config Updates Required

For each EN page, add to `/etc/caddy/Caddyfile`:

```caddy
handle /en/forecasting-methodology/ {
    rewrite * /en-forecasting-methodology/
    reverse_proxy localhost:2368
}
handle /en/forecast-scoring-and-resolution/ {
    rewrite * /en-forecast-scoring-and-resolution/
    reverse_proxy localhost:2368
}
handle /en/forecast-integrity-and-audit/ {
    rewrite * /en-forecast-integrity-and-audit/
    reverse_proxy localhost:2368
}
```

And redirect rules in `/etc/caddy/nowpattern-redirects.txt`:
```
redir /en-forecasting-methodology/ /en/forecasting-methodology/ permanent
redir /en-forecast-scoring-and-resolution/ /en/forecast-scoring-and-resolution/ permanent
redir /en-forecast-integrity-and-audit/ /en/forecast-integrity-and-audit/ permanent
```

### hreflang pairs required

Each JA page must have:
```html
<link rel="alternate" hreflang="ja" href="https://nowpattern.com/[slug]/" />
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/[slug]/" />
<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/[slug]/" />
```

Each EN page must have:
```html
<link rel="canonical" href="https://nowpattern.com/en/[slug]/" />
<link rel="alternate" hreflang="ja" href="https://nowpattern.com/[slug]/" />
<link rel="alternate" hreflang="en" href="https://nowpattern.com/en/[slug]/" />
<link rel="alternate" hreflang="x-default" href="https://nowpattern.com/[slug]/" />
```

---

## Blocking Dependencies

Phase 7 is blocked until Phase 0-5 are complete:
- Phase 1 must complete (question_type, semantic_key fields)
- Phase 3 must complete (PROVISIONAL tier labels ready for display)
- WS5 score display must be done (so reader pages link to honest score display)

**Current status**: Phase 2+3 complete. Phase 1 in progress. Phase 7 = PENDING.

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial spec document. Pages not yet created. |
