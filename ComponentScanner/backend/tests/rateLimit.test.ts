// tests/rateLimit.test.ts
import { describe, it, expect } from "vitest";
import { Hono } from "hono";
import { MemoryCache } from "../src/cache/memoryCache.js";
import { rateLimit } from "../src/middleware/rateLimit.js";

function appWithLimit(limit: number) {
  const app = new Hono();
  const cache = new MemoryCache(() => 0); // frozen time -> same window
  app.use("*", rateLimit({ cache, limit, windowSeconds: 60 }));
  app.get("/", (c) => c.text("ok"));
  return app;
}

describe("rateLimit", () => {
  it("allows requests under the limit", async () => {
    const app = appWithLimit(2);
    const headers = { "x-forwarded-for": "1.1.1.1" };
    expect((await app.request("/", { headers })).status).toBe(200);
    expect((await app.request("/", { headers })).status).toBe(200);
  });

  it("blocks the request that exceeds the limit with 429", async () => {
    const app = appWithLimit(1);
    const headers = { "x-forwarded-for": "2.2.2.2" };
    expect((await app.request("/", { headers })).status).toBe(200);
    expect((await app.request("/", { headers })).status).toBe(429);
  });

  it("tracks clients independently", async () => {
    const app = appWithLimit(1);
    expect(
      (await app.request("/", { headers: { "x-forwarded-for": "3.3.3.3" } }))
        .status,
    ).toBe(200);
    expect(
      (await app.request("/", { headers: { "x-forwarded-for": "4.4.4.4" } }))
        .status,
    ).toBe(200);
  });
});
