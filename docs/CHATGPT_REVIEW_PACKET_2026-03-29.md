# Nowpattern — ChatGPT Review Packet (2026-03-29)

> 10-section analysis: Repo reality → Product thesis → Implementation plan
> For external review and strategic alignment

---

## Section 1: Repo Reality（実態把握）

### What's actually built (verified 2026-03-29)

| Component | Status | Notes |
|-----------|--------|-------|
| Ghost CMS | ✅ Live | 1331 published articles (JA:211 + EN:1104) |
| prediction_db.json | ✅ Live | 1097 predictions (resolved=52, open=35) |
| /predictions/ + /en/predictions/ | ✅ Live | Full bilingual prediction pages |
| prediction_page_builder.py | ✅ Live | 3,660+ lines, daily cron 07:00 JST |
| reader_prediction_api.py | ✅ Live | FastAPI, port 8766, `/reader-predict/*` |
| reader_predictions.db | ✅ Live | SQLite WAL, /opt/shared/ |
| Voting CTA widget | ✅ Live (2026-03-29) | Injected into prediction cards |
| /leaderboard/ + /en/leaderboard/ | ✅ Live (2026-03-29) | Ghost pages with live API |
| prediction_auto_verifier.py | ✅ Live | Auto-Brier via Grok search |
| X (@nowpattern, Premium) | ✅ Active | 100 posts/day target |
| NEO-ONE / NEO-TWO | ✅ Active | Claude Opus 4.6, Telegram bots |
| OTS timestamp | ✅ Live | Bitcoin timestamping every hour |

### Current prediction accuracy
- **Avg Brier Score: 0.1828** (FAIR level, target: <0.20)
- Brier Index shown on leaderboard: `(1 - sqrt(brier)) * 100`
- 52 resolved, 1023 awaiting evidence, 35 open

---

## Section 2: Product Thesis（プロダクトの核心）

**What Nowpattern is:**
The world's first Japanese × English bilingual *calibration* prediction platform.
Not a news summary service. A forecasting oracle with a verifiable track record.

**The irreversible moat:**
3 years of timestamped, auto-verified predictions cannot be reproduced the next day.
UI, algorithm, format — all copyable. Track record: not copyable.

**Competitive gap:**
- Metaculus: English only, academic/niche, no JP/EN bilingual
- Polymarket: Crypto-native, no editorial intelligence, no articles
- Good Judgment Open: English only, no AI opponent to beat
- Nowpattern: JP+EN, AI vs Human framing, article → prediction → vote → verified

**The engagement frame that nobody else has:**
"Can You Beat the AI?" — Reader vs Nowpattern AI on Brier Score.
This is not "read and leave." This is "participate and return to see results."

---

## Section 3: Today's Implementations（2026-03-29完了）

### 1. Voting CTA widget in prediction cards
- patch_builder3.py ran on VPS
- `COUNTER_FORECAST_UI: True` in FEATURE_FLAGS
- `_voting_widget` injected into every prediction card (`data-pid` attribute)
- `npVote()` JS function: localStorage UUID → POST `/reader-predict/vote` → inline result
- Scenario select (optimistic/base/pessimistic) + probability slider (5-95%)

### 2. Leaderboard pages (JA + EN)
- `/leaderboard/` (slug: `leaderboard`, Ghost page id: `69c8ab52e04f498780047039`)
- `/en/leaderboard/` (slug: `en-leaderboard`, Ghost page id: `69c8ab53e04f49878004703d`)
- Routes added to routes.yaml, Caddy handles `/en/leaderboard/` correctly
- `/en-leaderboard/` → 301 → `/en/leaderboard/` redirect in place
- hreflang bilateral links injected to both pages
- EN canonical_url set to `https://nowpattern.com/en/leaderboard/`

### 3. Leaderboard API fix
- Bug: `prediction_db.json` uses `"RESOLVED"` (uppercase), API checked `"resolved"` (lowercase)
- Fix: All 5 status comparisons in `reader_prediction_api.py` → `.upper() == "RESOLVED"`
- Result: AI `avg_brier_score: 0.4431, resolved_count: 52` now visible in API

---

## Section 4: Reader Acquisition Strategy — Q0（読者獲得 = 最大のボトルネック）

**The core problem:**
1097 predictions, 52 resolved, 0 human forecasters with 5+ resolved predictions.
The leaderboard currently shows AI only. No social proof, no competition.

**Q0 hypothesis:**
The voting CTA + leaderboard combination will only generate engagement if readers arrive.
Current traffic source: X @nowpattern (100 posts/day) → nowpattern.com.

### Q0 Acquisition Channels (prioritized by ROI)

| Channel | Cost | Time to first vote | Bottleneck |
|---------|------|-------------------|------------|
| **X (existing @nowpattern)** | $0 | 24h if a post links to voting | Need link in posts |
| **X Poll ("AI predicts 70% — what do you think?")** | $0 | same session | Poll → voting page |
| **Prediction deep links from articles** | $0 | Same session as article reader | Need more articles with predictions |
| note.com (3-5 posts/day) | $0 | 3-7 days | Audience smaller |
| Substack | $0 | 1-2 weeks | Low list size currently |

### Immediate Q0 tactics (implement next)

1. **X post format: include voting CTA link**
   Current posts link to articles. Add: "投票はこちら → nowpattern.com/predictions/#np-2026-XXXX"
   Or: "Can you beat the AI? Vote → nowpattern.com/en/predictions/#np-2026-XXXX"

2. **X Poll on every prediction post**
   Auto-attach poll: "AIは YES 70%と予測。あなたは？ / YES / NO / 記事を読む"
   This is already designed in content-rules.md but not yet fully automated.

3. **"Voting starts now" announcement post**
   Single X post announcing the leaderboard and "Can you beat the AI?" challenge.
   This is the biggest single-day acquisition tactic available at $0.

4. **Article → prediction deep link enforcement**
   Every oracle-tagged article should have a working deep link to `/predictions/#np-XXXX`.
   Deep link runbook: `docs/PREDICTION_DEEP_LINK_RUNBOOK.md` (exists)

---

## Section 5: The Engagement Loop（エンゲージメントの設計）

```
Reader discovers Nowpattern via X post
  ↓
Reads article with "🎯 オラクル宣言" section
  ↓
Sees voting CTA widget: "Challenge the AI — Post your forecast"
  ↓
Votes (no login required, localStorage UUID)
  ↓
Receives inline confirmation: "✅ 投票完了! base 65%"
  ↓
Returns to /predictions/ to see their vote vs AI
  ↓
Prediction resolves → Brier Score calculated
  ↓
Appears on /leaderboard/ if 5+ resolved
  ↓
Shares their rank → virality
```

**Current friction points:**
- CTA widget not visible until JS loads (acceptable)
- Reader must scroll to oracle section to see CTA
- No notification when prediction resolves (TIER 1 feature: email notify)
- 5+ resolved predictions required for leaderboard (correct threshold, but long cycle time)

---

## Section 6: Monetization Roadmap（マネタイズ設計）

### Phase 1 (NOW): 完全無料 — データ蓄積
- Objective: Get first 10 humans on leaderboard
- Revenue: $0 intentional
- Measure: votes/day, unique voter UUIDs, resolved count with human votes

### Phase 2 (TIER 1 complete): Ghost Members
- Free tier: read + vote (same as now)
- Paid ($9-19/month):
  - Personal track record page
  - Brier Score history graph
  - Email notification on resolution
  - Monthly "AI vs Human" leaderboard report
- Infrastructure: Ghost Members + Stripe already built-in

### Phase 3 (TIER 3+): B2B
- Public prediction API: $99-499/month
- Superforecaster certification: $500+/report
- Corporate prediction contests

---

## Section 7: Technical Debt & Risk（技術的リスク）

### High priority
| Issue | Risk | Fix |
|-------|------|-----|
| `prediction_db.json` grows to 1000+ items, rebuilt daily | Performance | Already flat-file, add pagination if >2000 |
| `reader_predictions.db` no backup | Data loss | Add daily SQLite backup cron |
| Ghost Admin API key in .env | Security | Already managed, don't expose |
| Brier Score discrepancy (0.1828 vs 0.4431) | Credibility | Verify which calculation is canonical |

### Medium priority
| Issue | Risk | Fix |
|-------|------|-----|
| Voting widget inline JS (npVote) bypasses CSP | Security | Add nonce or move to external JS |
| `/reader-predict/leaderboard` returns 52 resolved_ids inline | Perf at scale | Paginate when >500 |
| `voter_uuid` in localStorage — cleared on browser wipe | UX | Not a problem until Phase 2 (when accounts exist) |

### Low priority (don't fix now)
- routes.yaml manual management (works, risky only if edited wrong)
- Leaderboard refresh on vote (requires WebSocket or polling — not worth it yet)

---

## Section 8: TIER Implementation Status（未実装機能）

### TIER 0 (Done)
- ✅ FastAPI reader prediction API
- ✅ Community stats API
- ✅ /predictions/ voting widgets
- ✅ Leaderboard page (JA + EN)
- ✅ Voting CTA in prediction cards

### TIER 1 (Next sprint)
- ❌ Personal track record page (`/my-predictions/`)
- ❌ Resolution notification via email (Ghost Members trigger)
- ❌ Title/badge system (Novice → Expert → Superforecaster)

### TIER 2 (Month 2)
- ❌ AI vs Human monthly report (Substack + X)
- ❌ Postcasting (historical prediction entry)

### TIER 3+ (Month 3+)
- ❌ Public API
- ❌ Account registration
- ❌ Superforecaster certification

---

## Section 9: Implementation Plan — Next 7 Days（次の7日間）

| Day | Task | Owner | Output |
|-----|------|-------|--------|
| Today | ✅ Voting CTA live | Done | Widget on all prediction cards |
| Today | ✅ Leaderboard live | Done | /leaderboard/ + /en/leaderboard/ |
| Today | ✅ API Brier fix | Done | AI shows 52 resolved |
| Day 1 | X announcement post | NEO-ONE | "Can you beat the AI?" launch post |
| Day 1 | X poll automation | NEO-ONE | Auto-attach poll to prediction posts |
| Day 2 | Article deep link audit | Script | All oracle articles have working #anchor |
| Day 3 | /my-predictions/ page | VPS | Show personal UUID vote history |
| Day 4 | Leaderboard cron update | Cron | Auto-rebuild leaderboard pages daily |
| Day 5 | Resolution notification | Ghost | Email on Brier Score update |
| Day 7 | Week 1 metrics review | Naoto | Votes count, unique UUIDs, leaderboard entries |

---

## Section 10: Success Metrics — Week 1 KPIs

| Metric | Baseline (now) | Target (Day 7) | Stretch |
|--------|---------------|----------------|---------|
| Total votes cast | 0 | 10+ | 50+ |
| Unique voter UUIDs | 0 | 5+ | 20+ |
| X impressions on CTA posts | 0 | 1,000+ | 5,000+ |
| Leaderboard entries (5+ resolved) | 0 | 0 (expected) | 1 |
| AI Brier Score visible | ✅ Fixed today | ✅ | ✅ |
| Leaderboard page 200 status | ✅ | ✅ | ✅ |

**Why 0 leaderboard entries in Week 1 is OK:**
A prediction takes time to resolve (weeks to months). The leaderboard shows up empty until
someone accumulates 5 resolved votes — this can take 1-3 months. The empty state is designed
with "No human forecasters yet. Need 5+ resolved." — which reads as an invitation, not a bug.

---

## Appendix: Key File Paths

| Purpose | Path |
|---------|------|
| Prediction DB | `/opt/shared/scripts/prediction_db.json` |
| Reader Votes DB | `/opt/shared/reader_predictions.db` |
| Reader Prediction API | `/opt/shared/scripts/reader_prediction_api.py` |
| Page Builder | `/opt/shared/scripts/prediction_page_builder.py` |
| Leaderboard HTML | Ghost Admin: slugs `leaderboard`, `en-leaderboard` |
| Leaderboard API | `GET /reader-predict/leaderboard` |
| Top Forecasters API | `GET /reader-predict/top-forecasters` |
| Ghost routes | `/var/www/nowpattern/content/settings/routes.yaml` |
| Caddy config | `/etc/caddy/Caddyfile` |

---

*Generated: 2026-03-29 | Session: voting CTA + leaderboard implementation*
