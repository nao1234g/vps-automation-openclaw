# NOWPATTERN REPRIORITIZED TODO — 2026-03-28
> Round 3 実装完了後の残タスク再優先順位付け
> PVQE-E（波及力）ボトルネックを最優先に置いた再整列
> ベース: OPERATING_PRINCIPLES.md 正典（PVQE定義）+ ALIGNMENT_AUDIT_2026-03-28.md 結果

---

## PVQE 優先原則（再確認）

```
OPERATING_PRINCIPLES.md 原文:
「今最もROIが高い投資は E（波及力）の強化。
 配信チャネルの拡充（X、newsletter）が最優先。」

E = 波及力 = 成果が社会へ広がる倍率
E ボトルネックを解除しない限り、P・V・Q の改善は波及しない。
```

---

## STATUS: Round 3 完了分（タッチ不要）

| REQ | 内容 | 状態 |
|-----|------|------|
| REQ-001 | llms.txt EN URL 修正 | ✅ DONE（2026-03-28） |
| REQ-003 | np-scoreboard / np-resolved ID 追加 | ✅ DONE（2026-03-28） |
| REQ-004 | llms-full.txt 404 解消 | ✅ DONE（2026-03-28） |
| REQ-005 | gzip 圧縮有効化 | ✅ DONE（2026-03-28） |
| REQ-009 | ホームページ hreflang | ✅ ALREADY PASSING |
| REQ-012 | 読者投票 API 疎通 | ✅ ALREADY PASSING |

---

## 残タスク（PVQE-E 優先順で再整列）

### 🔴 PRIORITY 1 — E 直結（次セッション最優先）

#### REQ-010: X DLQ 82件解消

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-010 |
| **PVQE 貢献** | **E（波及力）直接** — X からの流入 = E そのもの |
| **PVQE 理由** | DLQ 82件は「E が 0 に近い状態」。X 投稿 82件が届いていない = 波及力がゼロ |
| **ROI（FIX_PRIORITY）** | 7（ビジネスインパクト 4 + 修正コスト 3） |
| **ROI（PVQE-E補正）** | **実質 9** — E が最大ボトルネックのため E 直結は倍率補正 |
| **current_state** | x_dlq.json: 82件（`error:true` 79件 + `error:429` 3件）※FIX_PRIORITY の「403 エラー」は実態と不一致 |
| **why_now** | OPERATING_PRINCIPLES.md が E を最大ボトルネックと明示。X 流入回復が最優先。 |
| **effort** | 調査込みで 30〜60分 |
| **reversible** | ✅ DLQ を drain するか retry するだけ |
| **blast_radius** | 小（X 投稿のみ。本番 DB・Ghost に影響なし） |
| **confidence** | Medium（error 原因が error:true で不明確。まず調査） |

**最初の確認コマンド:**
```bash
ssh root@163.44.124.123 "python3 -c \"import json; d=json.load(open('/opt/shared/scripts/x_dlq.json')); [print(i, x.get('format'), x.get('error'), str(x.get('content',''))[:60]) for i,x in enumerate(d[:5])]\""
```

**完了定義:** x_dlq.json が 0件、または 429 の 3件のみに減少。

---

### 🟡 PRIORITY 2 — スキーマ/AI認知（Week 1）

#### REQ-008: FAQPage schema (/predictions/ + /en/predictions/)

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-008 |
| **PVQE 貢献** | E間接（Google AI Overview 掲載率 +40〜60%） |
| **ROI** | 8 |
| **why_now** | FAQPage schema = 実装コスト最小でAI Overview 掲載率を大きく上げる。WORLD_BENCHMARK_2026-03-28.md 確認済み（FAQ +60% AIO効果）。 |
| **effort** | 30分（Ghost Admin でcodeinjection_head更新） |
| **reversible** | ✅ Ghost Admin から削除するだけ |
| **blast_radius** | 最小（codeinjection_head変更のみ） |
| **confidence** | High |

**FAQ内容案（JA版 /predictions/):**
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {"@type": "Question", "name": "Brier Scoreとは？",
     "acceptedAnswer": {"@type": "Answer", "text": "予測精度を測る指標。0=完全予測、1=最悪。現在0.18（GOOD）。"}},
    {"@type": "Question", "name": "予測に参加するには？",
     "acceptedAnswer": {"@type": "Answer", "text": "登録不要。各予測カードの投票ウィジェットで参加できます。"}},
    {"@type": "Question", "name": "予測の的中・外れはどう判定する？",
     "acceptedAnswer": {"@type": "Answer", "text": "prediction_auto_verifier.py が自動検証。判定後にBrier Scoreが更新されます。"}}
  ]
}
```

---

#### REQ-006 + REQ-007: Dataset schema (EN + JA)

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-006, REQ-007 |
| **PVQE 貢献** | E間接（Google Dataset Search / AI Overview での認識強化） |
| **ROI** | 7〜8 |
| **why_now** | prediction_page_builder.py の修正 + 再生成で両ページ同時対応。モートを「データセット」として公式登録。 |
| **effort** | 60分（prediction_page_builder.py修正 + ページ再生成 + 検証） |
| **reversible** | ✅ バックアップから戻せる |
| **blast_radius** | 中（ページ再生成が必要。E2Eテスト必須） |
| **confidence** | High（JSON-LD テンプレートは FIX_PRIORITY に記載済み） |

---

### 🔵 PRIORITY 3 — Month 1

#### REQ-011: PARSE_ERROR 根本原因調査

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-011 |
| **PVQE 貢献** | V間接（構造化データ品質改善） |
| **ROI** | 5 |
| **why_now** | 調査フェーズが必要。Month 1 で十分。 |
| **confidence** | Low（調査前は原因不明） |

---

### 🚫 BLOCKED（実施不可）

#### REQ-002: portal_plans / Stripe

| フィールド | 内容 |
|-----------|------|
| **req_id** | REQ-002 |
| **ブロッカー** | Stripe 未接続。前提条件: Stripe アカウント設定 → Ghost Admin Stripe連携 → portal_plans更新 |
| **解除条件** | Naoto が Stripe を接続済みであることを確認してから |

---

## 推奨実施シーケンス（次セッション）

```
[次セッション冒頭 — 5分]
VPS状態確認: ssh root@163.44.124.123 "cat /opt/shared/SHARED_STATE.md"
DLQ件数確認: ssh root@163.44.124.123 "python3 -c ..."

[ステップ 1 — 30〜60分]
REQ-010: X DLQ 82件解消 → Eを0から正の値へ

[ステップ 2 — 30分]
REQ-008: FAQPage schema → Google AI Overview 掲載率向上

[ステップ 3 — 60分]
REQ-006+007: Dataset schema → prediction_page_builder.py 修正

[Month 1]
REQ-011: PARSE_ERROR 調査
ISS-012/014/015: about/taxonomy WebPage schema 修正、WebSite重複削除、robots.txt AI許可
```

---

## 7軸 実装準備度スコア（次セッション着手前チェック）

| REQ | impact | effort | confidence | reversible | blast | readiness | 実施可否 |
|-----|--------|--------|------------|------------|-------|-----------|---------|
| REQ-010 | 4 | 3 | Medium | ✅ | 小 | Medium | ✅ 実施可（調査から） |
| REQ-008 | 5 | 5 | High | ✅ | 最小 | High | ✅ 即実施可 |
| REQ-006+007 | 4 | 3 | High | ✅ | 中 | High | ✅ 実施可（E2Eテスト必須） |
| REQ-002 | 5 | 3 | — | ✅ | 大 | ❌ BLOCKED | Stripe接続後 |
| REQ-011 | 3 | 2 | Low | ✅ | 小 | Low | Month 1 |

---

*作成: 2026-03-28 | ALIGNMENT_AUDIT の結論を受けて再優先順位付け*
*PVQE-E: E（波及力）最大ボトルネック → REQ-010（X DLQ）が次セッション最優先*
