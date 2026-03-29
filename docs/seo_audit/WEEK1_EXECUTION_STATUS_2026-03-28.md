# Week 1 SEO Fix Execution Status — 2026-03-28

> Week 1 全REQ完了後のステータスサマリー。次セッションへの引き継ぎ用。

---

## 完了ステータス（Week 1 全件）

| REQ | タイトル | Week 1 ステータス | 検証 |
|-----|---------|-----------------|------|
| REQ-001 | llms.txt: en-predictions/ → en/predictions/ | ✅ DONE (Day 1) | curl 2 matches |
| REQ-003 | prediction_page_builder.py: np-scoreboard/np-resolved IDs | ✅ DONE (Day 1) | curl grep 1 match each |
| REQ-004 | Caddyfile: llms-full.txt file_server handle block | ✅ DONE (Day 1) | HTTP 200 |
| REQ-005 | Caddyfile: gzip/zstd compression | ✅ DONE (Day 1) | content-encoding: gzip |
| REQ-009 | Homepage hreflang | ✅ ALREADY PASSING | hreflang count ≥ 7 |
| REQ-012 | Reader prediction API health | ✅ ALREADY PASSING | health = ok |
| REQ-010 | X DLQ retry_dlq() bug fix + clear | ✅ DONE (Week 1) | DLQ = 0, 4 fixes verified |
| REQ-008 | FAQPage schema on /predictions/ + /en/predictions/ | ✅ DONE (Week 1) | @type=FAQPage confirmed |
| REQ-006/007 | Dataset schema (EN/JA) | ✅ DONE (Week 1) | @type=Dataset confirmed |
| REQ-002 | Ghost portal_plans (Stripe) | 🚫 BLOCKED — do not touch | Stripe未接続 |
| REQ-011 | PARSE_ERROR 根本原因調査 | ⏭ Month 1 | 調査フェーズ必要 |

**Week 1 完了率: 9/9 実施可能項目が完了（BLOCKED 1件 + Month 1 繰越 1件を除く）**

---

## JSON-LD Schema インベントリ（2026-03-28 時点）

### /predictions/ (JA)

| Block | @type | 目的 | 追加時期 |
|-------|-------|------|---------|
| 0 | NewsMediaOrganization | Brand identity | 元々存在 |
| 1 | WebSite | Sitelinks search | 元々存在 |
| 2 | (ClaimReview/Organization) | Credibility | 元々存在 |
| 3 | FAQPage | Google AI Overview | REQ-008 Week 1 |
| 4 | Dataset | Machine-readable DB | REQ-006+007 Week 1 |

codeinjection_head サイズ変遷:
- 初期: 4413 chars
- REQ-008 後: 5524 chars (+1111)
- REQ-006+007 後: 6202 chars (+678)

### /en/predictions/ (EN)

| Block | @type | 目的 | 追加時期 |
|-------|-------|------|---------|
| 0 | Article | Ghost default | 元々存在 |
| 1 | NewsMediaOrganization | Brand identity | 元々存在 |
| 2 | WebSite | Sitelinks search | 元々存在 |
| 3 | (ClaimReview/Organization) | Credibility | 元々存在 |
| 4 | FAQPage | Google AI Overview | REQ-008 Week 1 |
| 5 | Dataset | Machine-readable DB | REQ-006+007 Week 1 |

codeinjection_head サイズ変遷:
- 初期: 4566 chars
- REQ-008 後: 6124 chars (+1558)
- REQ-006+007 後: 6951 chars (+827)

---

## 変更ファイル一覧（Week 1 全件）

| ファイル | ホスト | バックアップ | 変更内容 |
|---------|------|------------|---------|
| `/var/www/nowpattern-static/llms.txt` | VPS | `.bak-20260328` | en-predictions/ → en/predictions/ |
| `/var/www/nowpattern-static/llms-full.txt` | VPS | NEW | 新規作成 |
| `/etc/caddy/Caddyfile` | VPS | `.bak-20260328` | llms-full.txt handle + encode gzip zstd |
| `/opt/shared/scripts/prediction_page_builder.py` | VPS | `.bak-20260328` `.bak-req006-v5` | np-scoreboard/resolved IDs + Dataset functions |
| `/opt/shared/scripts/x_swarm_dispatcher.py` | VPS | (inline patch) | 4 fixes: thread/dry-run/error-propagation/403 |
| `/opt/shared/scripts/x_dlq.json` | VPS | cleared to `[]` | 5 stuck items cleared |
| Ghost `predictions` codeinjection_head | Ghost CMS | — | FAQPage + Dataset schema |
| Ghost `en-predictions` codeinjection_head | Ghost CMS | — | FAQPage + Dataset schema |

---

## PVQE インパクト評価（Week 1 完了後）

| レバー | Week 1 前 | Week 1 後 | 変化 |
|--------|----------|----------|------|
| **P（判断精度）** | △ | △ | 変化なし（コンテンツ品質は既存） |
| **V（改善速度）** | ○ | ○ | 変化なし（ループは稼働中） |
| **Q（行動量）** | ○ | ○ | 変化なし |
| **E（波及力）** | △ | ↑ | REQ-010でX投稿5件→0件DLQ解消、REQ-004+005でAI/LLMクローラーの可視性向上 |

**E（波及力）改善の内訳:**
- DLQ 0件: 詰まっていたX投稿が流通再開
- gzip圧縮: 289KB→50KB。AI/botクローラーの巡回効率向上
- llms-full.txt: LLMクローラーが予測DBにアクセス可能
- Dataset schema: Google Dataset Search / AI Overviewでの認識強化
- FAQPage schema: Google AI Overview掲載確率向上

---

## Month 1 繰越タスク（次の優先順位）

| REQ | 内容 | 優先度 | 理由 |
|-----|------|--------|------|
| REQ-011 | PARSE_ERROR根本原因調査 | HIGH | X投稿の品質に直接影響 |
| REQ-002 | portal_plans (Stripe) | BLOCKED | Stripe接続先決。対応不可 |

### REQ-011 調査方針（引き継ぎ）

```bash
# VPSでのPARSE_ERRORログ確認
ssh root@163.44.124.123 "grep -n 'PARSE_ERROR' /opt/shared/scripts/x_swarm_dispatcher.py | head -20"
ssh root@163.44.124.123 "grep -rn 'PARSE_ERROR' /opt/shared/logs/ | tail -20"
```

PARSE_ERRORの発生パターン:
- x_swarm_dispatcher.py でコンテンツのパースに失敗
- format: RED_TEAM / NATIVE / LINK の特定フォーマットで発生している可能性
- 調査: ログからエラー頻度・フォーマット別分布を確認

---

## 技術的負債メモ（次セッション参考）

### prediction_page_builder.py の broken link check

JA predictions ページに10件のbroken linkが検出されており、builderがJAページの`update_ghost_page`を実行できない状態。

```
# 確認コマンド（VPS）
python3 -c "
import sys
sys.path.insert(0, '/opt/shared/scripts')
# prediction_page_builder.py --dry-run で broken link 一覧を確認
"
```

**影響**: `_update_dataset_in_head` は現在 `req006_direct.py` で直接適用済み。builderが動いてもDatasetは上書き（再適用）されるので問題なし。ただし broken linkそのものは修正すべき。

### Dataset schema の stats 自動更新

現在の `prediction_page_builder.py` では `_update_dataset_in_head` がbuilder実行時に毎回最新statsで更新される仕組みになっている（`pred_db.get("stats", {})`を渡す）。builderが正常動作すれば自動更新される。

---

*作成: 2026-03-28 Week 1完了後 | Engineer: Claude Code (local)*
