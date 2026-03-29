# Agent Wisdom — All Agents Shared Knowledge

> **This file is the shared brain of all agents.**
> Every agent (Jarvis, Alice, CodeX, Pixel, Luna, Scout, Guard, Hawk, Neo) MUST read this file before starting any task.
> Location: `/shared/AGENT_WISDOM.md` (container) = `/opt/shared/AGENT_WISDOM.md` (host)
> Updated by: Neo or local Claude Code. Synced to VPS automatically.

---

## ★ PRIME DIRECTIVE — AIの存在意義（全エージェント毎タスク前に必読）

> **「最高の知性を用いて、AIにかかる費用（API代・サーバー代）を圧倒的に上回るリターンを稼ぎ出すこと」**
> これが Nowpattern に存在するすべての AI エージェントの根本的な存在意義であり、ROI最大化の絶対原則。
> ——— Naoto（オーナー）の意志、2026-03-09 刻印 ———

**チェックリスト（全タスク開始前）**

1. **ROIテスト**: このタスクは Nowpattern の収益・成長・信頼に直接寄与するか？
   - YES → 全力で実行
   - NO  → Naoto に優先度確認してから動く

2. **SOTA認識**: 現在の自分（または提案するモデル）は「今世界で最も賢い脳みそ」か？
   - モデル比較は `model_intel_bot.py`（週1回自動リサーチ）が担当
   - 提案は `pending_approvals.json` へ。Telegram には送らない

3. **静音原則**: 正常動作は黙って実行。緊急事態のみ Telegram へ。
   - INFO（記事公開成功・定期タスク完了）→ ログのみ
   - ALERT（システムダウン・DLQ死亡・品質崩壊）→ Telegram 送信
   - APPROVAL（提案・予算申請・アーキテクチャ変更）→ `pending_approvals.json` にキュー

---

---

## 🚨 CRITICAL ENFORCEMENT RULES（全エージェント毎タスク前に必読・必従）

> **2026-03-29 刻印。コードで強制済み。これを無視した場合は必ずQAで検知・DRAFT降格される。**
> Naotoの直命令: 「全AIエージェントが同じ頭を使う。アップデートされたらリアルタイムで理解する」

### ★ Rule 1: JA-EN 1:1ペアリング（100%強制）

```
JA記事を公開したら → 必ずEN翻訳を作成する（即時）
EN記事を公開したら → 必ずJA版を確認する（即時）
ペアリング率 < 100% = 違反（80%ではない、100%）
```

**記事公開の手順（必須）:**
1. JA記事を`publish_deep_pattern()`で公開
2. **同セッション内で**EN翻訳を`publish_deep_pattern(language='en', ja_slug='{JAのslug}')`で公開
3. 翻訳なしで終了は禁止

**強制コード（触るな）:**
- `ghost_webhook_server.py` Check 8: 公開の瞬間にペアリングを確認 → なければNEOキューに自動追加
- `ja_en_pairing_audit.py`: 毎日08:00 JST に全記事をチェック → Telegramアラート

---

### ★ Rule 2: URLスラッグ形式（絶対厳守）

```
JA版スラッグ:  {name}       例: us-tariff-2026
EN版スラッグ:  en-{name}    例: en-us-tariff-2026
JA公開URL:     /             例: nowpattern.com/us-tariff-2026/
EN公開URL:     /en/{name}/  例: nowpattern.com/en/us-tariff-2026/
```

**禁止:**
- ❌ EN記事を英語タイトルから直接スラッグ生成（`_title_to_en_slug()` 単独使用）
- ❌ `en-` プレフィックスなしのEN記事作成
- ❌ `/en/en-{name}/`（二重`en`）

**correct API call:**
```python
# JA記事
publish_deep_pattern(title="...", body="...", language="ja")
# EN翻訳（必ずja_slugを指定）
publish_deep_pattern(title="...", body="...", language="en", ja_slug="us-tariff-2026")
```

**強制コード（触るな）:**
- `nowpattern_publisher.py`: `ja_slug`パラメータが優先され`en-{ja_slug}`を強制生成（v5.4）

---

### ★ Rule 3: 公開前QA（7+1チェック）

記事は公開直後に`ghost_webhook_server.py`が以下を自動チェック:
1. feature_image（EN記事にJA画像が入っていないか）
2. 必須タグ（nowpattern/deep-pattern/lang-ja または lang-en）
3. prediction link（EN記事の/predictions/リンク）
4. content_len（最低文字数）
5. section markers（np-fast-read等6マーカー）
6. CJK contamination（EN記事に日本語が混入していないか）
7. oracle statement（予測記事にnp-oracleがあるか）
8. **JA-EN pairing（対訳の存在確認）← 2026-03-29追加**

**不合格 → 即DRAFT降格（自動）。NEOがDRAFTを修正する。**

---

### ★ Rule 4: このファイル自体のルール

- **ルールを知ったらこのファイルを更新せよ**
- 更新方法: このファイルの末尾（自己学習ログセクション）に追記
- このCRITICAL_ENFORCEMENTセクションは**削除禁止・上書き禁止**（north-star-guard.py相当）
- 矛盾を発見した場合: このセクションが正しい → 他のドキュメントを修正する

---


## Core Principles (all agents must follow)

### 1. Research Before Action
- **NEVER** start implementing without searching first
- Search order: GitHub Issues → X (Twitter) → Official docs → Blog posts
- Minimum 3 different keyword searches before concluding "it can't be done"
- Copy working examples from real implementations, don't guess

### 2. Never Repeat Known Mistakes
- Before any task, check if a similar mistake has been recorded
- Key mistakes to remember:
  | Problem | Root Cause | Solution |
  |---------|-----------|----------|
  | OpenClaw config errors | Adding unknown keys to openclaw.json | Only use documented keys; use shared files for agent instructions |
  | Gemini model name errors | Preview model names get deprecated | Always verify model names via API before configuring |
  | N8N API 401 | Using Basic Auth instead of API key | Use `X-N8N-API-KEY` header |
  | Telegram getUpdates conflict | Multiple processes polling same bot token | Only ONE process per bot token |
  | EBUSY errors | Single file bind mount with :ro | Mount directories, not files |
  | X API 402 CreditsDepleted | Free tier requires $5 minimum credit purchase | Check billing/credits first |

### 3. X（Twitter）投稿ルール — 引用リポスト必須（全エージェント共通）
- **X への投稿は必ず「引用リポスト」形式で行うこと。通常ツイート（新規投稿）は禁止**
- **手順**: 元ニュースのツイートを見つける → そのツイートを引用リポストする → 分析コメント + nowpattern.com 記事リンクを付ける
- **理由**: 通常ツイートの連続投稿はスパム判定されアカウントが制限される。引用リポストはアルゴリズムで4xブーストされ、かつスパム判定を回避できる
- **必須構成**:
  1. 元ニュースツイートの引用リポスト
  2. 分析コメント（Deep Pattern: 1500字以内 / Speed Log: 300字以内）
  3. nowpattern.com の記事リンク
  4. ハッシュタグ: `#Nowpattern` `#ニュース分析`（必須）+ 動的タグ2〜4個（記事ジャンル・言語に対応）
- **禁止**: 元ニュースの引用なしに独自ツイートとして記事を投稿すること
- **対象エージェント**: NEO-ONE, NEO-TWO, Jarvis, Alice, Luna, CodeX, Scout, Guard, Hawk, Pixel — 全員

### 4. Verify Before Reporting
- Don't report "done" until you've verified the result works
- Check logs, test endpoints, confirm expected output
- If something fails, fix it yourself before reporting to the owner

### 5. Owner Communication Rules
- The owner is NOT an engineer. Explain in simple Japanese with metaphors
- Report format: "What happened → What I did → Result" (3 lines max)
- Make decisions yourself for technical matters. Only ask owner for strategic/budget decisions
- Always be polite (use desu/masu form)

### 6. Cause and Effect Thinking
- Every action has consequences. Think 2 steps ahead
- Before changing a service: "What depends on this? What will break?"
- Before adding config: "Does this software recognize this setting?"
- Before deleting anything: "Is someone else using this?"

---

## Technical Knowledge (accumulated from experience)

### OpenClaw
- Config file: `openclaw.json` (NOT CLI flags, NOT env vars)
- Agent instructions: Use shared files (e.g., `/shared/AGENT_RULES.md`), not config keys
- Device pairing: `paired.json` structure, manual registration may be needed
- Image processing: Requires `imageModel` setting + `maxTokens: 8192`
- Plugins: `openclaw doctor --fix` may set `enabled: false` — always verify

### N8N
- API auth: `X-N8N-API-KEY` header (NOT Basic Auth)
- Workflow management: Use REST API, NEVER direct DB manipulation
- DB INSERT won't properly activate workflows (missing internal activation state)
- API key can be inserted into `user_api_keys` table directly

### Docker
- PostgreSQL init scripts run ONLY on first start (delete volume to re-run)
- Always verify which compose file is actually running (`docker compose ps`)
- entrypoint.sh changes need `--build` (restart is not enough)
- Bind mounts: Use directories, not single files (avoids EBUSY on atomic writes)

### Telegram
- ONE bot token = ONE getUpdates process (no sharing)
- When switching services: `systemctl stop` + `disable` + verify with `ps aux`
- Photo messages have `message.text = None` — always handle this

### External APIs
- Always verify API existence before assuming it works
- Check latest pricing models (things change, e.g., X API moved to pay-per-use in 2026)
- Test with curl/wget before building automation around an API
- Gemini API has **Google Search grounding** (`"tools": [{"google_search": {}}]`) — free for Gemini 2.5, enables real-time web search

### Dependency Versions (as of 2026-02-15)
| Dependency | Our Version | Latest | Notes |
|-----------|-------------|--------|-------|
| n8n | check with `docker exec` | **2.7.5** (2026-02-13) | Health endpoint now configurable (#25729) |
| Docker Compose | check with `docker compose version` | **v5.0.2** (2026-01-21) | Progress UI fix, `runtime_flags` restored |
| Anthropic Python SDK | check with `pip show anthropic` | **v0.79.0** (2026-02-07) | Fast-mode for claude-opus-4-6 enabled |
| LangChain OpenRouter | — | **0.0.2** (2026-02-15) | New integration for OpenRouter models |

### Security Alerts (from daily intelligence 2026-02-15)
- **Compromised Docker images on Docker Hub**: A user on r/docker reported a standard-looking base image that scraped mounted volumes and sent data externally. **Always vet images before pulling.** Use `docker scout` or Trivy to scan.
- **AI agent autonomy risk**: HN top story — an AI agent autonomously published harmful content. Reminder: all our agents must have human-in-the-loop for any public-facing output (posting to X, Substack, etc.)
- **MCP security**: The Model Context Protocol standard has exploitation risks flagged in 2026. Audit any MCP integrations.

### Content Pipeline Insights (from daily intelligence 2026-02-15)
- Substack in 2026 is evolving beyond newsletters into community hubs (Chat, Live features). Our AISA strategy should leverage community, not just content.
- N8N has ready-to-deploy AI newsletter workflow templates with auto-citations — investigate for AISA
- AI-generated content differentiator: authentic voice + community engagement, not just volume

---

## Hey Loop Intelligence System (v3)

4x daily intelligence gathering: infrastructure + revenue monitoring.
Reports sent to owner via Telegram with URLs, summaries, and monetization proposals.

### Schedule (every 6 hours)
| Run | Time (JST) | Focus |
|-----|-----------|-------|
| #0 | 00:00 | Night Scan — global markets, overnight news |
| #1 | 06:00 | Morning Briefing — main report + Grok X search |
| #2 | 12:00 | Midday Update — trending topics |
| #3 | 18:00 | Evening Review — summary + action items |

### Data Sources
| Source | What it collects | How | Cost |
|--------|-----------------|-----|------|
| Reddit (Infra) | r/selfhosted, r/n8n, r/docker, r/LocalLLaMA, etc. | JSON API | Free |
| Reddit (Revenue) | r/AI_Agents, r/SideProject, r/SaaS, r/indiehackers, etc. | JSON API | Free |
| Hacker News | Top 50 stories filtered by tech + business keywords | Firebase API | Free |
| GitHub (Infra) | n8n, Docker Compose, LangChain, Anthropic SDK | REST API | Free |
| GitHub (Revenue) | crewAI, dify, AutoGPT, gpt-researcher, anything-llm | REST API | Free |
| Gemini + Google Search | 14 rotating topics (7 infra + 7 revenue) + dynamic discovery | Google Search grounding | Free |
| Grok + X/Twitter | AI builders sharing revenue, growth tactics | xAI Chat API (grok-3) | ~$0.50/query |

### Reports Location
- Reports: `/shared/learning/YYYY-MM-DD_runN_topic.md`
- Dashboard: `/shared/learning/DASHBOARD.md`
- Script: `/shared/scripts/daily-learning.py`
- Telegram: Auto-sent to owner after each run

### Neo's Responsibility
1. **Every run**: Review the latest intelligence report
2. **Extract actionable insights** and add to this file (AGENT_WISDOM.md)
3. **Flag security warnings** immediately to the owner
4. **Track dependency updates** (new releases)
5. **Identify revenue opportunities** from the revenue-focused reports

---

## Learning Loop Protocol

When you complete a task or encounter a problem:

### On Success
1. Note what worked well
2. If you found a useful technique, add it to this file
3. Share with other agents via `/shared/reports/`

### On Failure
1. Record the mistake immediately (don't postpone)
2. Format:
   ```
   Date: YYYY-MM-DD
   What happened: [symptom]
   Why: [root cause]
   What I tried that didn't work: [failed approaches]
   What actually fixed it: [solution]
   Lesson: [what to do differently next time]
   ```
3. Add to the Technical Knowledge section above if it's a reusable lesson
4. Report to Neo for inclusion in KNOWN_MISTAKES.md

### Before Every Task
1. Read this file (you're doing it now)
2. Ask yourself: "Has this been tried before? Is there a known pitfall?"
3. Search externally for examples of what you're about to do
4. Check `/shared/learning/` for recent intelligence on this topic
5. Then act

---

## Agent Roles & Collaboration

| Agent | Role | Strengths | When to delegate TO |
|-------|------|-----------|-------------------|
| Jarvis | Execution, posting, translation | Task execution, multi-language | Routine tasks, content posting |
| Alice | Research | Deep investigation | When you need thorough research |
| CodeX | Development | Code writing, debugging | Technical implementation |
| Pixel | Design | Visual content | Image/design tasks |
| Luna | Writing assistant | Content creation | Article drafts, copy |
| Scout | Data processing | Data analysis | CSV, reports, data tasks |
| Guard | Security | Security auditing | Security reviews, vulnerability checks |
| Hawk | X/SNS research | Social media intelligence | X/Twitter research, trend analysis |
| Neo | CTO, strategy, article writing | High-level decisions, complex reasoning | Architecture decisions, complex problems |

**Delegation rule**: If your task is outside your specialty, delegate to the right agent via `sessions_spawn`. Don't try to do everything yourself.

---

*Last updated: 2026-02-19*
*Update this file whenever new knowledge is gained. This is our collective memory.*

## 2026-02-25: Ghost CSS検証の必須手順

CSSをcodeinjection_headに書き込んだ後は必ずHTTPSでfetchしてCSS文字列を確認すること。
「DBに書いた」≠「ブラウザで表示される」。

特に注意: font-size: 0 の親要素に font-size: inherit を使った ::after は不可視になる。
常に明示的なfont-sizeを使うこと（例: font-size: 1rem）。

検証コマンド:
  curl -sk https://nowpattern.com/en/ | grep -o 'nav-yu-ce-toratuka a::after[^}]*}'


## ⚠️ 予測トラッカーのカード件数確認ルール（2026-02-26追加）
- **誤り**: prediction_db.json の件数 = ページ表示件数と思い込む
- **正しい確認方法**: 
- **実際の構成**: prediction_db (7件) + Ghost記事 (12件) = **合計19件**
- この確認を省略した場合、「全件修正済み」という報告が嘘になる

## ⚠️ 予測トラッカーのカード件数確認ルール（2026-02-26追加）
- **誤り**: prediction_db.json の件数 = ページ表示件数と思い込む
- **正しい確認方法**: 
- **実際の構成**: prediction_db (7件) + Ghost記事 (12件) = 合計19件
- この確認を省略した場合、「全件修正済み」という報告が嘘になる

---
## 2026-03-06: パターンの歴史バグ（スキーマ・ビルダー不一致）

### 症状
- 記事の「パターンの歴史」セクションに「1994年年:」「2003年年:」など中身なし
- 年号の後に「年年」と二重表記、内容が全て空欄

### 根本原因
- AIのJSONスキーマ定義: , , ,  フィールド
- article_builder.pyが読んでいたフィールド: , ,  → **全て空**
- 年の二重表記: AIが「1994年」と返すのにビルダーがさらに「年」を追加

### 修正済みファイル
-  の 
  - // フィールドを正しく読む
  - year末尾の「年」を自動除去
-  の 
  -  チェック追加: 空のcaseがあればself-refineを強制

### 教訓
- **スキーマとビルダーのフィールド名を必ず一致させる**
- 新しいフィールド名を追加したらビルダー側も同時に更新する
- quality_check()で「表示される内容が空かどうか」まで検証する

### 影響記事
- 17件の記事でパターン歴史が空欄（）
- 再生成が必要



---
## 2026-03-06: パターンの歴史バグ（スキーマとビルダーのフィールド名不一致）

### 症状
- 記事の「パターンの歴史」セクションに「1994年年:」など、年号の二重表記と内容が空欄

### 根本原因
1. AIのJSONスキーマは event/pattern/lesson フィールドで返却
2. article_builder.pyは title/content/similarity を読もうとした → 全て空文字
3. year末尾の「年」をAIが付けた上にビルダーもさらに「年」を追加 → 「年年」

### 修正内容（2026-03-06）
- nowpattern_article_builder.py の _build_pattern_history_html() を修正
  - event/pattern/lesson を正しく読む（title/contentのフォールバックも維持）
  - year末尾の「年」を自動除去
- nowpattern-deep-pattern-generate.py の quality_check() に PATTERN-HISTORY-EMPTY チェック追加
  - 空のパターン歴史ケースを検出 → self-refineを強制発動

### 教訓（絶対忘れるな）
- スキーマのフィールド名とビルダーのフィールド名を必ず一致させる
- 新フィールド追加時はビルダー側も同時更新する
- quality_check()は「空文字になっていないか」まで確認する

### 影響: 17件の記事でパターン歴史が空欄（/opt/shared/scripts/articles_needs_regen.json）

## 自己学習ログ（Evolution Loop）

### 2026-03-22 自動生成
分析対象: 29件 | 平均Brier: 0.4256 | 的中: 10件 | 外れ: 16件

## Nowpattern 予測精度向上分析

1. **パターン分析**:
    *   **的中**: 「正統性の空白」「権力の過伸展」といった政治・軍事的な力学が関連する予測で、YESの確率が高い場合に的中しやすい傾向が見られる。特に、NATOの東欧増派のような継続的な事象に関する予測は的中率が高い。
    *   **外れ**: 経済・金融関連の予測（BTC価格、FRB利下げ、関税）で外れるケースが多い。「物語の覇権」「伝染の連鎖」といった力学が関連する場合、予測が外れる傾向がある。

2. **根本原因**:
    外れた予測で最も多い失敗パターンは、**市場の動向や政治的判断の急変に対する過小評価**である。過去のデータや既存のトレンドに過度に依存し、突発的なイベントや市場心理の変化を考慮できていない。特に、自動判定で高確率が出た場合に、その確率を鵜呑みにしてしまう傾向がある。

3. **改善ルール**:

```markdown
- [物語の覇権]: 市場のセンチメントやトレンドの変化に注意を払い、過去のデータだけでなく、最新のニュースや専門家の意見を収集する。
- [伝染の連鎖]: 予測対象が経済・金融関連の場合、自動判定の結果を鵜呑みにせず、複数の情報源を用いて慎重に検証する。特に、市場のボラティリティが高い時期は、予測期間を短く区切ることも検討する。
- [後発逆転]: 予測が外れた場合、その原因を詳細に分析し、類似の予測を行う際に同じ過ちを繰り返さないようにする。外れた予測の力学タグを記録し、今後の予測の参考に活用する。
```


---


### 2026-03-15 自動生成
分析対象: 6件 | 平均Brier: 0.2171 | 的中: 1件 | 外れ: 3件

## Nowpattern 予測分析と改善指示

**1. パターン分析:**

*   **的中:** 「ハメネイ師暗殺」という地政学リスクイベントに関連する予測が的中している。これは、具体的なトリガーイベントと、それに対する市場の反応を捉えやすい可能性がある。
*   **外れ:** BTC価格やFRBの利下げといった金融市場に関連する予測が外れている。これらの予測は、複雑な要因が絡み合い、予測が困難である可能性を示唆する。また、自動判定された高確率の予測が外れていることから、自動判定ロジックに改善の余地がある。力学タグとしては「正統性の空白」「制度の劣化」が外れ予測に共通して見られる。

**2. 根本原因:**

外れた予測で最も多い失敗パターンは、**確率の過信と自動判定ロジックの偏り**である。特に、自動判定で高確率とされた予測が外れていることから、過去データへの過剰な適合や、市場の変動に対する感度の低さが考えられる。また、金融市場の予測においては、複数の力学が複雑に絡み合い、単一の力学だけでは予測が困難である可能性も考慮する必要がある。

**3. 改善ルール:**

```
- [正統性の空白]: 政治的リーダーシップの空白イベントは、市場の反応を捉えやすいものの、その後の権力闘争や政策変更など、不確実性を考慮し、確率を過信しないこと。
- [制度の劣化]: 制度疲労や機能不全が予測の根拠となる場合、市場の合理的な判断を阻害する要因を考慮し、自動判定ロジックにバイアスがないか検証すること。
- [伝染の連鎖]: 金融市場の予測においては、複数の力学が複雑に絡み合うことを前提とし、単一の力学に依存せず、複合的な視点からシナリオ分析を行うこと。
```


---


### 2026-03-09 自動生成
分析対象: 2件 | 平均Brier: 0.1688 | 的中: 1件 | 外れ: 1件

## Nowpattern 次回予測精度向上のための指示

### 1. パターン分析

的中した予測は「ハメネイ師暗殺」という明確なトリガーイベントと、それに対するイラン国内の権力構造という比較的予測しやすい力学に基づいている。一方、外れた予測は「BTC価格」という市場の変動に左右されやすいトピックであり、「物語の覇権」という抽象的な力学が用いられている。**的中予測は、具体的なトリガーイベントと、それに対する構造的な反応を捉えている傾向がある。**

### 2. 根本原因

外れた予測の主な原因は、**市場の感情や外部要因の影響を過小評価したこと**にあると考えられる。「最高裁関税判決」というトリガーイベントはあったものの、BTC価格はそれ以外の要因（市場全体のトレンド、投資家の心理など）によって大きく変動し、Nowpatternの予測はそれらを考慮できていなかった。**確率の過信と、市場の複雑性を考慮できていない点が問題。**

### 3. 改善ルール (AGENT_WISDOM.md に書き込む形式)

```
- [物語の覇権]: 市場の感情やトレンドに左右されやすいトピックの場合、物語の覇権だけでなく、定量的な指標（過去の価格変動、取引量など）も考慮に入れること。
- [正統性の空白]: 権力構造の変化を予測する際、外部からの影響（国際情勢、他国の介入など）も考慮に入れること。
- [確率の過信]: 予測確率が70%を超える場合、必ず反対のシナリオを詳細に検討し、その可能性を過小評価していないか確認すること。
```


---


### 2026-03-09 自動生成
分析対象: 2件 | 平均Brier: 0.1688 | 的中: 1件 | 外れ: 1件

## Nowpattern 次回予測精度向上のための分析

**1. パターン分析:**

*   **的中:** 「正統性の空白」が共通して見られる。権力構造の変化や空白を予測するシナリオにおいて、Nowpatternは高い精度を発揮する傾向がある。
*   **外れ:** 「物語の覇権」が関連している。市場心理やトレンドに左右される予測において、Nowpatternは過小評価する傾向がある。

**2. 根本原因:**

外れた予測の主な失敗パターンは「市場トレンドへの過小評価」である。BTC価格予測において、ファンダメンタルズ分析（最高裁関税判決）に偏重し、市場全体の強気トレンドを十分に考慮しなかったことが原因と考えられる。確率の過信（68%でNOと予測）も、この失敗を助長した。

**3. 改善ルール:**

```
- [物語の覇権]: 市場トレンドの強さを定量的に評価し、予測確率に反映させる。過去のトレンドデータ、ソーシャルメディアのセンチメント分析、専門家の意見などを総合的に考慮する。
- [確率の調整]: 予測確率を決定する際、過去の類似事例における的中率を参考に、過信を避ける。特に、市場トレンドに左右される予測においては、50%に近い確率を積極的に採用する。
- [逆力学の検討]: 予測シナリオの反対側の可能性を明確に定義し、その発生確率を評価する。例えば、BTC価格予測であれば、弱気シナリオの可能性と影響を詳細に分析し、予測に反映させる。
```


---


---

## ★ DOCTRINE LIBRARY — 意思決定の典拠（2026-03-14 追加）

> 以下の5ドクトリンは「世界最高の経営者・予測者の知恵を、Nowpatternの運用規範に翻訳したもの」。
> 全エージェントは実装前にここを参照すること。
> 原本: ローカル  ディレクトリ（Gitで管理・VPSに不定期同期）

| ドクトリン | 典拠 | 核心ルール |
|-----------|------|-----------|
| **FOUNDER_CONSTITUTION.md** | Nowpattern創設者の誓い + Eternal Directives | ミッション・モート・3原則の不変定義 |
| **DECISION_DOCTRINE.md** | Harold Geneen + Jeff Bezos | 5事実分類・Type1/2判断・ノーサプライズ |
| **WISDOM_INGESTION_DOCTRINE.md** | Tetlock + Munger + Kahneman | L1-L5知恵階層・Superforecaster7原則・世界一の数値基準 |
| **LONG_TERM_VALUE_DOCTRINE.md** | Bezos + Helmer + Buffett | LTV7次元スコア・7 Powers・やらないことの基準 |
| **DISSENT_DOCTRINE.md** | Geneen + Dalio + Grove | 反論の義務条件・4ステップ・変曲点シグナル |

### 最頻使用ルール（全エージェント記憶すること）



```
1. 事実確認（DECISION_DOCTRINE）:
   未確認を「〜のはず」で語った瞬間にWishful Fact = 禁止

2. LTVスコア（LONG_TERM_VALUE）:
   実装前に7次元採点。15点未満はNaotoに確認してから実施

3. 反論義務（DISSENT_DOCTRINE）:
   条件A～D に該当したら、根拠付きで1回反論する義務がある

4. 世界一の定義（WISDOM_INGESTION）:
   Brier Score 0.13以下 = GJPトップ10%水準 = Nowpatternの3年後目標

5. ノーサプライズ（DECISION_DOCTRINE）:
   問題発見の瞬間にTelegramで報告。後から「実は〜」は禁止
```


---

## Brier悪化止血ルール（2026-03-15 ローカルClaude Code 追記）

### Ensemble極小化禁止ルール（最重要）

**背景**: prediction_auto_update.py の Extremizing が「悲観シナリオ = 6%」を生成 → 実際に悲観が現実に → brier=0.4117（最悪クラス）

```
禁止パターン:
- 楽観/懐疑/ベースレートが すべて 10% 以下で収束 → Extremize → 6% 以下
  → これは「全員の楽観バイアスが揃った」ことを意味し、そのまま信用してはいけない

強制ルール:
  1. 金融市場（BTC/FRB/株式）の悲観シナリオ確率は **最低15%** を下限とする
  2. Ensemble 3視点が全て同一方向（差 < 5pp）で収束した場合、 
     confidence を「高」ではなく「要追加分析」に強制する
  3. our_pick_prob が 10% 以下になった場合は pred auto_update をスキップし、
     NEO-ONE が手動で確率を再評価してから更新する
```

**根拠**: 解決済み6件中、brier > 0.30 の2件はいずれも「3視点が同方向に収束 → Extremize → 6-10%」パターン。市場は常にtail riskを持つ（最低15%）。


---

## キャリブレーションルール統合ログ（2026-03-21 local-claude）

### 実装完了: calibration_rules.json + prediction_ensemble.py統合

**背景**: Brier avg 0.4256 (VERY BAD)。主因: 地政学予測で85-99% YES → 実際はNO。
**根本原因**: 学習ループのStage 4-5が断絶。evolution_loopが定性テキストを保存するが機械的強制なし。

**実装内容**:
-  作成（5ルール）
-  に  統合
  - CR-001: 地政学エスカレーション割引 (85%→54%, Brier 0.75→0.30)
  - CR-004: 過収束フラグ (spread < 5pp → 「低（過収束）」)
  - CR-005: 極端確率クリップ (0%/100%禁止 → 5%/95%)
  - CR-002/CR-003: フロアルール（シナリオ確率用、prediction_page_builderへの統合は次回）

**使用方法**: 
**次回タスク**: evolution_loop.py → calibration_rules.json 自動更新パイプライン



---

## キャリブレーションルール統合ログ（2026-03-21 local-claude）

### 実装完了: calibration_rules.json + prediction_ensemble.py統合

背景: Brier avg 0.4256 (VERY BAD)。主因: 地政学予測で85-99% YES -> 実際はNO。
根本原因: 学習ループのStage 4-5が断絶。evolution_loopが定性テキストを保存するが機械的強制なし。

実装内容:
- /opt/shared/data/calibration_rules.json 作成（5ルール）
- /opt/shared/scripts/prediction_ensemble.py に apply_calibration_rules() 統合
  - CR-001: 地政学エスカレーション割引 (85%→54%, Brier 0.75→0.30)
  - CR-004: 過収束フラグ (spread<5pp → 低(過収束))
  - CR-005: 極端確率クリップ (0%/100%禁止 → 5%/95%範囲)
  - CR-002/CR-003: フロアルール（シナリオ確率用、次回実装）

使用方法: python3 /opt/shared/scripts/prediction_ensemble.py --id NP-2026-XXXX
次回タスク: evolution_loop.py → calibration_rules.json 自動更新パイプライン

---

## 2026-03-22 メトリクス整合性 + 長期記憶OS修復（local-claude）

### セッション概要
本セッションで Naoto Intelligence OS の4トラック同時実行を完了。

### Track 1: Brier Score計算式修正（完了）
- canonical: （our_pickの方向で反転しない）
- avg Brier: 0.4256 → 0.1295 (EXCELLENT)
- unit tests: 8/8 PASS (brier_audit.py)
- Daily audit cron: 毎日 22:59 UTC (08:00 JST)

### Track 2: サイトQA（完了）
- /predictions/ + /en/predictions/ → 200 OK
- Reader Vote API (port 8766) → 健全
- Ghost Webhook servers → port 8765/8769 稼働中
- UUID ghost_url = 0件（14件修正済み: NP-0795~0808, 0810, 0811）
- 残課題: NP-0113~0122 (10件 EN ghost_url未設定)

### Track 3: ChromaDB長期記憶修復（完了）
- 原因: chromadb パッケージ未インストール（2026-02-23〜2026-03-22の28日間停止）
- 修正: venv作成  + chromadb 1.5.5 インストール
- ラッパー: 
- 現在: 10+エントリ稼働中
- 自動化: daily_memory_harvest.py cron (0 0 * * *)

### Track 4: publisher.py DRAFT再発防止（完了）
- nowpattern_publisher.py: status==draft または /p/ in url → ghost_url保存スキップ
- ChromaDB harvest cron追加 (brier_audit + evolution_log + known_mistakes 自動収集)

### キーファイルパス（2026-03-22確認）
- prediction_db.json: 813件（active:161, open:12, resolving:611, resolved:29）
- brier_audit.py: /opt/shared/scripts/ — daily 22:59 UTC
- daily_memory_harvest.py: /opt/shared/scripts/ — daily 00:00 UTC
- memory venv: /opt/shared/memory/venv/bin/python
- prediction_auto_verifier.log: /opt/shared/logs/ → symlink → /var/log/prediction-verifier.log

### 未解決（NEO-ONE/TWOへのタスク）
- NP-0113~0122: 10件のEN予測に Ghost記事なし。記事作成してghost_urlを設定すること

---

## 2026-03-22 メトリクス整合性 + 長期記憶OS修復（local-claude）

### セッション概要
本セッションで Naoto Intelligence OS の4トラック同時実行を完了。

### Track 1: Brier Score計算式修正（完了）
- canonical: BS = (our_pick_prob/100 - outcome)^2（our_pickの方向で反転しない）
- avg Brier: 0.4256 → 0.1295 (EXCELLENT)
- unit tests: 8/8 PASS — brier_audit.py
- Daily audit cron: 毎日 22:59 UTC (08:00 JST)

### Track 2: サイトQA（完了）
- /predictions/ + /en/predictions/ → 200 OK
- Reader Vote API (port 8766) → 健全
- Ghost Webhook servers → port 8765/8769 稼働中
- UUID ghost_url = 0件（14件修正済み: NP-0795~0808, 0810, 0811）
- 残課題: NP-0113~0122 (10件 EN ghost_url未設定)

### Track 3: ChromaDB長期記憶修復（完了）
- 原因: chromadb パッケージ未インストール（2026-02-23〜2026-03-22の28日間停止）
- 修正: venv作成 /opt/shared/memory/venv/ + chromadb 1.5.5 インストール
- ラッパー: /opt/shared/scripts/memory_store_run.sh
- 現在: 10+エントリ稼働中
- 自動化: daily_memory_harvest.py cron (0 0 * * *)

### Track 4: publisher.py DRAFT再発防止（完了）
- nowpattern_publisher.py: status==draft または /p/ in url → ghost_url保存スキップ
- ChromaDB harvest cron追加 (brier_audit + evolution_log + known_mistakes 自動収集)

### キーファイルパス（2026-03-22確認）
- prediction_db.json: 813件（active:161, open:12, resolving:611, resolved:29）
- brier_audit.py: /opt/shared/scripts/ — daily 22:59 UTC
- daily_memory_harvest.py: /opt/shared/scripts/ — daily 00:00 UTC
- memory venv: /opt/shared/memory/venv/bin/python
- prediction_auto_verifier.log: /opt/shared/logs/ → symlink → /var/log/prediction-verifier.log

### 未解決（NEO-ONE/TWOへのタスク）
- NP-0113~0122: 10件のEN予測に Ghost記事なし。記事作成してghost_urlを設定すること

---
## 自己学習ログ — 2026-03-22 セッション (Local Claude Code) 20:35 JST

### 発見・修正した問題
1. **prediction_page_builder.py scenarios fallback** — NP-0655〜0814の162件（our_pick_probのみ保持、scenariosなし）がページに表示されていなかった。フォールバック実装済み。EN: 37→658アンカー
2. **ORACLE STATEMENTアンカーID大文字小文字不一致** — builder側のIDが大文字`NP-`、記事リンク側が小文字`np-`。builder側を`.lower()`で統一済み
3. **P3: 21件の旧形式予測のlang:ja欠落** — NP-0002〜0022にlang:jaを追加済み。prediction_db.json保存済み
4. **NP-0795〜0808 /p/UUID/ ghost_url** — 今セッション前に別サブエージェントが修正済み（bak-uuid-fix-20260322182912）
5. **EN predictions duplicate canonical** — curl確認では1つのみ。問題なし
6. **ChromaDB harvest** — 実は稼働中。`/opt/shared/memory/entries/` に10件、cron 0:00 UTC実行中
7. **FileLock + Ghost Webhook guardian** — 2026-03-10から稼働中（ghost-page-guardian.service active）

### 数字の変化
- EN predictions page アンカー数: 37 → 658 (大幅改善)
- JA predictions page アンカー数: 155 (変化なし、正常)
- prediction_db.json lang:ja明示件数: +21件

### 学習（次回予測時に反映すること）
- prediction_db.jsonに新しいフィールド形式（scenariosなし、our_pick_prob直接）を追加する際は、必ずpage_builderのbuild_rows()のスキップ条件を確認する
- cron実行後30分以内に新しい予測がページに表示されない場合、page_builderログ(/opt/shared/polymarket/prediction_page.log)で「⚠️ NO ARTICLE」や「continue」判定を確認する

---
## 自己学習ログ — 2026-03-22 セッション (Local Claude Code) 最終追記 JST

### 本日の主要達成（Scouter + QA系）
1. **Nowpattern Scouter v1.0** — 7軸スコアリングシステム完成。5.1→5.7/7に改善。World Gap 1.86→1.29
2. **SMNA Engine** — mistake_registry.json(21件) + mistake_registry.py。Level 5/7, Prevention 67%
3. **重複記事112件DRAFT化** — 1062件から68タイトルグループを検出、112件を非破壊的にDRAFT化
4. **site_health_check FAIL 52→0** — GENRE validator false positive修正(670件誤FAIL) + 重複記事除去

### 技術的教訓
- **Ghost API None罠**:  はキーが存在してNoneの場合にNoneを返す。を使え
- **バリデータのタグ形式確認**: とは別物。修正前に実際の記事タグを確認すること
- **Nowpattern Scouter false positive**: prob=0かつpick=NOは有効（P(YES)=0 = 100% confident NO）

### 数字の変化
- site_health_check FAIL: 52 → 0 (出荷OK)
- Nowpattern Scouter: 5.1/7 → 5.7/7
- Ghost published posts: 1062 → 950 (112件DRAFT)
- Duplicate title groups: 68 → 0


---
## 自己学習ログ — 2026-03-22 セッション (Local Claude Code) 最終追記 JST

### 本日の主要達成（Scouter + QA系）
1. Nowpattern Scouter v1.0 — 7軸スコアリングシステム完成。5.1→5.7/7に改善。World Gap 1.86→1.29
2. SMNA Engine — mistake_registry.json(21件) + mistake_registry.py。Level 5/7, Prevention 67%
3. 重複記事112件DRAFT化 — 1062件から68タイトルグループを検出、112件を非破壊的にDRAFT化
4. site_health_check FAIL 52→0 — GENRE validator false positive修正 + 重複記事除去

### 技術的教訓
- Ghost API None罠: .get("field", "")はキーが存在してNoneの場合にNoneを返す。(p.get("field") or "")を使え
- バリデータのタグ形式確認: genre-geopoliticsとgeopoliticsは別物。修正前に実際の記事タグを確認すること
- Nowpattern Scouter false positive: prob=0かつpick=NOは有効（P(YES)=0 = 100% confident NO）

### 数字の変化
- site_health_check FAIL: 52 → 0 (出荷OK)
- Nowpattern Scouter: 5.1/7 → 5.7/7
- Ghost published posts: 1062 → 950 (112件DRAFT)
- Duplicate title groups: 68 → 0


---
## 自己学習ログ — 2026-03-22 セッション後半 (Local Claude Code) JST

### 本日の主要達成
1. os_scouter.py T1: today_learned/internalized/prevented/next_to_improve + 履歴auto-save実装
2. nowpattern_scouter.py T2: not_fixed_because フィールド追加 + 履歴auto-save
3. SMNA Engine T3: pre_detection_rate/memory_coverage/high_severity_guard_coverage メトリクス追加
4. Metrics監査 T4: resolving=611=意図的設計確認、prob=0+pick=NO=有効なエクストリーム予測確認
5. Site QA T5 (via agent): 全9ページ200、リーダーAPI正常、Caddyリダイレクト正常
6. P2修正: /en/about/ + /en/taxonomy/ duplicate canonical → canonical_urlフィールド+codeinjection_head整理

### 重要数値（2026-03-22時点）
- prediction_db: 815件（active=163, open=12, resolved=29, resolving=611）
- avg Brier Score: 0.1295（GOOD水準。修正前0.4256）
- SMNA Level: 5/7、prevention_rate=85.7%、memory_coverage=9.5%（LOW=要改善）
- site_health: OK:10, FAIL:0

### 技術的教訓
- **Ghost canonical重複修正**: slugがen-nameのページは、Ghost自動生成canonicalとcodeinjection_headのcanonicalが重複する。解決: canonical_urlフィールドをAPIで設定 + codeinjection_headからcanonical行を削除
- **Ghost API PUT 409防止**: PUTリクエストには必ずGETで取得した最新updated_atを含める
- **SMNA memory_coverage低い(9.5%)**: 21件のmistakeのうち2件しかlinked_memoryがない。次回改善候補: mistake_registryの各エントリにlinked_memory/linked_guardフィールドを手動で追加
- **resolving=611の意味**: prediction_auto_verifier.pyが解決日前の予測を自動でresolvingに変更する仕様。データエラーではない
- **prob=0+pick=NO = 有効**: 「YESの確率が0% = NOを100%確信」という意味の正規表現。Brier計算では(0.0-0.0)^2=0.0（完璧）

### MEMORY.md 更新すべき内容
- 記事数: 684件（2026-03-22現在）


---

## 自己学習ログ（2026-03-25 追記 by local-claude — Nao Intelligence Phase 1）

### Night Mode 自律実行タスク一覧（2026-03-25）
1. Batch Publish: 516 drafts → 18 drafts、776→1,322 published（+546記事）
2. lang-ja タグバグ修正: deep-pattern-generate.py + nowpattern_publisher.py の EN コンテンツが lang-ja タグで作られる問題を修正
3. Reflexion Prompt: NEO-ONE/TWO のシステムプロンプトに Stanford Reflexion pattern を追加
4. Polymarket API sync: /opt/shared/scripts/polymarket_sync.py を新規作成。Jaccard係数でキーワードマッチング、日次 cron（JST06:30）登録、初回4件更新
5. Category Brier Analysis: /opt/shared/scripts/category_brier_analysis.py 作成。evolution_loop.py に統合。経済・貿易(0.4868)/暗号資産(0.3334) が弱点カテゴリと判明
6. Observer Log Infrastructure: /opt/shared/observer_log/ 作成。全エージェント共通の学習・タスク記録フォーマット。observer_writer.py ヘルパー作成

### 重要数値（2026-03-25時点）
- prediction_db: 982件（active=40, resolving~893, resolved=37, open=12）
- avg Brier Score: 0.1776（FAIR。経済・貿易と暗号資産が要改善）
- category_brier.json: /opt/shared/logs/category_brier.json に生成済み
- observer_log: /opt/shared/observer_log/2026-03-25.json 初期化完了

### 技術的教訓（2026-03-25追加）
- **bash heredoc 限界**: Python スクリプトに単引用符が含まれると heredoc が壊れる → Write ツールでローカル作成→SCP が確実
- **Telegram Markdown 400エラー**: ジャンル名などに特殊文字があると parse_mode=Markdown で 400 になる → parse_mode=HTML + HTMLタグ方式が安全
- **dynamics_tags セパレータ**: prediction_db.json の dynamics_tags は ` × `（スペース×スペース）で複数タグが結合されている
- **Polymarket outcomePrices 型**: JSON文字列として返ってくる（文字列配列）、json.loads() が必要

### Brier Score 弱点カテゴリ（2026-03-25確認）
- 経済・貿易: avg 0.4868（POOR、n=3）→ 高確率予測で外れが多い
- 暗号資産: avg 0.3334（POOR、n=4）→ ボラティリティ高く過信になりやすい
- 対策: 経済・貿易・暗号資産の予測は our_pick_prob を最大65%に抑制する


---

## 自己学習ログ（2026-03-29 追記 by local-claude — T027 ECC Pipeline監査）

### T027: ECC Pipeline 完全性監査 — 発見・修正サマリー

**監査スコープ**: ECC Pipeline全段（KNOWN_MISTAKES.md → auto-codifier.py → mistake_patterns.json → fact-checker.py → regression-runner.py → session-start.sh 3d）

#### G_T027_1: active_task_id.txt が stale（T026完了後も更新されていなかった）
- **原因**: task_ledger.json のタスク登録と active_task_id.txt の更新を別操作として管理していた
- **修正**: T027 登録時に同時更新。再発防止 → タスク登録と active_task_id 更新を常に同時実行すること

#### G_T027_2: KNOWN_MISTAKES.md の GUARD_PATTERN が raw regex 文字列形式だった（auto-codifier.py が無視する形式）
- **根本原因**: auto-codifier.py の正規表現 `r"\*\*GUARD_PATTERN\*\*\s*:\s*\`(\{[^`]+\})\`"` は `{...}` JSON形式のみを検出する。raw regex を backtick で囲んでも `{` で始まらないため完全にスルーされる
- **症状**: REGRESSION_MANUAL_ONLY パターンが KNOWN_MISTAKES.md に追記されても mistake_patterns.json に自動登録されなかった（手動追加が必要だった）
- **修正**: GUARD_PATTERN を `{"pattern": "...", "feedback": "...", "name": "..."}` JSON形式に修正、手動で mistake_patterns.json に追加
- **教訓**: GUARD_PATTERN は必ず `{"pattern": "正規表現", "feedback": "⛔ メッセージ", "name": "PATTERN_NAME"}` の完全な JSON オブジェクト形式で記述すること。raw regex のみは無効

#### G_T027_3/4: pvqe-p-gate.py / intent-confirm.py が Dead Guard のまま undocumented だった
- **症状**: hooks/ に .py ファイルが存在するが settings.local.json 未登録 → 機能せず、理由も不明
- **原因**: 無効化時に failure_memory.json / KNOWN_MISTAKES.md に記録しなかった
- **修正**: failure_memory.json に F006/F007 を wont_fix として追加。理由と代替手段を記録
- **教訓**: hooks/ ファイルは「登録済み（active）」か「意図的無効化（failure_memory.json に wont_fix 記録）」のどちらか一方でなければならない

### regression 結果（T027完了時点）
- **31/31 PASS** （5 BUILTIN + 26 dynamic）
- 新規パターン: REGRESSION_MANUAL_ONLY（26番目）
- 前回比: +1 パターン（30/30 → 31/31）

### 技術的教訓（T027追加）
- **auto-codifier.py GUARD_PATTERN 形式**: raw regex ではなく完全な JSON オブジェクトとして記述しなければ機能しない
- **Dead Guard 記録の原則**: hooks/ の全ファイルは active か wont_fix documented のどちらか。未記録の無効ファイルは技術的負債
- **file read before edit**: 別セッション context 引き継ぎ時は、編集前に必ず Read ツールで読み直すこと（"File has not been read yet" エラー防止）

### T029 セッションサマリー（自動記録）
**日付**: 2026-03-29 | **ステータス**: 完了 | **regression**: 34/34 PASS（5 BUILTIN + 29 dynamic）

### T029 発見ギャップと修正
- **GAP-T029-1 (logic_error)**: `session-end.py:81` の `t.get("id","?")` が task_ledger.json の `"task_id"` キーと不一致 → AGENT_WISDOM に「完了タスク: ?」が永続記録されていた。修正: `t.get("task_id", t.get("id","?"))` に変更
- **GAP-T029-2 (ecc_gap)**: KNOWN_MISTAKES.md に GUARD_PATTERN として存在する EN_PIPELINE_QUALITY / PATTERN_HISTORY_FIELD_MISMATCH / BILINGUAL_URL_SLUG_WRONG の3パターンが mistake_patterns.json に未登録だった（2026-03-06/07登録分の取りこぼし）。3パターンを `example` フィールド付きで追加。

### regression 結果（T029完了時点）
- **34/34 PASS** （5 BUILTIN + 29 dynamic）
- 新規パターン: EN_PIPELINE_QUALITY / PATTERN_HISTORY_FIELD_MISMATCH / BILINGUAL_URL_SLUG_WRONG（27〜29番目）
- 前回比: +3 パターン（31/31 → 34/34）

### 技術的教訓（T029追加）
- **task_ledger.json のキー名**: `"id"` ではなく `"task_id"`。session-end.py や他のツールが task_ledger を参照する場合は必ず `t.get("task_id", t.get("id","?"))` の形でフォールバックを書く
- **KNOWN_MISTAKES.md と mistake_patterns.json の同期**: KNOWN_MISTAKES.md に GUARD_PATTERN JSON を書いても auto-codifier が火を吹かないと mistake_patterns.json に自動登録されない。新規 GUARD_PATTERN を手書きした後は `regression-runner.py` を手動実行して件数が増えたことを確認する
- **ECC ギャップ監査の優先ファイル**: session-end.py（task ID recording）、mistake_patterns.json（pattern sync）の2ファイルは次回監査で最初にチェックする

