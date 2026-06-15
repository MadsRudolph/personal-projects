// tests/memoryCache.test.ts
import { describe, it, expect } from "vitest";
import { MemoryCache } from "../src/cache/memoryCache.js";

describe("MemoryCache", () => {
  it("returns a stored value before expiry", async () => {
    let now = 1000;
    const cache = new MemoryCache(() => now);
    await cache.set("k", "v", 60); // ttl seconds
    expect(await cache.get("k")).toBe("v");
  });

  it("returns null after expiry", async () => {
    let now = 1000;
    const cache = new MemoryCache(() => now);
    await cache.set("k", "v", 60);
    now = 1000 + 61_000;
    expect(await cache.get("k")).toBeNull();
  });

  it("returns null for unknown keys", async () => {
    const cache = new MemoryCache(() => 0);
    expect(await cache.get("missing")).toBeNull();
  });
});
