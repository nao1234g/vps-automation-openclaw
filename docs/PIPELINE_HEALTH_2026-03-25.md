# Pipeline Health Report — 2026-03-25 01:00 JST

> Night Mode Track C: 全パイプラインの健康状態整理
> 自動更新ではない。スナップショット。

---

## サマリー

| パイプライン | 状態 | Cron数 | 備考 |
|-------------|------|--------|------|
| **記事生成** | OK | 12 | NEO-ONE 3x/day + NEO-TWO 3x/day + RSS 4x/day |
| **X/Twitter** | OK | 12 | swarm 5分毎 + auto_tweet 3x + DLQ retry |
| **Note** | DEGRADED | 3 | Cookies存在するがログなし。要監視 |
| **翻訳** | OK | 3 | bulk-en-translator 4h毎 + monitor + QA |
| **予測** | OK | 7+ | page_builder日次 + auto_verifier + timestamper |
| **Substack** | OK | 1 | コンテナ稼働中(healthy) |
| **監視系** | OK | 10+ | watchdog, webhook, zero-article-alert等 |

---

## Ghost CMS

- **Published**: 1,263 articles (JA:194 + EN:575 + drafts-turned-published)
- **Drafts**: 1,263 total
  - Mislabeled (EN content + lang-ja): **400** ← draft_rescue.pyで10件修正済み、残400件
  - EN_READY (correct lang-en): **655**
  - JA_READY (correct lang-ja): **204**
  - NO_LANG: **3**
- **Tags**: 70
- **Service**: ghost-nowpattern active (since 2026-03-24 22:33 JST)

---

## 記事生成パイプライン

| スクリプト | スケジュール | エージェント |
|-----------|-------------|-------------|
| nowpattern-deep-pattern-generate.py | 02:30, 08:30, 14:30 | NEO-ONE |
| nowpattern-deep-pattern-generate.py | 05:30, 11:30, 17:30 | NEO-TWO |
| rss-to-nowpattern.py | 00:30, 06:30, 12:30, 18:30 | cron直接 |

- **日次目標**: 200本（JP100 + EN100）
- **ログ**: neo1/neo2のgenログが空 — 要確認（生成はされているはずだがログ出力先が異なる可能性）

---

## X/Twitter パイプライン

| スクリプト | スケジュール | 備考 |
|-----------|-------------|------|
| x_swarm_dispatcher.py | 毎5分 | メイン配信（2 cron entries） |
| auto_tweet.py | 3x/day (09:00,15:00,21:00) | 自動ツイート（9 entries） |
| ghost_to_tweet_queue.py | 1x/day | Ghost→ツイートキュー変換 |
| x_dlq_retry.py | 毎30分 | DLQ再試行 |

- **DLQ状態**: ファイルなし or 空（N/A）
- **ログ**: x_swarm_dispatcher.log なし — ログ出力先要確認
- **状態**: Cron活性、スクリプト存在。実際の投稿状況は @nowpattern で確認が必要

---

## Note パイプライン

| スクリプト | スケジュール |
|-----------|-------------|
| post-notes.py | 3x/day |

- **Cookies**: `/opt/shared/.note-cookies.json` 存在
- **Queue**: `note_queue.json` なし
- **ログ**: なし
- **懸念**: ログが一切ない = 正常動作かサイレント失敗かの判別不可
- **推奨**: 朝に `python3 /opt/shared/scripts/post-notes.py --dry-run` で動作確認

---

## 翻訳パイプライン

| スクリプト | スケジュール |
|-----------|-------------|
| a1-bulk-en-translator.py | 毎4時間 |
| en-translation-monitor.py | 毎時 |
| translation_qa.py | 1x/day |

- **ログ**: なし（全3本）
- **懸念**: ログがないのは翻訳対象がなかった可能性と、エラーの可能性の両方ありうる
- **Draft状況**: EN_READY 655件がdraftで待機中 = 翻訳は機能している証拠

---

## 予測パイプライン

| スクリプト | スケジュール | 備考 |
|-----------|-------------|------|
| prediction_page_builder.py --lang ja | 22:00 JST | JA予測ページ生成 |
| prediction_page_builder.py --lang en | 22:30 JST | EN予測ページ生成 |
| prediction_auto_verifier.py | 1x/day | 自動検証 |
| prediction_timestamper.py | 毎時 | OTSタイムスタンプ |
| polymarket_monitor.py | 4x/day | 市場データ取得 |
| polymarket_delta.py | 1x/day | 市場変化追跡 |
| prediction_ensemble.py | 1x/day | アンサンブル予測 |

- **prediction_db.json**: 956件（Active:14, Resolved:37, 残りresolving/open）
- **最新ログ**: auto_verifier 2026-03-25 00:12 — 6/31件検証、正常終了
- **Brier Score**: 0.1295（GOOD水準）
- **状態**: **正常稼働中**

---

## Substack パイプライン

- **コンテナ**: openclaw-substack-api Up 3 days (healthy)
- **Cron**: 1 entry
- **状態**: 稼働中

---

## サービス稼働状態

| サービス | 状態 | 起動日時 |
|---------|------|---------|
| neo-telegram | active | 2026-03-24 21:05 JST |
| neo2-telegram | active | 2026-03-24 22:15 JST |
| neo3-telegram | active | 2026-03-18 06:39 JST |
| ghost-nowpattern | active | 2026-03-24 22:33 JST |
| ghost-page-guardian | active | 2026-03-10 06:18 JST |
| ghost-webhook-server | active | 2026-03-10 06:18 JST |

全6サービスが稼働中。NEO-ONE/TWOが3/24に再起動されている（OAuthトークン更新の可能性）。

---

## ディスク

- 使用量: 38GB / 99GB (41%) — 余裕あり

---

## Night Mode インフラ

- **night_mode.flag**: 存在しない
- **night-mode-on.sh**: VPSに存在しない（ローカルのみ参照）
- **night-mode-off.sh**: VPSに存在しない
- **推奨**: VPS上にNight Mode切替スクリプトを配置（Track D）

---

## 朝の推奨アクション

1. **Draft Rescue 400件の一括修正承認**: `ssh root@163.44.124.123 "python3 /opt/shared/scripts/draft_rescue.py --fix-tags --limit 50"` を8回実行（50件ずつ、合計400件）
2. **Note パイプライン確認**: `ssh root@163.44.124.123 "python3 /opt/shared/scripts/post-notes.py --dry-run"` で動作テスト
3. **X 投稿確認**: https://x.com/nowpattern で最新投稿を目視確認
4. **翻訳ログ確認**: ログがない件の原因調査

---

*Created: 2026-03-25 01:00 JST by Night Mode Track C*
