# Permissions Policy — Claude Code Setup
> Updated: 2026-03-26

## Current Mode
`defaultMode: "bypassPermissions"` — all ops allowed unless denied

## Applied Fixes (2026-03-26)
1. **Removed bare `"WebFetch"` wildcard** → domain whitelist now enforced (80+ domains)
2. **vps-health-gate timeout**: 60s → 30s

## Deny List (Active)
| Pattern | Block Type |
|---------|-----------|
| `**/.env`, `**/.env.*` | Read + Write |
| `**/*credentials*`, `**/*private_key*` | Read + Write |
| `**/*.pem`, `**/*.key` | Read |
| `**/*secret*` | Read |
| `rm -rf /`, `dd if=`, `mkfs`, `fdisk` | Bash |
| `DROP TABLE`, `DROP DATABASE` | Bash |

## Additional Directories Allowed
- `\tmp`, `c:\tmp` — temp files
- `C:\Users\user\AppData\Roaming\Code\User` — VSCode settings
- `naoto-os`, `claude-peers-mcp` — sibling projects

## Recommendation (Future Sprint)
Switch from `bypassPermissions` to `default` mode with explicit allows:
```json
"defaultMode": "default",
"allow": ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]
```
This would make deny rules meaningful as a security boundary rather than fallback.

## WebFetch Approved Domains (Summary)
- LLM/AI: ai.google.dev, claude.ai, openai.com, anthropic.com, x.ai, openrouter.ai
- SEO/Search: search.google.com, developers.google.com, web.dev
- Prediction: polymarket.com, metaculus.com, manifold.markets
- Finance/News: bloomberg.com, ft.com, reuters.com, nikkei.com
- Technical: github.com, docs.docker.com, systemd.io
- Ghost/CMS: ghost.org, ghost.io
- 70+ additional domain-specific entries
