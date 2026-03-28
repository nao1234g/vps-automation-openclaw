/**
 * equity-intelligence — TypeScript utility types
 * (non-Zod helper types used throughout the codebase)
 */

/** Generic async result wrapper — avoids throwing across module boundaries */
export type Result<T, E = Error> =
  | { ok: true; data: T }
  | { ok: false; error: E };

export function ok<T>(data: T): Result<T> {
  return { ok: true, data };
}

export function err<E = Error>(error: E): Result<never, E> {
  return { ok: false, error };
}

/** Partial deep — useful for patch operations */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/** Convenience: ISO8601 date string */
export type ISODate = string;

/** JP stock code always 4 digits as string ("7203") */
export type JpTickerCode = string;

/** US stock ticker ("AAPL") */
export type UsTickerSymbol = string;

export type TickerId = JpTickerCode | UsTickerSymbol;
