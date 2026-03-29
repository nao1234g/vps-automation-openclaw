# Blocked Items — 2026-03-28

Items that could NOT be implemented this session and why.

---

## REQ-002: portal_plans に monthly/yearly を追加する

| フィールド | 内容 |
|-----------|------|
| **状態** | 🚫 BLOCKED |
| **ROI スコア** | 8（ビジネスインパクト最大級） |
| **ブロッカー** | Stripe 未接続。portal_plans に paid プランを追加しても、Stripe 接続なしでは実際の課金フローが動かない |
| **必要な前提条件** | (1) Stripe アカウント設定、(2) Ghost Admin → Settings → Stripe 連携、(3) その後に portal_plans 更新 |
| **SQLite コマンド（Stripe接続後）** | `sqlite3 /var/www/nowpattern/content/data/ghost.db "UPDATE settings SET value='{\"plans\":[\"free\",\"monthly\",\"yearly\"]}' WHERE key='portal_plans';"` + Ghost再起動 |
| **現在の値** | `portal_plans: ["free"]` |
| **解決後の効果** | Phase 2 有料転換（$9〜19/月 個人トラックレコード）が実現可能になる |

---

## REQ-010: X DLQ エラーの解消

| フィールド | 内容 |
|-----------|------|
| **状態** | ⚠️ 未着手（Week 1 実施予定） |
| **ROI スコア** | 7（E波及力への直接影響） |
| **現在の状態** | DLQ に 82件滞留: `error:true` 79件 + `error:429` 3件 |
| **注意** | 監査ドキュメントには「403エラー79件」と記載されていたが、実測値は `error:true`（エラーコード不明）79件 + `error:429` 3件 |
| **調査コマンド** | `ssh root@163.44.124.123 "python3 /opt/shared/scripts/x_swarm_dispatcher.py --dry-run"` または DLQ内容の詳細確認 |
| **PVQE影響** | E（波及力）がボトルネック（OPERATING_PRINCIPLES.md 診断）。X配信回復は最優先 |
| **解決後の効果** | X からの流入回復（82件の予測/記事投稿が実際に届く） |

---

## REQ-011: PARSE_ERROR スキーマの根本原因調査

| フィールド | 内容 |
|-----------|------|
| **状態** | ⏭ Month 1 実施予定 |
| **ROI スコア** | 5 |
| **理由** | 原因調査（Ghost自動生成 vs codeinjection_head 手動追加の切り分け）が必要。調査なしに修正不可 |

---

*作成: 2026-03-28 | 参照: NOWPATTERN_FIX_PRIORITY_2026-03-28.md*
