// tests/identify.test.ts
import { describe, it, expect, vi } from "vitest";
import { Hono } from "hono";
import { createIdentifyRoute } from "../src/routes/identify.js";
import { MemoryCache } from "../src/cache/memoryCache.js";
import type { VisionProvider } from "../src/vision/visionProvider.js";

function makeApp(vision: VisionProvider) {
  const app = new Hono();
  const cache = new MemoryCache(() => 0);
  app.post("/identify", createIdentifyRoute({ vision, cache, cacheTtl: 600 }));
  return app;
}

const body = (mode = "single") =>
  JSON.stringify({ imageBase64: "QUJD", mimeType: "image/jpeg", mode });

describe("POST /identify", () => {
  it("returns candidates from the vision provider", async () => {
    const vision: VisionProvider = {
      identify: vi.fn(async () => [
        { partNumber: "LM358N", manufacturer: "TI", confidence: 0.9 },
      ]),
    };
    const res = await makeApp(vision).request("/identify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: body(),
    });
    expect(res.status).toBe(200);
    const json = (await res.json()) as { candidates: Array<{ partNumber: string }> };
    expect(json.candidates[0]?.partNumber).toBe("LM358N");
  });

  it("uses the cache on a second identical request (vision called once)", async () => {
    const identify = vi.fn(async () => [
      { partNumber: "LM358N", confidence: 0.9 },
    ]);
    const app = makeApp({ identify });
    const req = () =>
      app.request("/identify", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: body(),
      });
    await req();
    await req();
    expect(identify).toHaveBeenCalledOnce();
  });

  it("rejects a malformed body with 400", async () => {
    const app = makeApp({ identify: vi.fn() });
    const res = await app.request("/identify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ mimeType: "image/jpeg" }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects an imageBase64 over 12 MB with 400", async () => {
    const app = makeApp({ identify: vi.fn() });
    // 12_000_001 'A' characters — just over the cap
    const oversize = "A".repeat(12_000_001);
    const res = await app.request("/identify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ imageBase64: oversize, mimeType: "image/jpeg", mode: "single" }),
    });
    expect(res.status).toBe(400);
  });
});
