# Architecture Decision Record: Claude Code CLI Backend
## LangChain → `claude -p` (Claude Max OAuth)

> Date: 2026-03-28
> Status: **IMPLEMENTED**
> Replaces: `@langchain/anthropic` ChatAnthropic wrapper in 3 service files

---

## Problem

`buildThesis()`, `compareCompanies()`, and `answerCompanyQuestion()` were **BLOCKED**
(FV-15/16 ⛔) because they depended on `@langchain/anthropic` which requires `ANTHROPIC_API_KEY`.

Per `CLAUDE.md`: **"Claude Max $200/月（定額）— Anthropic API従量課金は使用禁止"**

The pay-per-use API is explicitly prohibited. `ANTHROPIC_API_KEY` is not set in this environment.

---

## Options Considered

### Option A: Set `ANTHROPIC_API_KEY` (❌ Rejected)
Violates project constraint. Pay-per-use billing prohibited.

### Option B: Keep LangChain, use `@langchain/anthropic` with OAuth (❌ Not viable)
`@langchain/anthropic` does not support Claude Max OAuth. It requires an API key.

### Option C: Claude Code CLI headless mode — `claude -p` (✅ Selected)
Claude Code CLI `--print` mode authenticates via Claude Max OAuth stored in system
keychain (same token used by the VSCode extension). No ANTHROPIC_API_KEY needed.

### Option D: Anthropic Agent SDK with OAuth (❌ Investigated, not available)
The official Agent SDK also requires `ANTHROPIC_API_KEY`. No OAuth path exposed in SDK.

---

## Decision: Option C — Claude Code CLI (`claude -p`)

### Runtime Probe (2026-03-28, confirmed)

```bash
$ claude --version
# → claude 1.3.2 (Claude Code)

$ echo "respond with JSON: {ok:true}" | claude -p --output-format json --tools "" --no-session-persistence --model claude-opus-4-6
# stdout (trimmed):
# {
#   "type": "result",
#   "subtype": "success",
#   "is_error": false,
#   "result": "...",
#   "session_id": "...",
#   "usage": { "service_tier": "standard", ... }
# }
```

`service_tier: "standard"` confirms Claude Max subscription is active. No ANTHROPIC_API_KEY required.

**Windows note**: `claude` is a `.cmd` shim. Must use `cmd /c claude` when spawning via `Bun.spawn`.

---

## Implementation

### New file: `packages/services/src/llm/claude_code_backend.ts`

Internal module. NOT exported from `@equity/services` public index.

**Architecture:**
```
callClaudeJson<T>(prompt)  ──┐
callClaudeText(prompt)     ──┤──→ spawnClaude(prompt)
                             │        │
                             │    Bun.spawn(["cmd","/c","claude","-p",...])
                             │        │
                             │    JSON envelope: { type, subtype, is_error, result }
                             │        │
                             │    stripFences(result)   ← removes ```json fences
                             │        │
                             └────Result<T> (ok | err)
```

**CLI flags used:**
```
--output-format json         ← machine-readable envelope
--tools ""                   ← disable all tools (pure LLM)
--no-session-persistence     ← stateless (each call is independent)
--model claude-opus-4-6      ← Claude Opus 4.6 (Max subscription)
```

**TypeScript fixes required:**
1. `/// <reference types="bun-types" />` — `Bun` global not in tsconfig types array
2. `proc.stdout as ReadableStream<Uint8Array>` — Bun.spawn output union narrowing

### Migration: 3 files updated

| File | Old | New |
|------|-----|-----|
| `packages/services/src/thesis/builder.ts` | `new ChatAnthropic().withStructuredOutput()` | `callClaudeJson<ThesisLlmOutput>(prompt)` |
| `packages/services/src/compare/index.ts` | `new ChatAnthropic().invoke()` | `callClaudeText(prompt)` |
| `packages/services/src/query/walltalk.ts` | `new ChatAnthropic().invoke()` | `callClaudeText(userPrompt, sysPrompt)` |

### Dependency: `@langchain/anthropic` removed from call paths

The package is still listed in `package.json` but is no longer imported by any runtime-critical
service path. It can be removed from `package.json` in a follow-up cleanup if desired.

---

## Verification

### TypeScript (post-migration)

```bash
bun run typecheck  # → 0 errors ✅
```

### Runtime behavior

`callClaudeJson<T>` and `callClaudeText`:
- Return `Result<T>` with structured `ok(data)` or `err(Error)`
- Never throw — all subprocess errors caught and wrapped
- JSON fence stripping handles `claude -p` output format automatically

### FV-15/16 status change

| Requirement | Before migration | After migration |
|-------------|-----------------|-----------------|
| `buildThesis()` 1件生成 | ⛔ BLOCKED (ANTHROPIC_API_KEY) | 🟡 PARTIAL (実装完了・end-to-end未実行) |
| `compareCompanies()` 1件実行 | ⛔ BLOCKED (ANTHROPIC_API_KEY) | 🟡 PARTIAL (実装完了・end-to-end未実行) |

**BLOCKED → PARTIAL**: The API-key blocker is resolved. The remaining gap is that no end-to-end
`buildThesis()` call with a live dossier has been executed in this session.
To move from PARTIAL → DONE: call `buildThesis(someDossier)` with a live registry and verify
the returned `Thesis` object.

---

## Trade-offs

| Factor | LangChain (old) | Claude CLI (new) |
|--------|----------------|------------------|
| Auth | ANTHROPIC_API_KEY (pay-per-use) | Claude Max OAuth (fixed $200/mo) |
| Structured output | LangChain `.withStructuredOutput(schema)` | JSON prompt + `stripFences()` + `JSON.parse()` |
| Streaming | Supported | Not used (single response only) |
| Latency | Direct API call | Subprocess spawn overhead (~100-200ms extra) |
| Availability | Any environment with API key | Requires `claude` CLI in PATH + Max subscription |
| Token counting | LangChain metadata | Available in JSON envelope usage field |

### Subprocess overhead
`Bun.spawn(["cmd","/c","claude",...])` adds ~100-200ms initialization per call.
For thesis generation (typically 3-10s per LLM call), this overhead is negligible.

---

## Constraints

1. `claude` CLI must be in PATH (`claude --version` must succeed)
2. Claude Max subscription must be active (`service_tier: "standard"` in response)
3. `--bare` flag MUST NOT be used — it disables OAuth and re-requires ANTHROPIC_API_KEY
4. Windows: `Bun.spawn(["cmd", "/c", "claude", ...])` — cmd shim resolution required

---

*Decision record created: 2026-03-28 — equity-intelligence CLI backend migration*
