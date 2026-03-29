# Implementation Run — 2026-03-28

## Overview

Implemented audit-identified fixes in priority order (minimum diff, reversible-first, evidence-based).

Source: `docs/NOWPATTERN_FIX_PRIORITY_2026-03-28.md`

---

## Scope

| Issue ID | Title | Status |
|----------|-------|--------|
| REQ-001 | llms.txt: fix en-predictions/ → en/predictions/ | ✅ DONE |
| REQ-003 | prediction_page_builder.py: add np-scoreboard/np-resolved IDs | ✅ DONE |
| REQ-004 | Caddyfile: llms-full.txt file_server handle block | ✅ DONE |
| REQ-005 | Caddyfile: enable gzip/zstd compression | ✅ DONE |
| REQ-009 | Homepage hreflang | ✅ ALREADY PASSING |
| REQ-012 | Reader prediction API health | ✅ ALREADY PASSING |
| REQ-002 | Ghost portal_plans (Stripe) | 🚫 BLOCKED — do not touch |
| REQ-006/007 | Dataset schema (EN/JA) | ✅ DONE (Week 1) |
| REQ-008 | FAQPage schema on predictions pages | ✅ DONE (Week 1) |
| REQ-010 | X DLQ retry_dlq() bug fix + clear | ✅ DONE (Week 1) |
| REQ-011 | PARSE_ERROR 根本原因調査 | ⏭ Month 1 |

---

## Execution Timeline

| Time (JST) | Action |
|------------|--------|
| 2026-03-28 session | REQ-001: llms.txt static file on VPS identified and fixed |
| 2026-03-28 session | REQ-009: Already passing (hreflang count ≥ 7) |
| 2026-03-28 session | REQ-012: Already passing (reader API health = ok) |
| 2026-03-28 session | REQ-004+005: Caddyfile patched (Python replace), llms-full.txt created |
| 2026-03-28 session | REQ-003: prediction_page_builder.py patched (4 lines, line-targeted Python) |
| Week 1 session | REQ-010: x_swarm_dispatcher.py 4 fixes applied; 5 stuck DLQ items cleared |
| Week 1 session | REQ-008: FAQPage JSON-LD (4 Q&As) added to JA+EN predictions pages via codeinjection_head |
| Week 1 session | REQ-006+007: Dataset JSON-LD added to prediction_page_builder.py + applied to JA+EN via codeinjection_head |

---

## Files Changed

| File | Host | Backup |
|------|------|--------|
| `/var/www/nowpattern-static/llms.txt` | VPS | `llms.txt.bak-20260328` |
| `/var/www/nowpattern-static/llms-full.txt` | VPS | NEW (no prior version) |
| `/etc/caddy/Caddyfile` | VPS | `Caddyfile.bak-20260328` |
| `/opt/shared/scripts/prediction_page_builder.py` | VPS | `prediction_page_builder.py.bak-20260328` |
| `/opt/shared/scripts/x_swarm_dispatcher.py` | VPS | (patched inline, prior session) |
| `/opt/shared/scripts/x_dlq.json` | VPS | cleared to `[]` (was 5 items) |
| Ghost page `predictions` (JA) codeinjection_head | Ghost CMS | FAQPage + Dataset added |
| Ghost page `en-predictions` (EN) codeinjection_head | Ghost CMS | FAQPage + Dataset added |

---

## Verification Results

| Check | Before | After |
|-------|--------|-------|
| `curl -s https://nowpattern.com/llms.txt \| grep en/predictions/` | 0 matches | 2 matches |
| `curl -s https://nowpattern.com/llms-full.txt \| head -1` | 404 | `# Nowpattern.com — llms-full.txt` |
| `curl -sI https://nowpattern.com/predictions/ \| grep Content-Encoding` | (none) | `content-encoding: gzip` |
| `curl -s https://nowpattern.com/predictions/ \| grep -c 'id="np-scoreboard"'` | 0 | 1 |
| `curl -s https://nowpattern.com/predictions/ \| grep -c 'id="np-resolved"'` | 0 | 1 |
| `curl -s https://nowpattern.com/en/predictions/ \| grep -c 'id="np-scoreboard"'` | 0 | 1 |
| `curl -s https://nowpattern.com/en/predictions/ \| grep -c 'id="np-resolved"'` | 0 | 1 |
| Reader API health | ✅ ok | ✅ ok |
| Homepage hreflang count | ≥7 | ≥7 |
| X DLQ items | 5 stuck (error=True) | 0 (cleared) |
| x_swarm_dispatcher retry_dlq() thread bug | present | fixed (4 patches) |
| `/predictions/` `@type=FAQPage` | absent | ✅ present |
| `/en/predictions/` `@type=FAQPage` | absent | ✅ present |
| `/predictions/` `@type=Dataset` | absent | ✅ present |
| `/en/predictions/` `@type=Dataset` | absent | ✅ present |

---

## Rollback Instructions

```bash
# REQ-001 (llms.txt)
ssh root@163.44.124.123 "cp /var/www/nowpattern-static/llms.txt.bak-20260328 /var/www/nowpattern-static/llms.txt"

# REQ-004+005 (Caddyfile)
ssh root@163.44.124.123 "cp /etc/caddy/Caddyfile.bak-20260328 /etc/caddy/Caddyfile && systemctl reload caddy"

# REQ-003 (prediction_page_builder.py)
ssh root@163.44.124.123 "cp /opt/shared/scripts/prediction_page_builder.py.bak-20260328 /opt/shared/scripts/prediction_page_builder.py && python3 /opt/shared/scripts/prediction_page_builder.py"
```

---

*Completed: 2026-03-28 | Engineer: Claude Code (local)*
