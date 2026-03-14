# FAILURE_TAXONOMY.md — 失敗分類体系

> **failure_memory.json の `failure_type` フィールドの唯一の定義。**
> 新しい失敗を記録する際はこの分類を使う。
> 更新: 変更時は末尾のCHANGELOGに1行追記。

---

## Severity（重大度）の定義

| severity | 意味 | リリース影響 | 例 |
|----------|------|------------|-----|
| `critical` | 本番破壊・データロス | **ブロック** (exit 2) | DB削除、記事全消失 |
| `high` | 主要機能停止 | **ブロック** (exit 2) | パイプライン停止、NEO応答なし |
| `medium` | 部分的な機能低下 | 警告 (exit 1) | 一部記事の投稿失敗、タグエラー |
| `low` | 軽微な不具合 | 警告 (exit 1) | ログフォーマット崩れ、リトライ成功 |

**`release_gate.py` との連携:**
- `critical` / `high` + `resolved_status: "open"` → `exit 2`（デプロイブロック）
- `medium` / `low` + `resolved_status: "open"` → `exit 1`（警告のみ）
- `--strict` フラグ → medium/low もブロック対象に昇格

---

## failure_type（失敗タイプ）の分類

### 1. api_mismatch — API仕様の不一致

| サブタイプ | 具体例 | 初発パターン |
|-----------|--------|------------|
| `api_auth_error` | 401/403 レスポンス | 古いAPIキー、ヘッダー誤り |
| `api_endpoint_changed` | 404 / URL変更 | APIバージョンアップ |
| `api_schema_changed` | レスポンス構造の変化 | フィールド名変更、型変更 |
| `api_rate_limit` | 429 レスポンス | バースト超過 |
| `api_ssl_error` | SSL/TLS検証失敗 | 証明書問題、`verify=False`未設定 |

**防止策:**
- 実装前にWebSearchで最新APIドキュメントを確認
- APIレスポンスを実際に取得してスキーマを確認してから実装

---

### 2. path_mismatch — ファイルパスの不一致

| サブタイプ | 具体例 | 初発パターン |
|-----------|--------|------------|
| `file_not_found` | `FileNotFoundError` | VPS専用ファイルをローカルで参照 |
| `wrong_cwd` | 相対パスの誤解 | スクリプト実行ディレクトリの違い |
| `env_path_diff` | ローカルvsVPSのパス差異 | `python` vs `python3` 等 |
| `permission_denied` | 権限不足 | root権限が必要なファイル |

**防止策:**
- `CLAUDE_PROJECT_DIR` 環境変数でプロジェクトルートを解決
- `os.path.abspath(__file__)` を使ってスクリプト相対パスで解決
- VPS専用ファイルはSSH経由でのみ操作

---

### 3. logic_error — ロジックの誤り

| サブタイプ | 具体例 | 初発パターン |
|-----------|--------|------------|
| `off_by_one` | インデックス/境界値の誤り | ループの終端条件 |
| `null_handling` | `None`/空リストへのアクセス | `.get()` 未使用 |
| `encoding_error` | UnicodeDecodeError | UTF-8/Shift-JIS混在 |
| `type_mismatch` | `str` vs `int` の混在 | JSONから読んだ値の型 |
| `state_mismatch` | 期待するステートと実態の乖離 | cacheやファイルの古い値 |
| `concurrent_write` | 同一ファイルへの競合書き込み | 複数プロセス同時実行 |

**防止策:**
- `if not items: return` パターンで空チェック
- `fcntl.flock()` でファイルロック（VPS/Linux）
- `encoding="utf-8", errors="replace"` を常に明示

---

### 4. config_error — 設定の誤り

| サブタイプ | 具体例 | 初発パターン |
|-----------|--------|------------|
| `missing_env_var` | 環境変数未設定 | `.env` 未読み込み |
| `wrong_model_id` | 存在しないモデル名指定 | APIで確認せず推測 |
| `hook_misconfigured` | settings.local.json の誤った設定 | タイムアウト不足、コマンドパス誤り |
| `cron_syntax_error` | cronジョブの構文エラー | タイムゾーン指定ミス |
| `docker_config_error` | Compose設定の誤り | 環境変数展開失敗 |

**防止策:**
- 環境変数は `/opt/cron-env.sh` またはローカル環境変数から読む
- モデルIDはAPIドキュメントまたは `WebSearch` で確認してから設定

---

### 5. data_integrity — データ整合性の問題

| サブタイプ | 具体例 | 初発パターン |
|-----------|--------|------------|
| `prediction_db_corruption` | prediction_db.jsonの不正な変更 | `APPEND ONLY`ルール違反 |
| `duplicate_entry` | 同一予測の重複登録 | IDチェック不足 |
| `schema_violation` | 必須フィールド欠落 | 古いスキーマでの作成 |
| `tag_taxonomy_violation` | 未定義タグの使用 | taxonomy.json未参照 |
| `brier_score_invalid` | 0.0〜1.0範囲外のスコア | 計算式の誤り |

**防止策:**
- prediction_db.jsonへの書き込みはAPPEND ONLYフラグを常に確認
- タグはnowpattern_taxonomy.jsonから取得
- Brier Score計算: `BS = (forecast_prob - outcome)²`（0〜1に正規化）

---

### 6. service_failure — サービス障害

| サブタイプ | 具体例 | 初発パターン |
|-----------|--------|------------|
| `ghost_down` | Ghost CMS応答なし | systemdサービス停止 |
| `neo_unresponsive` | NEO-ONE/TWOが応答なし | OAuthトークン期限切れ |
| `docker_container_exit` | コンテナが予期せず停止 | メモリ不足、クラッシュ |
| `telegram_api_error` | Telegram通知失敗 | BOTトークン無効 |
| `caddy_config_error` | Caddy設定エラーでリバースプロキシ停止 | 設定ファイル構文エラー |

**防止策:**
- `service_watchdog.py` が30分ごとに全サービスを監視
- NEO OAuthトークンは4時間ごとにSCPコピー（Windowsタスクスケジューラ）
- Telegram通知失敗は警告のみ（アラート系のクリティカルパスに置かない）

---

### 7. pipeline_failure — パイプライン固有の失敗

| サブタイプ | 具体例 | 初発パターン |
|-----------|--------|------------|
| `zero_articles` | 生成記事が0件 | ニュースソース枯渇、クラッシュ |
| `stub_article` | スタブ記事が公開された | 品質ゲート未通過 |
| `translation_missing` | EN版が生成されなかった | 翻訳パイプライン停止 |
| `prediction_not_recorded` | 予測がDBに未記録 | `prediction_db.json` 書き込みエラー |
| `qa_gate_failure` | QAゲートでDRAFT降格 | 必須マーカー欠落 |

**防止策:**
- `zero-article-alert.py` が30分ごとに記事数監視
- 記事生成後に `nowpattern_visual_verify.py` を自動実行
- 全記事に6必須マーカーを確認（`np-fast-read` 〜 `np-oracle`）

---

## resolved_status の遷移

```
open → in_progress → fixed
           ↓
       regressed → fixed
           ↓
       wont_fix （意図的に修正しない場合）
```

| resolved_status | 意味 |
|-----------------|------|
| `open` | 未対応。release_gate がブロック対象にする |
| `in_progress` | 対応中。release_gate はブロック対象にする |
| `fixed` | 修正完了。release_gate はスキップ |
| `regressed` | 再発した。release_gate はブロック対象にする |
| `wont_fix` | 意図的に修正しない。release_gate はスキップ |

---

## failure_memory.json への記録例

```json
{
  "failure_id": "F042",
  "failure_type": "api_mismatch",
  "subtype": "api_schema_changed",
  "severity": "high",
  "resolved_status": "fixed",
  "symptom": "Ghost API lexical フィールドが null を返す",
  "root_cause": "Ghost 5.x でlexical形式に移行。?source=html パラメータは無効",
  "fix_applied": "lexical JSONを直接操作するロジックに変更",
  "prevention_rule": "Ghost API変更はWebSearchでforum.ghost.orgを確認してから実装",
  "first_seen": "2026-02-24T01:00:00Z",
  "last_seen": "2026-02-24T01:00:00Z",
  "recurrence_count": 1,
  "related_task": "T003"
}
```

---

## CHANGELOG

| 日付 | 変更内容 |
|------|---------|
| 2026-03-14 | 初版。7種類のfailure_type定義。Severity×resolved_status遷移。release_gate.pyとの連携。 |
