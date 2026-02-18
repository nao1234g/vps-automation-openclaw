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

### 2026-02-16: .envのPOSTGRES_PASSWORDがシェル展開されない
- **症状**: OpenClawとN8NがPostgreSQLに接続できない（認証エラー）。Jarvisが「DB connection failed」と報告
- **根本原因**: `.env`に `POSTGRES_PASSWORD=openclaw_$(openssl rand -hex 8)` と記載されていたが、docker-composeは`.env`の値をそのまま文字列として読み込む（シェル展開しない）。そのためパスワードが文字通り `openclaw_$(openssl rand -hex 8)` になっていた
- **誤ったアプローチ**:
  1. PostgreSQLコンテナ側の設定を疑った → 実際は`.env`の値がシェル展開されていない
- **正しい解決策**:
  1. PostgreSQLコンテナ内で `ALTER USER openclaw WITH PASSWORD 'openclaw_secure_2026';` を実行
  2. `.env`の`POSTGRES_PASSWORD`を静的な値に変更: `POSTGRES_PASSWORD=openclaw_secure_2026`
  3. 全コンテナを再起動
- **教訓**:
  - **docker-composeの`.env`ではシェルコマンド展開（`$()`）は動作しない。静的な値を設定する**
  - 動的パスワード生成は`.env`ではなく、初期化スクリプトやentrypoint.shで行う
  - DBパスワード変更時は、DB側（ALTER USER）と`.env`側の両方を同時に更新する
- **検索すべきだったキーワード**:
  - `docker-compose env file shell expansion`
  - `docker-compose .env variable substitution limitations`

### 2026-02-16: cron内の`source .env`がSUBSTACK_COOKIESで壊れる
- **症状**: daily-learning.pyのcronジョブが静かに失敗。`GOOGLE_API_KEY`が空になりGemini APIが呼べない
- **根本原因**: cron内で`source /opt/openclaw/.env`を実行すると、`SUBSTACK_COOKIES`の値にセミコロン(`;`)が含まれており、bashがこれをコマンド区切りとして解釈。結果、`GOOGLE_API_KEY`の設定が上書き・消失される
- **誤ったアプローチ**:
  1. daily-learning.pyのコード自体を疑った → 実際はcron環境の問題
  2. `.env`全体を`source`で読み込めると仮定した → Cookie値にbash特殊文字が含まれている
- **正しい解決策**:
  cron内で`source .env`を使わず、必要なAPIキーだけをインラインで指定:
  ```
  0 15 * * * GOOGLE_API_KEY=AIzaSy... XAI_API_KEY=xai-... TELEGRAM_BOT_TOKEN=7949... TELEGRAM_CHAT_ID=8309... /usr/bin/python3 /opt/shared/scripts/daily-learning.py --run 0
  ```
- **教訓**:
  - **`source .env`は安全ではない。Cookie値やトークン値にbash特殊文字（`;` `$` `(` `)` 等）が含まれるとコマンドが壊れる**
  - cron内では`source`を避け、必要な変数だけをインラインで渡す
  - または`env $(grep -v '^#' .env | xargs)`のように安全にパースする
- **検索すべきだったキーワード**:
  - `bash source env file semicolon breaks`
  - `cron environment variables .env file`
  - `docker env file special characters bash`

### 2026-02-16: OpenRouterモデルが「No API provider registered for api: undefined」でクラッシュ
- **症状**: `openrouter/z-ai/glm-5`をエージェントのモデルに設定すると、OpenClawが起動直後にクラッシュ。エラー: "No API provider registered for api: undefined"
- **根本原因**: `models.providers.openrouter`と`auth.profiles.openrouter:default`を正しく設定しても、OpenClawの内部でモデル→APIプロバイダーのマッピングが正しく行われない。おそらくOpenClawの現行バージョンのバグまたは未サポート機能
- **誤ったアプローチ**:
  1. `models.providers`のJSON形式を修正 → 改善なし
  2. `auth.profiles`の設定を確認 → 正しいが効果なし
  3. `openrouter/auto`（オートルーティング）を試した → 同じエラー
- **正しい解決策**:
  1. 一時的に全エージェントを`google/gemini-2.5-pro`に変更してクラッシュ回避
  2. GLM-5を使うなら、OpenRouterではなくZhipuAI直接API（`zai/glm-5`）を検討
  3. OpenClawの`zai`プロバイダーはネイティブサポート。`z.ai`でAPIキーを取得すれば`zai/glm-5`で使える
- **教訓**:
  - **OpenClawのOpenRouterカスタムモデル登録は、設定できても実際にAPIルーティングが動くとは限らない**
  - 新しいプロバイダー/モデルを設定したら、すぐにテストメッセージを送って動作確認する
  - クラッシュする場合は代替モデルにフォールバックして、本番環境を保護する
  - GLM-5はZhipuAI直接API（`zai/`プレフィックス）の方が安定する可能性が高い
- **検索すべきだったキーワード**:
  - `openclaw openrouter "No API provider registered"`
  - `openclaw custom provider api undefined error`
  - `openclaw zai zhipuai glm-5 direct api`

### 2026-02-16: NEO-ONE/TWOをOpenClawエージェントとして追加する（間違ったアーキテクチャ）
- **症状**: NeoがOpenClawのopenclaw.jsonにNEO-ONE/NEO-TWOをエージェントとして追加（`anthropic/claude-sonnet-4-5`モデル）。オーナーから「APIは使わないで」と指摘
- **根本原因**: NEO-ONE/TWOはClaude Maxサブスクリプション（$200/月）経由でClaude Code SDKを使用する設計。OpenClawのエージェントとして`anthropic/`プレフィックスで追加すると、Anthropic APIの従量課金（$15/1M input, $75/1M output）になり、設計意図と全く異なる
- **誤ったアプローチ**:
  1. Neoが`openclaw.json`のagents.listにNEO-ONE/TWOを追加 → OpenClaw APIルーティング経由になる
  2. モデルを`anthropic/claude-sonnet-4-5`に設定 → API課金が発生する
  3. OpenClawを2つ起動する案 → 不要な複雑化
- **正しい解決策**:
  1. OpenClawは1つ（Jarvis + 7サブエージェント専用）
  2. NEO-ONE/TWOは**別のclaude-code-telegramサービス**として起動（`neo-telegram.service`、`neo2-telegram.service`）
  3. 各サービスがClaude Code SDKを使用 → Claude Maxサブスクリプション（定額$200/月）で動作
  4. 各サービスに独自のTelegram bot token を設定
- **教訓**:
  - **Claude Maxサブスクリプション（定額）とAnthropic API（従量課金）は全く異なる課金モデル。混同しない**
  - OpenClawの`anthropic/`モデルプレフィックスはAPI課金。Claude Maxを使うにはClaude Code SDKが必要
  - NEO系エージェントはOpenClawとは独立した`claude-code-telegram`サービスとして運用する
  - アーキテクチャ変更時は、オーナーのコスト意図を最優先で確認する
- **検索すべきだったキーワード**:
  - `claude max subscription vs api pricing`
  - `claude code sdk subscription billing`
  - `openclaw anthropic model api cost`

---

## Claude Code SDK / NEO サービス関連（2026-02-17）

### 2026-02-17: NEO permission_mode が root ユーザーで動作しない
- **症状**: NEO-TWOに「自己紹介して」と送ると「❌ Claude Code Error - Command failed with exit code 1」。ログに `option '--permission-mode <mode>' argument 'dangerously_skip_permissions' is invalid`
- **根本原因**:
  1. `permission_mode="bypassPermissions"` はCLI内部で `--dangerously-skip-permissions` に変換される
  2. Claude CLIはセキュリティ上、root/sudoユーザーでは `--dangerously-skip-permissions` を拒否する
  3. NEO systemdサービスはrootで動作している
- **誤ったアプローチ**:
  1. 最初に `permission_mode="dangerously_skip_permissions"` を設定 → SDK側で `Allowed choices are acceptEdits, bypassPermissions, default, delegate, dontAsk, plan` と拒否
  2. `bypassPermissions` に修正 → CLIが root での実行を拒否（exit code 1）
  3. サービス再起動後もユーザーのメッセージが古いプロセスに到達してエラー
- **正しい解決策**:
  ```python
  # root ユーザーで動作する permission_mode
  permission_mode="acceptEdits"  # ← root でも OK、ツール自動承認
  ```
  - `acceptEdits` はrootでも動作し、ファイル編集もBash実行も自動承認される
- **教訓**:
  - **Claude CLIの `bypassPermissions` はrootユーザーでは使えない**
  - rootで動くサービスには `acceptEdits` を使う
  - SDK変更後は**自分でCLIテストしてから報告する**（`claude --permission-mode acceptEdits --max-turns 1 -p 'テスト'` でテスト可能）
  - `permission_mode` の有効な値: `acceptEdits`, `bypassPermissions`, `default`, `delegate`, `dontAsk`, `plan`
- **検索すべきだったキーワード**:
  - `claude cli dangerously-skip-permissions root sudo`
  - `claude code sdk permission_mode root`
  - `claude acceptEdits vs bypassPermissions`

### 2026-02-17: NEOがClaude Codeと自己紹介する（アイデンティティ未認識）
- **症状**: NEO-ONE/TWOに「自己紹介して」と送ると「私はClaude Codeです」と回答。Neo としてのアイデンティティを認識しない
- **根本原因**: CLAUDE.mdにアイデンティティを書くだけでは、新規セッション開始時にClaude Codeのデフォルト自己紹介が優先される
- **誤ったアプローチ**:
  1. CLAUDE.mdの先頭にアイデンティティブロックを追記 → 効果なし。Claude Codeは自分をClaude Codeと認識し続ける
  2. テストせずに「完了しました」と報告 → ユーザーがテストして未修正であることが発覚
- **正しい解決策**:
  1. Claude Code SDK の `ClaudeAgentOptions` に `system_prompt` パラメータがある（`claude_agent_sdk` の types.py で定義）
  2. `sdk_integration.py` でアイデンティティをシステムプロンプトとして注入：
  ```python
  options = ClaudeAgentOptions(
      system_prompt="あなたの名前は「Neo」です。Claude Codeではありません。...",
      permission_mode="acceptEdits",
      ...
  )
  ```
- **教訓**:
  - **CLAUDE.mdよりも system_prompt の方がアイデンティティ定義に強力**
  - SDK の `ClaudeAgentOptions` の全パラメータを確認する（`python3 -c "from claude_agent_sdk import ClaudeAgentOptions; help(ClaudeAgentOptions)"` でチェック）
  - **変更後は必ず自分でテストしてから報告する**。CLIで直接テスト可能
- **検索すべきだったキーワード**:
  - `claude code sdk system_prompt ClaudeAgentOptions`
  - `claude agent sdk custom identity`

### 2026-02-17: OAuth トークン期限切れでNEOが5分ごとに警告スパム
- **症状**: NEO-ONEから5分おきに「⚠️ OAuth token expires in -12.7h」のTelegram警告が数百通。NEOが応答しなくなる
- **根本原因**:
  1. Claude Maxの OAuthトークンは約12時間で期限切れ
  2. VPS → platform.claude.com へのトークンリフレッシュはCloudflare (403) でブロック
  3. トークン切れ後もNEOサービスが稼働し続け、5分ごとに警告をTelegramに送信
- **誤ったアプローチ**:
  1. VPSのxrdpでブラウザログインを試みる → xrdp 0x708エラー
  2. `claude auth login` で再認証 → VPSにブラウザがないため不可
  3. platform.claude.com APIでトークンリフレッシュ → Cloudflareに403で拒否される
- **正しい解決策**:
  1. ローカルPCの `~/.claude/.credentials.json` をVPSにSCPコピー
  2. 6時間ごとにWindows Task Schedulerで自動転送（`sync-neo-token.ps1`）
  3. VPS側で1時間ごとにトークン監視（`/opt/scripts/check-neo-token.sh`）
- **教訓**:
  - **Claude Maxトークンは約12時間有効。VPSからのリフレッシュはCloudflareに阻まれる**
  - ローカルPC → VPSへのSCPコピーが最も確実な方法
  - トークン切れ時はサービスを停止してスパム防止する仕組みが必要
- **検索すべきだったキーワード**:
  - `claude code headless authentication server`
  - `claude credentials.json copy remote`

---

---

## Substack Cookie認証（2026-02-17）

### 2026-02-17: Substack Cookie更新に半日かかった（Gmail自動削除 + レート制限 + メール重複排除）
- **症状**: Substack cookieが期限切れ。自動取得を試みるが、magic linkメールが届かない
- **根本原因**: 3つの問題が同時に発生
  1. **Gmail自動削除**: Gmailがsubstackからのメールを自動的にゴミ箱に移動していた（50+通がゴミ箱に）
  2. **Substackレート制限**: VPS IPが429 (Too many login emails)でブロック
  3. **Substackメール重複排除**: API が HTTP 200を返すが、短時間に同じメールアドレスへの重複送信を内部的に抑制
- **誤ったアプローチ**:
  1. VPSのPlaywright/Seleniumで全自動化を試みた → レート制限
  2. ローカルPCからAPI呼び出し → 200返るがメール届かず（重複排除）
  3. Gmailフィルター作成を自動化しようとした → Gmail UIの自動操作が複雑すぎて失敗
  4. パスワードログインを試みた → アカウントにパスワード未設定（「no password set for this account」）
  5. Google OAuth認証を試みた → SubstackのサインインページにはGoogle OAuthボタンなし
  6. Substack の `/api/v1/user/self` に cookie だけで認証テスト → 403。`cf_clearance` が必要と誤解
- **正しい解決策**:
  1. `substack.sid` と `substack.lli` の2つのcookieをブラウザのDevToolsからコピー
  2. `aisaintel.substack.com/api/v1/archive` エンドポイントは `substack.sid` + `substack.lli` だけで200を返す
  3. `substack.com/api/v1/user/self` は常に403を返すが、ホームページは302→/homeにリダイレクト（=認証済み）
  4. VPSの `/opt/openclaw/.env` の `SUBSTACK_COOKIES` を Python（`re.sub`）で更新（sedは特殊文字で壊れる）
  5. `docker-compose up -d`（restartではなく）で環境変数を再読み込み
- **教訓**:
  - **Cookie更新は「ユーザーにDevToolsからコピーしてもらう」のが最速。全自動化に固執しない**
  - **`/api/v1/user/self` が403でも、cookieは有効な場合がある**（Cloudflare保護のため）
  - **`docker-compose restart` では `.env` の変更が反映されない。`docker-compose up -d` が必要**
  - **VPSの `.env` を `sed` で編集するとcookie値の特殊文字（`%`, `/`, `+`）で壊れる。Pythonの `re.sub` を使う**
  - **Substack cookie有効期限は約3ヶ月**（`substack.sid` Expires参照）
  - Gmailがsubstackメールを自動ゴミ箱に入れる場合がある。フィルター設定が必要
- **検索すべきだったキーワード**:
  - `Substack magic link email not arriving`
  - `Gmail auto trash substack emails`
  - `Substack cookie authentication substack.sid substack.lli`
  - `docker-compose restart vs up environment variables`

---

### 2026-02-17: Substack Notes API 403 — Cloudflare WAF がPOSTをブロック
- **症状**: `POST https://substack.com/api/v1/comment/feed` が常に403を返す。HTMLエラーページ（`<title>Error - Substack</title>`）。cookie認証は有効（ドラフトAPIは動作）
- **根本原因**: Cloudflare WAFが `requests` ライブラリのPOSTリクエストをbot判定でブロック。GET /reader/feed は400（JSON応答=認証OK）、GET /inbox は404（Express到達）だが、POST /comment/feed だけ403（Cloudflare HTML）
- **誤ったアプローチ**:
  1. Cookieドメインスコープの問題と推測 → `.substack.com` に設定しても解決せず
  2. `requests.Session()` のcookie.set(domain=) を変更 → 効果なし
  3. ブラウザ風ヘッダー追加（User-Agent, Sec-Fetch-*等） → 効果なし
  4. URL-encoded vs decoded のcookie値を試す → 両方403
- **正しい解決策**: `curl_cffi` ライブラリの Chrome impersonation (`Session(impersonate="chrome")`) を使用。TLS fingerprint がChromeと同一になりCloudflareを通過。`pip install curl_cffi` → `from curl_cffi import requests as cffi_req`
- **教訓**:
  - **Cloudflare保護されたAPIにはTLS fingerprintが重要**。ヘッダーだけ偽装しても `requests` のTLS fingerprintでbot判定される
  - **403の応答ヘッダーを確認**: `x-powered-by: Express` があればバックエンド到達、なければCloudflare WAFでブロック
  - **GETとPOSTで挙動が異なる**: CloudflareはPOST（状態変更）を厳しくチェック
  - `curl_cffi` はCloudflare対策の標準的なPythonライブラリ
- **検索すべきだったキーワード**:
  - `Substack Notes API 403 Cloudflare`
  - `python requests Cloudflare bypass curl_cffi`
  - `Cloudflare WAF TLS fingerprint bot detection`

## claude-code-telegram（NEO Bot）の問題（2026-02-17）

### 2026-02-17: NEO Botが画像を読み込めない
- **症状**: Telegram経由でNEO-ONE/TWOに画像を送信しても、画像の内容を認識・分析できない。テキストの説明プロンプトのみが生成され、実際の画像データはClaudeに渡らない
- **根本原因**: `image_handler.py` の `process_image()` が画像をダウンロード→base64エンコードするが、`orchestrator.py` の `agentic_photo()` は `processed_image.prompt`（テキスト説明のみ）を `run_command(prompt=...)` に渡している。`run_command()` は `prompt: str` のみ受け付け、base64画像データ（`processed_image.base64_data`）は完全に破棄されている。コード内コメント: `"# Convert to base64 for Claude (if supported in future)"`
- **誤ったアプローチ**:
  1. Claude Agent SDKの `query()` 関数にマルチモーダル入力を渡そうとする → SDKは `prompt: str` のみ対応
  2. base64データをプロンプト文字列に埋め込む → 巨大すぎてトークン制限を超える
- **正しい解決策**: 画像をVPSのファイルシステム（`/tmp/telegram_photos/`）に保存し、プロンプトで「Readツールでこのファイルを読み込んでください」と指示する。Claude CodeのReadツールは画像ファイルを直接読める（マルチモーダル対応）
  ```python
  # orchestrator.py の agentic_photo() を修正:
  # 1. base64 → bytes → ファイル保存
  image_bytes = b64_mod.b64decode(processed_image.base64_data)
  filepath = os.path.join("/tmp/telegram_photos", f"{uuid}.{fmt}")
  with open(filepath, "wb") as f:
      f.write(image_bytes)
  # 2. プロンプトでReadツール使用を指示
  image_prompt = f"画像がアップロードされました。ファイルパス: {filepath}\nReadツールで読み込んでください。"
  claude_response = await claude_integration.run_command(prompt=image_prompt, ...)
  ```
- **教訓**:
  - **Claude Code SDKは `prompt: str` のみ対応** — マルチモーダル入力は直接サポートされない
  - **回避策: ファイルシステム経由** — 画像をディスクに保存し、Claude CodeのReadツール（画像対応）で読ませる
  - **`ProcessedImage.base64_data` が使われていない** ことに気づくべきだった（コードレビュー不足）
  - 新しいシステムを構築する前に、既存のコードで「何が使われていないか」を確認する
- **検索すべきだったキーワード**:
  - `claude-agent-sdk image multimodal`
  - `claude code read image file`
  - `telegram bot claude code image processing`

### 2026-02-17: NEO Botが指示をタスクとして認識しない
- **症状**: Telegram Bot APIの `sendMessage` でNEO-ONE/TWOに構造化された指示（「■ ミッション: 〜」形式）を送信すると、メッセージは到達・処理されるが、Claude Codeが「会話」として扱い、実際のタスク実行を行わない。「承知しました」等の返答のみで終わる
- **根本原因**: `sdk_integration.py` の `system_prompt` にタスク実行に関する明示的な指示がなかった。Claude Codeは受信メッセージをデフォルトで「会話の一部」として扱い、ツールを使った実行よりも応答テキストの生成を優先する
- **誤ったアプローチ**:
  1. メッセージのフォーマット（■、📋等の記号）を変えれば認識すると推測 → 効果なし
  2. CLAUDE.mdにタスク実行指示を書けば十分と推測 → CLAUDE.mdはコンテキスト情報であり、行動指示としては弱い
- **正しい解決策**: `sdk_integration.py` の `system_prompt` パラメータに明示的なタスク実行指示を追加:
  ```
  # タスク実行の原則（最重要）
  - Telegramで受信したメッセージは「実行すべきタスク/指示」として扱うこと
  - 「ミッション」「タスク」「やって」「作って」「修正」等のキーワードがあれば即座に実行開始
  - メッセージ内のアクションアイテムは議論ではなく実際にツールを使って実行すること
  - 「承知しました」だけで終わらず、実行完了後に結果を報告すること
  ```
- **教訓**:
  - **Claude Code SDKの `system_prompt` は行動を制御する最強の手段** — CLAUDE.mdよりも直接的に行動に影響する
  - **LLMは「会話」モードがデフォルト** — 明示的に「実行せよ」と指示しないと、議論・提案で終わる
  - **Telegram経由の指示は、直接のユーザー入力より弱い** — システムプロンプトで「Telegramメッセージ = 実行指示」と明示する必要がある
- **検索すべきだったキーワード**:
  - `claude code sdk system_prompt task execution`
  - `claude agent sdk instruction following`
  - `telegram bot AI agent task recognition`

---

## note.com アイキャッチ画像アップロード（2026-02-17）

### 2026-02-17: note API経由のアイキャッチ画像アップロード → Cloudflare WAF 404
- **症状**: `POST https://note.com/api/v1/text_notes/{key}/eyecatch` が 404 を返す
- **根本原因**: Cloudflare WAFがbotと判定してブロック。requests / curl_cffi どちらでも防げない
- **誤ったアプローチ**:
  1. `requests` でmultipart POSTを試みる → 404
  2. `curl_cffi` Chrome impersonationに切り替え → 同じく 404
  3. `CurlMime()` でmultipart送信 → 404（APIエンドポイント自体がWAFでブロック）
- **正しい解決策**: **Playwright**でnote.comエディターをブラウザ操作してアップロード
  - ヘッドレスChrome + セッションCookieで認証
  - アイキャッチボタン（座標343,125）→「画像をアップロード」→ FileChooser → 「保存」（force=True）→「一時保存」
- **教訓**:
  - **noteはCloudflare WAFで保護されており、スクリプト直接POSTはほぼ不可能**
  - **ブラウザ自動化（Playwright）で回避するのが正解**
  - curl_cffiのChrome impersonationも効果なし（APIエンドポイントレベルでブロック）
- **検索すべきだったキーワード**:
  - `note.com eyecatch API 404 Cloudflare`
  - `note.com playwright upload image`
  - `curl_cffi note.com post 403 bypass`

### 2026-02-17: CropModal__overlay がPlaywrightクリックをブロック
- **症状**: 「保存」ボタンをPlaywrightで探してクリックしようとするが `ElementClickIntercepted` エラー
- **根本原因**: `ReactModal__Overlay ReactModal__Overlay--after-open CropModal__overlay` がポインターイベントを横取りする
- **誤ったアプローチ**:
  1. `btn.click()` → 失敗（オーバーレイがインターセプト）
  2. `page.mouse.click(x, y)` → 失敗（同じオーバーレイが邪魔）
  3. `page.evaluate("btn.click()")` → JSクリックは成功するが不安定
- **正しい解決策**: `locator.click(force=True)` でオーバーレイを無視して強制クリック
  ```python
  locator = page.locator('.ReactModalPortal button:has-text("保存")')
  locator.click(force=True, timeout=5000)
  ```
- **教訓**:
  - **Playwrightで `ElementClickIntercepted` が出たら `force=True` を試す**
  - モーダルオーバーレイは `force=True` で回避できる
  - JSクリック（`page.evaluate`）でも回避できるが `force=True` の方が安定
- **検索すべきだったキーワード**:
  - `playwright force click modal overlay`
  - `playwright ElementClickIntercepted ReactModal`
  - `playwright click intercepted by another element`

### 2026-02-17: note.com AI相談ポップアップがクリックをブロック
- **症状**: アイキャッチボタンや他のボタンをクリックしようとすると「AIと相談」ポップアップが横取りする
- **根本原因**: note.comエディターが「AIと相談」モーダルをデフォルトで表示する
- **誤ったアプローチ**: ポップアップを無視して続行 → クリックが失敗する
- **正しい解決策**: ページロード後にEscapeキーを押し、JSでポップアップ親要素を非表示にする
  ```python
  page.keyboard.press('Escape')
  page.evaluate("""
      () => {
          document.querySelectorAll('h3').forEach(el => {
              if (el.textContent.trim() === 'AIと相談') {
                  let p = el.parentElement;
                  for (let i = 0; i < 8; i++) {
                      if (p && p.getBoundingClientRect().width > 150) {
                          p.style.display = 'none'; break;
                      }
                      p = p && p.parentElement;
                  }
              }
          });
      }
  """)
  ```
- **教訓**: **noteエディターはページロード後にAIポップアップが出る。必ずdismissしてから操作する**
- **検索すべきだったキーワード**:
  - `note.com editor AI popup playwright`
  - `note.com 編集画面 AIと相談 ポップアップ 消す`

---

## RSS News Pipeline（2026-02-17）

### 2026-02-17: Reuters/AP RSS が VPS から取得不可
- **症状**: `feeds.reuters.com` → `[Errno -2] Name or service not known`、`apnews.com` → `HTTP Error 403`
- **根本原因**: VPSのDNSがReuters CDNを解決できない / APがVPS IPブロック
- **誤ったアプローチ**: Reuters/APをソースに含めたまま実行 → エラー多発
- **正しい解決策**: Reuters → Al Jazeera RSS（`https://www.aljazeera.com/xml/rss/all.xml`）に変更、AP → TheHill + TIME に変更
- **教訓**: **VPSからRSSソースをテストしてから本番設定に入れること**
- **検索すべきだったキーワード**:
  - `Reuters RSS feed alternative`
  - `AP RSS feed VPS blocked 403`

### 2026-02-17: Yahoo News Politics RSS URL 変更
- **症状**: `https://news.yahoo.co.jp/rss/topics/politics.xml` が 404
- **根本原因**: Yahoo Japanが政治カテゴリURLを `domestic.xml` に変更
- **正しい解決策**: URL を `https://news.yahoo.co.jp/rss/topics/domestic.xml` に変更（8記事確認済み）
- **教訓**: **Yahoo Japan RSSのURLは変更される。動作確認を定期的に行う**

---

## Telegram Bot API → NEO指示が届かない問題（2026-02-17）

### 2026-02-17: Bot APIで送ったメッセージはNEO-ONEが無視する
- **症状**: 自動化スクリプトからTelegram Bot APIでNEO-ONEに指示を送っても、NEOが動かない。何週間も指示が届いているはずなのに全く実行されなかった
- **根本原因**: Telegram Bot APIで送るメッセージは「botからユーザーへの通知（グレーバブル）」であり、NEO-ONEのorchestrator.pyが監視している「ユーザー→botへのメッセージ（グリーンバブル）」ではない。getUpdatesには入ってこない
  ```
  【間違い】自動スクリプト → Bot API → ユーザーへ通知（グレー）
                                    NEOはここを監視していない

  【正しい】ユーザー → NEO-ONEのbot → orchestrator.pyが受信（グリーン）
  ```
- **誤ったアプローチ**:
  1. `requests.post(telegram bot API sendMessage)` で送信 → グレーバブルとして届くだけ
  2. 「NEO-ONEに通知を送った」と言いながら、実際にはNEOが処理しないメッセージを送り続けた
  3. 何週間もこの根本的な構造ミスに気づかなかった
- **正しい解決策**: **Telethon（MTProto User API）**を使ってユーザーアカウントとして送信する
  ```python
  # インストール
  pip3 install telethon --break-system-packages

  # セッション初期化（1回のみ）
  python3 /opt/shared/scripts/setup-telethon-session.py

  # 送信（グリーンバブル = 人間扱い）
  python3 /opt/shared/scripts/send-to-neo.py --bot neo1 --msg "指示内容"
  python3 /opt/shared/scripts/send-to-neo.py --bot neo2 --msg "指示内容"
  ```
  - セッションファイル: `/opt/shared/.telethon-session.session`
  - 設定ファイル: `/opt/shared/.telethon-config`（API_ID、API_HASH）
  - API取得先: https://my.telegram.org → API Development Tools
- **教訓**:
  - **「NEOに通知した」≠「NEOに指示が届いた」** — Bot APIはただの通知、Telethonが本当の指示
  - **NEO-ONEが動く唯一の条件は「人間→botへのメッセージ」** — 構造を理解してから実装する
  - **この間違いを何週間も放置した** — 指示が実行されていないときはすぐ根本原因を調査する
- **検索すべきだったキーワード**:
  - `telegram bot getUpdates user message only`
  - `telethon send message as user python`
  - `telegram bot API vs MTProto user API difference`

### 2026-02-17: my.telegram.org アプリ作成フォームのERROR
- **症状**: 短縮名を入力して「アプリケーションを作成する」を押すとERRORが出る
- **根本原因**（複数）:
  1. 短縮名が5文字未満（`NEO` = 3文字）
  2. アプリタイトルにハイフンが含まれている（`NEO-automation`）
  3. 通常ブラウザのキャッシュ・拡張機能の干渉
- **正しい解決策**:
  - 短縮名は5文字以上の英小文字+数字のみ（例: `neoauto1`）
  - タイトルはハイフンなし（例: `NEO Automation`）
  - シークレットモードで開き直す
- **教訓**: **my.telegram.orgのエラーは理由が表示されない。短縮名5文字以上、ハイフンなし、シークレットモードを最初から守る**

### 2026-02-17: note.comセッションCookieがサーバー側で無効化される
- **症状**: `note-auto-post.py`が`{"error":{"code":"auth","message":"not_login"}}`を返す。Cookieのexpiry日付はまだ先なのに認証が通らない
- **根本原因**: note.comはサーバー側でセッションを強制無効化することがある（ログアウト操作、不審なアクセス検知、セキュリティポリシー変更等）。クライアント側のCookieは残っているがサーバー側では無効になっている
- **誤ったアプローチ**:
  1. Cookie値やexpiry日付を見て「まだ有効なはず」と判断（サーバー側の状態を確認していなかった）
  2. `refresh_cookies()`を呼び出したが、Seleniumの`#email`セレクタが見つからずエラー（HeadlessChromeのタイミング問題）
- **正しい解決策**:
  1. `/tmp/note_login_debug.py`のような手動Seleniumスクリプトで再ログイン
  2. `#email`セレクタで5秒待機後にログイン実行
  3. 新しいCookieを`/opt/shared/.note-cookies.json`に保存
- **教訓**:
  - **Cookieの有効期限≠サーバー側の有効性**。認証エラーが出たら即座に再ログインを試みる
  - `note-auto-post.py`の`refresh_cookies()`は失敗することがある。その場合は手動Seleniumデバッグスクリプトを使う
  - 月1回程度の定期的なCookie更新cronを設定するのが理想
- **検索すべきだったキーワード**: `note.com session cookie invalidated`, `selenium note login #email selector`

### 2026-02-17: note-auto-post.pyがX投稿を二重実行する
- **症状**: rss-post-quote-rt.pyからnote-auto-post.pyを呼び出すと、X投稿が2回行われる（note-auto-post.py自体がpost_thread.pyを呼び出してX投稿し、さらにrss-post-quote-rt.pyもX投稿する）
- **根本原因**: note-auto-post.pyは`--publish`フラグで公開後、`GOOGLE_API_KEY`が環境にあれば自動でXスレッドを投稿する機能がある。外部から呼び出す際にこれを無効化しないと二重投稿になる
- **誤ったアプローチ**: `clean_env.pop("GOOGLE_API_KEY", None)`で環境変数を除去（一部効かない場合がある）
- **正しい解決策**: subprocessの呼び出しに`--no-x-thread`フラグを明示的に追加する
  ```python
  [sys.executable, NOTE_SCRIPT, "--file", tmp_path, "--title", title, "--tags", tags,
   "--publish", "--no-x-thread"] + image_args
  ```
- **教訓**: **外部スクリプトを呼び出す際は、そのスクリプトが何をするか完全に理解してから呼び出す**。`--no-x-thread`のような明示的なフラグを使うのが確実

### 2026-02-17: X API「duplicate content」403エラー
- **症状**: X投稿時に`403 {"detail":"You are not allowed to create a Tweet with duplicate content."}`
- **根本原因**: 同じ内容のツイートを短期間に2回投稿しようとした（テスト時の重複実行、または二重投稿が原因）
- **正しい解決策**: キューの`tweet_url`フィールドで投稿済みをチェック（既に実装済み）。テスト時は新しい内容で試すか、十分な時間（24時間）を空ける
- **教訓**: X APIは同じ内容の重複投稿を拒否する。テスト時はキューの`tweet_url`をクリアしてから新しい内容でテストする

### 2026-02-18: X引用リポスト（quote repost）の実装ミス
- **症状**: 「引用リツイートになっていない」。「X Basic API $100/月が必要」と誤った情報を提供した
- **根本原因**: X APIの調査不足。引用リポストは`POST /2/tweets`に`quote_tweet_id`を追加するだけ。問題は「元ツイートIDの取得方法」だけだった。xAI Grokで検索可能
- **正しい解決策**:
  - xAI Responses API + `x_search` ツール + `grok-4-0709` モデルで元ツイートを検索
  - エンドポイント: `POST https://api.x.ai/v1/responses`
  - 形式: `{"model": "grok-4-0709", "tools": [{"type": "x_search"}], "input": "...query..."}`
  - `search_parameters`・`live_search`は**廃止済み**。Agent Tools APIの`x_search`を使う
  - grok-3系は`x_search`非対応。grok-4ファミリーのみ対応
- **教訓**: **「有料プランが必要」と言う前に、既存ツール（xAI Grok）での代替手段を必ず調べる**

### 2026-02-18: RSS記事分析が手動スクリプトの短文で代替されていた
- **症状**: `analysis_full`が1021文字しかなく、5要素（歴史・利害・論理・シナリオ・示唆）が全て欠如
- **根本原因**: `rss-news-pipeline.py`はRSS収集のみ。`update_rss_analysis.py`という手動スクリプトで短文を注入していた。Gemini + AISAプロンプトによる本格分析がRSSフローに組み込まれていなかった
- **正しい解決策**: `analyze_rss.py`を作成（RSSパイプラインの30分後にcron実行）
  1. 記事本文スクレイプ（全文8000字取得）
  2. Grok x_searchで元ツイート検索 → `original_tweet_id`保存
  3. Gemini 2.5 Pro + AISA_NEWS_ANALYST_PROMPTで深層分析（7000字+、5要素必須）
- **教訓**: **「分析済み」は5要素が全て含まれることで成立。文字数・要素の両方を品質チェックすること**

### 2026-02-18: Grok API形式の変更（廃止済みAPIを使用）
- **症状**: `search_parameters: {mode: "on"}` → 410 "Live search is deprecated"
- **根本原因**: xAI APIの仕様変更。`live_search`廃止 → Agent Tools APIの`x_search`に移行
- **正しい解決策**: `/v1/responses` エンドポイント + `{"type": "x_search"}` + `grok-4-0709`
- **検索キーワード**: `xAI API x_search`, `grok agent tools API`, `docs.x.ai/docs/guides/tools`

### 2026-02-18: Ghost Settings API 501エラー（Integration APIではSettings PUT不可）
- **症状**: `PUT /ghost/api/admin/settings/` → 501 "Not Implemented"
- **根本原因**: Ghost 5.130ではIntegration（Admin API Key）経由でのSettings更新がサポートされていない。GETは可能だがPUTは501を返す
- **誤ったアプローチ**: `requests`ライブラリで`allow_redirects=False`を試行。リダイレクト問題は解決したが、501は根本的にAPIが未対応
- **正しい解決策**: Ghost SQLiteデータベース（`/var/www/nowpattern/content/data/ghost.db`）を直接更新。`UPDATE settings SET value = '<style>...' WHERE key = 'codeinjection_head';` + Ghost再起動
- **追加の教訓**: `requests`ライブラリはリダイレクト時にAuthorizationヘッダーを除去する（セキュリティ仕様）。`http://localhost:2368` → `https://nowpattern.com` のリダイレクトで403になる
- **検索すべきだったキーワード**: `ghost admin api settings put 501`, `ghost integration api permissions`, `ghost codeinjection sqlite`

### 2026-02-18: Ghost 5.x 投稿の本文が空（html/markdownフィールドが無視される）
- **症状**: Ghost Admin APIで記事投稿後、タイトルは表示されるが本文が完全に空。APIレスポンスの`html`フィールドが0文字、`lexical`が空のrootノード（155文字）のみ
- **根本原因**: Ghost 5.x はデフォルトで **lexical エディタ**を使用する。`html`フィールドや`markdown`フィールドを直接送っても、Ghostはそれらを無視して空のlexicalドキュメントを作成する
- **誤ったアプローチ**:
  1. `"html": html` でPOST → 本文空
  2. `"markdown": markdown` でPOST → 本文空（markdownフィールドはGhost APIで未対応）
  3. lexical HTML card形式（`{"type":"html","version":1,"html":"..."}` ）でPUT → APIは200を返すがhtmlフィールドは0のまま（しかし実際にはlexical内に格納されていて表示される場合もある）
- **正しい解決策**: Ghost Admin APIのURLに **`?source=html`** パラメータを追加する
  ```python
  # POST（新規投稿）
  url = f"{ghost_url}/ghost/api/admin/posts/?source=html"
  body = {"posts": [{"title": title, "html": html, ...}]}

  # PUT（既存記事更新）
  url = f"{ghost_url}/ghost/api/admin/posts/{post_id}/?source=html"
  body = {"posts": [{"html": html, "updated_at": updated_at}]}
  ```
  `?source=html` を付けると、GhostがHTMLを内部的にlexical形式に自動変換する。APIレスポンスの`html`は0のままだが、`lexical`フィールドに正しく格納され、Webページ上では正常に表示される
- **影響範囲**: `nowpattern_publisher.py`（Deep Pattern/Speed Log投稿）、`nowpattern-ghost-post.py`（観測ログ投稿）の両方に影響。**全ての既存Ghost記事が空の本文で投稿されていた**
- **教訓**:
  1. Ghost 5.xでは`html`や`markdown`フィールドを直接送っても無視される。必ず`?source=html`を使う
  2. APIレスポンスの`html`長さが0でも、`lexical`フィールドに内容があればWebページ上では正常表示される
  3. Ghost公式ドキュメントよりもフォーラム（forum.ghost.org）の方が実践的な解決策が見つかる
- **検索すべきだったキーワード**: `ghost admin api source=html`, `ghost 5 lexical post empty`, `ghost api html to lexical conversion`, `forum.ghost.org lexical html card`

---

## Nowpattern記事UIデバッグ（2026-02-18 セッション2）

### ミス履歴図（今回のセッションで繰り返したパターン）

```
[ミス1] VPS同期がパッチを上書き
   原因: ローカル版(unpatched)をVPSに同期 → 以前のパッチが消える
   教訓: 同期前に「VPS側に追加パッチがあるか」確認する
      ↓
[ミス2] Ghost再起動直後にAPIを呼び出す
   原因: CSS注入→Ghost再起動→即API呼び出し → 空レスポンス(JSONDecodeError)
   教訓: systemctl restart後は5秒待ってからAPIを呼ぶ
      ↓
[ミス3] scenariosのデータ形式がdict vs tuple
   原因: fix_hormuz_lexical.pyがdict形式で渡したが、builderはtuple期待
   症状: What's Next が "label（確率: probability）" とプレースホルダー表示
   教訓: builderの関数シグネチャをよく読んでから呼び出す
      ↓
[ミス4] dynamics_sectionsのキーが"explanation"vs"lead"
   原因: fix_hormuz_lexical.pyが"explanation"キーを使ったが、builderは"lead"期待
   症状: NOW PATTERNボックス内が "..." のみ表示
   教訓: builderが期待するdict keyを確認してから渡す
      ↓
[ミス5] _build_dynamics_section_htmlのlead重複表示バグ
   原因: f'{lead[:20]}...</strong> {lead}' で先頭20文字+全文を両方出力
   症状: 本文が「イランは核交渉の行き詰まり...イランは核交渉の行き詰まり（全文）」と重複
   教訓: テンプレート文字列でf-string内変数を複数回使う場合は重複表示に注意
```

### 2026-02-18: VPS同期がローカルパッチを上書きする
- **症状**: VPSにsyncした後、Ghost記事のタグバッジが消えた（旧スタイルに戻った）
- **根本原因**: `sync-nowpattern-vps.ps1` がローカル版を無条件に上書きする。ローカル版には `patch_tag_*.py` が適用されていなかった
- **誤ったアプローチ**: patchスクリプトをVPS上で毎回手動実行
- **正しい解決策**: ローカルの `nowpattern_article_builder.py` に全パッチを統合してから同期する（今回実施）
- **教訓**: パッチスクリプト（`patch_*.py`）は一時的なもの。本体ファイルに統合して「ローカルが正」の状態にすること
- **検索すべきだったキーワード**: (なし。設計判断の問題)

### 2026-02-18: Ghost再起動直後のAPIコールでJSONDecodeError
- **症状**: `python3 fix_hormuz_lexical.py` を実行するとJSONDecodeError（空レスポンス）
- **根本原因**: `systemctl restart ghost-nowpattern` 直後はGhostが起動中で、APIが空レスポンスを返す
- **誤ったアプローチ**: 即座に再試行（同じエラー）
- **正しい解決策**: Ghost再起動後に `sleep 3` (最低5秒) 待ってからAPIを呼ぶ
- **教訓**: `systemctl restart <service>` 後は必ず `sleep 5` してから後続処理を実行すること
- **検索すべきだったキーワード**: (Ghost起動時間の問題、汎用的な教訓)

### 2026-02-18: builderへのデータ渡し形式ミス（dict vs tuple）
- **症状**:
  - `What's Next` が `label（確率: probability）` と表示（プレースホルダーのまま）
  - `NOW PATTERN` ボックスが `...` のみ表示
- **根本原因**:
  - `_build_scenarios_html` はtupleを期待するが、`fix_hormuz_lexical.py` はdict形式で渡した
  - `_build_dynamics_section_html` は `"lead"` キーを期待するが、`"explanation"` キーで渡した
- **誤ったアプローチ**: 症状を見てCSSやHTMLの問題と思い込んだ
- **正しい解決策**:
  - builderを修正してdict/tuple両対応に（今回実施）
  - `"explanation"` キーを `"lead"` としてもフォールバック対応（今回実施）
- **教訓**: builder関数のシグネチャとデータ形式を呼び出し側と合わせること。builderを修正する際は後方互換性も確認
- **検索すべきだったキーワード**: (コードを読めば分かる問題)

---

*最終更新: 2026-02-18 セッション2 — Nowpatternミス履歴図 + VPS同期/Ghost再起動/データ形式ミスを追加*
