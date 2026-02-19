# Agent Wisdom — All Agents Shared Knowledge

> **This file is the shared brain of all agents.**
> Every agent (Jarvis, Alice, CodeX, Pixel, Luna, Scout, Guard, Hawk, Neo) MUST read this file before starting any task.
> Location: `/shared/AGENT_WISDOM.md` (container) = `/opt/shared/AGENT_WISDOM.md` (host)
> Updated by: Neo or local Claude Code. Synced to VPS automatically.

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
