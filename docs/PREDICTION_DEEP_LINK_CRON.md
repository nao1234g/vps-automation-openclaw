# Prediction Deep Link — Cron スケジュール

> 作成日: 2026-03-28
> VPS: 163.44.124.123

---

## 稼働中の Cron エントリ

### 1. Oracle CTA 週次 lint（regression guard）

```cron
0 8 * * 1 /usr/bin/python3 /opt/shared/scripts/lint_oracle_cta_cron.py >> /opt/shared/logs/lint_oracle_cta.log 2>&1
```

| 項目 | 値 |
|------|----|
| スケジュール | 毎週月曜日 08:00 UTC（JST 17:00） |
| スクリプト | `/opt/shared/scripts/lint_oracle_cta_cron.py` |
| ログ | `/opt/shared/logs/lint_oracle_cta.log` |
| 成功時 | ログのみ。Telegram通知なし（サイレント） |
| 失敗時（bare CTA検出） | Telegram アラート送信 + exit 1 |

**アラート内容（失敗時）:**
```
⚠️ [REGRESSION] Oracle CTA 未アンカーリンク検出

時刻: YYYY-MM-DD HH:MM UTC
<lint出力抜粋>
修正: python3 /opt/shared/scripts/migrate_prediction_links.py
```

---

### 2. /predictions/ ページ日次ビルド（既存cron）

```cron
# ← VPS既存のcrontabにある（prediction_page_builder.py）
# 毎日 JST 07:00 に実行
```

| 項目 | 値 |
|------|----|
| スケジュール | 毎日 JST 07:00（前後する場合あり） |
| スクリプト | `/opt/shared/scripts/prediction_page_builder.py --lang ja` |
| 効果 | prediction_db.json の最新内容でアンカーID付きHTMLを再生成 |

**重要:** このcronが毎日実行されるため、`prediction_page_builder.py` のコードが正しければ
アンカーは毎日再生成される。Oracle Guardian パッチが適用済みであれば、アンカーは維持される。

---

## ログ確認コマンド

```bash
# lint ログの最新エントリを確認
ssh root@163.44.124.123 "tail -30 /opt/shared/logs/lint_oracle_cta.log"

# lintを手動で今すぐ実行（クーロン確認用）
ssh root@163.44.124.123 "python3 /opt/shared/scripts/lint_oracle_cta_cron.py"
# → exit 0 かつTelegramが来なければ正常

# lintスクリプト単体（詳細出力）
ssh root@163.44.124.123 "python3 /opt/shared/scripts/lint_prediction_links.py"
```

---

## crontab 確認・変更

```bash
# 現在のcrontab確認
ssh root@163.44.124.123 "crontab -l | grep -E 'prediction|lint'"

# crontab編集（追加・変更が必要な場合）
ssh root@163.44.124.123 "crontab -e"
```

---

## アラートが来た場合の対処

→ `docs/PREDICTION_DEEP_LINK_RUNBOOK.md` の「Case 1: lint で bare oracle CTAが検出された」を参照

---

## 監視の設計思想

```
毎日 07:00: ページ再ビルド（prediction_page_builder.py）
  → 毎日アンカーが新鮮に保たれる

毎週月曜 17:00 JST: lint チェック（lint_oracle_cta_cron.py）
  → 記事側リンクの integrity を週次で検証
  → 問題があれば月曜の業務時間内にNaotoへ通知

理由で毎日lintにしない:
  - Ghost API を叩く処理はlimitがある
  - lint_prediction_links.py は 192件のGhost記事を取得するため、毎日は過剰
  - 毎週で十分（新規記事のfuture guardがarticle_builder.py L1145で保証済み）
```

---

*作成: 2026-03-28 | Claude Code (claude-sonnet-4-6)*
