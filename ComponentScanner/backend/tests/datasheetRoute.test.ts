// tests/datasheetRoute.test.ts
import { describe, it, expect, vi } from "vitest";
import { Hono } from "hono";
import { createDatasheetRoute } from "../src/routes/datasheet.js";
import { MemoryCache } from "../src/cache/memoryCache.js";
import type { DatasheetProvider } from "../src/datasheet/datasheetProvider.js";

function makeApp(provider: DatasheetProvider) {
  const app = new Hono();
  const cache = new MemoryCache(() => 0);
  app.get("/datasheet", createDatasheetRoute({ datasheet: provider, cache, cacheTtl: 86400 }));
  return app;
}

const SHEET = {
  partNumber: "LM358N",
  manufacturer: "Texas Instruments",
  datasheetUrl: "https://www.ti.com/lit/ds/symlink/lm358.pdf",
  keySpecs: [],
};

describe("GET /datasheet", () => {
  it("returns the datasheet for a known part", async () => {
    const provider: DatasheetProvider = { resolve: vi.fn(async () => SHEET) };
    const res = await makeApp(provider).request("/datasheet?part=lm358n");
    expect(res.status).toBe(200);
    const json = (await res.json()) as { manufacturer: string };
    expect(json.manufacturer).toBe("Texas Instruments");
  });

  it("returns 400 when part is missing", async () => {
    const provider: DatasheetProvider = { resolve: vi.fn() };
    const res = await makeApp(provider).request("/datasheet");
    expect(res.status).toBe(400);
  });

  it("returns 404 when no datasheet is found", async () => {
    const provider: DatasheetProvider = { resolve: vi.fn(async () => null) };
    const res = await makeApp(provider).request("/datasheet?part=NOPART");
    expect(res.status).toBe(404);
  });

  it("caches the result (provider called once for repeated parts)", async () => {
    const resolve = vi.fn(async () => SHEET);
    const app = makeApp({ resolve });
    await app.request("/datasheet?part=LM358N");
    await app.request("/datasheet?part=LM358N");
    expect(resolve).toHaveBeenCalledOnce();
  });

  it("caches a not-found result so the paid lookup is not repeated", async () => {
    const resolve = vi.fn(async () => null);
    const app = makeApp({ resolve });
    const r1 = await app.request("/datasheet?part=NOPART");
    const r2 = await app.request("/datasheet?part=NOPART");
    expect(r1.status).toBe(404);
    expect(r2.status).toBe(404);
    expect(resolve).toHaveBeenCalledOnce(); // second served from cache
  });
});
