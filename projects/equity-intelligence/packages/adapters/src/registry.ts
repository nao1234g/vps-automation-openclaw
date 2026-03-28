/**
 * Adapter Registry — runtime wiring
 *
 * Instantiates concrete adapters from environment variables.
 * The agent layer calls getXxxAdapter(market) — never imports clients directly.
 */

import type {
  AdapterRegistry,
  SecurityAdapter,
  PriceAdapter,
  FinancialStatementsAdapter,
  FilingsAdapter,
  SearchAdapter,
} from "./interfaces.js";
import type { Market } from "@equity/domain";

import { JQuantsAdapter } from "./jquants/client.js";
import { EdinetAdapter } from "./edinet/client.js";
import { FinancialDatasetsAdapter } from "./us/client.js";
import { ExaAdapter } from "./exa/client.js";

export function buildRegistry(env: NodeJS.ProcessEnv): AdapterRegistry {
  const usAdapter = env["FINANCIAL_DATASETS_API_KEY"]
    ? new FinancialDatasetsAdapter(env["FINANCIAL_DATASETS_API_KEY"])
    : undefined;

  const jpPriceAdapter =
    env["JQUANTS_MAIL_ADDRESS"] && env["JQUANTS_PASSWORD"]
      ? new JQuantsAdapter(env["JQUANTS_MAIL_ADDRESS"], env["JQUANTS_PASSWORD"])
      : undefined;

  const jpFilingsAdapter = env["EDINET_SUBSCRIPTION_KEY"]
    ? new EdinetAdapter(env["EDINET_SUBSCRIPTION_KEY"])
    : undefined;

  const searchAdapter = env["EXASEARCH_API_KEY"]
    ? new ExaAdapter(env["EXASEARCH_API_KEY"])
    : undefined;

  const registry: AdapterRegistry = {
    getSecurityAdapter(market: Market): SecurityAdapter | undefined {
      if (market === "US") return usAdapter;
      if (market === "JP") return jpPriceAdapter; // JQuantsAdapter implements SecurityAdapter
      return undefined;
    },

    getPriceAdapter(market: Market): PriceAdapter | undefined {
      if (market === "US") return usAdapter;
      if (market === "JP") return jpPriceAdapter;
      return undefined;
    },

    getFinancialsAdapter(market: Market): FinancialStatementsAdapter | undefined {
      if (market === "US") return usAdapter;
      // JP financials: J-Quants free tier has no statements — agent should use EDINET
      if (market === "JP") return jpPriceAdapter; // stubs return clear error messages
      return undefined;
    },

    getFilingsAdapter(market: Market): FilingsAdapter | undefined {
      if (market === "US") return usAdapter;
      if (market === "JP") return jpFilingsAdapter;
      return undefined;
    },

    getSearchAdapter(): SearchAdapter | undefined {
      return searchAdapter;
    },
  };

  return registry;
}
