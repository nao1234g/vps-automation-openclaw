# MVP_CHECKLIST.md — 実装チェックリスト

> 作成: 2026-03-29 | ステータス: READY TO EXECUTE
> 原則: 今日できる低リスク作業の先送り禁止

---

## WEEK 1 — 最小参加体験の改善（今すぐやる）

### ✅ DB Migration (リスク: 最低 / 可逆: YES)
- [ ] VPS: `ALTER TABLE reader_votes ADD COLUMN explanation TEXT;`
  - ファイル: `/opt/shared/reader_predictions.db`
  - 非破壊的 additive change。既存データに影響なし
  - 確認: `sqlite3 /opt/shared/reader_predictions.db ".schema reader_votes"`

### ✅ API Update (リスク: 低 / 可逆: YES)
- [ ] `VoteRequest` に `explanation: Optional[str] = None` 追加
  - ファイル: `/opt/shared/scripts/reader_prediction_api.py`
  - max 200文字バリデーション追加
- [ ] `POST /reader-predict/vote` ハンドラで explanation を DB に保存
- [ ] 新規エンドポイント: `PATCH /reader-predict/vote/{prediction_id}/{voter_uuid}/explanation`
  - 投票後に説明を追加・更新できる（後から補足可能）
- [ ] 確認: `curl -X POST http://localhost:8766/reader-predict/vote -d '{"prediction_id":"NP-2026-0001","voter_uuid":"test","scenario":"base","probability":60,"explanation":"テスト"}' -H 'Content-Type: application/json'`

### ✅ Feature Flags (リスク: 最低 / 可逆: YES)
- [ ] `prediction_page_builder.py` に FEATURE_FLAGS dict 追加
  ```python
  FEATURE_FLAGS = {
      "COUNTER_FORECAST_UI": False,
      "LEADERBOARD_PAGE": False,
      "NAMED_PROFILES": False,
      "RESOLUTION_NOTIFICATIONS": False,
  }
  ```
  - ファイル: `/opt/shared/scripts/prediction_page_builder.py`
  - 現時点では全フラグ False（UIを触らない）

---

## WEEK 2 — 参加 CTA 強化

### ✅ Leaderboard ページ作成 (リスク: 低)
- [ ] Ghost CMS に `/leaderboard/` ページを新規作成
  - スラッグ: `leaderboard`
  - EN版: スラッグ `en-leaderboard`, Caddy `/en/leaderboard/` リワイト
  - Static HTML + JS で `GET /reader-predict/top-forecasters` を表示
  - "AI vs あなた" のスコアボード + Brier Index 表示
  - hreflang 双方向リンク設置
- [ ] Caddy ルール追加:
  ```
  handle /en/leaderboard/ {
      rewrite * /en-leaderboard/
      reverse_proxy localhost:2368
  }
  ```

### ✅ Brier Index 表示切り替え (リスク: 低)
- [ ] `/predictions/` の公開スコア表示を raw Brier → Brier Index (1-√Brier)×100% に変更
  - 計算: `round((1 - math.sqrt(brier)) * 100, 1)`
  - 表示例: 「精度スコア: 57.3%」（内部では Brier 0.1828）

### ✅ X 週次投稿設定 (リスク: 低)
- [ ] 毎週月曜 cron: leaderboard 結果 + "今週のNo.1 Forecaster" を X 投稿
  - 既存 `x-auto-post.py` または新規スクリプト
  - 内容: Brier Index top 1 + AI vs 人間の対決スコア

---

## MONTH 2 — アカウント基盤（Phase 1.5）

### ✅ Ghost Members Bridge
- [ ] `POST /reader-predict/register-name` エンドポイント実装
  - Input: `voter_uuid, display_name, email`
  - Action: Ghost Members API で free tier メンバー作成 + reader_votes.voter_display_name 更新
- [ ] `/forecaster/{voter_uuid}` 個人ページ実装
  - 投票履歴、Brier Index 推移グラフ、取得バッジ
- [ ] 解決時メール通知
  - prediction_auto_verifier.py 解決時 → 投票者リストへメール送信

---

## 絶対にやらないこと（スコープ外）

- ❌ ユーザー生成予測（モデレーション問題）
- ❌ リアルマネートーナメント（法的整理必要）
- ❌ コメント欄（対抗予想型で代替）
- ❌ 外部ソーシャルログイン（Ghost Members で十分）
- ❌ 既存 prediction_page_builder.py の HTML クラス/ID 変更（凍結ベースライン）

---

## 検証コマンド（各タスク完了後に実行）

```bash
# DB migration 確認
ssh root@163.44.124.123 "sqlite3 /opt/shared/reader_predictions.db '.schema reader_votes'"

# API ヘルスチェック
ssh root@163.44.124.123 "curl -s http://localhost:8766/reader-predict/health | python3 -m json.tool"

# API テスト投票（explanation 付き）
ssh root@163.44.124.123 "curl -s -X POST http://localhost:8766/reader-predict/vote \
  -H 'Content-Type: application/json' \
  -d '{\"prediction_id\":\"NP-2026-0001\",\"voter_uuid\":\"test-explanation\",\"scenario\":\"base\",\"probability\":60,\"explanation\":\"テスト説明文\"}'
"

# prediction_page_builder.py feature flags 確認
ssh root@163.44.124.123 "grep -n 'FEATURE_FLAGS' /opt/shared/scripts/prediction_page_builder.py"
```
