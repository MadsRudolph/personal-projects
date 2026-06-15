// src/middleware/rateLimit.ts
import type { MiddlewareHandler } from "hono";
import type { Cache } from "../cache/cache.js";

export interface RateLimitOptions {
  cache: Cache;
  limit: number;
  windowSeconds: number;
  /** Injectable clock for deterministic tests. Defaults to Date.now. */
  nowMs?: () => number;
}

interface RateLimitEntry {
  count: number;
  resetAtMs: number;
}

export function rateLimit(opts: RateLimitOptions): MiddlewareHandler {
  const clock = opts.nowMs ?? (() => Date.now());

  return async (c, next) => {
    const ip =
      c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ||
      c.req.header("cf-connecting-ip") ||
      "unknown";
    const key = `rl:${ip}`;
    const now = clock();

    const raw = await opts.cache.get(key);
    let entry: RateLimitEntry | null = null;
    if (raw !== null) {
      try {
        entry = JSON.parse(raw) as RateLimitEntry;
      } catch {
        entry = null;
      }
    }

    if (entry === null || now >= entry.resetAtMs) {
      // Start a new window
      const newEntry: RateLimitEntry = { count: 1, resetAtMs: now + opts.windowSeconds * 1000 };
      await opts.cache.set(key, JSON.stringify(newEntry), opts.windowSeconds);
      await next();
      return;
    }

    if (entry.count >= opts.limit) {
      return c.json({ error: "rate limit exceeded" }, 429);
    }

    // Increment within the existing window, preserve remaining TTL
    const ttlSeconds = Math.max(1, Math.ceil((entry.resetAtMs - now) / 1000));
    const updated: RateLimitEntry = { count: entry.count + 1, resetAtMs: entry.resetAtMs };
    await opts.cache.set(key, JSON.stringify(updated), ttlSeconds);
    await next();
  };
}
