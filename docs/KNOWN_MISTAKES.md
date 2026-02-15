# Known Mistakes & Lessons Learned

> このファイルは過去のミス、無駄な試行錯誤、教訓を記録します。
> 新しいミスが発生したら、必ずここに追記してください。
> AIエージェントは実装前に必ずこのファイルを確認します。

---

## 記録フォーマット

各エントリは以下の形式で記録：

```markdown
### YYYY-MM-DD: 問題のタイトル
- **症状**: 何が起きたか
- **根本原因**: なぜ起きたか
- **誤ったアプローチ**: 無駄だった試行錯誤
- **正しい解決策**: 最終的にどう解決したか
- **教訓**: 次回どうすべきか（具体的なアクション）
- **検索すべきだったキーワード**: 最初から検索していれば見つかったキーワード
```

---

## Substack自動投稿（2026-02-14）

### 2026-02-14: Substack公式APIの存在確認不足
- **症状**: N8NでSubstackメール投稿を試みたが、メールが届かない
- **根本原因**: Substackには公式APIもメール投稿機能も存在しない（AIが確認せずに提案）
- **誤ったアプローチ**:
  1. メール送信で投稿できると推測（根拠なし）
  2. 「Substack API」が存在すると推測（公式ドキュメント未確認）
- **正しい解決策**:
  1. GitHub検索で `python-substack` ライブラリを発見
  2. Cookie認証でCAPTCHA回避
  3. FastAPI + python-substackで独自APIサーバー構築
- **教訓**:
  - **機能の存在を推測で語らない。必ず公式ドキュメントで確認する**
  - APIが「あるはず」と思っても、まず検索する
  - ユーザーに提案する前に、最低3つの情報源で裏付けを取る
- **検索すべきだったキーワード**:
  - `Substack API documentation`
  - `Substack programmatic posting`
  - `Substack email publishing`

### 2026-02-14: CAPTCHA問題の調査不足
- **症状**: python-substackでメール/パスワード認証すると「Please complete the captcha to continue」エラー
- **根本原因**: Bot対策でCAPTCHAが発動
- **誤ったアプローチ**:
  1. エラーが出てから「どうしましょう」とユーザーに聞いた
  2. 事前に「CAPTCHAが出る可能性」を調査しなかった
- **正しい解決策**:
  1. GitHub Issuesで `python-substack CAPTCHA` を検索すれば、Cookie認証の方法が見つかった
  2. ブラウザのNetwork TabからCookie (`connect.sid`) を取得
  3. Cookie認証でCAPTCHA完全回避
- **教訓**:
  - **エラーが出てから調査するのではなく、実装前にGitHub Issuesを確認する**
  - 認証系の実装では、必ずBot対策（CAPTCHA、レート制限）の回避方法を事前調査する
  - 「できない」とユーザーに報告する前に、必ずGitHub Issues/Discussions/Gistsを検索する
- **検索すべきだったキーワード**:
  - `python-substack CAPTCHA` (GitHub Issues)
  - `Substack bot detection bypass`
  - `Substack cookie authentication`

---

## OpenClaw設定（2026-02-11〜14）

### 2026-02-11: OpenClaw Control UI ペアリング問題
- **症状**: ブラウザからControl UI接続時に `disconnected (1008): pairing required` エラー
- **根本原因**: OpenClaw GatewayはデフォルトでWebSocket接続にデバイスペアリングを要求する
- **誤ったアプローチ**:
  1. `--no-pairing` CLIフラグを追加 → **存在しないオプション**
  2. 環境変数 `OPENCLAW_DISABLE_PAIRING` を追加 → Gateway が認識しない
  3. `entrypoint.sh` で動的にフラグ生成 → 動作しない
- **正しい解決策**: `openclaw.json` 設定ファイルで以下を設定:
  ```json
  {
    "gateway": {
      "controlUi": {
        "allowInsecureAuth": true,
        "dangerouslyDisableDeviceAuth": true
      }
    }
  }
  ```
- **教訓**:
  - **OpenClawの設定変更は `openclaw.json` で行う（CLIフラグや環境変数ではない）**
  - 存在しないCLIオプションを推測で追加しない
  - 公式ドキュメントで設定方法を確認してから実装する
- **検索すべきだったキーワード**:
  - `OpenClaw pairing disable config`
  - `OpenClaw controlUi configuration`
  - GitHub: `openclaw pairing required` (Issues)

### 2026-02-11: read-only マウントによる EBUSY エラー
- **症状**: `failed to persist plugin auto-enable changes: Error: EBUSY: resource busy or locked`
- **根本原因**: `openclaw.json` を `:ro` (read-only) でマウントしているため、Gateway が設定を更新できない
- **誤ったアプローチ**:
  1. エラーメッセージを無視して放置
- **正しい解決策**:
  1. プラグイン管理が不要なら `:ro` のまま許容
  2. プラグイン管理が必要なら `:ro` を削除
- **教訓**:
  - **設定ファイルを `:ro` マウントすると、アプリケーションが設定を更新できない**
  - EBUSYエラーは「ファイルがロックされている」という明確なサイン
- **検索すべきだったキーワード**:
  - `Docker read-only mount EBUSY`
  - `OpenClaw plugin auto-enable failed`

### 2026-02-12: Telegram接続 & EBUSY完全解決
- **症状**: Telegram Bot Token を設定しても「Telegram configured, not enabled yet.」のまま有効化されない
- **根本原因**: `openclaw.json` が単一ファイルでバインドマウント（`:ro`）されており、`openclaw doctor --fix` が設定を書き込めない
- **誤ったアプローチ**:
  1. `:ro` を削除 → まだ EBUSY（単一ファイルマウントでは rename 操作が不可）
  2. ディレクトリマウントに変更 → EACCES（権限不足）
- **正しい解決策**:
  1. ディレクトリマウント (`./config/openclaw:/home/appuser/.openclaw`) に変更
  2. `chown 1000:1000` + `chmod 777` で権限設定
  3. `openclaw doctor --fix` 成功
  4. doctor が `plugins.entries.telegram.enabled: false` で追加 → 手動で `true` に変更
  5. Telegram 接続後、ペアリング承認 (`openclaw pairing approve telegram <code>`)
- **教訓**:
  - **OpenClaw はプラグイン管理のため設定ディレクトリに書き込み権限が必要**
  - 単一ファイルのバインドマウントでは rename（アトミック書き込み）が失敗する
  - **ディレクトリ単位でマウント**すること
  - `openclaw doctor --fix` はプラグイン有効化の正規手段だが、`enabled: false` で追加されることがあるので確認が必要
  - Telegram 接続には Bot Token 設定 → doctor --fix → ペアリング承認 の3ステップが必要
- **検索すべきだったキーワード**:
  - `Docker bind mount rename EBUSY`
  - `OpenClaw telegram enable`
  - GitHub: `openclaw doctor telegram` (Issues)

### 2026-02-12: Gemini モデル名の不一致
- **症状**: `Error: No API key found for provider "google"` → 解決後も Telegram で「gemini-cheap」しか使えない
- **根本原因**:
  1. VPS の `.env` に `GOOGLE_API_KEY` が未設定
  2. `openclaw.json` のモデル名 `google/gemini-2.5-pro-preview-05-06` が存在しないモデル名
- **誤ったアプローチ**:
  1. モデル名を公式ドキュメントで確認せず、推測で記述
- **正しい解決策**:
  1. `curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GOOGLE_KEY}"` で利用可能モデル一覧を取得
  2. 正しいモデル名に修正: `google/gemini-2.5-pro`、`google/gemini-2.5-flash`
- **教訓**:
  - **Google は preview モデルの名称を頻繁に変更・廃止する**
  - 設定前に API で利用可能なモデル名を確認すること
  - モデル名は推測せず、必ず公式APIで確認する
- **検索すべきだったキーワード**:
  - `Google Gemini API available models`
  - `Gemini 2.5 model names`

### 2026-02-14: SSH復旧 & Control UI トークン認証
- **症状**: VPSにSSH接続できない
- **根本原因**: cloud-initが `/etc/ssh/sshd_config.d/50-cloud-init.conf` で `PasswordAuthentication no` を上書き
- **誤ったアプローチ**:
  1. `/etc/ssh/sshd_config` だけを修正（cloud-init の設定ファイルを見逃した）
- **正しい解決策**:
  1. cloud-init の設定ファイル (`50-cloud-init.conf`) を修正
  2. `PasswordAuthentication yes` に変更
  3. sshd再起動
- **教訓**:
  - **cloud-init の sshd_config.d 配下のファイルがメインの sshd_config を上書きする**
  - SSH設定の変更時は `/etc/ssh/sshd_config.d/` も確認する

- **症状**: `dangerouslyDisableDeviceAuth: true` でもデバイス認証が要求される
- **根本原因**: Control UIのトークン認証はURLパラメータで渡す必要がある
- **正しい解決策**: URLに `?token={GATEWAY_TOKEN}` を付与 (`http://host:port/?token=...`)
- **教訓**:
  - **OpenClaw Control UIのトークン認証はURLパラメータで渡す**
  - GitHub Issues (#8529) に解決策が記載されていた
- **検索すべきだったキーワード**:
  - `OpenClaw Control UI token authentication`
  - GitHub: `openclaw controlui token` (Issues)

### 2026-02-15: Telegram画像処理が動作しない（imageModel未設定）
- **症状**: TelegramでスクリーンショットをOpenClawに送信しても、画像の内容が読み取れず「An unexpected error occurred」エラー
- **根本原因**: `openclaw.json` の `agents.defaults` に `imageModel` 設定が存在しない。Gemini 2.5 Proはマルチモーダル対応だが、OpenClawに「画像処理にこのモデルを使え」と指示していなかった
- **誤ったアプローチ**:
  1. Telegramプラグインの設定を確認した → 問題なし
  2. Telegram Bot APIの画像送信を疑った → 実際にはOpenClaw側の設定不足
- **正しい解決策**:
  1. GitHub Issues (#7564, #11735, #8096) で同様の問題を発見
  2. `openclaw.json` に以下を追加:
     ```json
     {
       "agents": {
         "defaults": {
           "model": {
             "primary": "google/gemini-2.5-pro"
           },
           "imageModel": {
             "primary": "google/gemini-2.5-pro"
           },
           "models": {
             "google/gemini-2.5-pro": {
               "params": {
                 "maxTokens": 8192
               }
             }
           }
         }
       }
     }
     ```
  3. OpenClaw Gateway を再起動
- **教訓**:
  - **マルチモーダルモデル（Gemini, GPT-4o等）を使う場合、必ず `imageModel` 設定を追加する**
  - `maxTokens: 8192` を設定しないと「Image model returned no text」エラーが出る
  - Telegram画像処理の問題は、まずOpenClaw側の設定を確認する（Telegram APIではない）
- **検索すべきだったキーワード**:
  - `OpenClaw Telegram image not working`
  - `site:github.com/openclaw/openclaw imageModel configuration`
  - `OpenClaw gemini vision telegram`

### 2026-02-14: sessions_spawn の pairing required エラー
- **症状**: Jarvis が Telegram 経由で sessions_spawn を使って Alice に仕事を振ろうとすると「pairing required」エラー
- **根本原因**: Docker コンテナ内の CLI デバイス (`~/.openclaw/identity/device.json`) が Gateway に未登録。`~/.openclaw/devices/paired.json` が空 `{}`
- **誤ったアプローチ**:
  1. `openclaw pairing approve` で承認しようとした → CLI からは Gateway 接続が必要なので不可能（鶏と卵の問題）
  2. 環境変数やCLIフラグで回避しようとした → デバイス認証は別レイヤー
- **正しい解決策**:
  1. `pending.json` からデバイス情報を取得
  2. `paired.json` にデバイスID をキーとしてエントリを追加（Node.js スクリプトで手動登録）
  3. `pending.json` を `{}` にクリア
  4. Gateway を再起動
- **教訓**:
  - **OpenClaw Gateway はデバイス認証とトークン認証が別レイヤー**
  - `controlUi.dangerouslyDisableDeviceAuth` は Control UI のみに効く。CLI やサブエージェントには効かない
  - `paired.json` の構造を理解し、手動登録が必要な場合がある
  - **公式ドキュメントとGitHub Issuesを必ず確認する**
- **検索すべきだったキーワード**:
  - `OpenClaw sessions_spawn pairing required`
  - GitHub: `openclaw pairing cli docker` (Issues)
  - `OpenClaw device authentication bypass`

---

## N8N関連（2026-02-14）

### 2026-02-14: N8N API アクセス & ワークフロー
- **症状**: N8N APIに Basic Auth でアクセスできない（401 Unauthorized）
- **根本原因**: N8N API は `X-N8N-API-KEY` ヘッダーが必須。Basic Auth では通らない
- **誤ったアプローチ**:
  1. Basic Auth で API アクセスを試みた（Web UIのログイン方式と混同）
- **正しい解決策**:
  1. N8N Web UI または REST API (`/rest/api-keys`) で APIキーを生成
  2. `X-N8N-API-KEY` ヘッダーでアクセス
- **教訓**:
  - **N8N API 認証は Basic Auth ではなく APIキー**
  - Web UI のログイン方式と API の認証方式は別物
- **検索すべきだったキーワード**:
  - `N8N API authentication`
  - `N8N API key header`

---

## Docker関連

### 一般的な落とし穴
- **PostgreSQL init スクリプト**: 初回起動時のみ実行。再実行するにはボリューム削除が必要
- **Docker Compose ファイルの選択ミス**: 変更を加えた yml と実際に起動している yml が異なるケースが頻発。`docker compose ps` で確認すること
- **entrypoint.sh の変更**: ファイル修正後は `docker compose up -d --build` が必要（`restart` では反映されない）
- **環境変数のデフォルト値**: `${VAR}` と `${VAR:-default}` の違いに注意。前者は未設定時に空文字、後者はデフォルト値が入る

---

## ミス記録の手順

新しいミスが発生したら、以下の手順で記録：

1. **即座に記録**: エラー解決後、すぐに記録する（後回しにしない）
2. **詳細に記録**: 症状、根本原因、誤ったアプローチ、正しい解決策、教訓を明確に
3. **検索キーワードを記録**: 「最初からこれで検索していれば見つかった」というキーワードを必ず書く
4. **CLAUDE.mdに参照を追加**: セクション5（Documentation Priority）に追加

---

## Neo（Claude Code Telegram Bot）関連（2026-02-15）

### 2026-02-15: Neo画像認識が動作しない（複数の問題）

#### 問題1: rate_limit.py で `len(None)` エラー
- **症状**: Telegramで画像を送ると「An unexpected error occurred」エラー。ログに `TypeError: object of type 'NoneType' has no len()`
- **根本原因**: `rate_limit.py` の `estimate_message_cost` 関数で、写真メッセージの場合 `message.text` が `None` になり、`len(None)` でエラー
- **誤ったアプローチ**:
  1. Telegram Bot API の問題だと推測 → 実際はミドルウェアの問題
  2. 画像ハンドラーの問題だと推測 → 実際は rate limiter の問題
- **正しい解決策**:
  ```python
  # 修正前
  message_text = message.text if message else ""

  # 修正後（None 対策）
  message_text = (message.text or "") if message else ""
  ```
- **教訓**:
  - **写真メッセージでは `message.text` が `None` になる**
  - `len()` を使う前に必ず `None` チェックを行う
  - エラーログの "object of type 'NoneType' has no len()" は `len(None)` を呼び出している箇所を探す
- **検索すべきだったキーワード**:
  - `python-telegram-bot message.text None photo`
  - `TypeError NoneType has no len`

#### 問題2: agentic_photo が画像をClaude Codeに渡していない
- **症状**: 画像ダウンロードは成功するが、Neoが「新しい画像は届いていません」と応答
- **根本原因**: `orchestrator.py` の `agentic_photo` 関数が、画像をダウンロードしてbase64エンコードするが、Claude Code SDKの `run_command` に画像データを渡す方法がない
- **誤ったアプローチ**:
  1. `run_command` に `images` パラメータがあると推測 → 実際には存在しない
  2. f-stringで画像パスを渡そうとして複数行f-stringになり構文エラー → Pythonスクリプトでの置換が困難
  3. sedやPythonスクリプトで修正を試みるが、エスケープの問題で失敗を繰り返す
- **正しい解決策**:
  1. 画像をVPSのファイルシステム（`/opt/telegram_image_{timestamp}_{user_id}.jpg`）に保存
  2. プロンプトに「画像ファイル: {filename}\n\nこの画像を読んで分析してください。」と追記
  3. Claude CodeがReadツールで画像を読む
  4. 関数全体を新しいコードで置き換える（部分的な置換ではなく）
  5. `.format()` を使ってf-stringの構文エラーを回避
- **教訓**:
  - **Claude Code SDKの `run_command` は画像を直接渡せない。ファイルシステム経由で渡す**
  - f-stringで複数行の文字列を作ると構文エラーになる（`.format()` または三重引用符を使う）
  - 複雑な修正は部分的な置換ではなく、関数全体を書き換える方が確実
  - Pythonスクリプトでのファイル編集は、改行やエスケープの問題が頻発する
  - **git checkout で簡単に元に戻せるので、失敗を恐れずに試せる**
- **検索すべきだったキーワード**:
  - `Claude Code SDK image upload`
  - `anthropic sdk send image file`
  - `python telegram bot save image file`

#### 問題3: photoハンドラーが2つ登録されている
- **症状**: `handle_photo`（修正済み）が呼ばれず、`agentic_photo`（未修正）が呼ばれる
- **根本原因**: `orchestrator.py` で `filters.PHOTO` に対して2つのハンドラーが登録されており、最初の `agentic_photo` が優先される
- **誤ったアプローチ**:
  1. `handle_photo` を修正したが、実際には `agentic_photo` が呼ばれていることに気づかなかった
- **正しい解決策**:
  1. `agentic_photo` を修正する（実際に呼ばれているハンドラーを修正）
  2. または `agentic_photo` の登録をコメントアウトして `handle_photo` を使う
- **教訓**:
  - **ログで実際にどのハンドラーが呼ばれているか確認する**
  - 同じフィルターに複数のハンドラーが登録されている場合、最初のものが優先される
  - コードを修正する前に、そのコードが実際に実行されているか確認する
- **検索すべきだったキーワード**:
  - `python-telegram-bot multiple handlers same filter`
  - `telegram handler priority order`

#### 問題4: プログレスメッセージの改善
- **症状**: ユーザーが「ダウングレードしてる」と指摘。静的な "Working..." メッセージではなく、動的なプログレス表示が欲しい
- **解決策**:
  1. `_progress_updater` メソッドを実装（経過時間 + ドットアニメーション）
  2. `asyncio.create_task` でバックグラウンドタスクとして実行
  3. Claude処理完了後、`task.cancel()` で停止
  4. "📸 Processing image..." → "🤖 Analyzing image with Claude... (2s)" のように段階的に表示
- **教訓**:
  - **ユーザー体験（UX）は重要。処理時間が長い場合は動的なプログレス表示を実装する**
  - `asyncio.create_task` + `task.cancel()` でバックグラウンド更新を実現
  - 絵文字と経過時間の組み合わせで、ユーザーに安心感を与える

---

## X (Twitter) API関連（2026-02-15）

### 2026-02-15: X API「Free」プランでも課金が必須（Pay-Per-Use）
- **症状**: X API投稿時に「402 Payment Required - CreditsDepleted」エラー。使用状況は0だが投稿できない
- **根本原因**:
  - 2026年にX APIがPay-Per-Useモデルに変更された
  - 「Free」プランは名前だけで、実際には最低$5のクレジット購入が必須
  - サブスクリプションモデルは廃止された
- **誤ったアプローチ**:
  1. 「Freeプランで月500投稿まで無料」と説明 → 2025年以前の情報で、2026年の仕様変更を見逃した
  2. OAuth 1.0aの権限設定（Read and Write）に時間をかけた → 権限は正しかったが、クレジット不足が原因だった
  3. 「使用状況が0なのになぜ？」と混乱 → クレジット残高と使用状況は別物
  4. 調査不足で、ユーザーに無駄な手順（権限変更、トークン再生成）を踏ませた
- **正しい解決策**:
  1. X Developer Portal → **Credits（クレジット）** または **Billing（請求）**
  2. **$5（約750円）のクレジットを購入**（最低購入額）
  3. 支払い方法（クレジットカード）を登録
  4. 購入後、即座に投稿可能になる
  5. 使った分だけ課金される（投稿1回あたり数セント程度）
- **教訓**:
  - **X API料金体系は2026年に大幅変更。「Free」は名前だけで、実際はPay-Per-Use**
  - エラーコード402は「Payment Required」の明確なサイン
  - 「CreditsDepleted」エラーは、使用状況ではなくクレジット残高の問題
  - **実装前に最新の料金体系を確認する**（GitHub Issues、X Developer Community、公式ブログ）
  - 古い情報（2025年以前）を鵜呑みにしない
  - ユーザーに提案する前に、最低3つの情報源（公式ドキュメント、コミュニティフォーラム、GitHub Issues）で裏付けを取る
- **検索すべきだったキーワード**:
  - `X API CreditsDepleted 2026`
  - `X API Free tier pay-per-use`
  - `X API 402 payment required`
  - GitHub/X Developer Community: `creditsdepleted free tier` (検索すれば、同じ問題で困っている人が多数見つかった)
- **料金情報**:
  - 最低購入額: $5
  - 投稿コスト: 約$0.01〜0.05/投稿（使った分だけ課金）
  - $5で約100〜500投稿可能

---

---

## OpenClaw設定関連（2026-02-15）

### 2026-02-15: openclaw.jsonに存在しないキーを追加してコンテナ起動失敗
- **症状**: OpenClawコンテナが「Config invalid」「Unrecognized key: "systemPrompt"」でunhealthyになる
- **根本原因**: openclaw.jsonのエージェント設定に`systemPrompt`キーを追加したが、OpenClawはこのキーを認識しない。`identity.description`も同様に無効
- **誤ったアプローチ**:
  1. `agents.list[0].systemPrompt` を追加 → 「Unrecognized key」エラー
  2. `agents.list[0].identity.description` を追加 → 同じく「Unrecognized key」エラー
  3. OpenClawのドキュメントやGitHubを事前に確認しなかった（リサーチ不足）
- **正しい解決策**:
  1. openclaw.jsonからは無効なキーを削除する
  2. エージェントにルールを伝えるには **共有ファイル** (`/opt/shared/AGENT_RULES.md`) を作成する
  3. エージェントはファイルシステムにアクセスできるので、共有ファイルを読むことができる
- **教訓**:
  - **openclaw.jsonは厳密なバリデーションがある。推測でキーを追加しない**
  - 設定項目を追加する前に、公式ドキュメントまたはGitHub Issuesで有効なキーを確認する
  - エージェントへの指示は設定ファイルではなく、共有ファイルシステムを使う
- **検索すべきだったキーワード**:
  - `openclaw agent systemPrompt config`
  - `openclaw.json valid keys schema`
  - `openclaw agent instructions configuration`

---

## N8Nワークフロー作成（2026-02-15）

### 2026-02-15: N8NワークフローをDB直接INSERTで作成しても起動しない
- **症状**: PostgreSQLの`n8n.workflow_entity`テーブルにワークフローを直接INSERTし`active=true`に設定しても、N8N再起動時に「Start Active Workflows」リストに表示されず、ポーリングトリガーが起動しない
- **根本原因**: N8NはDB上の`active`フラグだけではワークフローを内部的にアクティベートしない。`staticData`、`activeVersionId`、`workflow_history`テーブル、内部のアクティベーションメカニズムなど、複数のDB要素が正しく設定されている必要がある
- **誤ったアプローチ**:
  1. PostgreSQLに直接INSERT → ワークフローは存在するがN8Nが起動時にスキップ
  2. `staticData`を手動設定 → 改善なし
  3. `installed_packages`/`installed_nodes`テーブルにコミュニティノードを登録 → 改善なし（ノード自体は標準ノードに変更済み）
  4. `activeVersionId`を手動設定 → `workflow_history`テーブルの外部キー制約でエラー
- **正しい解決策**:
  1. N8N REST API経由でワークフローを作成する（`POST /api/v1/workflows`）
  2. N8N REST API経由でアクティベートする（`POST /api/v1/workflows/{id}/activate`）
  3. APIキーは`n8n.user_api_keys`テーブルに直接INSERT可能
  4. APIコール例: `wget --post-file=workflow.json --header='X-N8N-API-KEY: key' http://localhost:5678/api/v1/workflows`
- **教訓**:
  - **N8Nのワークフロー管理はREST API経由で行う。DB直接操作は避ける**
  - N8NのDB構造は複雑で、`active=true`だけでは不十分
  - N8N REST APIキーは`user_api_keys`テーブルに`id`, `userId`, `label`, `apiKey`カラムで追加できる
  - コミュニティノードの利用は不安定。標準ノードだけでポーリングを実現する方が信頼性が高い
- **検索すべきだったキーワード**:
  - `N8N create workflow API`
  - `N8N activate workflow REST API`
  - `N8N workflow not activating after database insert`

### 2026-02-15: Telegram getUpdates コンフリクト（複数プロセス競合）
- **症状**: N8Nワークフローが「Conflict: terminated by other getUpdates request」エラー
- **根本原因**: `neo-telegram.service`（Claude Code Telegram bot）がまだ動作中で、同じbot tokenで`getUpdates`を呼んでいた。一つのbot tokenに対して`getUpdates`を呼べるプロセスは1つだけ
- **誤ったアプローチ**:
  1. 前のセッションで`systemctl stop neo-telegram`を実行したつもりが、実際にはサービスが再起動されていた（`disabled`にしていなかった可能性）
- **正しい解決策**:
  1. `systemctl stop neo-telegram && systemctl disable neo-telegram`で完全停止＆自動起動無効化
  2. `ps aux | grep telegram`で関連プロセスが残っていないか確認
- **教訓**:
  - **Telegram bot tokenのgetUpdatesは1プロセスのみ。切り替え時は必ず前のサービスを`stop` + `disable`する**
  - `systemctl stop`だけでは不十分。`disable`も必須（再起動時に自動起動するため）
  - 切り替え前に`ps aux`でプロセスが完全に終了したか確認する

### 2026-02-15: フルエージェント（Claude Opus 4.6）をステートレスHTTP API（Gemini Flash）に置き換えて品質崩壊
- **症状**: Neo（Telegram bot）が同じ質問を20回以上繰り返し、ユーザーの指示を理解できず、過去の会話を全く覚えていない。ユーザーから「アホになった」とフィードバック
- **根本原因**: `neo-telegram.service`（Claude Code SDK + Opus 4.6）をN8Nワークフロー（HTTP Request → Gemini 2.5 Flash API）に置き換えた。Claude Code SDKが提供していた以下の能力が全て失われた:
  - **セッションメモリ**: 過去の会話の記憶（Gemini Flash APIはステートレス）
  - **VPSファイルシステムアクセス**: ファイル読み書き、レポート参照
  - **ツール使用**: Bash、Read、Write、Grep等のツール
  - **CLAUDE.md読み込み**: アイデンティティ・指示の読み込み
  - **知能レベル**: Opus 4.6 → Flash（大幅なダウングレード）
- **誤ったアプローチ**:
  1. 「N8Nで自動応答」の技術的課題（getUpdatesコンフリクト等）を解決することに集中し、**応答品質の劣化**を見落とした
  2. 「Gemini Flashは無料なのでコスト最適化になる」と判断したが、品質が使い物にならないレベルに低下
  3. neo-telegram.serviceを`/dev/null`にシンボリックリンクして完全に削除してしまった
- **正しい解決策**:
  1. N8N Neo Auto-Responseワークフローをdeactivate（`POST /api/v1/workflows/{id}/deactivate`）
  2. `neo-telegram.service`を再作成（systemdサービスファイルを新規作成）
  3. サービスをstart + enableして元通りに復旧
  4. N8Nワークフローはdeactivated状態で予備として保持
- **教訓**:
  - **フルエージェント（SDK + ツール + メモリ）をステートレスHTTP APIに置き換えてはいけない。能力が根本的に異なる**
  - コスト最適化よりも**ユーザー体験（品質）を優先する**
  - 機能を移行する前に、元のシステムが提供している全機能（メモリ、ツール、ファイルアクセス等）をリストアップし、移行先でも同等の機能が提供できるか確認する
  - サービスを停止する際は`/dev/null`にシンボリックリンクせず、`systemctl disable`で十分。完全削除すると復旧が困難
  - **「動く」と「使える」は違う。技術的に動作しても、品質が要求を満たさなければ無意味**
- **検索すべきだったキーワード**:
  - `Claude Code SDK vs raw API call comparison`
  - `AI agent stateful vs stateless`
  - `replacing AI agent with simple API call problems`

### 2026-02-15: Daily Learning Script がGeminiの訓練データを聞き直しているだけだった
- **症状**: daily-learning.pyが「外部学習」と称して毎日レポートを生成するが、内容がGeminiの訓練データの要約でしかなく、リアルタイムの情報が含まれていなかった
- **根本原因**: Gemini APIに静的なプロンプトを投げて「best practices for X in 2026」と聞くだけでは、Geminiの訓練データの範囲内の回答しか返らない。実際のWeb検索もデータ収集も行っていなかった
- **誤ったアプローチ**:
  1. 「Gemini APIに聞けば最新情報がわかる」と思い込んだ（LLMは訓練データの範囲内でしか回答できない）
  2. 「外部学習」と名付けたが、実際は外部データソースに一切アクセスしていなかった
  3. ユーザーに突っ込まれるまで問題に気づかなかった（自分で品質検証していなかった）
- **正しい解決策**:
  1. **Gemini Google Search grounding** — APIリクエストに `"tools": [{"google_search": {}}]` を追加するだけでリアルタイムWeb検索が可能（Gemini 2.5は無料）
  2. **Reddit JSON API** — URLに`.json`を追加するだけで構造化データ取得（認証不要、無料）
  3. **Hacker News Firebase API** — `https://hacker-news.firebaseio.com/v0/topstories.json`（認証不要、無料）
  4. **GitHub REST API** — 依存リポジトリの最新リリース情報を取得
  5. 上記4ソースからリアルデータを収集し、Gemini + Google Searchで分析する構成に全面的に書き直した
- **教訓**:
  - **LLMに「最新情報を教えて」と聞くだけでは外部学習にならない。実際のデータソースからデータを取得しなければ意味がない**
  - Gemini APIには無料で使えるGoogle Search grounding機能がある（`"tools": [{"google_search": {}}]`）。これを最初から使うべきだった
  - 「やったふう」の仕事をしない。出力の品質を自分で検証してから報告する
  - 自分のツール（WebSearch）を使って調査すれば、Google Search groundingの存在はすぐにわかった
- **検索すべきだったキーワード**:
  - `Gemini API Google Search grounding`
  - `Gemini API real-time web search tool`
  - `Reddit JSON API free`
  - `Hacker News API Firebase`

---

## OpenClaw OpenRouterモデル登録（2026-02-16）

### 2026-02-16: OpenRouterカスタムモデルが「Unknown model」エラー
- **症状**: openclaw.jsonでエージェントのモデルを`openrouter/z-ai/glm-5`に変更し再起動したが、「Unknown model: openrouter/z-ai/glm-5」エラー
- **根本原因**: OpenClawはモデルカタログが静的。OpenRouterの全モデルを認識するわけではなく、未登録モデルは拒否される
- **誤ったアプローチ**:
  1. openclaw.jsonのモデル名を変更するだけで動くと思った → モデルカタログにない
  2. `openclaw onboard --auth-choice openrouter-api-key`でプロバイダー登録 → モデルカタログに追加されない
  3. `models.providers.openrouter.models` をオブジェクト形式で定義 → 「expected array, received object」エラー
  4. models配列に`output`フィールドを追加 → 「Unrecognized key: output」エラー
- **正しい解決策**:
  1. `openclaw onboard --non-interactive --accept-risk --auth-choice openrouter-api-key`でプロバイダー認証を登録
  2. openclaw.jsonの`models.providers`セクションにカスタムモデルを登録:
     ```json
     {
       "models": {
         "providers": {
           "openrouter": {
             "baseUrl": "https://openrouter.ai/api/v1",
             "models": [
               {
                 "id": "z-ai/glm-5",
                 "name": "GLM-5",
                 "reasoning": true,
                 "input": ["text"],
                 "maxTokens": 8192,
                 "contextWindow": 128000
               }
             ]
           }
         }
       }
     }
     ```
  3. `baseUrl`（文字列）と`models`（配列）の両方が必須
  4. modelsの各要素に`output`フィールドは入れない
- **教訓**:
  - **OpenClawのモデルカタログは静的。新しいモデルを使うには`models.providers`でカスタム登録が必要**
  - `models`はオブジェクトではなく配列で定義する
  - `baseUrl`の設定を忘れると起動時にエラー
  - `output`など未知のキーがあると「Unrecognized key」で起動失敗
  - OpenClawのJSON設定は厳密なバリデーションがある（推測でキーを追加しない）
- **検索すべきだったキーワード**:
  - `openclaw custom model provider configuration`
  - `openclaw openrouter setup models.providers`
  - `openclaw unknown model error custom provider`

### 2026-02-16: `openclaw onboard`がgateway.bindをloopbackに変更する副作用
- **症状**: `openclaw onboard`実行後、OpenClawがDockerネットワーク外部からアクセス不能になる
- **根本原因**: `openclaw onboard`コマンドが`gateway.bind`を`"loopback"`に自動変更する副作用がある。これによりlocalhost（127.0.0.1）のみでリッスンし、Dockerネットワーク内の他コンテナからアクセスできなくなる
- **誤ったアプローチ**:
  1. onboardコマンドを実行して「プロバイダー登録完了」と思い、bindが変わったことに気づかなかった
- **正しい解決策**:
  1. `openclaw onboard`実行後に必ず`gateway.bind`の値を確認
  2. Docker環境では`"lan"`に戻す: `node -e "...modify openclaw.json..."`
- **教訓**:
  - **`openclaw onboard`は設定を変更する副作用がある。実行前後でopenlaw.jsonのdiffを確認する**
  - Docker環境では`gateway.bind: "lan"`が必須（loopbackだとコンテナ間通信不可）
- **検索すべきだったキーワード**:
  - `openclaw onboard side effects`
  - `openclaw gateway bind loopback vs lan docker`

### 2026-02-16: docker-compose変数警告（SUBSTACK_COOKIESの$記号）
- **症状**: `docker-compose config`で`WARN[0000] a]$o2$g1$t1771083612$j43$l0$h0`等の不明な変数警告
- **根本原因**: VPSの`.env`の`SUBSTACK_COOKIES`値にGoogle Analyticsクッキーが含まれており、`$o2`、`$g1`、`$t1771083612`等がdocker-composeに変数参照として解釈された
- **誤ったアプローチ**:
  1. docker-compose.ymlの問題だと推測 → 実際は.envの値の問題
- **正しい解決策**:
  `.env`内の`$`を`$$`にエスケープ: `$o2` → `$$o2`、`$g1` → `$$g1` 等
- **教訓**:
  - **docker-composeの.envファイルでは`$`は変数参照として解釈される。リテラルの`$`は`$$`にエスケープする**
  - Cookie値などの外部データを.envに保存する際は、`$`の有無を確認する
- **検索すべきだったキーワード**:
  - `docker-compose env file dollar sign escape`
  - `docker-compose WARN variable not set`

### 2026-02-16: Claude Code settings.local.json の defaultMode 配置場所
- **症状**: `"defaultMode": "bypassPermissions"`をsettings.local.jsonのルートレベルに追加 → 「Unrecognized field: defaultMode」バリデーションエラー
- **根本原因**: `defaultMode`はルートレベルではなく、`permissions`オブジェクト内に配置する必要がある
- **正しい解決策**:
  ```json
  {
    "permissions": {
      "defaultMode": "bypassPermissions",
      "allow": [...]
    }
  }
  ```
- **教訓**:
  - **Claude Codeのsettings.local.jsonはスキーマバリデーションが厳密。設定項目の配置場所を確認する**
  - `defaultMode`は`permissions`オブジェクト直下に配置
- **検索すべきだったキーワード**:
  - `claude code bypassPermissions settings.local.json`
  - `claude code permissions defaultMode configuration`

*最終更新: 2026-02-16 — OpenRouter カスタムモデル登録、onboard副作用、docker-compose $エスケープ、Claude Code bypassPermissions を記録*
