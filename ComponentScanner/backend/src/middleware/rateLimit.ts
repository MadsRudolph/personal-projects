// src/middleware/rateLimit.ts
import type { MiddlewareHandler } from "hono";
import type { Cache } from "../cache/cache.js";

export interface RateLimitOptions {
  cache: Cache;
  limit: number;
  windowSeconds: number;
}

export function rateLimit(opts: RateLimitOptions): MiddlewareHandler {
  return async (c, next) => {
    const ip =
      c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ||
      c.req.header("cf-connecting-ip") ||
      "unknown";
    const key = `rl:${ip}`;
    const current = Number((await opts.cache.get(key)) ?? "0");
    if (current >= opts.limit) {
      return c.json({ error: "rate limit exceeded" }, 429);
    }
    await opts.cache.set(key, String(current + 1), opts.windowSeconds);
    await next();
  };
}
