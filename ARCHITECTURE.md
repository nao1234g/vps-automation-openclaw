# システムアーキテクチャ

OpenClaw VPS環境の全体構成図と各コンポーネントの説明です。

## 🏗️ 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS (443)
                             │ HTTP (80) → HTTPS Redirect
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         UFW Firewall                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Allowed Ports:                                           │   │
│  │  - 22/2222 (SSH - Key Auth Only)                        │   │
│  │  - 80 (HTTP - Let's Encrypt Challenge)                  │   │
│  │  - 443 (HTTPS)                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Fail2ban Protection
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      VPS Host System                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Ubuntu 22.04 LTS                                         │   │
│  │  - Docker Engine (Latest)                               │   │
│  │  - Docker Compose v2                                     │   │
│  │  - Trivy (Vulnerability Scanner)                        │   │
│  │  - Certbot (Let's Encrypt)                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Docker Network Architecture                 │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────┐     │   │
│  │  │         Frontend Network (Bridge)              │     │   │
│  │  │                                                 │     │   │
│  │  │  ┌──────────────────────────────────┐          │     │   │
│  │  │  │      Nginx Reverse Proxy         │          │     │   │
│  │  │  │  ┌────────────────────────────┐  │          │     │   │
│  │  │  │  │ - SSL/TLS Termination      │  │          │     │   │
│  │  │  │  │ - Security Headers         │  │          │     │   │
│  │  │  │  │ - Rate Limiting            │  │          │     │   │
│  │  │  │  │ - Gzip Compression         │  │          │     │   │
│  │  │  │  │ - WebSocket Support        │  │          │     │   │
│  │  │  │  └────────────────────────────┘  │          │     │   │
│  │  │  └────────────┬─────────────────────┘          │     │   │
│  │  └───────────────┼────────────────────────────────┘     │   │
│  │                  │                                       │   │
│  │                  │ Proxy Pass                            │   │
│  │                  ▼                                       │   │
│  │  ┌────────────────────────────────────────────────┐     │   │
│  │  │        Backend Network (Internal Only)         │     │   │
│  │  │                                                 │     │   │
│  │  │  ┌──────────────────┐  ┌──────────────────┐   │     │   │
│  │  │  │   Application    │  │    Database      │   │     │   │
│  │  │  │  ┌────────────┐  │  │  ┌────────────┐  │   │     │   │
│  │  │  │  │ OpenClaw   │  │  │  │ PostgreSQL │  │   │     │   │
│  │  │  │  │ Node.js    │◄─┼──┼─►│   16-alpine│  │   │     │   │
│  │  │  │  │ Non-root   │  │  │  │  Non-root  │  │   │     │   │
│  │  │  │  │ UID:1000   │  │  │  │  Encrypted │  │   │     │   │
│  │  │  │  └────────────┘  │  │  └────────────┘  │   │     │   │
│  │  │  └──────────────────┘  └──────────────────┘   │     │   │
│  │  │                                                 │     │   │
│  │  │  ┌──────────────────┐  ┌──────────────────┐   │     │   │
│  │  │  │       N8N        │  │  OpenNotebook    │   │     │   │
│  │  │  │  ┌────────────┐  │  │  ┌────────────┐  │   │     │   │
│  │  │  │  │ Workflow   │  │  │  │   Notes    │  │   │     │   │
│  │  │  │  │ Automation │  │  │  │  Storage   │  │   │     │   │
│  │  │  │  │ Non-root   │  │  │  │  Non-root  │  │   │     │   │
│  │  │  │  └────────────┘  │  │  └────────────┘  │   │     │   │
│  │  │  └──────────────────┘  └──────────────────┘   │     │   │
│  │  └─────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Docker Volumes (Persistent)                 │   │
│  │  - db_data (PostgreSQL Data)                            │   │
│  │  - n8n_data (Workflow Data)                             │   │
│  │  - notebook_data (Notes Data)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🔒 セキュリティレイヤー

```
┌─────────────────────────────────────────────────────────────────┐
│                      Security Layers                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Layer 1: Network Security                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - UFW Firewall (Deny All by Default)                    │   │
│  │ - Fail2ban (SSH Brute Force Protection)                 │   │
│  │ - Rate Limiting (Nginx)                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Layer 2: Access Control                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - SSH Key Authentication Only                           │   │
│  │ - Root Login Disabled                                    │   │
│  │ - Password Authentication Disabled                       │   │
│  │ - Non-root Container Execution                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Layer 3: Container Security                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - Read-only Filesystem                                   │   │
│  │ - Capability Drop (ALL)                                  │   │
│  │ - No New Privileges                                      │   │
│  │ - Network Isolation (Internal Backend)                  │   │
│  │ - Resource Limits (CPU/Memory)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Layer 4: Application Security                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - Security Headers (HSTS, CSP, X-Frame-Options)         │   │
│  │ - Input Validation                                       │   │
│  │ - SQL Injection Prevention                              │   │
│  │ - XSS Prevention                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Layer 5: Encryption                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - SSL/TLS (Let's Encrypt)                               │   │
│  │ - TLS 1.2+ Only                                          │   │
│  │ - Strong Cipher Suites                                   │   │
│  │ - Database Encryption at Rest (Optional)                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Layer 6: Monitoring & Auditing                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - Trivy Vulnerability Scanning                          │   │
│  │ - Docker Bench Security Auditing                        │   │
│  │ - Log Monitoring (journald)                             │   │
│  │ - Health Checks                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 自動化フロー

```
┌─────────────────────────────────────────────────────────────────┐
│                     Automation Flow                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Daily (Cron)                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 04:00 → Image Vulnerability Scan (Trivy)                │   │
│  │ 05:00 → System Update Check                             │   │
│  │ Manual → Daily Backup (Recommended)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│           │                                                       │
│           ▼                                                       │
│  Weekly (Cron)                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Sun 02:00 → Full Security Scan                          │   │
│  │ Sun 02:30 → SSL Certificate Renewal Check               │   │
│  │ Sun 03:30 → Maintenance Dry Run                         │   │
│  │ Mon 01:00 → Docker Cleanup                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│           │                                                       │
│           ▼                                                       │
│  Monthly (Cron)                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1st 03:00 → Full System Maintenance                     │   │
│  │ 15th 01:00 → Old Log Cleanup (90+ days)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Alerts & Notifications                         │   │
│  │  - Critical Vulnerabilities → Email/Slack               │   │
│  │  - Disk Usage > 85% → Email                             │   │
│  │  - SSL Expiry < 7 days → Email                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 💾 バックアップ戦略

```
┌─────────────────────────────────────────────────────────────────┐
│                    Backup Architecture                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Source Data                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. PostgreSQL Database (pg_dumpall)                     │   │
│  │ 2. Docker Volumes (tar.gz)                              │   │
│  │ 3. Configuration Files (.env, docker-compose.yml)       │   │
│  │ 4. System Information (metadata)                        │   │
│  └────────────┬────────────────────────────────────────────┘   │
│               │                                                   │
│               ▼                                                   │
│  Local Backup (/opt/backups)                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ backup_YYYYMMDD_HHMMSS/                                 │   │
│  │  ├─ database_YYYYMMDD_HHMMSS.sql.gz                     │   │
│  │  ├─ volumes/                                             │   │
│  │  │   ├─ db_data_YYYYMMDD_HHMMSS.tar.gz                  │   │
│  │  │   └─ app_data_YYYYMMDD_HHMMSS.tar.gz                 │   │
│  │  ├─ config_YYYYMMDD_HHMMSS.tar.gz                       │   │
│  │  └─ system_info.txt                                      │   │
│  └────────────┬────────────────────────────────────────────┘   │
│               │                                                   │
│               ├─── Retention: 30 days (configurable)             │
│               │                                                   │
│               ▼                                                   │
│  Remote Backup (Optional)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ AWS S3 / Compatible Storage                             │   │
│  │  - Encrypted at rest                                     │   │
│  │  - Versioning enabled                                    │   │
│  │  - Cross-region replication                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Restore Process                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Stop containers                                       │   │
│  │ 2. Restore database                                      │   │
│  │ 3. Restore volumes                                       │   │
│  │ 4. Restore configuration                                 │   │
│  │ 5. Start containers                                      │   │
│  │ 6. Verify health                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 データフロー

```
User Request
    │
    ▼
Internet (HTTPS)
    │
    ▼
UFW Firewall (Port 443)
    │
    ▼
Nginx Container
    │
    ├─ SSL/TLS Termination
    ├─ Security Headers
    ├─ Rate Limiting
    └─ Gzip Compression
    │
    ▼
Application Container
    │
    ├─ Request Processing
    ├─ Business Logic
    └─ Data Validation
    │
    ▼
Database Container
    │
    ├─ Query Execution
    ├─ Transaction Management
    └─ Data Persistence
    │
    ▼
Response (JSON/HTML)
    │
    ▼
Nginx (Caching/Compression)
    │
    ▼
User
```

## 🛠️ 運用ツールスタック

```
┌─────────────────────────────────────────────────────────────────┐
│                      Tool Stack                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Setup & Configuration                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - setup.sh (Master Wizard)                              │   │
│  │ - setup_vps_security.sh                                  │   │
│  │ - setup_docker_security.sh                               │   │
│  │ - setup_ssl.sh                                           │   │
│  │ - setup_cron_jobs.sh                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Operations                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - backup.sh (DB, Volumes, Config)                       │   │
│  │ - restore.sh (Disaster Recovery)                        │   │
│  │ - health_check.sh (System Health)                       │   │
│  │ - maintenance.sh (Cleanup, Updates)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Security                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - security_scan.sh (Trivy + Docker Bench)               │   │
│  │ - UFW (Network Firewall)                                │   │
│  │ - Fail2ban (Intrusion Prevention)                       │   │
│  │ - Trivy (Vulnerability Scanner)                         │   │
│  │ - Certbot (SSL Certificates)                            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 ディレクトリ構造

```
/opt/vps-automation-openclaw/
├── setup.sh                           # マスターセットアップ
├── docker-compose.yml                 # Compose設定
├── .env                              # 環境変数（秘密）
├── .env.example                      # 環境変数テンプレート
│
├── scripts/                          # 運用スクリプト
│   ├── setup_vps_security.sh
│   ├── setup_docker_security.sh
│   ├── setup_ssl.sh
│   ├── setup_cron_jobs.sh
│   ├── security_scan.sh
│   ├── maintenance.sh
│   ├── backup.sh
│   ├── restore.sh
│   └── health_check.sh
│
├── docker/                           # Docker設定
│   ├── docker-compose.secure.template.yml
│   ├── Dockerfile.secure.template
│   └── nginx/
│       ├── nginx.conf
│       └── conf.d/
│           └── app.conf.example
│
├── docs/                             # ドキュメント
│   └── SSH_KEY_SETUP.md
│
├── SECURITY_CHECKLIST.md
├── QUICKSTART_SECURITY.md
├── OPERATIONS_GUIDE.md
├── QUICK_REFERENCE.md
└── ARCHITECTURE.md                   # このファイル

/opt/backups/openclaw/               # バックアップ
/var/log/openclaw/                   # ログ
/var/lib/docker/volumes/             # Dockerボリューム
```

## 🔗 コンポーネント連携

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Internet   │───▶│     UFW      │───▶│   Fail2ban   │
└──────────────┘    └──────────────┘    └──────────────┘
                                                │
                                                ▼
┌──────────────────────────────────────────────────────────┐
│                    Docker Host                            │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    │
│  │   Nginx    │───▶│    App     │───▶│     DB     │    │
│  │   (SSL)    │    │ (OpenClaw) │    │(PostgreSQL)│    │
│  └────────────┘    └────────────┘    └────────────┘    │
│         │                 │                  │          │
│         ▼                 ▼                  ▼          │
│  ┌────────────────────────────────────────────────┐    │
│  │            Docker Volumes (Persistent)          │    │
│  └────────────────────────────────────────────────┘    │
│                            │                             │
│                            ▼                             │
│                   ┌──────────────┐                      │
│                   │    Backup    │                      │
│                   └──────────────┘                      │
└──────────────────────────────────────────────────────────┘
```

---

## 🌐 Nowpattern コンテンツハブ（現在の稼働構成）

> 最終更新: 2026-02-23

### 全体フロー

```
ユーザー（Telegram）
    │
    ├─ @openclaw_nn2026_bot ─── Jarvis（OpenClaw Agent）
    │                              ├─ Alice/CodeX/Pixel/Luna/Scout/Guard（Gemini 2.5 Pro）
    │                              └─ Hawk（Grok 4.1）
    │
    ├─ @claude_brain_nn_bot ── NEO-ONE（Claude Opus 4.6 via Max subscription）
    │                              └─ VPS /opt filesystem操作
    │
    └─ @neo_two_nn2026_bot ─── NEO-TWO（Claude Opus 4.6）補助・並列タスク
```

### コンテンツパイプライン

```
┌──────────────────────────────────────────────────────────────┐
│               AISAコンテンツパイプライン（N8N管理）             │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  JST 7/13/19時                                               │
│  rss-news-pipeline.py ──→ rss_article_queue.json             │
│                                                               │
│  JST 7:30/13:30/19:30時                                      │
│  analyze_rss.py                                              │
│    Step1: 記事本文スクレイプ                                   │
│    Step2: Grok x_search（元ツイート検索）                      │
│    Step3: Gemini 2.5 Pro 深層分析（7,000字+）                 │
│                                                               │
│  毎時0分（+0-10分ランダム遅延）                                 │
│  rss-post-quote-rt.py                                        │
│    JA: note（サムネイル付き）→ X引用リポスト                    │
│    EN: Substack → X引用リポスト                               │
│    Ghost: nowpattern.com自動投稿                              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### プラットフォーム配信先

```
NEO-ONE（記事執筆）
    │
    ▼
Jarvis（翻訳 JA→EN + 投稿実行）
    │
    ├──→ note（日本語）
    ├──→ Substack（英語）
    ├──→ X @aisaintel（JA/EN）
    └──→ nowpattern.com（Ghost CMS / SSL自動更新）
             ↑
         n8n-workflows/nowpattern-ghost-post.py
```

### 共有ストレージ

```
VPS /opt/shared/
    ├── reports/        ← Jarvis書き込み → Neo読み取り
    ├── scripts/        ← 各種Pythonスクリプト
    ├── articles/       ← 生成記事・プロンプト
    ├── task-log/       ← 全エージェントの作業ログ
    ├── learning/       ← daily-learning.py 出力
    └── AGENT_WISDOM.md ← 全エージェント共通知識（Neoが管理）
```

### Nowpatternスクリプト群（ローカル scripts/）

| スクリプト | 役割 |
|-----------|------|
| `nowpattern_article_builder.py` | Deep Pattern HTML生成（v3.0） |
| `nowpattern_publisher.py` | Ghost投稿 + 記事インデックス管理 |
| `gen_dynamics_diagram.py` | 力学ダイアグラムSVG自動生成 |
| `daily-learning.py` | 情報収集（Reddit/HN/GitHub、1日4回） |

---

**このアーキテクチャは、セキュリティ、可用性、保守性のベストプラクティスに基づいて設計されています。**
