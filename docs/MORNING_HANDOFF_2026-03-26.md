# Morning Handoff — 2026-03-26（Night Mode 完走版）

> セッション: LEFT_EXECUTOR session_20260326_0509
> 作成: 2026-03-26 05:09 JST
> 執行者: claude-sonnet-4-6 (local Claude Code)

---

## 📊 おはようございます。昨夜の作業を報告します。

### ✅ 一番大事なこと（3行）

1. **1,331記事が published 済み**（JA:211 + EN:1,104）。昨日朝の803から+528増。
2. **Lang bug（全EN記事がlang-jaタグ取得）の根本原因を確認・修正済み**。今後の新規記事は正しく動作する。
3. **Prediction DB が 1,006件**（+24増）。Brier 0.1776、的中率 75.7%。

---

## 📈 KPI（2026-03-26 05:09 確認）

| 指標 | 値 | 前日比 |
|------|----|--------|
| Published 記事 | **1,331** | +528 |
| JA published | 211 | +9 |
| EN published | 1,104 | +519 |
| Draft 残り | **17** | -520 |
| Prediction DB | **1,006** | +24 |
| Resolved predictions | 41 | +4 |
| Avg Brier Score | 0.1776 | — |
| Hit rate | 75.7% | — |

---

## 🔧 昨夜実施した修正

### Lang Bug 根本修正（最重要）
- **原因**: `publish_deep_pattern()` → `post_to_ghost()` に `language` パラメータ未渡し → 全記事デフォルト `"ja"`
- **修正**: `language=_pub_lang` を明示追加（`nowpattern_publisher.py`、18:40）
- **救済**: `draft_rescue.py` で 429件修正済み
- **現在**: `draft:17`（うち8件は品質チェック失敗の正常 draft）

### Batch Publish 完走
- 22:09〜22:34 の25分で全 EN/JA draft を一括 publish
- エラー: 実質 0件

### Nao Intelligence Phase 1
- `polymarket_sync.py` 作成 + cron 21:30 UTC 登録
- `category_brier_analysis.py` 作成 + `evolution_loop.py` 統合
- `observer_log/` インフラ構築（observer_writer + archiver）

---

## ✅ 追加実装完了（継続セッションで実施）

### FileLock + Ghost Webhook 改ざん検知 — 全 PASS

**実施日時**: 2026-03-26 朝（このセッション）

#### 何を防げるか

| リスク | 対策 | 効果 |
|--------|------|------|
| `prediction_page_builder.py` が cron 重複起動し、Ghost ページを壊す | **fcntl 排他ロック** (stale PID 検出付き) | 2つ目のプロセスは `[SKIP] already running` で即終了 |
| Ghost Admin から `/predictions/` を誰かが予期せず編集 | **Ghost Page Guardian v2.0** (port 8765) | 編集イベントを検知 → 5秒以内に Telegram 通知 |
| 改ざんが HMAC 未検証で通る | **HMAC-SHA256 署名検証** (body-only) | 署名なし・不正署名は 403 で拒否 |
| 古いリクエストのリプレイ攻撃 | **タイムスタンプ + ID キャッシュ** (±5分) | 5分以上古い webhook を 403 で拒否 |
| `prediction_page_builder.py` が無変更ページを上書き | **コンテンツハッシュ比較** (SHA-256) | 内容が同じなら PUT をスキップ |

#### テスト結果
```
FileLock (3/3 PASS):
  [PASS] T1: Stale PID detection → expect LOCK acquired
  [PASS] T2: Stale age detection → expect LOCK acquired
  [PASS] T3: Live lock rejection → expect SKIP

Ghost Webhook (6/6 PASS):
  [PASS] T1: No signature → 403
  [PASS] T2: Valid sig, non-protected slug → 200
  [PASS] T3: Valid sig, predictions slug → 200+alert
  [PASS] T4: Replay same ID → 200 skip
  [PASS] T5: Wrong HMAC → 403
  [PASS] T6: Old timestamp (10min) → 403
```

#### 変更ファイル一覧
- `/opt/shared/scripts/prediction_page_builder.py` — BLOCK G-1 v2.0（stale lock 検出付き）
- `/opt/shared/scripts/ghost_page_guardian.py` — v2.0 新規作成
- `/etc/systemd/system/ghost-page-guardian.service` — systemd 登録・稼働中
- Ghost SQLite `webhooks` テーブル — 2件追加（page.published + page.published.edited）
- `/opt/shared/state/guardian_webhook_secret.txt` — chmod 600

---

## ⚠️ 朝の判断事項

---

### [任意] 8件の lang-en draft 確認

品質チェック失敗（oracle_question 空や必須セクション欠落）で draft に降格した記事。
内容確認して必要なら再生成:
```bash
ssh root@163.44.124.123 "python3 /opt/shared/scripts/nowpattern-deep-pattern-generate.py --regen <slug> --lang en"
```

対象スラッグ（品質失敗）:
- `taiwan-drone-incursions-...`
- `gpt-6-and-the-reasoning-...`
- `us-stablecoin-crackdown-...`
- `house-gop-vs-white-house-...`
- `moldovas-energy-emergency-...`
- `steinmeiers-rebuke-...`
- `dhs-shutdown-standoff-...`
- `south-china-sea-near-collision-...`

---

### [低優先] Polymarket 連携拡充

現在 3件のみ。`polymarket_sync.py` の日次 cron が自動で増やします（急がなくてOK）。

---

## 📁 関連ファイル

- 詳細ログ: [reports/night_mode/session_20260326_0509.md](../reports/night_mode/session_20260326_0509.md)
- JSON: [reports/night_mode/session_20260326_0509.json](../reports/night_mode/session_20260326_0509.json)

---

## ✅ 追加実装完了（SEO監査セッション — 09:xx JST）

### SEO 監査 + 修正（3件完了）

| 修正 | 詳細 | 検証 |
|------|------|------|
| **Fix 1**: `/tag/genre-*` noindex 化 | Caddyfile Guard 1 拡張 | `X-Robots-Tag: noindex, follow` ✅ |
| **Fix 2**: 全記事 hreflang 一括注入 | `a4-hreflang-injector.py --lang=all` | **1326/1342 記事完了**（エラー: 0） |
| **Fix 3**: ホームページ hreflang | Caddy `handle /` / `handle /en/` ブロック | `Link: ... hreflang=ja ...` ✅ |

**hreflang 注入の内訳**:
- JA-EN ペアリング済み: 約617記事
- EN ソロ（JA対訳なし）: 約494記事
- `__GHOST_URL__` プレースホルダー使用でドメインハードコードなし

### SEO 監査ドキュメント（7件作成 → `docs/seo_audit/`）

| ファイル | 内容 |
|----------|------|
| `implemented_low_risk_fixes.md` | 3修正の詳細記録 |
| `indexing_crawl_diagnosis.md` | クロールバジェット診断 |
| `hreflang_architecture.md` | 3層 hreflang 設計書 |
| `quality_and_trust_risk_map.md` | P0〜P4 リスクマトリクス |
| `search_console_current_state_report.md` | GSC 確認ガイド |
| `template_level_prevention_plan.md` | 再発防止策・SEO ゲート提案 |
| `final_priority_recommendations.md` | 優先度別推奨アクション |

### Naoto が今日確認すべきこと

1. **xmrig 除去確認（P0）**: `ps aux | grep xmrig` — なければ安全
2. **Google Safe Browsing 確認**: `https://transparencyreport.google.com/safe-browsing/search?url=nowpattern.com`
3. **GSC 国際ターゲティング**: hreflang エラー数確認（1〜2週間後に反映）

詳細: [docs/seo_audit/final_priority_recommendations.md](seo_audit/final_priority_recommendations.md)

---

*LEFT_EXECUTOR Night Mode — 2026-03-26 05:09 JST*
*SEO Audit Session — 2026-03-26 09:xx JST*
