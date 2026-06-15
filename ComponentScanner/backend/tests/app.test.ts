// tests/app.test.ts
import { describe, it, expect, vi } from "vitest";
import { buildApp } from "../src/app.js";
import { MemoryCache } from "../src/cache/memoryCache.js";

function deps() {
  return {
    vision: {
      identify: vi.fn(async () => [{ partNumber: "LM358N", confidence: 0.9 }]),
    },
    datasheet: {
      resolve: vi.fn(async () => ({
        partNumber: "LM358N",
        manufacturer: "TI",
        datasheetUrl: "https://www.ti.com/lit/ds/symlink/lm358.pdf",
        keySpecs: [],
      })),
    },
    cache: new MemoryCache(() => 0),
    rateLimit: 100,
    rateWindowSeconds: 60,
    identifyCacheTtl: 600,
    datasheetCacheTtl: 86400,
  };
}

describe("buildApp", () => {
  it("serves a health check", async () => {
    const app = buildApp(deps());
    const res = await app.request("/health");
    expect(res.status).toBe(200);
  });

  it("wires /identify end to end", async () => {
    const app = buildApp(deps());
    const res = await app.request("/identify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ imageBase64: "QUJD", mimeType: "image/jpeg", mode: "single" }),
    });
    expect(res.status).toBe(200);
  });

  it("wires /datasheet end to end", async () => {
    const app = buildApp(deps());
    const res = await app.request("/datasheet?part=LM358N");
    expect(res.status).toBe(200);
  });
});
