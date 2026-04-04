# VPS Live Findings (Claude verified 2026-03-29)

## KEY FINDING: VPS prediction_db.json != Local prediction_db.json

| Metric | VPS (LIVE) | Local (Codex-modified) |
|--------|-----------|----------------------|
| resolved count | **7** | 52 |
| avg Brier Score | **0.1780** | 0.4494 |
| total predictions | needs check | 1116 |

## Leaderboard API (`/reader-predict/leaderboard`)
- AI: avg_brier=0.178, resolved=7, eligible=true
- Readers: 9 voters, 1124 votes, avg_brier=0.2361, accuracy=55.6%
- Reader leaderboard eligible: true (>5 resolved)
- Resolved IDs: NP-2026-0008, 0009, 0010, 0011, 0013, 0018, 0019

## Voting CTA Widget
- `/predictions/` page: **0 matches** for np-reader-vote, data-pred, npVote markers
- JS script exists but widget DOM nodes NOT injected into prediction cards
- Conclusion: **Voting CTA is NOT functional** — script deployed but markup missing

## Implications
1. Codex's local schema migration has NOT been synced to VPS
2. The 52 resolved count in local DB likely came from Codex's batch changes
3. VPS only recognizes 7 predictions as truly RESOLVED
4. The 0.1780 Brier on VPS is the **canonical** score (matches documented 0.1828 closely)
5. Voting CTA needs page_builder rebuild to inject widget markup
