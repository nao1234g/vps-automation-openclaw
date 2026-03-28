/**
 * Research Agent — Dexter-pattern LangChain agent for equity research
 *
 * Architecture mirrors Dexter's 4-agent workflow:
 *   Planner → Executor (tool loop) → Validator → Answerer
 *
 * Key differences from Dexter:
 *   - Supports both US (Financial Datasets API) and JP (J-Quants + EDINET) markets
 *   - Uses AdapterRegistry for pluggable market data
 *   - Claude as default LLM (Claude Max $200/month — no API charges)
 *   - Produces structured Dossier output
 */

import * as dotenv from "dotenv";
dotenv.config();

import { ChatAnthropic } from "@langchain/anthropic";
import { DynamicStructuredTool } from "@langchain/core/tools";
import { AgentExecutor, createToolCallingAgent } from "langchain/agents";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { z } from "zod";

import { buildRegistry } from "@equity/adapters";
import type { Market, Dossier } from "@equity/domain";

// ─────────────────────────────────────────────
// Tool definitions
// ─────────────────────────────────────────────

function buildTools(registry: ReturnType<typeof buildRegistry>) {
  const tools: DynamicStructuredTool[] = [];

  // ── Security info ──────────────────────────────────────

  tools.push(
    new DynamicStructuredTool({
      name: "get_security_info",
      description: "Get company/security info (name, sector, listing date, currency) for a ticker.",
      schema: z.object({
        ticker: z.string().describe("Stock ticker, e.g. 'AAPL' or '7203'"),
        market: z.enum(["US", "JP"]).describe("US or JP market"),
      }),
      func: async ({ ticker, market }) => {
        const adapter = registry.getSecurityAdapter(market as Market);
        if (!adapter) return `No security adapter configured for ${market} market.`;
        const result = await adapter.getSecurity(ticker);
        if (!result.ok) return `Error: ${result.error.message}`;
        return JSON.stringify(result.data, null, 2);
      },
    })
  );

  // ── Price data ─────────────────────────────────────────

  tools.push(
    new DynamicStructuredTool({
      name: "get_latest_price",
      description: "Get the latest closing price for a ticker.",
      schema: z.object({
        ticker: z.string(),
        market: z.enum(["US", "JP"]),
      }),
      func: async ({ ticker, market }) => {
        const adapter = registry.getPriceAdapter(market as Market);
        if (!adapter) return `No price adapter configured for ${market} market.`;
        const result = await adapter.getLatestPrice(ticker);
        if (!result.ok) return `Error: ${result.error.message}`;
        const b = result.data;
        return `${b.date}: Open=${b.open}, High=${b.high}, Low=${b.low}, Close=${b.close}, Vol=${b.volume}`;
      },
    })
  );

  tools.push(
    new DynamicStructuredTool({
      name: "get_daily_price_history",
      description: "Get daily OHLCV price history for a date range.",
      schema: z.object({
        ticker: z.string(),
        market: z.enum(["US", "JP"]),
        from: z.string().describe("ISO date YYYY-MM-DD"),
        to: z.string().describe("ISO date YYYY-MM-DD"),
      }),
      func: async ({ ticker, market, from, to }) => {
        const adapter = registry.getPriceAdapter(market as Market);
        if (!adapter) return `No price adapter configured for ${market} market.`;
        const result = await adapter.getDailyBars(ticker, from, to);
        if (!result.ok) return `Error: ${result.error.message}`;
        if (result.data.length === 0) return "No price data available for range.";
        const first = result.data[0]!;
        const last = result.data[result.data.length - 1]!;
        return JSON.stringify({
          count: result.data.length,
          firstBar: first,
          lastBar: last,
          priceChange: `${(((last.close - first.close) / first.close) * 100).toFixed(2)}%`,
        }, null, 2);
      },
    })
  );

  // ── Financial statements ───────────────────────────────

  tools.push(
    new DynamicStructuredTool({
      name: "get_income_statements",
      description: "Get income statements (revenue, operating income, net income, EPS) for a ticker. JP: use EDINET for 有価証券報告書 data.",
      schema: z.object({
        ticker: z.string(),
        market: z.enum(["US", "JP"]),
        limit: z.number().default(4),
      }),
      func: async ({ ticker, market, limit }) => {
        const adapter = registry.getFinancialsAdapter(market as Market);
        if (!adapter) return `No financials adapter configured for ${market} market.`;
        const result = await adapter.getIncomeStatements(ticker, limit);
        if (!result.ok) return `Error: ${result.error.message}`;
        return JSON.stringify(result.data, null, 2);
      },
    })
  );

  tools.push(
    new DynamicStructuredTool({
      name: "get_balance_sheets",
      description: "Get balance sheets (total assets, liabilities, equity, cash) for a ticker.",
      schema: z.object({
        ticker: z.string(),
        market: z.enum(["US", "JP"]),
        limit: z.number().default(4),
      }),
      func: async ({ ticker, market, limit }) => {
        const adapter = registry.getFinancialsAdapter(market as Market);
        if (!adapter) return `No financials adapter configured for ${market} market.`;
        const result = await adapter.getBalanceSheets(ticker, limit);
        if (!result.ok) return `Error: ${result.error.message}`;
        return JSON.stringify(result.data, null, 2);
      },
    })
  );

  // ── Filings ────────────────────────────────────────────

  tools.push(
    new DynamicStructuredTool({
      name: "list_filings",
      description: "List recent regulatory filings. US: SEC (10-K, 10-Q, 8-K). JP: EDINET (有価証券報告書, 四半期報告書, 決算短信).",
      schema: z.object({
        ticker: z.string(),
        market: z.enum(["US", "JP"]),
        limit: z.number().default(5),
      }),
      func: async ({ ticker, market, limit }) => {
        const adapter = registry.getFilingsAdapter(market as Market);
        if (!adapter) return `No filings adapter configured for ${market} market.`;
        const result = await adapter.listFilings(ticker, undefined, limit);
        if (!result.ok) return `Error: ${result.error.message}`;
        return JSON.stringify(result.data, null, 2);
      },
    })
  );

  // ── News search (optional, only if Exa configured) ────

  const searchAdapter = registry.getSearchAdapter();
  if (searchAdapter) {
    tools.push(
      new DynamicStructuredTool({
        name: "search_news",
        description: "Search for recent financial news and analyst commentary about a company or topic.",
        schema: z.object({
          query: z.string().describe("Search query, e.g. 'Apple Q4 earnings 2025' or 'トヨタ 決算 2025'"),
          limit: z.number().default(5),
        }),
        func: async ({ query, limit }) => {
          const result = await searchAdapter.search(query, limit);
          if (!result.ok) return `Error: ${result.error.message}`;
          return result.data.map((r) =>
            `**${r.title}** (${r.publishedAt ?? "?"})\n${r.snippet}\n${r.url}`
          ).join("\n\n");
        },
      })
    );
  }

  return tools;
}

// ─────────────────────────────────────────────
// Agent setup
// ─────────────────────────────────────────────

async function buildAgent(tools: DynamicStructuredTool[]) {
  const model = new ChatAnthropic({
    model: process.env["DEFAULT_MODEL"] ?? "claude-opus-4-6",
    temperature: 0.1,
    maxTokens: 4096,
  });

  const prompt = ChatPromptTemplate.fromMessages([
    ["system", `You are an expert equity research analyst with deep knowledge of both US and Japanese stock markets.

Your workflow:
1. **Plan**: Decompose the research query into specific data needs
2. **Execute**: Use tools to gather data systematically
3. **Validate**: Cross-check figures and ensure consistency
4. **Synthesize**: Write a clear, structured research report

Key rules:
- Always identify the market (US or JP) before calling tools
- For Japanese stocks, use 4-digit codes (e.g., "7203" for Toyota)
- For US stocks, use uppercase symbols (e.g., "AAPL" for Apple)
- J-Quants free tier has 12-week price delay — always mention this in your report
- J-Quants free tier does NOT provide financial statements → use EDINET for JP financials
- EDINET requires server-side access only (already handled by the adapter)
- Be precise with numbers; include currency (USD or JPY)
- Structure your final answer as markdown with clear sections

Always state: "Note: J-Quants free tier data has a 12-week delay" when reporting JP prices.`],
    ["human", "{input}"],
    ["placeholder", "{agent_scratchpad}"],
  ]);

  const agent = createToolCallingAgent({ llm: model, tools, prompt });

  return AgentExecutor.fromAgentAndTools({
    agent,
    tools,
    verbose: process.env["DEBUG"] === "true",
    maxIterations: Number(process.env["MAX_ITERATIONS"] ?? "10"),
    returnIntermediateSteps: true,
  });
}

// ─────────────────────────────────────────────
// Main entry point
// ─────────────────────────────────────────────

export async function runResearch(query: string): Promise<{
  answer: string;
  steps: Array<{ tool: string; input: unknown; output: unknown }>;
}> {
  const registry = buildRegistry(process.env as NodeJS.ProcessEnv);
  const tools = buildTools(registry);
  const agent = await buildAgent(tools);

  const result = await agent.invoke({ input: query });

  const steps = (result.intermediateSteps ?? []).map((step: {
    action: { tool: string; toolInput: unknown };
    observation: unknown;
  }) => ({
    tool: step.action.tool,
    input: step.action.toolInput,
    output: step.observation,
  }));

  return {
    answer: result.output as string,
    steps,
  };
}

// ─────────────────────────────────────────────
// CLI runner (bun run packages/services/src/research/agent.ts "query")
// ─────────────────────────────────────────────

if (import.meta.main ?? process.argv[1] === import.meta.url?.replace("file://", "")) {
  const query = process.argv.slice(2).join(" ");
  if (!query) {
    console.error("Usage: bun run packages/services/src/research/agent.ts '<query>'");
    console.error("Example: bun run ... 'Analyze Toyota 7203 financials'");
    process.exit(1);
  }

  console.log(`\n🔍 Research query: "${query}"\n${"─".repeat(60)}`);

  const { answer, steps } = await runResearch(query);

  if (steps.length > 0) {
    console.log("\n📊 Tool calls:");
    for (const step of steps) {
      console.log(`  • ${step.tool}`);
    }
  }

  console.log("\n📝 Research Report:");
  console.log("─".repeat(60));
  console.log(answer);
}
