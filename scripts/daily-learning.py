#!/usr/bin/env python3
"""
Hey Loop Intelligence System v3

4x daily intelligence gathering focused on BOTH infrastructure AND revenue.
Sends Telegram reports with article URLs, summaries, and monetization proposals.
Dynamically discovers new "information stars" — people making money with AI.

Data sources:
  1. Reddit (JSON API) — infrastructure + revenue subreddits
  2. Hacker News (Firebase API) — tech + business keywords
  3. GitHub (REST API) — dependency tracking + AI builder repos
  4. Gemini + Google Search grounding — deep research + dynamic discovery
  5. Grok/xAI (Chat API) — X/Twitter real-time intelligence

Schedule: 4x daily (every 6 hours)
  Run 0: 00:00 JST — Night scan (global markets, overnight news)
  Run 1: 06:00 JST — Morning briefing (main daily report)
  Run 2: 12:00 JST — Midday update (trending topics)
  Run 3: 18:00 JST — Evening review (summary + action items)

Usage:
  python3 daily-learning.py              # Auto-detect run based on JST hour
  python3 daily-learning.py --run 0      # Force specific run (0-3)
  python3 daily-learning.py --force      # Skip duplicate check
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# =============================================================================
# Config
# =============================================================================
LEARNING_DIR = "/opt/shared/learning"
WISDOM_FILE = "/opt/shared/AGENT_WISDOM.md"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

JST = timezone(timedelta(hours=9))

RUN_LABELS = {
    0: "Night Scan",
    1: "Morning Briefing",
    2: "Midday Update",
    3: "Evening Review",
}

# --- Subreddits (infrastructure + revenue) ---
INFRA_SUBREDDITS = [
    "selfhosted", "n8n", "docker", "PostgreSQL",
    "LocalLLaMA", "MachineLearning", "ClaudeAI",
    "Automate", "webdev", "netsec",
]

REVENUE_SUBREDDITS = [
    "AI_Agents", "SideProject", "EntrepreneurRideAlong",
    "passive_income", "newsletters", "SaaS",
    "indiehackers", "Entrepreneur", "startups",
    "juststart",
]

ALL_SUBREDDITS = INFRA_SUBREDDITS + REVENUE_SUBREDDITS

# --- GitHub repos (infrastructure + revenue/AI builders) ---
INFRA_GITHUB_REPOS = [
    "open-claw/open-claw",
    "n8n-io/n8n",
    "docker/compose",
    "langchain-ai/langchain",
    "anthropics/anthropic-sdk-python",
]

REVENUE_GITHUB_REPOS = [
    "joaomdmoura/crewAI",
    "langgenius/dify",
    "significant-gravitas/AutoGPT",
    "assafelovic/gpt-researcher",
    "Mintplex-Labs/anything-llm",
]

ALL_GITHUB_REPOS = INFRA_GITHUB_REPOS + REVENUE_GITHUB_REPOS

# --- Hacker News keywords (tech + business) ---
HN_KEYWORDS = [
    # Infrastructure
    "ai agent", "llm", "docker", "n8n", "postgres",
    "telegram bot", "self-hosted", "automation", "gemini",
    "claude", "grok", "vector database", "rag", "mcp", "open source",
    # Revenue / Business
    "newsletter", "content pipeline", "revenue", "startup",
    "saas", "monetize", "passive income", "indie hacker",
    "side project", "ai business", "pricing", "mrr",
    "subscription", "creator economy", "ai tool",
]

# --- Deep research topics (14 = ~3.5 day full rotation at 4x/day) ---
DEEP_TOPICS = [
    # Infrastructure (7)
    {
        "area": "AI Agent Architecture",
        "category": "infra",
        "search_query": (
            "multi-agent AI system architecture 2026 best practices coordination"
        ),
    },
    {
        "area": "Docker Security",
        "category": "infra",
        "search_query": (
            "Docker container security hardening 2026 non-root CVE"
        ),
    },
    {
        "area": "N8N Advanced Patterns",
        "category": "infra",
        "search_query": (
            "n8n workflow automation advanced patterns error handling 2026"
        ),
    },
    {
        "area": "LLM Cost Optimization",
        "category": "infra",
        "search_query": (
            "LLM API cost optimization prompt caching 2026 Gemini Claude"
        ),
    },
    {
        "area": "Content Automation Pipeline",
        "category": "infra",
        "search_query": (
            "AI newsletter automation pipeline Substack multilingual 2026"
        ),
    },
    {
        "area": "PostgreSQL Performance",
        "category": "infra",
        "search_query": (
            "PostgreSQL 16 17 performance tuning indexing 2026"
        ),
    },
    {
        "area": "Telegram Bot Best Practices",
        "category": "infra",
        "search_query": (
            "Telegram bot development python 2026 best practices webhook"
        ),
    },
    # Revenue (7)
    {
        "area": "AI Newsletter Revenue",
        "category": "revenue",
        "search_query": (
            "AI newsletter business revenue model 2026 Substack subscription "
            "earnings The Rundown Superhuman AI"
        ),
    },
    {
        "area": "AI Automation Agencies",
        "category": "revenue",
        "search_query": (
            "AI automation agency business model pricing clients 2026 "
            "revenue case study"
        ),
    },
    {
        "area": "AI SaaS Products",
        "category": "revenue",
        "search_query": (
            "AI SaaS product launch revenue MRR 2026 indie maker solo "
            "developer bootstrapped"
        ),
    },
    {
        "area": "Content Monetization Strategies",
        "category": "revenue",
        "search_query": (
            "AI content monetization multilingual newsletter sponsorship "
            "affiliate 2026 Asia"
        ),
    },
    {
        "area": "AI Builder Case Studies",
        "category": "revenue",
        "search_query": (
            "AI builder making money case study 2026 solo developer revenue "
            "journey transparent"
        ),
    },
    {
        "area": "Multilingual AI Content Business",
        "category": "revenue",
        "search_query": (
            "multilingual AI content creation translation business Asia "
            "Japan Korea 2026"
        ),
    },
    {
        "area": "AI Agent Marketplace",
        "category": "revenue",
        "search_query": (
            "AI agent marketplace selling bots automation service 2026 "
            "pricing gig economy"
        ),
    },
]

# --- X Watchlist: 特定アカウントを毎日監視 (フォロー不要、from:username で取得) ---
# ベースリスト（50人）+ 動的発見リスト（/opt/shared/watchlist_dynamic.json）
# Grokが毎朝新しい高シグナルアカウントを発見して自動追加する
X_WATCHLIST = {
    # ─── 日本語AI/テック ───────────────────────────────────────────────────
    "jp_ai_tech": [
        "issei_y",       # 山本一成 / チューリングCEO / 自動運転
        "shaneguML",     # Shane Gu / Google DeepMind / Gemini
        "shanegJP",      # シェイン・グウ / Google DeepMind JP
        "kudotomoaki",   # 工藤智昭 / JAPAN AI CEO
        "daiu_ko",       # Daiu Ko / Kudan CEO / フィジカルAI
        "KudanNews",     # Kudan公式
        "nishiohirokazu",# 西尾泰和 / Cybozu Labs / 技術・AI研究
        "shi3z",         # 清水亮 / AI研究者・起業家
        "yusuke_arclamp",# 勝俣哲生 / AIビジネス
    ],
    # ─── 日本語マクロ/経済 ──────────────────────────────────────────────────
    "jp_macro": [
        "yurumazu",      # エミン・ユルマズ / グローバルストラテジスト
        "goto_finance",  # 後藤達也 / 元日経記者 / 経済・投資
        "ryuichirot",    # 竹下隆一郎 / TBS Bloomberg PIVOT
        "kenkusunoki",   # 楠木建 / 競争戦略
        "tanakayu6",     # 田中宇 / 国際ニュース独立解説
        "hidetomitanaka",# 田中秀臣 / 上武大学 / 経済政策
    ],
    # ─── グローバルAIトップ (CEO/創業者/意思決定層) ──────────────────────────
    "global_ai_leaders": [
        "sama",          # Sam Altman / OpenAI CEO
        "demishassabis", # Demis Hassabis / Google DeepMind CEO
        "satyanadella",  # Satya Nadella / Microsoft CEO
        "elonmusk",      # Elon Musk / xAI・Tesla
        "gdb",           # Greg Brockman / OpenAI
        "ylecun",        # Yann LeCun / Meta AI Chief Scientist
        "andrewyng",     # Andrew Ng / DeepLearning.AI
        "ilyasut",       # Ilya Sutskever / SSI
        "aidan_gomez",   # Aidan Gomez / Cohere CEO
        "garrytan",      # Garry Tan / YC President
        "paulg",         # Paul Graham / YC
        "naval",         # Naval Ravikant / AngelList
        "balajis",       # Balaji Srinivasan / network state
    ],
    # ─── グローバルAIビルダー (MRR公開・プロダクト系・高シグナル) ───────────────
    "global_ai_builders": [
        "levelsio",      # Pieter Levels / 月収公開 / nomad.so
        "emollick",      # Ethan Mollick / Wharton / AI×ビジネス実証
        "karpathy",      # Andrej Karpathy / ex-OpenAI / 技術解説最高峰
        "steipete",      # Peter Steinberger / OpenClaw作者
        "swyx",          # swyx / AI engineer trends / early signal
        "benedictevans", # Benedict Evans / テック構造分析
        "rowancheung",   # Rowan Cheung / AIツールレビュー
        "therundownai",  # The Rundown AI / AIニュース集約
        "marc_louvion",  # Marc Lou / AI SaaS MRR公開
        "mattshumer_",   # Matt Shumer / AI product builder
        "andrewchen",    # Andrew Chen / a16z GP / growth
        "shreyas",       # Shreyas Doshi / PM / product strategy
        "david_perell",  # David Perell / Writing + AI newsletter
    ],
    # ─── 地政学・マクロ (Nowpattern直結) ─────────────────────────────────────
    "global_geopolitics": [
        "ianbremmer",    # Ian Bremmer / Eurasia Group創業者
        "adam_tooze",    # Adam Tooze / Columbia / 経済歴史家
        "foreignpolicy", # Foreign Policy 公式
        "CFR_org",       # Council on Foreign Relations
        "rbrtstr",       # Robin Brooks / 国際経済・ドル
    ],
    # ─── W1フォローリスト全件 (オーナー @w105743926 のフォロー一覧より) ──────────
    # スクリーンショット順に追加中。「どんどん渡してく」→ 随時追加。
    # フィルタリングしない — 全件監視してGrokが意味のある投稿を判定する
    "w1_following": [
        # --- バッチ1 (セッション圧縮復元分) ---
        "nikkeimj",          # 日経MJ / 消費・流通・マーケティング
        "irtv2022",          # IR TV / 投資家向け情報
        "PeptiDream_Inc",    # PeptiDream / 創薬ベンチャー
        "hineken_al",        # ひねけん / AI × ビジネス
        "itandi_noguchi",    # イタンジ 野口 / 不動産DX
        "Q_Portal_",         # Qポータル / 量子コンピュータ情報
        "quantinuum_jp",     # Quantinuum Japan
        "Geniee_inc",        # Geniee / DSP・DX・AI
        "quantumbizmag",     # Quantum Business Magazine
        "BridgeSalon",       # Bridge Salon / スタートアップ情報
        "JapanStockC",       # Japan Stock Channel
        "nikkei_business",   # 日経ビジネス
        "nikkei_bizdaily",   # 日経ビジネス電子版
        "ReHacQ",            # ReHacQ / 経済・ビジネスYouTube
        "sa3i8te7n8",        # 山田進太郎 (メルカリ創業者)
        "GoogleDeepMind",    # Google DeepMind 公式
        "OpenAI",            # OpenAI 公式
        "cjhiking",          # CJ Hiking / 起業・テック
        "commu_blog",        # コミュニティ・ブログ系
        "BiotechMania",      # バイオテックマニア
        "wired_jp",          # WIRED Japan
        "YoichiTakahashi",   # 高橋洋一 / 経済学者・元財務省
        "Kantei_Saigai",     # 首相官邸防災
        "kantei_hisai",      # 官邸被災者支援
        "quick_cvrc",        # QUICKコーポレートバリュー研究センター
        "kabumatome",        # 株まとめ / 株式投資情報
        "Investment_kabu",   # 投資 × 株
        "stockprayer",       # ストックプレイヤー / 株式投資
        "BioFinWizard",      # バイオ × 金融
        "joshm",             # Josh Miller / Product Hunt関連
        "toyamarudasi",      # とやまる大志 / 投資・情報
        "YassLab",           # YassLab / Railsチュートリアル・教育
        # --- バッチ2 (スクリーンショット提供分 2026-02-23) ---
        "money_eeexit",      # タナカ / 副業起業家 / 10億Exit / マーケ会社経営
        "jimmybajimmyba",    # Jimmy Ba / 100x / xAI co-founder @xai @uoft ★高シグナル
        "kei31ai",           # AIけいすけ / AI・テクノロジー解説 / Zenn・note
        "MrinankSharma",     # mrinank / AI researcher
        "1namaiki",          # なまいきくん / コンテンツ系
        "rohit4verse",       # Rohit / FullStack + Agentic AI builder
        "L_go_mrk",          # AI駆動塾 / スモビジオーナー / AI×SaaS 10個のプロジェクト
        "aiyabai1219",       # AIやばい / AI×動画編集 / Antigravity × Remotion
        "aiehon_aya",        # 妖精アーヤさん / AI動画クリエイター / 著書あり
        "unikoukokun",       # ユニコ / AIエージェント開発 / 売上2.5億円・投資6億円 ★
        "openworkceo",       # Openwork CEO / The Agent Economy / $OPENWORK
        "MattPRD",           # Matt Schlicht / moltbook / TheoryForgeVC / YC W12
        "ryolu_",            # Ryo Lu / Cursor.ai・NotionHQ・Stripe出身 ★高シグナル
        "moriyorihayash1",   # 林拓海 / honkoma代表 / 東大農学部 / 起業家
        "shinkaron",         # 規格外 / 独立ニッチ市場 / 月平均5000フォロワー増 ★
        "muhweb",            # muh / 事業家 / Web3/ゲームHoB / AIサービス / 東京⇔アジア
        "y_ruo1",            # ゆるおくん / AI自動運用で月120万 ★
        "jujulife7",         # じゅじゅ / ライフハッカー / AI・ビジネス・英語
        "ck_novasphere",     # チャンキョメ / NovaSphere / 月額98,000円AI広告 ★
        "4610_hotel",        # ど素人ホテル再建計画 / 42アカウントバズらせ中 ★
        "ashtom",            # Thomas Dohmke / EntireHQ / Former CEO @GitHub ★高シグナル
        "GrowAIHub",         # GrowAIHub / AIツール・Threads・Growthコンテンツ
        "maxjaderberg",      # Max Jaderberg / IsomorphicLabs President / ex-DeepMind ★
        # --- バッチ3 (スクリーンショット提供分 2026-02-23 全件 No.25〜329, 重複除く) ---
        # ── AI/テック 海外 ────────────────────────────────────────────
        "mustafasuleyman",   # Mustafa Suleyman / Microsoft AI CEO / The Coming Wave著者
        "miramurati",        # Mira Murati / ThinkingMachines / ex-OpenAI CTO
        "OriolVinyalsML",    # Oriol Vinyals / VP Research GoogleDeepMind / Gemini共同リード
        "polynoamial",       # Noam Brown / OpenAI / o3・o1推論モデル共同開発
        "ch402",             # Chris Olah / @AnthropicAI / ニューラルネット解釈研究
        "DarioAmodei",       # Dario Amodei / Anthropic CEO
        "VahidK",            # Vahid Kazemi / ex-xAI・OpenAI・Apple・Google
        "giffmana",          # Lucas Beyer / Meta researcher / ex-OpenAI DeepMind
        "arankomatsuzaki",   # Aran Komatsuzaki / GPT-J・LAION / AI研究者
        "rhythmrg",          # Rhythm Garg / AppliedCompute CTO / ex-OpenAI research
        "VictorTaelin",      # Taelin / Kind / Bend / HVM / λCalculus
        "rayhotate",         # Ray Hotate / xAI MTS / Stanford CS / ex-Goldman
        "Hidenori8Tanaka",   # Hidenori Tanaka / Harvard Physics of AI
        "DKokotajlo",        # Daniel Kokotajlo / AI safety
        "bioshok3",          # bioshok / AI Safety・Alignment・X-Risk / INODS Research
        "Dr_Singularity",    # Dr Singularity / Futurist / AGI/ASI by 2030
        "drfeifei",          # Fei-Fei Li / Stanford CS / WorldLabs CEO / 空間AI
        "KelseyTuoc",        # Kelsey Piper / 「We're not doomed」AI楽観主義者
        "hokazuya",          # Hodachi / RAGOps / EZO LLMs
        "superforecaster",   # Good Judgment / Superforecasting
        "PTetlock",          # Philip Tetlock / Penn / スーパーフォーキャスティング理論
        "wfrhatch",          # Warren Hatch / Good Judgment CEO
        "aileenlee",         # Aileen Lee / CowboyVC創業者 / coined「unicorn」
        "nrmehta",           # Nick Mehta / Gainsight創業者 / Vista売却
        "RajanAnandan",      # Rajan Anandan / Peak XV Partners (Sequoia India)
        "benthompson",       # Ben Thompson / Stratechery著者
        "WillHeaven",        # Will Heaven / Dyson Comms / ex-Spectator
        "TEDchris",          # Chris Anderson / TED Head
        "lexfridman",        # Lex Fridman / Podcast / ロボット・人間
        "RayDalio",          # Ray Dalio / Bridgewater 創業者 / Principles著者
        "SteveMiran",        # Stephen Miran / FRB理事
        "rakyll",            # Jaana Dogan / Google SWE / APIs platform
        "joshwoodward",      # Josh Woodward / VP @Google @GeminiApp
        "OfficialLoganK",    # Logan Kilpatrick / @GoogleAIStudio / Gemini API
        "tom_doerr",         # Tom Dörr / GitHub repos・DSPy・agents / ニュースレター
        "memU_ai",           # memU / agentic memory framework for LLMs
        "narendramodi",      # Narendra Modi / インド首相
        "tim_cook",          # Tim Cook / Apple CEO
        "sundarpichai",      # Sundar Pichai / Google & Alphabet CEO
        "BillGates",         # Bill Gates / Microsoft共同創業者
        "realDonaldTrump",   # Donald J. Trump / 45th & 47th President
        "POTUS",             # President Donald J. Trump @POTUS 公式
        "snakajima",         # Satoshi Nakajima / GraphAI / MulmoCast / メルマガ
        "BrandonKHill",      # Brandon K. Hill / btrax CEO / 日米デザイン会社
        # ── AI/テック 国内 ────────────────────────────────────────────
        "ymatsuo",           # 松尾 豊 / 東大教授 / 日本DL協会理事長
        "Matsuo_Lab",        # 東京大学 松尾・岩澤研究室 公式
        "ImAI_Eruel",        # 今井翔太 / GenesisAI CEO / JAIST客員教授
        "takahiroanno",      # 安野貴博 / チームみらい党首・参院議員 / AIエンジニア起業家
        "Tebasaki_lab",      # 手羽先 / 国産LLM開発 / ZEN大学特待生
        "cumulo_autumn",     # あき先生 / ShizukuAILabs / UCBerkeley PhD / ex-Meta
        "ozaken_AI",         # おざけん / AIエージェントの教科書著者 / AICX協会代表
        "kajikent",          # 梶谷健人 / POSTS代表 / AI事業・プロダクト顧問
        "snakehakase",       # すねーく博士 / ローンチ30億 / AIエージェントx マーケ
        "AI_masaou",         # まさお / AI駆動開発CEO / Web3000万人利用 / YouTube1.5万
        "commte",            # コムテ / Claude Code実践 / izanami.dev運営
        "akihiro_genai",     # あきひろ / AI活用・Codex情報コミュ1000名 / Android Dev
        "santa128bit",       # Shinji Yamada / AI Agent Operator / Software Dev
        "sora19ai",          # そら / AgentSkills / 21歳起業家 / 令和の虎ALL
        "AI_Studenttt",      # るるむ / AI開発大学生 / Udemy BS / 爆速開発
        "aoyama_code",       # 青山 / AIクリエイター / AI×SNS1000万
        "genkai_syatikuu",   # ルナ / AIクリエイター / AI×SNS1000万 / サイドFIRE
        "rich_armadillo",    # あるまじろ / 東大AIエンジニア / AI×X880万/年
        "develogon0",        # デベロゴン / AI自動化ツール月200万 / Fラン卒ニート
        "nero_sansei",       # ねろ / AI活用で月30万振り込まれる / 社不ニート
        "y_ruo1",            # ゆるおくん / AI自動運用で月120万 ★（batch2重複確認用に保持）
        "shota7180",         # 木内翔大 / SHIFT AI代表 / 日本最大AIスクール3万人
        "kawai_design",      # KAWAI / SHIFT AIデザイン部長 / AI×デザイン本著者
        "SakuSaku23TOP8",    # サクサク / 中学生AIエンジニア起業家 / East Ventures
        "quronekox",         # Quro / 日蘭スタートアップCTO / @wnb_community
        "_nogu66",           # nogu / Claude Code・Agent SDK好き / SWE
        "taishiyade",        # Taishi / 個人開発月1000万 / 元Silicon Valley CTO
        "0317_hiroya",       # Hiroya Iizuka / Levers代表 / ex-CTO ex-医師 / Obsidian
        "qumaiu",            # 熊井悠 / ランスティアCEO / GEAR.indigo開発
        "labelmake",         # Kyohei / pdfme(4K★) / 外資ITエンジニア
        "Shin_Engineer",     # Shin / YouTuber7万人 / Udemy24万人 / Next.js書籍
        "K8292288065827",    # Lofi boy川本翔 / BuildKit / 10分でAIサービス開発
        "azukiazusa9",       # azukiazusa / フロントエンドエンジニア
        "yutakashino",       # Yuta Kashino / BakFoo / エンジニア起業家
        "Sikino_Sito",       # 式乃シト / 作家・世界観アーキテクト / izanami Awards受賞
        "tsuchi_ya_84",      # tsuchi_ya / macOS Native Developer / Solopreneur
        "shotovim",          # 松濤Vimmer / CyberAgent SWE / Obsidian×AI
        "at_sushi_",         # 門脇 敦司 / Knowledge Sense CEO / 東大 / SWE募集中
        "usutaku_channel",   # usutaku / Michikusa CEO / AI研修 / #AI木曜会
        "iwashi86",          # iwashi / NTTドコモ生成AI周り / エバンジェリスト
        "nwiizo",            # nwiizo / Software Developer
        "Aoi_genai",         # あおい / 生成AI研修・開発 / 上場企業取引多数 / ReHacQ MC
        "AiAircle34052",     # Aircle / 学生AIコミュニティ / 体験ベースAI発信
        "compassinai",       # AI時代の羅針盤 / AGI→ASI・自律エージェント発信
        "yugen_matuni",      # まつにぃ / 生成AIえばんじぇりすと / エクスプラザ
        "ai_Prompt_1144",    # 七里信一 / 生成AIセミナー550回・参加35万人
        "tetumemo",          # テツメモ / AI図解×検証 / Newsletterブロガー
        "proica1",           # ぷろいか / AI失業毎日投稿 / AGI・シンギュラリティ
        "Tsubame33785667",   # Tsubame / シンギュラリティ・カーツワイル情報
        "ai_lin_creation",   # LIN / 最新AI分かりやすく解説 / 早稲田 / Cross AI共同創業
        "chatgptair",        # あるる / ChatGPT × AIツール 一番わかりやすく発信
        "suguruKun_ai",      # すぐる / ChatGPTガチ勢 / AI研修開発会社CEO
        "pop_ikeda",         # 池田 朋弘 / ChatGPT最強の仕事術4万部
        "masahirochaen",     # チャエン / デジライズCEO / AI情報最速発信 / Gemini顧問
        "ctgptlb",           # AGIラボ / ChatGPT・Gemini・Claude解説
        "The_AGI_WAY",       # ハヤシシュンスケ / ゴールシークプロンプト / #PPAL主宰
        "keitaro_aigc",      # けいたろう / AI×GASで業務改善 / Notion大使 / skywork大使
        "dify_base",         # Dify Base / AX情報発信・DifyコンサルAI開発
        "omluc_ai",          # 岸田崇史 / Omluc代表 / Difyではじめる〜著者
        "genspark_japan",    # Genspark 日本公式 / All-in-one AIワークスペース
        "ai_database",       # AIDB / 生成AI・論文ベースプラットフォーム
        "skywork_ai_jp",     # Skywork 日本公式 / AI オフィスエージェント
        "d_1d2d",            # d / 海外AI情報まとめ
        "ManusAI_JP",        # Manus 日本公式 (Meta) / 汎用AIエージェント
        "ManusAI",           # Manus 公式 (Meta) 英語版
        "GlbGPT",            # GlobalGPT / GPT-5・Claude・Sora・100+ AI tools統合
        "arena",             # Arena.ai / LMArena / AI評価コミュニティ
        "deepseek_ai",       # DeepSeek 公式
        "ChatGPTapp",        # ChatGPT 公式 @ChatGPTapp
        "OpenAIDevs",        # OpenAI Developers 公式
        "OpenAINewsroom",    # OpenAI Newsroom 公式
        "AnthropicAI",       # Anthropic 公式
        "claudeai",          # Claude 公式 @claudeai
        "MicrosoftAI",       # Microsoft AI 公式
        "metaai",            # AI at Meta 公式
        "openclaw",          # OpenClaw 公式 @openclaw
        "Remotion",          # Remotion / Make videos programmatically
        "moltbook",          # moltbook / OpenClaw bots & AI agents hang out
        "steipete",          # Peter Steinberger / ClawFather / @openclaw ★
        "obsdmd",            # Obsidian 公式
        # ── ビジネス・起業 国内 ────────────────────────────────────────
        "IHayato",           # イケハヤ / テレビアニメ・AIアニメ作者 / CryptoNinja
        "note_ai_mousigo",   # まな / AI×note 8ヶ月で売上2000万 / メンシプ300人
        "sako_brain",        # さこ社長 / Brain代表 / 利用者33万人 / 年商10億
        "gagarot200",        # ガガロット / AI×SNS月100万 / フリーランス
        "koala_YouTube99",   # コアラ / YouTube累計1.5億 / AI×外注化
        "Fujin_Metaverse",   # FujinAI / 1週間でAIで売上1000万 / Opal講座1位
        "ck_novasphere",     # チャンキョメ / NovaSphere / 月額98,000円AI広告 ★
        "smobijiman_sss",    # スモビジまん / 司法試験合格→事業売却13億
        "bmr_sri",           # BMR スモールビジネス研究所 / 月100万スモールビジ
        "milbon_",           # みるぼん / 外資コンサル×副業 / 月商1000万
        "career_koumei",     # キャリア孔明 / 沖縄 / 年間8億インプ / X1年5万
        "fladdict",          # 深津 貴之 / THE GUILD / note CXO
        "minowanowa",        # 箕輪厚介 / 幻冬舎編集者・社長
        "Kohaku_NFT",        # こはく / AI社員実装 / 18歳起業 / Pika・Haggsfieldと提携
        "920raian",          # ライアン / 法人4期目 / SNS×トレード
        "ceo_tommy1",        # トミー / ドバイ在住
        "0x__tom",           # Tom / 生成AI2社目起業 / ドバイ←大手広告売却
        "kosuke_agos",       # Kosuke / noimos_AI / メディア売却→150億上場
        "Ryo_Ogawa70",       # 小川嶺 / タイミー代表取締役 / 将棋連盟普及指導員
        "ozarnozarn",        # 小澤隆生 / BoostCapital VC / JFA理事
        "tabbata",           # 田端信太郎 / アクティビスト個人投資家 / LINEヤフー元役員
        "densetsufm",        # 伝説ラジオ Podcast / スタートアップ業界本音
        "suan_news",         # SUAN / スタートアップアンテナ
        "Ptaro_chan",         # ぴーたろ / 40代〜 / 本業2100万×副業1500万
        "happyyoshigi",      # よしぎ / AI時代のキャリア戦略 / SNS6万
        "moto_recruit",      # moto / 転職と副業のかけ算著者 / HIRED代表
        "Kuniyuki119",       # 今村 邦之 / ナウビレッジ上場CEO / 東京科学大講師
        "norihiko_sasaki",   # 佐々木紀彦 / PIVOT CEO
        "koji_gp",           # 山本康二 / 光通信常務出身 / アリババマーケ設立
        "tsubasamizuguch",   # 水口翼 / fonfun CEO / 自己資金でTOB / 時価総額10億→100億
        "shunkurosaki",      # 黒崎俊 / PLEX CEO / 700名
        "ozawa_group",       # 小澤辰矢 / 令和の虎 / 日本一の児童養護施設目標
        "ShusukeTerada",     # 寺田修輔 / Dual Bridge Capital / 元米系アナリスト
        "naotomatsushita",   # 松下直人 / EC経営支援機構 / Yahoo認定パートナー
        "m_kumagai",         # 熊谷正寿 / GMOインターネットグループ代表
        "hmikitani",         # 三木谷浩史 / 楽天グループCEO
        "takoratta",         # 及川卓也 / Tably / GHOVC Founding Partner
        "takahashi_ntu",     # 高橋弘樹 / ReHacQ プロデューサー / tonari CEO
        "yuji_daisuki1",     # ムササビ / JTC新規事業・商品企画
        "daigo_3_8",         # Daigo Yokota / StandBy / physical context is all you need
        "Jumpei_Mitsui",     # 三井淳平 / レゴ認定プロビルダー世界24人 / 灘→東大→藝大
        "keyplayers",        # 高野秀敏 / キープレイヤーズ / 投資実績80社超
        "damadama777",       # 黒田真行 / ルーセントドアーズ / リクナビNEXT編集長
        "K_Ishi_AI",         # K.Ishi / EPFL卒 CS専攻 / キャメルテクノロジーCTO
        "yuusaku_buddica",   # 中野優作 / BUDDICA代表 / 「成長以外全て死」
        "Leon_hongo",        # 本郷レオン / 上場企業採用面接2000人 / 転職
        "snakajima",         # Satoshi Nakajima / MulmoCast / ms-japanマイクロソフト元社長
        "moritaeiichi",      # もりっしー / 組織開発顧問 / 25年1000社 / HRアワード最優秀
        "MasanoriKanda",     # 神田昌典 / 経営コンサル / 非常識な成功法則著者
        "Money_Massa",       # マッサ / 投資コーチ / 米国個別株2倍
        "suh_sunaneko",      # すぅ / PM & PdM / アクセンチュア出身 / 支援会社経営
        # ── 投資・金融 ────────────────────────────────────────────────
        "cissan_9984",       # cis / 資産430億円株投資家
        "alljon12",          # マサニー / 純金融資産40億ニート / 成金生活
        "hakureifarm",       # 五月 / 250億円投資家 / ヘッジファンド / 競走馬生産牧場
        "teslafan1201",      # テスラ資本家Plaid / TSLA×PLTR / 内科医副業
        "Yoshi0Mura",        # 村上世彰 / 村上財団 / 「生涯投資家」著者
        "TakayamaJoe",       # Joe Takayama / 米国株×暗号資産×マクロ / Backpack BD
        "Masa_Aug2020",      # Masa / 元外資系IB役員 / 再エネ×不動産×金融
        "nicosokufx",        # にこそく / FX / 金融市場実況
        "ishiharajun",       # 石原順（西山孝四郎）/ FX・マーケット
        "Market_Letter_",    # 米国市場これ読んどけメモ
        "Barchart",          # Barchart / 金融市場ツール / Stocks・Options・Futures
        "kiyohara_stock",    # 清原投資術研究所 / ネットキャッシュ比率投資
        "DAIBAKUTO",         # DAIBAKUTO / 43年外資系金融→FIRE / 高配当株
        "entry20210104",     # 株GPT / AI×投資 / 決算分析システム開発
        "toushi_kenshou",    # ぽこたん / AI×投資家 / 資産5000万
        "paurooteri",        # パウロ / 生成AI × 半導体テック企業note
        "hukugyootaku",      # 副業オタクにゃふ / 月収500〜1000万
        "ASTS_SpaceMob",     # $ASTS SpaceMobile 情報ハブ / Since 2020
        "ASTS_Investors",    # AST Spacemobile investors
        "AST_SpaceMobile",   # AST SpaceMobile 公式 / 宇宙基地携帯通信
        "Defiantclient2",    # Kevin Chen / $ASTS $QS / economics theology
        "YasuNomu1",         # 野村泰紀 / UCバークレー理論物理学者
        "kenn",              # Kenn Ejima / Gista.js / Admit AI / ex-Quora Head JP
        # ── ニュース・メディア ──────────────────────────────────────────
        "BloombergJapan",    # Bloomberg Japan 日本語公式
        "Bank_of_Japan_j",   # 日本銀行 公式
        "TrumpPostsJA",      # トランプ氏発言速報 / Truth Social最速
        "TrumpTrackerJP",    # トランプ大統領ニュース / トランプトラッカー
        "sputnik_jp",        # Sputnik 日本 / 国際ニュース
        "turningpointjpn",   # TotalNewsWorld / 世界の情報
        "tkzwgrs",           # 滝沢ガレソ / Twitterの今まとめ
        "ZARASOKU",          # ざら速 / 株・仮想通貨ニュース速報
        "NazologyInfo",      # ナゾロジー / 科学ニュースメディア / 生き物・宇宙
        "NIKKEIxTREND",      # 日経クロストレンド / マーケティング
        "matchan_jp",        # 松島 倫明 / WIRED日本版編集長
        "WIRED",             # WIRED 公式（英語）
        "sutoroveli_news",   # テクノロジーニュース速報
        "TechCrunch",        # TechCrunch 公式
        "VentureBeat",       # VentureBeat / 変革的テクノロジー
        "thenextweb",        # TNW / The Next Web
        "engadget",          # Engadget / テック系メディア
        "PCMag",             # PCMag / 40年テックレビュー
        "ForbesTech",        # Forbes Tech
        "ycombinator",       # Y Combinator 公式
        "bayareawriter",     # Mary Ann Azevedo / Crunchbase記者
        "koder_dev",         # Koder / 海外Tech速報
        "AInokuhaku",        # AIの空白 / AI稼ぎ方毎日発信
        "norihiko_sasaki",   # 佐々木紀彦 / PIVOT CEO（重複チェック）
        "GOROman",           # null-sensei / GOROman
        "EEL_PR",            # 編集工学研究所
        "isis_es",           # イシス編集学校
        "kenjuman",          # 吉村堅樹 / 編集工学研究所
        # ── 政治・法律・行政 ───────────────────────────────────────────
        "haraeiji2",         # 原英史 / 政策工房代表 / 規制改革
        "satsukikatayama",   # 片山さつき / 自民党参議院議員
        "ikegai",            # 生貝直人 / 一橋大教授 / 情報法・AI政策
        "HiromitsuTakagi",   # 高木浩光 / セキュリティ研究員
        "Matsuo1984",        # 松尾剛行 / 弁護士 / 生成AIの法律実務著者
        "IB57185560",        # IBコンサルティング / 企業防衛 / 元野村證券
        "yoshitaka_kitao",   # 北尾吉孝 / SBIホールディングス代表
        "noricoco",          # 新井紀子 / 東ロボ / 「AI vs. 教科書が読めない子どもたち」
        "carecon_biz",       # 森田昇 / リベラルコンサル代表 / キャリコン
        "damadama777",       # 黒田真行 / ルーセントドアーズ（重複チェック）
        "takano_nara",       # 高野あつし / 元警視庁刑事・元外交官 / 危機管理会社
        "cryps1s",           # DANΞ / CISO @OpenAI / ex-CISO @Palantir
        "ssomurice_local",   # 弓月恵太 / 政治・金融・ベッセント推し
        "monozukuritarou",   # ものづくり太郎 / 製造業YouTuber35万人
        "dennotai",          # 川邊健太郎 / LINEヤフー会長 / AI起業予定
        "narendramodi",      # Narendra Modi / インド首相（再掲）
        # ── 研究・学術 ─────────────────────────────────────────────────
        "singularity20xy",   # あいシンギュラリティ / テスラ式周波数
        "namahoge",          # Naruya Kondo / 東大推薦→松尾研→落合研 / 未踏AI
        "daigo_3_8",         # Daigo Yokota / StandBy / physical context is all you need（再掲）
        "TechRacho",         # TechRacho / 現役SWE向け技術ブログ
        "RailsGuidesJP",     # Railsガイド 公式
        "RailsTutorialJP",   # Railsチュートリアル 公式
        "yasulab",           # 安川要平 / YassLab CEO / CoderDojo Japan
        # ── その他 ────────────────────────────────────────────────────
        "1fCB3jDGh651022",   # Mook / 日本在住韓国人 / Elon Musk好き
        "summer3919",        # ひろたつ / 本を読んで生きている
        "nyanko_movies",     # ニャンコ / 映画3000本 / 2.7億インプ
        "ib_kiri",           # 𝓞𝓶𝓸𝓬𝓱𝓲
        "IkawaMototaka",     # 井川意高 / 大王製紙元会長
        "midorikawa_cyo",    # ミドリさん / アラフォー婚活
        "hebitigo",          # 困惑bot
        "yosimuraya",        # 家系じゃぱん / 吉村家公認アンバサダー
        "Tsubame33785667",   # Tsubame / シンギュラリティ・カーツワイル
        # ── 追加漏れ分 ──────────────────────────────────────────────
        "tyomateee",         # 最多情報局 / 世界の話題・まとめ
        "slow_developer",    # Haider / together we build an intelligent future
        "kabutociti",        # 満州中央銀行 / 経済情報まとめ
        "toshimitsu_sowa",   # 曽和利光 / 人材研究所代表 / 採用面接2万人以上
        "m_kac",             # エムカク / 書籍著者
        "ShinWorkout0207",   # Shin / テクノロジー・ファッション
    ],
}

# 動的発見リストの保存先（Grokが毎朝発見→永続保存→次回から監視）
DYNAMIC_WATCHLIST_PATH = "/opt/shared/watchlist_dynamic.json"

# --- Grok X/Twitter search queries (rotate per run) ---
# 収益数字を含むクエリに絞る（眺めるだけの有名人は除外）
GROK_SEARCH_QUERIES = [
    (
        "Search X/Twitter for posts from the last 48 hours where people "
        "share concrete AI revenue numbers. Use queries like: "
        "(MRR OR ARR OR '$' OR revenue OR 'made money') AND (AI OR SaaS OR agent OR automation). "
        "Find posts with actual dollar amounts, subscriber counts, or client numbers."
    ),
    (
        "Search X/Twitter for posts from the last 48 hours about AI "
        "newsletter creators and content businesses sharing subscriber growth, "
        "revenue, and monetization. Find posts with real numbers like "
        "'hit $X MRR', 'X subscribers', 'earning $X/month'."
    ),
    (
        "Search X/Twitter for posts from solo developers or indie hackers "
        "in the last 48 hours: (launched OR 'just hit' OR 'reached') AND "
        "(MRR OR users OR subscribers OR revenue) AND (AI OR automation OR SaaS). "
        "Find people with real traction and concrete numbers."
    ),
    (
        "Search X/Twitter for posts in the last 48 hours about: "
        "new AI models released, API pricing changes, cost optimization tricks, "
        "or Claude/Gemini/Grok updates that could affect AI automation systems. "
        "Focus on breaking news with technical implications."
    ),
]


# =============================================================================
# API Keys
# =============================================================================
def get_api_key():
    """Get Gemini API key from environment or .env file."""
    key = os.environ.get("GOOGLE_API_KEY")
    if key:
        return key

    env_paths = ["/opt/openclaw/.env", "/opt/shared/.env"]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GOOGLE_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def get_xai_api_key():
    """Get xAI API key from environment or .env files."""
    key = os.environ.get("XAI_API_KEY")
    if key:
        return key

    env_paths = [
        "/opt/openclaw/.env", "/opt/shared/.env", "/opt/.env",
        "/opt/claude-code-telegram/.env",
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("XAI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def get_telegram_config():
    """Get Telegram bot token and owner chat ID from Neo's .env."""
    token = None
    chat_id = None
    env_path = "/opt/claude-code-telegram/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("ALLOWED_USERS="):
                    chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
    return token, chat_id


# =============================================================================
# Dynamic Watchlist — 自動発見したアカウントを永続保存
# =============================================================================
def load_dynamic_watchlist():
    """Load dynamically discovered accounts from JSON file.
    Returns a list of username strings (deduped with base list in caller).
    """
    if not os.path.exists(DYNAMIC_WATCHLIST_PATH):
        return []
    try:
        with open(DYNAMIC_WATCHLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        accounts = [e["username"] for e in data.get("discovered", []) if e.get("username")]
        print(f"  Dynamic watchlist: {len(accounts)} accounts loaded")
        return accounts
    except Exception as e:
        print(f"  Dynamic watchlist load error: {e}")
        return []


def save_dynamic_watchlist(new_discoveries):
    """Append newly discovered accounts to the persistent JSON file.
    Returns the number of new accounts actually added (deduped).
    """
    existing = []
    if os.path.exists(DYNAMIC_WATCHLIST_PATH):
        try:
            with open(DYNAMIC_WATCHLIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            existing = data.get("discovered", [])
        except Exception:
            existing = []

    existing_usernames = {e["username"].lower() for e in existing}
    added = 0
    for d in new_discoveries:
        if d.get("username") and d["username"].lower() not in existing_usernames:
            existing.append(d)
            existing_usernames.add(d["username"].lower())
            added += 1

    # Keep newest 300 entries
    existing = existing[-300:]

    os.makedirs(os.path.dirname(DYNAMIC_WATCHLIST_PATH), exist_ok=True)
    with open(DYNAMIC_WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"discovered": existing, "total": len(existing),
             "last_updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M")},
            f, indent=2, ensure_ascii=False,
        )
    print(f"  Dynamic watchlist: +{added} new accounts saved (total: {len(existing)})")
    return added


def get_all_watchlist_accounts():
    """Return deduplicated list of all accounts (base + dynamic)."""
    all_accounts = []
    seen = set()
    for accounts in X_WATCHLIST.values():
        for a in accounts:
            if a.lower() not in seen:
                all_accounts.append(a)
                seen.add(a.lower())
    for a in load_dynamic_watchlist():
        if a.lower() not in seen:
            all_accounts.append(a)
            seen.add(a.lower())
    return all_accounts


# =============================================================================
# Source 1: Reddit
# =============================================================================
def fetch_reddit(subreddit, limit=10):
    """Fetch hot posts from a subreddit via JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "HeyLoopIntelligence/3.0 (daily research; non-commercial)"
            )
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            posts = []
            for child in data.get("data", {}).get("children", []):
                d = child["data"]
                if d.get("stickied"):
                    continue
                posts.append({
                    "title": d.get("title", ""),
                    "score": d.get("score", 0),
                    "comments": d.get("num_comments", 0),
                    "url": d.get("url", ""),
                    "permalink": "https://reddit.com" + d.get("permalink", ""),
                    "selftext": (d.get("selftext") or "")[:500],
                    "created": d.get("created_utc", 0),
                    "subreddit": subreddit,
                })
            return posts
    except Exception as e:
        print(f"  Reddit r/{subreddit} error: {e}")
        return []


def collect_reddit_data(run_number):
    """Collect posts from rotating subset of both infra and revenue subs."""
    day = datetime.now(JST).timetuple().tm_yday

    # Each run picks different subreddits: 3 infra + 3 revenue
    infra_start = ((day * 4 + run_number) * 3) % len(INFRA_SUBREDDITS)
    rev_start = ((day * 4 + run_number) * 3) % len(REVENUE_SUBREDDITS)

    todays_infra = [
        INFRA_SUBREDDITS[(infra_start + i) % len(INFRA_SUBREDDITS)]
        for i in range(3)
    ]
    todays_revenue = [
        REVENUE_SUBREDDITS[(rev_start + i) % len(REVENUE_SUBREDDITS)]
        for i in range(3)
    ]

    all_subs = todays_infra + todays_revenue
    print(f"  Infra subs: {', '.join(todays_infra)}")
    print(f"  Revenue subs: {', '.join(todays_revenue)}")

    all_posts = {}
    for sub in all_subs:
        posts = fetch_reddit(sub, limit=8)
        if posts:
            posts.sort(key=lambda p: p["score"], reverse=True)
            all_posts[sub] = posts[:5]
            print(f"  r/{sub}: {len(posts)} posts fetched")
        time.sleep(1.5)  # Respect rate limit

    return all_posts


# =============================================================================
# Source 2: Hacker News
# =============================================================================
def fetch_hn_top_stories(limit=30):
    """Fetch top stories from Hacker News, filtered by relevance."""
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            story_ids = json.loads(resp.read().decode("utf-8"))[:limit]
    except Exception as e:
        print(f"  HN top stories error: {e}")
        return []

    relevant = []
    for sid in story_ids:
        try:
            item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            with urllib.request.urlopen(item_url, timeout=10) as resp:
                item = json.loads(resp.read().decode("utf-8"))
                if not item:
                    continue
                title = (item.get("title") or "").lower()
                for kw in HN_KEYWORDS:
                    if kw in title:
                        relevant.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "score": item.get("score", 0),
                            "comments": item.get("descendants", 0),
                            "hn_url": (
                                f"https://news.ycombinator.com/item?id={sid}"
                            ),
                            "matched_keyword": kw,
                        })
                        break
        except Exception:
            continue
        time.sleep(0.1)

    relevant.sort(key=lambda x: x["score"], reverse=True)
    print(f"  HN: {len(relevant)} relevant stories from top {limit}")
    return relevant[:10]


# =============================================================================
# Source 3: GitHub Releases
# =============================================================================
def fetch_github_updates(run_number):
    """Check latest releases. Full check on run 1, quick check on others."""
    # Full repo check on morning run (1), subset on other runs
    if run_number == 1:
        repos = ALL_GITHUB_REPOS
    else:
        # Alternate between infra and revenue repos
        repos = (
            INFRA_GITHUB_REPOS if run_number % 2 == 0
            else REVENUE_GITHUB_REPOS
        )

    updates = []
    for repo in repos:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "HeyLoopIntelligence/3.0",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                updates.append({
                    "repo": repo,
                    "tag": data.get("tag_name", ""),
                    "name": data.get("name", ""),
                    "published": data.get("published_at", ""),
                    "body": (data.get("body") or "")[:800],
                    "url": data.get("html_url", ""),
                })
                print(f"  GitHub {repo}: {data.get('tag_name', 'no release')}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  GitHub {repo}: no releases")
            else:
                print(f"  GitHub {repo}: HTTP {e.code}")
        except Exception as e:
            print(f"  GitHub {repo}: {e}")
        time.sleep(0.5)

    return updates


# =============================================================================
# Source 4: Gemini + Google Search grounding + Dynamic Discovery
# =============================================================================
def query_gemini_with_search(api_key, search_topic, context_data):
    """Query Gemini with Google Search grounding for real-time analysis."""
    url = f"{GEMINI_API_URL}?key={api_key}"

    prompt = f"""You are a technology + business intelligence analyst for
the "Hey Loop" project — an AI system that uses AI to generate returns
far exceeding token costs.

**Topic**: {search_topic['area']}
**Category**: {search_topic['category']}
**Search focus**: {search_topic['search_query']}

Raw data collected from Reddit and Hacker News:

{context_data}

Provide analysis in this format:

## Key Findings (from web search)
- Real news, releases, announcements from the past 7 days
- Include source URLs for EVERY claim
- For revenue topics: include specific dollar amounts, subscriber counts, growth rates

## Reddit & HN Highlights
- Most important discussions from the data above
- Include original post URLs
- Flag any revenue/business model discussions

## Revenue Signals
- Any information about people making money in this space
- Business models that are working RIGHT NOW
- Pricing data, revenue numbers, growth metrics
- Who is succeeding and how

## Actionable for Our System
- Specific things we should implement, change, or investigate
- For each action: estimated effort and potential revenue impact
- Be concrete: "Do X because Y, expected result Z"

## Newly Discovered Sources
- 2-3 NEW people, blogs, accounts, or newsletters relevant to this topic
  that are actively sharing valuable insights RIGHT NOW
- Include their URLs and what makes them worth following
- Prefer people who share revenue numbers publicly

## Warnings
- Breaking changes, deprecations, security issues
- Market shifts that could affect our strategy

Keep it factual. Every claim needs a source URL. No speculation."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.3},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            parts = result["candidates"][0]["content"]["parts"]
            text_parts = [p["text"] for p in parts if "text" in p]
            return "\n".join(text_parts)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No details"
        print(f"  Gemini Search API error {e.code}: {error_body[:300]}")
        return None
    except Exception as e:
        print(f"  Gemini Search error: {e}")
        return None


# =============================================================================
# Source 5: Grok/xAI — X/Twitter real-time search
# =============================================================================
def search_x_via_grok(xai_key, run_number):
    """Use Grok API to search X/Twitter for real-time intelligence."""
    query = GROK_SEARCH_QUERIES[run_number % len(GROK_SEARCH_QUERIES)]

    payload = {
        "model": "grok-3",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an X/Twitter intelligence analyst. Search for "
                    "recent posts and threads. Always include the @username, "
                    "post content summary, engagement metrics if visible, "
                    "and the post URL. Focus on posts with real numbers "
                    "(revenue, subscribers, growth rates)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{query}\n\n"
                    "Return the top 5 most relevant and recent posts/threads. "
                    "Format each as:\n"
                    "- @username: [summary] (likes/retweets if visible)\n"
                    "  URL: [post URL]\n"
                    "  Revenue signal: [any concrete numbers mentioned]\n"
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROK_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {xai_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            print(f"  Grok X search: {len(content)} chars")
            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No details"
        print(f"  Grok API error {e.code}: {error_body[:300]}")
        return None
    except Exception as e:
        print(f"  Grok X search error: {e}")
        return None


# =============================================================================
# Source 5b: X Watchlist — ベース+動的リスト全件を毎朝監視
# =============================================================================
def search_x_watchlist_via_grok(xai_key):
    """Search all watchlist accounts (base list + dynamically discovered).

    Combines X_WATCHLIST (static) + watchlist_dynamic.json (auto-discovered).
    No X API subscription needed — Grok's internal X access handles it.
    Grokに渡せるfrom:クエリは長さ制限があるため最大100件をバッチ処理。
    """
    all_accounts = get_all_watchlist_accounts()

    # from: クエリが長すぎるとGrokが切り捨てるので最大100件に分割
    batch_size = 100
    batches = [all_accounts[i:i + batch_size]
               for i in range(0, len(all_accounts), batch_size)]

    combined_results = []
    for batch_num, batch in enumerate(batches):
        from_query = " OR ".join(f"from:{a}" for a in batch)
        payload = {
            "model": "grok-3",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an X/Twitter intelligence analyst monitoring a "
                        "curated list of AI builders, researchers, economists, "
                        "and market strategists (Japan + Global). "
                        "Surface the highest-signal posts only. "
                        "Always include @username, summary, and post URL."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Search X/Twitter for the most insightful posts from "
                        f"the last 48 hours by these accounts:\n{from_query}\n\n"
                        "Prioritize:\n"
                        "1. AI revenue milestones (MRR, ARR, user numbers)\n"
                        "2. Geopolitical/macro analysis (Japan, Asia, US, global)\n"
                        "3. AI model releases or API changes with real impact\n"
                        "4. Original insights — NOT retweets of others' content\n\n"
                        "Return the top 8 most valuable posts:\n"
                        "- @username: [one-line summary]\n"
                        "  URL: [post URL]\n"
                        "  Signal: [concrete number or key insight]\n"
                    ),
                },
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GROK_API_URL, data=data,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {xai_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                print(
                    f"  Grok Watchlist batch {batch_num + 1}/{len(batches)}: "
                    f"{len(content)} chars ({len(batch)} accounts)"
                )
                combined_results.append(content)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else "No details"
            print(f"  Grok Watchlist batch {batch_num + 1} error {e.code}: "
                  f"{error_body[:200]}")
        except Exception as e:
            print(f"  Grok Watchlist batch {batch_num + 1} error: {e}")
        if batch_num < len(batches) - 1:
            time.sleep(2)  # Rate limiting between batches

    if not combined_results:
        return None

    total = len(all_accounts)
    header = (
        f"[Watchlist: {total} accounts monitored "
        f"(base:{sum(len(v) for v in X_WATCHLIST.values())} "
        f"+ dynamic:{total - sum(len(v) for v in X_WATCHLIST.values())})]\n\n"
    )
    return header + "\n\n---\n\n".join(combined_results)


# =============================================================================
# Source 5c: X 自動発見 — 毎朝新しい高シグナルアカウントを発見して保存
# =============================================================================
def discover_new_x_accounts_via_grok(xai_key, current_accounts):
    """Ask Grok to suggest new X accounts worth monitoring.

    Runs once per morning (Run 1). Parses @username lines and saves to
    watchlist_dynamic.json. Next morning these accounts are automatically
    included in search_x_watchlist_via_grok().
    """
    # Show first 50 of current list to avoid prompt bloat
    existing_sample = " ".join(f"@{a}" for a in current_accounts[:50])

    payload = {
        "model": "grok-3",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are building a curated X/Twitter intelligence watchlist. "
                    "Discover accounts actively posting high-signal content about "
                    "AI business revenue, geopolitics, and macroeconomics. "
                    "Focus on accounts that share concrete data, not just opinions."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Already monitoring (partial list): {existing_sample}\n\n"
                    "Based on X/Twitter activity in the last 7 days, suggest "
                    "10 NEW accounts I should monitor. Strict criteria:\n"
                    "1. AI builders publicly sharing MRR/ARR/revenue or product "
                    "launch traction\n"
                    "2. Geopolitics/macro analysts (Asia focus preferred) posting "
                    "original structural analysis\n"
                    "3. Emerging voices: under 300K followers but consistently "
                    "high-signal\n"
                    "4. Japanese AI/business accounts not widely known outside Japan\n\n"
                    "IMPORTANT: Respond in EXACTLY this format, one per line:\n"
                    "@username | Display Name | category | reason (one sentence)\n"
                    "(category: ai_builder / geopolitics / ai_research / jp_media / macro)\n"
                    "No preamble. No explanations outside this format."
                ),
            },
        ],
        "temperature": 0.6,
        "max_tokens": 1024,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROK_API_URL, data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {xai_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            print(f"  Grok Discovery raw: {len(content)} chars")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No details"
        print(f"  Grok Discovery API error {e.code}: {error_body[:200]}")
        return []
    except Exception as e:
        print(f"  Grok Discovery error: {e}")
        return []

    # Parse "@username | Display Name | category | reason" lines
    discoveries = []
    today = datetime.now(JST).strftime("%Y-%m-%d")
    for line in content.split("\n"):
        line = line.strip()
        m = re.match(
            r"@(\w+)\s*\|\s*([^|]+)\s*\|\s*(\w[\w_]*)\s*\|\s*(.+)",
            line,
        )
        if m:
            discoveries.append({
                "username": m.group(1),
                "display_name": m.group(2).strip(),
                "category": m.group(3).strip(),
                "reason": m.group(4).strip(),
                "added_date": today,
                "source": "grok_discovery",
            })
    print(f"  Grok Discovery: parsed {len(discoveries)} new accounts")
    return discoveries


# =============================================================================
# Report Formatting
# =============================================================================
def _load_polymarket_data():
    """Load Polymarket snapshot + alerts prepared by polymarket_monitor.py.

    The monitor runs 5 min before each Hey Loop via cron.
    Files: /opt/shared/polymarket/latest_snapshot.json, alerts.json
    """
    snapshot_path = "/opt/shared/polymarket/latest_snapshot.json"
    alerts_path = "/opt/shared/polymarket/alerts.json"

    snapshot = {}
    alerts = []

    try:
        if os.path.exists(snapshot_path):
            with open(snapshot_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

    try:
        if os.path.exists(alerts_path):
            with open(alerts_path, "r", encoding="utf-8") as f:
                alerts = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

    if not snapshot:
        return None

    lines = [
        "### Polymarket Prediction Markets",
        f"Active markets tracked: {len(snapshot)}",
        "",
    ]

    if alerts:
        lines.append(f"Significant odds movements: {len(alerts)}")
        for a in alerts[:5]:
            if a.get("type") == "movement":
                lines.append(
                    f"  - {a.get('question', '?')[:60]}: "
                    f"{a.get('outcome', '?')} "
                    f"{a.get('prev_prob', 0)*100:.0f}% -> "
                    f"{a.get('curr_prob', 0)*100:.0f}% "
                    f"({a.get('delta', 0)*100:+.1f}%)"
                )
        lines.append("")

    # Top 10 by volume
    lines.append("Top markets by volume:")
    items = sorted(snapshot.values(), key=lambda x: x.get("volume", 0), reverse=True)
    for item in items[:10]:
        title = item.get("title", "?")[:55]
        vol = item.get("volume", 0)
        genres = [g.get("name_en", "") for g in item.get("genres", [])]

        markets = item.get("markets", {})
        if markets:
            first_m = next(iter(markets.values()))
            prices = first_m.get("prices", {})
            odds_str = " | ".join(
                f"{k}={v*100:.0f}%" for k, v in list(prices.items())[:3]
            )
        else:
            odds_str = ""

        lines.append(f"  ${vol/1e6:.1f}M | {title}")
        if odds_str:
            lines.append(f"         {odds_str}")
        if genres:
            lines.append(f"         [{', '.join(genres)}]")

    return "\n".join(lines)


def format_raw_data(reddit_data, hn_data, github_data, x_data):
    """Format raw collected data into readable context for Gemini."""
    sections = []

    if reddit_data:
        sections.append("### Reddit Posts")
        for sub, posts in reddit_data.items():
            is_revenue = sub in REVENUE_SUBREDDITS
            tag = "[REVENUE]" if is_revenue else "[INFRA]"
            for p in posts:
                sections.append(
                    f"- {tag} r/{sub}: \"{p['title']}\" "
                    f"(score:{p['score']}, comments:{p['comments']})"
                )
                sections.append(f"  URL: {p['permalink']}")
                if p["selftext"]:
                    sections.append(f"  Summary: {p['selftext'][:200]}")

    if hn_data:
        sections.append("\n### Hacker News Top Stories")
        for s in hn_data:
            sections.append(
                f"- \"{s['title']}\" (score:{s['score']}, "
                f"comments:{s['comments']}) [{s['matched_keyword']}]"
            )
            sections.append(f"  Article: {s['url']}")
            sections.append(f"  Discussion: {s['hn_url']}")

    if github_data:
        sections.append("\n### GitHub Releases")
        for g in github_data:
            if g["tag"]:
                sections.append(
                    f"- {g['repo']} -> {g['tag']} ({g['published'][:10]})"
                )
                sections.append(f"  URL: {g['url']}")
                if g["body"]:
                    sections.append(f"  Notes: {g['body'][:300]}")

    if x_data:
        sections.append("\n### X/Twitter Intelligence (via Grok)")
        sections.append(x_data)

    # Polymarket prediction markets (data prepared by polymarket_monitor.py cron)
    polymarket_text = _load_polymarket_data()
    if polymarket_text:
        sections.append("\n" + polymarket_text)

    return "\n".join(sections) if sections else "(No raw data collected)"


# =============================================================================
# Report Saving
# =============================================================================
def save_report(run_number, topic, raw_data_text, analysis, reddit_data,
                hn_data, github_data, x_data, date_str):
    """Save the intelligence report with run number."""
    os.makedirs(LEARNING_DIR, exist_ok=True)

    area_slug = topic["area"].lower().replace(" ", "-").replace("&", "and")
    filename = f"{date_str}_run{run_number}_{area_slug}.md"
    filepath = os.path.join(LEARNING_DIR, filename)

    run_label = RUN_LABELS.get(run_number, f"Run {run_number}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Hey Loop Intelligence: {topic['area']}\n")
        f.write(f"**Date**: {date_str} | **Run**: #{run_number} ({run_label})\n")
        f.write(f"**Category**: {topic['category'].upper()}\n")
        f.write(
            f"**Sources**: Reddit, Hacker News, GitHub, Gemini+Google Search"
        )
        if x_data:
            f.write(", Grok+X/Twitter")
        f.write(f"\n**Search focus**: {topic['search_query']}\n\n")
        f.write("---\n\n")

        # Analysis
        f.write("## Analysis (Gemini + Google Search grounding)\n\n")
        if analysis:
            f.write(analysis)
        else:
            f.write("*Gemini analysis failed. Review raw data below.*\n")

        f.write("\n\n---\n\n")

        # X/Twitter data
        if x_data:
            f.write("## X/Twitter Intelligence (Grok)\n\n")
            f.write(x_data)
            f.write("\n\n---\n\n")

        # Raw data
        f.write("## Raw Data Collected\n\n")
        f.write(raw_data_text)

        f.write("\n\n---\n\n")

        # Stats
        reddit_count = sum(
            len(v) for v in reddit_data.values()
        ) if reddit_data else 0
        f.write("## Collection Stats\n")
        f.write(f"- Reddit posts: {reddit_count}\n")
        f.write(f"- HN stories: {len(hn_data)}\n")
        f.write(f"- GitHub repos: {len(github_data)}\n")
        f.write(f"- Gemini web search: {'Yes' if analysis else 'Failed'}\n")
        f.write(f"- X/Twitter (Grok): {'Yes' if x_data else 'N/A'}\n")

    print(f"Saved: {filepath}")
    return filepath


def update_dashboard(run_number, topic, date_str, filepath, stats):
    """Update the learning dashboard."""
    dashboard_path = os.path.join(LEARNING_DIR, "DASHBOARD.md")

    entries = []
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r", encoding="utf-8") as f:
            content = f.read()
            for line in content.split("\n"):
                if line.startswith("| 2"):
                    entries.append(line)

    new_entry = (
        f"| {date_str} #{run_number} | {topic['area']} "
        f"[{topic['category']}] | "
        f"R:{stats['reddit']} HN:{stats['hn']} GH:{stats['github']} "
        f"X:{'Y' if stats.get('x') else 'N'} | "
        f"Pending | {os.path.basename(filepath)} |"
    )
    entries.insert(0, new_entry)
    entries = entries[:60]  # Keep 60 entries (15 days at 4x/day)

    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write("# Hey Loop Intelligence Dashboard\n\n")
        f.write("> 4x daily intelligence | Infrastructure + Revenue\n\n")
        f.write("| Date/Run | Topic [Category] | Sources | Status | File |\n")
        f.write("|----------|------------------|---------|--------|------|\n")
        for entry in entries:
            f.write(entry + "\n")
        f.write(f"\n\n*Last updated: {date_str} run #{run_number}*\n")

    print(f"Dashboard updated: {dashboard_path}")


# =============================================================================
# Telegram: Enhanced proposals with URLs + monetization ideas
# =============================================================================
def generate_proposals(api_key, run_number, topic, analysis, github_data,
                       x_data, stats):
    """Generate owner-facing Telegram report in Japanese with monetization."""
    url = f"{GEMINI_API_URL}?key={api_key}"

    run_label = RUN_LABELS.get(run_number, f"Run {run_number}")

    github_summary = ""
    for g in github_data:
        if g.get("tag"):
            github_summary += f"- {g['repo']}: {g['tag']}\n"

    x_summary = ""
    if x_data:
        x_summary = f"\n## X/Twitter情報:\n{x_data[:2000]}\n"

    prompt = f"""あなたはHey Loopプロジェクトの経済アナリスト兼テクノロジーアドバイザーです。
以下のインテリジェンスレポートから、オーナー（非エンジニア）への報告メッセージを作成してください。

## レポート情報
- Run: #{run_number} ({run_label})
- トピック: {topic['area']} [{topic['category']}]
- 収集: Reddit {stats['reddit']}件, HN {stats['hn']}件, GitHub {stats['github']}件

## 分析結果（抜粋）:
{(analysis or '分析失敗')[:3000]}

## 依存関係リリース:
{github_summary}
{x_summary}

## 報告フォーマット（必ずこの順番で書く）:

[注目ニュース] (最大3つ、URL必須)
1. タイトル
   URL: 記事のURL
   要約: 1行で何が重要か
   収益化: この情報をどうお金に変えられるか

[インフラ更新] (あれば)
- 依存関係のアップデート、セキュリティ警告

[新発見の情報源] (最大2つ)
- 新しく見つけた人物/ブログ/アカウント + URL + なぜフォローすべきか

[提案アクション] (最大3つ)
1. 何をすべきか → なぜ → 推定効果
   承認なら「やって」と返信

## ルール:
1. 全体3500文字以内
2. 専門用語は（）で説明
3. URLは必ず含める（URLがない情報は省略）
4. 収益に関する話は最優先で記載
5. 「情報を見てどう稼ぐか」の視点を必ず入れる
6. 提案がない場合は「今回はアクション不要」と書く
7. オーナーが読んで5分で判断できるレベルに落とす"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.3},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  Proposal generation error: {e}")
        return None


def send_telegram(token, chat_id, message):
    """Send message(s) to owner via Telegram. Splits if > 4000 chars."""
    # Strip markdown (Telegram strict parser causes 400 errors)
    clean = message.replace("**", "").replace("*", "").replace("_", "")

    # Split into chunks at line boundaries
    chunks = []
    current = ""
    for line in clean.split("\n"):
        if len(current) + len(line) + 1 > 4000:
            if current:
                chunks.append(current)
            current = line
        else:
            current += ("\n" if current else "") + line
    if current:
        chunks.append(current)

    success = True
    for i, chunk in enumerate(chunks):
        url = TELEGRAM_API_URL.format(token=token)
        payload = {"chat_id": chat_id, "text": chunk}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("ok"):
                    print(
                        f"  Telegram message {i + 1}/{len(chunks)} sent"
                    )
                else:
                    print(f"  Telegram error: {result}")
                    success = False
        except Exception as e:
            print(f"  Telegram send error: {e}")
            success = False
        if i < len(chunks) - 1:
            time.sleep(1)  # Avoid rate limiting between chunks

    return success


# =============================================================================
# Run Number Detection
# =============================================================================
def detect_run_number():
    """Auto-detect run number from current JST hour."""
    jst_hour = datetime.now(JST).hour
    return jst_hour // 6  # 0-5=0, 6-11=1, 12-17=2, 18-23=3


def parse_args():
    """Parse command-line arguments."""
    run_number = None
    force = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--run" and i + 1 < len(args):
            run_number = int(args[i + 1])
            i += 2
        elif args[i] == "--force":
            force = True
            i += 1
        else:
            i += 1

    if run_number is None:
        run_number = detect_run_number()

    return run_number, force


# =============================================================================
# Main
# =============================================================================
def main():
    run_number, force = parse_args()
    date_str = datetime.now(JST).strftime("%Y-%m-%d")
    jst_time = datetime.now(JST).strftime("%H:%M")
    run_label = RUN_LABELS.get(run_number, f"Run {run_number}")

    print(f"=== Hey Loop Intelligence v3 ===")
    print(f"Date: {date_str} | Time: {jst_time} JST")
    print(f"Run: #{run_number} ({run_label})")
    print()

    # Get API keys
    api_key = get_api_key()
    if not api_key:
        print("ERROR: No GOOGLE_API_KEY found.")
        sys.exit(1)

    xai_key = get_xai_api_key()
    if xai_key:
        print("xAI API key: found (X/Twitter search enabled)")
    else:
        print("xAI API key: not found (X/Twitter search disabled)")

    # Pick today's deep-research topic
    day = datetime.now(JST).timetuple().tm_yday
    topic_index = (day * 4 + run_number) % len(DEEP_TOPICS)
    topic = DEEP_TOPICS[topic_index]
    print(f"Topic: {topic['area']} [{topic['category']}]")

    # Duplicate check
    if not force:
        area_slug = (
            topic["area"].lower().replace(" ", "-").replace("&", "and")
        )
        expected = os.path.join(
            LEARNING_DIR, f"{date_str}_run{run_number}_{area_slug}.md"
        )
        if os.path.exists(expected):
            print(f"Already ran. File: {expected}")
            print("Use --force to re-run.")
            return

    # Phase 1: Collect from all sources
    print("\n--- Phase 1: Collecting real-world data ---")

    print("\n[Reddit]")
    reddit_data = collect_reddit_data(run_number)

    print("\n[Hacker News]")
    hn_data = fetch_hn_top_stories(limit=50)

    print("\n[GitHub]")
    github_data = fetch_github_updates(run_number)

    # Phase 2: X/Twitter via Grok (morning run only to conserve $5 credit)
    x_data = None
    if xai_key and run_number == 1:
        all_accounts = get_all_watchlist_accounts()
        print(
            f"\n[X/Twitter via Grok — Watchlist ({len(all_accounts)} accounts: "
            f"base {sum(len(v) for v in X_WATCHLIST.values())} "
            f"+ dynamic {len(all_accounts) - sum(len(v) for v in X_WATCHLIST.values())})]"
        )
        watchlist_data = search_x_watchlist_via_grok(xai_key)
        if watchlist_data:
            x_data = "### X Watchlist\n" + watchlist_data

        print("\n[X/Twitter via Grok — General revenue search]")
        general_data = search_x_via_grok(xai_key, run_number)
        if general_data:
            x_data = (x_data + "\n\n" if x_data else "") + "### X General\n" + general_data

        # 自動発見: 新しい高シグナルアカウントを提案させて保存
        print("\n[X/Twitter via Grok — Auto-discover new accounts]")
        new_discoveries = discover_new_x_accounts_via_grok(xai_key, all_accounts)
        if new_discoveries:
            added_count = save_dynamic_watchlist(new_discoveries)
            if added_count > 0 and x_data:
                names = ", ".join(
                    f"@{d['username']}" for d in new_discoveries[:5]
                )
                x_data += f"\n\n### New Accounts Discovered\nAdded {added_count}: {names}"

    elif xai_key:
        print("\n[X/Twitter] Skipped (Grok runs on morning briefing only)")
    else:
        print("\n[X/Twitter] Skipped (no xAI API key)")

    # Phase 3: Format raw data for Gemini
    raw_data_text = format_raw_data(reddit_data, hn_data, github_data, x_data)

    # Phase 4: Gemini analysis with Google Search grounding
    print("\n--- Phase 2: Gemini analysis with web search ---")
    analysis = query_gemini_with_search(api_key, topic, raw_data_text)

    if analysis:
        print(f"  Analysis received: {len(analysis)} chars")
    else:
        print("  WARNING: Gemini analysis failed, saving raw data only")

    # Phase 5: Save report
    print("\n--- Phase 3: Saving report ---")
    stats = {
        "reddit": sum(
            len(v) for v in reddit_data.values()
        ) if reddit_data else 0,
        "hn": len(hn_data),
        "github": len(github_data),
        "x": bool(x_data),
    }
    filepath = save_report(
        run_number, topic, raw_data_text, analysis,
        reddit_data, hn_data, github_data, x_data, date_str,
    )
    update_dashboard(run_number, topic, date_str, filepath, stats)

    # Phase 6: Telegram report with URLs + monetization proposals
    print("\n--- Phase 4: Sending Telegram report ---")
    tg_token, tg_chat_id = get_telegram_config()
    if tg_token and tg_chat_id:
        proposals = generate_proposals(
            api_key, run_number, topic, analysis, github_data, x_data, stats,
        )
        if proposals:
            header = (
                f"[Hey Loop #{run_number}] {run_label}\n"
                f"{date_str} {jst_time} JST\n"
                f"Topic: {topic['area']} [{topic['category']}]\n"
                f"---\n\n"
            )
            message = header + proposals
            send_telegram(tg_token, tg_chat_id, message)
        else:
            print("  WARNING: Could not generate proposals")
    else:
        print("  WARNING: Telegram config not found")

    # Summary
    print(f"\n=== Done ===")
    print(f"Report: {filepath}")
    watchlist_note = " + X Watchlist(25)" if (x_data and "X Watchlist" in x_data) else ""
    print(
        f"Sources: Reddit({stats['reddit']}) + HN({stats['hn']}) + "
        f"GitHub({stats['github']}) + Gemini Search"
        + (f" + Grok/X{watchlist_note}" if x_data else "")
    )


if __name__ == "__main__":
    main()
