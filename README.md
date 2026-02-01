# VPS自動化ロードマップ：OpenClaw（旧Clawdbot/Moltbot）導入ガイド

## 📖 概要

このリポジトリは、VPSサーバーへOpenClaw（旧名：Clawdbot → Moltbot）をセルフホストで導入し、N8N・OpenNotebookと連携するためのオートパイロットワークフローを提供します。

**OpenClawとは？**
- Anthropic Claude APIを使った強力なAIエージェント
- - ブラウザ操作、コード実行、ファイル操作などを自動化
  - - Telegram等のメッセンジャーと連携可能
    - - 2026年1月29日に名称が「Moltbot」から「OpenClaw」に変更
     
      - ---

      ## ⚠️ 重要な注意事項

      ### 🔒 セキュリティリスク
      OpenClawは**非常に強力な権限**を持つため、セキュリティ対策が必須です：

      - ❌ **メイン使用PCへのインストールは危険**
      - - ❌ **公開サーバーでの運用は厳禁**
        - - ✅ **専用VPS環境の利用を強く推奨**
          - - ✅ **SSHトンネル経由でのみアクセス**
           
            - ### 🛡️ 2つの防御層
           
            - #### 1. トンネル（外部攻撃からの防御）
            - - SSHトンネルで暗号化された通信経路を確立
              - - 外部からの不正アクセスを完全にシャットダウン
                - - ローカルホスト経由でのみUI接続
                 
                  - #### 2. ガードレール（内部事故の防止）
                  - - 重要な変更前に必ず人間の承認を得る（Human-in-the-loop）
                    - - 定期的な自動バックアップの設定
                      - - 大規模タスク前の確認プロセス
                       
                        - ---

                        ## 🚀 導入ロードマップ

                        ### Phase 1: VPSサーバーの契約

                        **推奨サービス:**
                        - **Xサーバー VPS**（日本語サポート・安定性）
                        - - AWS（グローバル展開・柔軟性）
                          - - ConoHa VPS（日本語・シンプル）
                           
                            - **最小スペック:**
                            - - CPU: 2コア以上
                              - - RAM: 4GB以上
                                - - ストレージ: 50GB以上
                                  - - OS: Ubuntu 22.04 LTS推奨
                                   
                                    - **代替案：自宅PC利用**
                                    - - 中古PC（1〜3万円程度）でも可能
                                      - - Linux（Ubuntu）をインストール
                                        - - リモックスなどの仮想化も検討
                                          - - ⚠️ メイン使用PCは絶対に避ける
                                           
                                            - ---

                                            ### Phase 2: SSH認証の設定


ConoHa VPSでは、コントロールパネルから簡単にSSH接続の設定ができます。

#### ステップ 2.1: ConoHaコントロールパネルでIPアドレスを確認

[1] [ConoHaコントロールパネル](https://cp.conoha.jp/)にログイン

[2] 左側のメニューから「**サーバー**」を選択

[3] サーバーリストが表示されます。対象のサーバーの**ネームタグ**をクリック

[4] 「**ネットワーク情報**」の「**IPアドレス**」の項目で確認

> 💡 このIPアドレスを後の手順で使用します

---

#### ステップ 2.2: SSHクライアントソフトの準備

**Windowsの場合**、以下のSSHクライアントを推奨：
- **TeraTerm**（無料、日本語対応）
  - 公式サイト: https://ttssh2.osdn.jp/
- **PuTTY**（無料、多機能）
  - 公式サイト: https://www.putty.org/

**macOS / Linuxの場合**：
- 標準搭載の`ssh`コマンドを使用（ターミナルから）

---

#### ステップ 2.3: パスワード認証でSSH接続（初回）

**■ macOS / Linuxの場合**

ターミナルを開いて以下を実行：
\`\`\`bash
ssh root@YOUR_VPS_IP
# 例: ssh root@123.456.789.012
\`\`\`

初回接続時に以下のメッセージが表示されます：
\`\`\`
The authenticity of host '123.456.789.012' can't be established.
Are you sure you want to continue connecting (yes/no)?
\`\`\`
→ **yes** と入力してEnter

VPS作成時に設定した**rootパスワード**を入力してログイン

**■ Windows（TeraTerm）の場合**

1. TeraTermを起動
2. 「ホスト」にVPSの**IPアドレス**を入力
3. 「TCPポート」は **22** のまま
4. 「サービス」は **SSH** を選択
5. 「OK」をクリック
6. ユーザ名：**root**
7. パスワード：VPS作成時に設定した**rootパスワード**
8. 「OK」をクリックしてログイン

> 📚 **詳細な手順は公式ドキュメント参照：**
> - [SSH接続でVPSにログインする](https://support.conoha.jp/v/vps_ssh/)
> - [TeraTermでのSSH接続設定](https://support.conoha.jp/v/vpstera/)
> - [PuTTYでのSSH接続設定](https://support.conoha.jp/v/vpsputty/)

---

#### ステップ 2.4: 公開鍵認証の設定（推奨・セキュリティ強化）

パスワード認証よりも安全な**公開鍵認証**の設定を強く推奨します。

**■ ローカルPCで鍵ペアを生成**

macOS / Linuxの場合：
\`\`\`bash
# ED25519鍵の生成（推奨）
ssh-keygen -t ed25519 -C "openclaw-conoha-vps"

# 保存場所を聞かれたらEnter（デフォルト: ~/.ssh/id_ed25519）
# パスフレーズは設定を推奨（空欄でも可）
\`\`\`

Windowsの場合（Git Bash）：
\`\`\`bash
ssh-keygen -t ed25519 -C "openclaw-conoha-vps"
# 保存場所: C:\\Users\\YourName\\.ssh\\id_ed25519
\`\`\`

**■ 公開鍵をVPSに配置**

方法1：\`ssh-copy-id\`コマンド（macOS/Linux/Git Bash）
\`\`\`bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@YOUR_VPS_IP
\`\`\`

方法2：手動で配置
\`\`\`bash
# ローカルPCで公開鍵の内容をコピー
cat ~/.ssh/id_ed25519.pub

# VPSにSSHログイン後
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
# コピーした公開鍵を貼り付けて保存（Ctrl+O → Enter → Ctrl+X）
chmod 600 ~/.ssh/authorized_keys
\`\`\`

**■ 鍵認証でのSSH接続テスト**

\`\`\`bash
ssh -i ~/.ssh/id_ed25519 root@YOUR_VPS_IP
# パスワードなしでログインできれば成功！
\`\`\`

> 🔐 **セキュリティTips：**
> - 公開鍵認証設定後は、パスワード認証を無効化することを推奨
> - 一般ユーザーでの公開鍵認証手順：[ConoHa公式ガイド](https://support.conoha.jp/v/vpssshuser/)
> - ConoHaコントロールパネルでもSSH Key登録が可能：[SSH Key登録方法](https://support.conoha.jp/v/sshkey/)

**✅ ゴール:** VPSにSSH接続できる状態（パスワード認証または公開鍵認証）

                                            ---

                                            ### Phase 3: AIエージェントのセットアップ（AntiGravity/Cursor/Windsurf）

                                            #### オプション A: AntiGravityを使用（推奨）

                                            1. **AntiGravityのインストール**
                                            2.    - [公式サイト](https://antigravity.dev)からダウンロード
                                                  -    - ローカルPCにインストール
                                                   
                                                       - 2. **SSH接続の設定**
                                                         3.    ```json
                                                                  {
                                                                    "host": "YOUR_VPS_IP",
                                                                    "user": "root",
                                                                    "privateKeyPath": "~/.ssh/openclaw_vps"
                                                                  }
                                                                  ```

                                                               3. **リモート開発環境の起動**
                                                               4.    - AntiGravityでVPSに接続
                                                                     -    - ターミナルを開いてVPS上で作業開始
                                                                      
                                                                          - #### オプション B: 手動でのプロンプト利用
                                                                      
                                                                          - AIチャットツール（ChatGPT/Claude）に以下を入力：
                                                                      
                                                                          - ```
                                                                            私はUbuntu 22.04のVPSサーバーに、以下のGitHubリポジトリからOpenClawをインストールしたいです。

                                                                            リポジトリURL: https://github.com/Sh-Osakana/open-claw

                                                                            インストール手順を段階的にナビゲートしてください。
                                                                            エラーが発生した場合は、その内容を共有して解決策を提示してもらいます。
                                                                            ```

                                                                            ---

                                                                            ### Phase 4: OpenClawのインストール

                                                                            #### ステップ 4.1: システムのアップデート

                                                                            ```bash
                                                                            sudo apt update && sudo apt upgrade -y
                                                                            ```

                                                                            #### ステップ 4.2: 必要なパッケージのインストール

                                                                            ```bash
                                                                            # Node.js 20.xのインストール
                                                                            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                                                                            sudo apt install -y nodejs

                                                                            # Gitのインストール
                                                                            sudo apt install -y git

                                                                            # その他の依存関係
                                                                            sudo apt install -y build-essential
                                                                            ```

                                                                            #### ステップ 4.3: OpenClawのクローン

                                                                            ```bash
                                                                            cd /opt
                                                                            sudo git clone https://github.com/Sh-Osakana/open-claw.git
                                                                            cd open-claw
                                                                            ```

                                                                            #### ステップ 4.4: 依存関係のインストール

                                                                            ```bash
                                                                            sudo npm install
                                                                            ```

                                                                            #### ステップ 4.5: 環境変数の設定

                                                                            ```bash
                                                                            sudo nano .env
                                                                            ```

                                                                            以下の内容を記述：
                                                                            ```env
                                                                            # LLM Provider設定（AntiGravity使用の場合）
                                                                            ANTHROPIC_API_KEY=your_api_key_here

                                                                            # または ZhipuAI GLM-4を使用する場合
                                                                            ZHIPUAI_API_KEY=your_zhipuai_api_key
                                                                            MODEL_PROVIDER=zhipuai
                                                                            MODEL_NAME=glm-4-flash

                                                                            # Telegramボット設定
                                                                            TELEGRAM_BOT_TOKEN=your_telegram_bot_token
                                                                            TELEGRAM_CHAT_ID=your_chat_id

                                                                            # セキュリティ設定
                                                                            ALLOWED_HOSTS=localhost,127.0.0.1
                                                                            PORT=3000
                                                                            ```

                                                                            #### ステップ 4.6: OpenClawの起動

                                                                            ```bash
                                                                            # 開発モード
                                                                            sudo npm run dev

                                                                            # 本番モード（推奨）
                                                                            sudo npm run build
                                                                            sudo npm start
                                                                            ```

                                                                            #### ステップ 4.7: systemdサービス化（自動起動設定）

                                                                            ```bash
                                                                            sudo nano /etc/systemd/system/openclaw.service
                                                                            ```

                                                                            以下を記述：
                                                                            ```ini
                                                                            [Unit]
                                                                            Description=OpenClaw AI Agent
                                                                            After=network.target

                                                                            [Service]
                                                                            Type=simple
                                                                            User=root
                                                                            WorkingDirectory=/opt/open-claw
                                                                            ExecStart=/usr/bin/npm start
                                                                            Restart=always
                                                                            RestartSec=10

                                                                            [Install]
                                                                            WantedBy=multi-user.target
                                                                            ```

                                                                            サービスの有効化：
                                                                            ```bash
                                                                            sudo systemctl daemon-reload
                                                                            sudo systemctl enable openclaw
                                                                            sudo systemctl start openclaw
                                                                            sudo systemctl status openclaw
                                                                            ```

                                                                            ---

                                                                            ### Phase 5: SSHトンネルの確立

                                                                            #### SSHトンネルとは？
                                                                            - 暗号化された秘密のトンネルを作成
                                                                            - - ローカルPCとVPS間で安全な通信
                                                                              - - 外部からのアクセスを完全にブロック
                                                                               
                                                                                - #### SSHトンネルの作成
                                                                               
                                                                                - ローカルPCから実行：
                                                                                - ```bash
                                                                                  ssh -i ~/.ssh/openclaw_vps -L 3000:localhost:3000 root@YOUR_VPS_IP -N
                                                                                  ```

                                                                                  **パラメータ説明:**
                                                                                  - `-L 3000:localhost:3000`: ローカルの3000番ポートをVPSの3000番にフォワード
                                                                                  - - `-N`: コマンド実行なし（トンネルのみ）
                                                                                    - - バックグラウンド実行の場合は `-f` を追加
                                                                                     
                                                                                      - #### UIへのアクセス
                                                                                     
                                                                                      - ブラウザで以下を開く：
                                                                                      - ```
                                                                                        http://localhost:3000
                                                                                        ```

                                                                                        **✅ ゴール:** ローカルブラウザからOpenClaw UIにアクセス可能

                                                                                        ---

                                                                                        ### Phase 6: Telegramボットの設定

                                                                                        #### ステップ 6.1: BotFatherでボット作成

                                                                                        1. Telegramで @BotFather を検索
                                                                                        2. 2. `/newbot` コマンドを実行
                                                                                           3. 3. ボット名とユーザー名を設定
                                                                                              4. 4. **BOT_TOKEN** を取得
                                                                                                
                                                                                                 5. #### ステップ 6.2: Chat IDの取得
                                                                                                
                                                                                                 6. 1. 作成したボットに何かメッセージを送信
                                                                                                    2. 2. ブラウザで以下にアクセス：
                                                                                                       3.    ```
                                                                                                                https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
                                                                                                                ```
                                                                                                             3. `"chat":{"id":XXXXXXXX}` から **CHAT_ID** を取得
                                                                                                         
                                                                                                             4. #### ステップ 6.3: 環境変数に追加
                                                                                                         
                                                                                                             5. `.env` ファイルに追加：
                                                                                                             6. ```env
                                                                                                                TELEGRAM_BOT_TOKEN=your_bot_token_here
                                                                                                                TELEGRAM_CHAT_ID=your_chat_id_here
                                                                                                                ```
                                                                                                                
                                                                                                                OpenClawを再起動：
                                                                                                                ```bash
                                                                                                                sudo systemctl restart openclaw
                                                                                                                ```
                                                                                                                
                                                                                                                ---
                                                                                                                
                                                                                                                ## 🔗 連携ツールの導入
                                                                                                                
                                                                                                                ### N8Nワークフロー自動化
                                                                                                                
                                                                                                                #### N8Nのインストール
                                                                                                                
                                                                                                                ```bash
                                                                                                                cd /opt
                                                                                                                sudo git clone https://github.com/n8n-io/n8n.git
                                                                                                                cd n8n

                                                                                                                # Dockerを使用する場合（推奨）
                                                                                                                docker run -d \
                                                                                                                  --name n8n \
                                                                                                                  -p 5678:5678 \
                                                                                                                  -v ~/.n8n:/home/node/.n8n \
                                                                                                                  n8nio/n8n
                                                                                                                ```
                                                                                                                
                                                                                                                #### OpenClawとN8Nの連携スキル作成
                                                                                                                
                                                                                                                1. **N8N Webhook URLの取得**
                                                                                                                2. 2. **OpenClawにスキルを追加**
                                                                                                                  
                                                                                                                   3. スキル例（`skills/n8n-integration.js`）：
                                                                                                                   4. ```javascript
                                                                                                                      module.exports = {
                                                                                                                        name: "trigger_n8n_workflow",
                                                                                                                        description: "N8Nワークフローをトリガーする",
                                                                                                                        async execute({ workflowId, data }) {
                                                                                                                          const response = await fetch(`http://localhost:5678/webhook/${workflowId}`, {
                                                                                                                            method: "POST",
                                                                                                                            headers: { "Content-Type": "application/json" },
                                                                                                                            body: JSON.stringify(data)
                                                                                                                          });
                                                                                                                          return await response.json();
                                                                                                                        }
                                                                                                                      };
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ---
                                                                                                                      
                                                                                                                      ### OpenNotebook（NotebookLMオープンソース版）
                                                                                                                      
                                                                                                                      #### OpenNotebookのインストール
                                                                                                                      
                                                                                                                      ```bash
                                                                                                                      cd /opt
                                                                                                                      sudo git clone https://github.com/yourusername/open-notebook.git
                                                                                                                      cd open-notebook

                                                                                                                      # 依存関係のインストール
                                                                                                                      npm install

                                                                                                                      # 環境変数設定
                                                                                                                      cp .env.example .env
                                                                                                                      nano .env
                                                                                                                      ```
                                                                                                                      
                                                                                                                      `.env` 設定例：
                                                                                                                      ```env
                                                                                                                      # LLMプロバイダー（複数モデル対応）
                                                                                                                      OPENAI_API_KEY=your_openai_key
                                                                                                                      ANTHROPIC_API_KEY=your_anthropic_key
                                                                                                                      ZHIPUAI_API_KEY=your_zhipuai_key
                                                                                                                      
                                                                                                                      # データベース
                                                                                                                      DATABASE_URL=postgresql://user:password@localhost:5432/opennotebook

                                                                                                                      # サーバー設定
                                                                                                                      PORT=8080
                                                                                                                      ```
                                                                                                                      
                                                                                                                      #### サブドメインの設定
                                                                                                                      
                                                                                                                      Nginxでリバースプロキシ設定：
                                                                                                                      ```bash
                                                                                                                      sudo nano /etc/nginx/sites-available/opennotebook
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ```nginx
                                                                                                                      server {
                                                                                                                          listen 80;
                                                                                                                          server_name notebook.yourdomain.com;

                                                                                                                          location / {
                                                                                                                              proxy_pass http://localhost:8080;
                                                                                                                              proxy_http_version 1.1;
                                                                                                                              proxy_set_header Upgrade $http_upgrade;
                                                                                                                              proxy_set_header Connection 'upgrade';
                                                                                                                              proxy_set_header Host $host;
                                                                                                                              proxy_cache_bypass $http_upgrade;
                                                                                                                          }
                                                                                                                      }
                                                                                                                      ```
                                                                                                                      
                                                                                                                      有効化：
                                                                                                                      ```bash
                                                                                                                      sudo ln -s /etc/nginx/sites-available/opennotebook /etc/nginx/sites-enabled/
                                                                                                                      sudo nginx -t
                                                                                                                      sudo systemctl reload nginx
                                                                                                                      ```
                                                                                                                      
                                                                                                                      #### OpenClawとOpenNotebookの連携
                                                                                                                      
                                                                                                                      スキル例（`skills/opennotebook-integration.js`）：
                                                                                                                      ```javascript
                                                                                                                      module.exports = {
                                                                                                                        name: "create_notebook",
                                                                                                                        description: "OpenNotebookに新しいノートを作成",
                                                                                                                        async execute({ title, content, sources }) {
                                                                                                                          const response = await fetch("http://localhost:8080/api/notebooks", {
                                                                                                                            method: "POST",
                                                                                                                            headers: {
                                                                                                                              "Content-Type": "application/json",
                                                                                                                              "Authorization": `Bearer ${process.env.OPENNOTEBOOK_API_KEY}`
                                                                                                                            },
                                                                                                                            body: JSON.stringify({ title, content, sources })
                                                                                                                          });
                                                                                                                              return await response.json();
                                                                                                                        }
                                                                                                                      };
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ---
                                                                                                                      
                                                                                                                      ## 🎯 オートパイロットワークフロー例
                                                                                                                      
                                                                                                                      ### 1. 研究ノート自動作成
                                                                                                                      
                                                                                                                      ```
                                                                                                                      ユーザー（Telegram）: "最新のAI論文を調査してノートにまとめて"
                                                                                                                          ↓
                                                                                                                      OpenClaw: Web検索 → 論文収集 → 要約生成
                                                                                                                          ↓
                                                                                                                      OpenNotebook: ノート作成・保存
                                                                                                                          ↓
                                                                                                                      N8N: Slackへ通知 + カレンダーに記録
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ### 2. コード自動デプロイ
                                                                                                                      
                                                                                                                      ```
                                                                                                                      ユーザー: "GitHubのIssue #123を修正してプルリク作成"
                                                                                                                          ↓
                                                                                                                      OpenClaw: Issue内容分析 → コード修正 → テスト実行
                                                                                                                          ↓
                                                                                                                      GitHub: ブランチ作成 → Push → PR作成
                                                                                                                          ↓
                                                                                                                      N8N: レビュー依頼通知
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ### 3. VPSメンテナンス
                                                                                                                      
                                                                                                                      ```
                                                                                                                      定期実行（Cron）: 毎週日曜 3:00 AM
                                                                                                                          ↓
                                                                                                                      N8N: OpenClawにトリガー送信
                                                                                                                          ↓
                                                                                                                      OpenClaw: システム更新 → ログ解析 → バックアップ作成
                                                                                                                          ↓
                                                                                                                      OpenNotebook: メンテナンスレポート保存
                                                                                                                          ↓
                                                                                                                      Telegram: 実行結果通知
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ---
                                                                                                                      
                                                                                                                      ## 🛠️ トラブルシューティング
                                                                                                                      
                                                                                                                      ### Q1: OpenClawが起動しない
                                                                                                                      
                                                                                                                      ```bash
                                                                                                                      # ログ確認
                                                                                                                      sudo journalctl -u openclaw -f

                                                                                                                      # ポート確認
                                                                                                                      sudo netstat -tlnp | grep 3000

                                                                                                                      # 権限確認
                                                                                                                      sudo chown -R $USER:$USER /opt/open-claw
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ### Q2: SSH接続ができない
                                                                                                                      
                                                                                                                      ```bash
                                                                                                                      # SSH設定確認
                                                                                                                      ssh -vvv -i ~/.ssh/openclaw_vps root@YOUR_VPS_IP

                                                                                                                      # ファイアウォール確認
                                                                                                                      sudo ufw status
                                                                                                                      sudo ufw allow 22/tcp
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ### Q3: Telegramボットが反応しない
                                                                                                                      
                                                                                                                      ```bash
                                                                                                                      # Webhook状態確認
                                                                                                                      curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo

                                                                                                                      # ボット再起動
                                                                                                                      sudo systemctl restart openclaw
                                                                                                                      ```
                                                                                                                      
                                                                                                                      ---
                                                                                                                      
                                                                                                                      ## 📚 参考リソース
                                                                                                                      
                                                                                                                      ### 公式リポジトリ
                                                                                                                      - **OpenClaw**: https://github.com/Sh-Osakana/open-claw
                                                                                                                      - - **N8N**: https://github.com/n8n-io/n8n
                                                                                                                        - - **OpenNotebook**: https://github.com/yourusername/open-notebook
                                                                                                                          - 
                                                                                                                          ### コミュニティ
                                                                                                                          - Discord: [招待リンク]
                                                                                                                          - - Telegram: [グループリンク]
                                                                                                                           
                                                                                                                            - ### 動画ガイド（推奨）
                                                                                                                            - - Jun SuzukiさんのYouTube解説動画
                                                                                                                              - - https://www.youtube.com/watch?v=KDK40fNX4Ko
                                                                                                                               
                                                                                                                                - ---
                                                                                                                                
                                                                                                                                ## 🎨 今後の拡張予定
                                                                                                                                
                                                                                                                                - 🎤 **Ibyスピーチ連携**（高品質日本語TTS）
                                                                                                                                - - 🎬 **RemoTion統合**（動画自動生成）
                                                                                                                                  - - 🤖 **サブエージェント機能**（複数LLMの並列実行）
                                                                                                                                    - - 📊 **ダッシュボード機能**（進捗可視化）
                                                                                                                                     
                                                                                                                                      - ---
                                                                                                                                      
                                                                                                                                      ## 📝 ライセンス
                                                                                                                                      
                                                                                                                                      MIT License
                                                                                                                                      
                                                                                                                                      ---
                                                                                                                                      
                                                                                                                                      ## 🤝 貢献
                                                                                                                                      
                                                                                                                                      プルリクエスト・Issue報告を歓迎します！
                                                                                                                                      
                                                                                                                                      1. このリポジトリをフォーク
                                                                                                                                      2. 2. Featureブランチを作成（`git checkout -b feature/amazing-feature`）
                                                                                                                                         3. 3. 変更をコミット（`git commit -m 'Add amazing feature'`）
                                                                                                                                            4. 4. ブランチにプッシュ（`git push origin feature/amazing-feature`）
                                                                                                                                               5. 5. プルリクエストを作成
                                                                                                                                                 
                                                                                                                                                  6. ---
                                                                                                                                                 
                                                                                                                                                  7. ## 📧 お問い合わせ
                                                                                                                                                 
                                                                                                                                                  8. 質問・提案がある場合は、Issueを作成してください。
                                                                                                                                                 
                                                                                                                                                  9. ---
                                                                                                                                                 
                                                                                                                                                  10. **⚡ 免責事項:** このガイドは教育目的で作成されています。セキュリティリスクを理解した上で、自己責任で使用してください。
