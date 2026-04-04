# Prediction Public Pages — Copy Reference (JA/EN)

> Canonical copy for the 6 reader-facing prediction platform pages.
> These pages are live on nowpattern.com as of 2026-03-29.
> Last updated: 2026-03-29

> Historical note (2026-04-04): this file covers the legacy fixed pages
> `/forecast-rules/`, `/scoring-guide/`, and `/integrity-audit/`.
> The newer reader-facing methodology set
> `/forecasting-methodology/`,
> `/forecast-scoring-and-resolution/`,
> `/forecast-integrity-and-audit/`
> is now tracked separately in
> [`docs/PREDICTION_READER_PAGES_SPEC.md`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/docs/PREDICTION_READER_PAGES_SPEC.md)
> and the source-controlled updater
> [`scripts/update_prediction_methodology_pages.py`](/mnt/c/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/scripts/update_prediction_methodology_pages.py).

---

## Page Inventory

| Slug (JA) | Slug (EN) | Ghost Page ID (JA) | Ghost Page ID (EN) |
|-----------|-----------|-------------------|-------------------|
| `/forecast-rules/` | `/en/forecast-rules/` | 69c87e8e2c3f3511b9f2e827 | 69c87e922c3f3511b9f2e831 |
| `/scoring-guide/` | `/en/scoring-guide/` | 69c87e922c3f3511b9f2e837 | 69c87e932c3f3511b9f2e83d |
| `/integrity-audit/` | `/en/integrity-audit/` | 69c87e932c3f3511b9f2e843 | 69c87e932c3f3511b9f2e849 |

### Alias Redirects (Caddy 301)

| New Slug → | Canonical Slug |
|-----------|---------------|
| `/forecasting-methodology/` | `/forecast-rules/` |
| `/en/forecasting-methodology/` | `/en/forecast-rules/` |
| `/forecast-scoring-and-resolution/` | `/scoring-guide/` |
| `/en/forecast-scoring-and-resolution/` | `/en/scoring-guide/` |
| `/forecast-integrity-and-audit/` | `/integrity-audit/` |
| `/en/forecast-integrity-and-audit/` | `/en/integrity-audit/` |

---

## Page 1: 予測ルール / Forecast Rules

### JA: /forecast-rules/
**Title**: 予測ルール — Nowpatternの予測はこう作られる

**Key content**:
- Nowpatternの予測について（力学分析 + 検証可能な予測）
- 予測の構造（判定質問 / 確率 / 的中条件 / オラクル期限 / Polymarket）
- 確率の意味（キャリブレーション志向）
- 後継予測について
- 暫定スコアについての注意（⚠️ PROVISIONAL disclaimer）
- 予測の状態一覧（OPEN / RESOLVING / HIT / MISS / EXPIRED_UNRESOLVED / NOT_SCORED）

**PROVISIONAL notice required**: YES — displayed as gray left-border box

### EN: /en/forecast-rules/
**Title**: Forecast Rules — How Nowpattern Makes Predictions

**Key content** (mirrors JA):
- About Nowpattern Predictions
- Prediction Structure (resolution question / probability / hit condition / oracle deadline / Polymarket)
- What the Probability Means (calibration)
- Successor Predictions
- Note on Provisional Scores (⚠️ PROVISIONAL disclaimer)
- Prediction Statuses

---

## Page 2: スコアリングガイド / Scoring Guide

### JA: /scoring-guide/
**Title**: スコアリングガイド — ブライアースコアと予測精度の測り方

**Key content**:
- ブライアースコアとは（0〜1、低いほど優秀）
- 計算式: `BS = (確率/100 - 結果)²` with examples
- スコア階層テーブル (EXCELLENT/GOOD/FAIR/WEAK/POOR with color coding)
- 現在のNowpatternスコア（黒背景4列グリッド: 1116件 / 的中35 / 外れ18 / 72.9%）
- 平均Brier Score: 0.47 ※暫定
- 解決プロセス（5ステップ）
- 未解決の予測（EXPIRED_UNRESOLVED説明）

**Statistics as of 2026-03-29**:
- Total: 1116 predictions
- Hits: 35
- Misses: 18
- Accuracy: 72.9%
- Avg Brier (provisional): 0.47

### EN: /en/scoring-guide/
**Title**: Scoring Guide — Brier Score and Prediction Accuracy

**Key content** (mirrors JA in English):
- What is the Brier Score?
- Formula: `BS = (probability/100 - outcome)²`
- Score Tiers table
- Current Nowpattern Score (same statistics)
- Resolution Process
- Unresolved Predictions

---

## Page 3: 整合性・監査 / Integrity & Audit

### JA: /integrity-audit/
**Title**: 整合性・監査 — 予測記録はなぜ改ざんできないのか

**Key content**:
- 誠実な予測の4条件（事前記録 / 完全公開 / 自動検証 / 数値化）
- 改ざん耐性の仕組み:
  - SHA-256マニフェスト（prediction_manifest.json）
  - 追記専用レジャー（prediction_ledger.jsonl — 1,172エントリ）
  - OTSタイムスタンプ（実装中 — timestamp_pending=True）
- スコアティアとロードマップ（4行テーブル）
- なぜ「暫定」なのか（説明テキスト）

**Score tier table**:
| Tier | Count | Condition | Status |
|------|-------|-----------|--------|
| PROVISIONAL | 1111 | 遡及的に記録 | ✅ 現在の標準 |
| MIGRATED_OFFICIAL | 0 | OTS確認済み | 🔄 実装中 |
| VERIFIED_OFFICIAL | 0 | 公開前ハッシュ+OTS | 📋 2026-03-29以降 |
| NOT_SCORABLE | 4 | 解決不可能 | — |

### EN: /en/integrity-audit/
**Title**: Integrity & Audit — Why Prediction Records Cannot Be Altered

**Key content** (mirrors JA in English):
- Four Conditions for Honest Forecasting
- Tamper-Resistance Mechanisms (SHA-256 / ledger / OTS)
- Score Tiers and Roadmap (same 4-row table in English)
- Why "Provisional"? (explanation)

---

## Maintenance Notes

### When to update these pages

| Trigger | Update |
|---------|--------|
| Prediction count changes significantly | Update counts in /scoring-guide/ and /en/scoring-guide/ |
| OTS timestamps confirmed | Update /integrity-audit/ tier table (PROVISIONAL → MIGRATED_OFFICIAL count) |
| New predictions use VERIFIED_OFFICIAL | Update /integrity-audit/ + /en/integrity-audit/ tier table |
| Brier Score moves significantly | Update avg Brier display in /scoring-guide/ |

### Update command

```bash
# Re-run Phase 7 script after updating CONTENT_MAP counts
python3 /tmp/phase7_update_pages.py
```

The script at `/tmp/phase7_update_pages.py` (VPS) or `C:/Users/user/AppData/Local/Temp/phase7_update_pages.py` (local) uses Ghost Admin API to update the pages directly.

---

## Deployment History

| Date | Action |
|------|--------|
| 2026-03-29 (Phase 7, session 1) | 6 pages created as empty shells by phase7_public_rules_pages.py |
| 2026-03-29 (Phase 7, session 2) | 6 pages updated with PROVISIONAL-aware content by phase7_update_pages.py |
| 2026-03-29 | Caddy 301 redirects added for 6 alias slugs |

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial document. All 6 pages live with content, 6 Caddy alias redirects active. |
