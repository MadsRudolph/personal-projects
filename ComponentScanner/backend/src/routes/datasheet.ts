// src/routes/datasheet.ts
import type { Handler } from "hono";
import type { DatasheetProvider } from "../datasheet/datasheetProvider.js";
import type { Cache } from "../cache/cache.js";
import { normalizePartNumber } from "../normalize.js";

export interface DatasheetDeps {
  datasheet: DatasheetProvider;
  cache: Cache;
  cacheTtl: number; // seconds
  /** TTL for caching "not found" so unresolvable parts don't re-run a paid
   *  lookup on every retry. Defaults to 1 day. */
  notFoundTtl?: number;
}

const NOT_FOUND = '{"__notfound":true}';

export function createDatasheetRoute(deps: DatasheetDeps): Handler {
  return async (c) => {
    const partParam = c.req.query("part");
    if (!partParam) {
      return c.json({ error: "missing 'part' query parameter" }, 400);
    }
    const part = normalizePartNumber(partParam);

    const cacheKey = `datasheet:${part}`;
    const cached = await deps.cache.get(cacheKey);
    if (cached !== null) {
      if (cached === NOT_FOUND) {
        return c.json({ error: "datasheet not found", partNumber: part }, 404);
      }
      try {
        return c.json(JSON.parse(cached));
      } catch {
        // Cache entry is corrupt — fall through to provider
      }
    }

    const result = await deps.datasheet.resolve(part);
    if (!result) {
      // Cache the miss too — avoids paying for the same failed search repeatedly.
      await deps.cache.set(cacheKey, NOT_FOUND, deps.notFoundTtl ?? 86400);
      return c.json({ error: "datasheet not found", partNumber: part }, 404);
    }
    await deps.cache.set(cacheKey, JSON.stringify(result), deps.cacheTtl);
    return c.json(result);
  };
}
