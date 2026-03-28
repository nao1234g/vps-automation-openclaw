/// <reference types="bun-types" />

/**
 * Claude Code CLI backend — programmatic LLM calls via `claude -p`
 *
 * Uses Claude Code's headless/print mode which authenticates via
 * Claude Max OAuth. No ANTHROPIC_API_KEY required.
 *
 * Architecture:
 *   Bun.spawn(["claude", "-p", prompt, ...flags])
 *   → JSON envelope: { type, subtype, is_error, result }
 *   → strip markdown fences from `result` field
 *   → return typed Result<T>
 *
 * Windows note: `claude` resolves via `cmd /c claude` to find claude.cmd.
 * POSIX: direct `claude` executable via PATH.
 */

import { ok, err } from "@equity/domain";
import type { Result } from "@equity/domain";

// ── CLI flags (shared across all calls) ──────────────────────────────────────

const CLI_FLAGS = [
  "--output-format", "json",
  "--tools", "",
  "--no-session-persistence",
  "--model", "claude-opus-4-6",
] as const;

// ── JSON envelope returned by `claude -p --output-format json` ───────────────

interface ClaudeCliEnvelope {
  type: string;
  subtype: string;
  is_error: boolean;
  result: string;
}

// ── Core subprocess helper ────────────────────────────────────────────────────

async function spawnClaude(prompt: string): Promise<Result<string>> {
  // Use `claude` directly on all platforms.
  // On Windows, claude is installed as claude.exe (not a .cmd shim), so it can
  // be spawned directly without `cmd /c`. Using `cmd /c` would cause cmd.exe to
  // split multi-line prompts at newline boundaries, corrupting the argument.
  const args: string[] = ["claude", "-p", prompt, ...CLI_FLAGS];

  let proc: ReturnType<typeof Bun.spawn>;
  try {
    proc = Bun.spawn(args, { stdout: "pipe", stderr: "pipe" });
  } catch (e) {
    return err(
      new Error(
        `Failed to spawn claude CLI: ${e instanceof Error ? e.message : String(e)}`
      )
    );
  }

  const [rawStdout, , exitCode] = await Promise.all([
    new Response(proc.stdout as ReadableStream<Uint8Array>).text(),
    new Response(proc.stderr as ReadableStream<Uint8Array>).text(),
    proc.exited,
  ]);

  if (exitCode !== 0) {
    return err(new Error(`claude CLI exited with code ${exitCode}`));
  }

  let envelope: ClaudeCliEnvelope;
  try {
    envelope = JSON.parse(rawStdout.trim()) as ClaudeCliEnvelope;
  } catch {
    return err(
      new Error(
        `claude CLI output not valid JSON: ${rawStdout.slice(0, 200)}`
      )
    );
  }

  if (envelope.is_error || envelope.subtype !== "success") {
    return err(
      new Error(
        `claude CLI returned error: ${(envelope.result ?? "").slice(0, 200)}`
      )
    );
  }

  return ok(envelope.result ?? "");
}

// ── Strip markdown code fences (```json ... ``` or ``` ... ```) ──────────────

function stripFences(raw: string): string {
  return raw
    .replace(/^```(?:json)?\s*\n?/, "")
    .replace(/\n?```\s*$/, "")
    .trim();
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Call the Claude CLI and return the raw text response.
 *
 * @param userPrompt   Main instruction / question
 * @param systemPrompt Optional system-level context prepended to the prompt
 */
export async function callClaudeText(
  userPrompt: string,
  systemPrompt?: string
): Promise<Result<string>> {
  const full = systemPrompt
    ? `${systemPrompt}\n\n${userPrompt}`
    : userPrompt;
  const res = await spawnClaude(full);
  if (!res.ok) return res;
  return ok(stripFences(res.data));
}

/**
 * Call the Claude CLI expecting a JSON response, returning parsed T.
 * Markdown code fences in the response are stripped automatically.
 * A JSON-only instruction is prepended to the prompt.
 */
export async function callClaudeJson<T = unknown>(
  userPrompt: string,
  opts?: { systemPrompt?: string }
): Promise<Result<T>> {
  const jsonInstruction =
    "You MUST respond with ONLY valid JSON. Do NOT wrap in markdown code fences. No text outside the JSON object.";

  const full = opts?.systemPrompt
    ? `${opts.systemPrompt}\n\n${jsonInstruction}\n\n${userPrompt}`
    : `${jsonInstruction}\n\n${userPrompt}`;

  const res = await spawnClaude(full);
  if (!res.ok) return res as unknown as Result<T>;

  const cleaned = stripFences(res.data);
  try {
    return ok(JSON.parse(cleaned) as T);
  } catch {
    return err(
      new Error(
        `Claude returned non-JSON output: ${cleaned.slice(0, 300)}`
      )
    );
  }
}
