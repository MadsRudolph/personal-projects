// tests/kvCache.test.ts
import { describe, it, expect, vi } from "vitest";
import { KVCache, type KVNamespaceLike } from "../src/cache/kvCache.js";

/** Minimal in-memory fake KV namespace for tests. */
function fakeKV(): KVNamespaceLike & { _store: Map<string, string> } {
  const _store = new Map<string, string>();
  return {
    _store,
    async get(key: string) {
      return _store.get(key) ?? null;
    },
    async put(key: string, value: string, _opts?: { expirationTtl?: number }) {
      _store.set(key, value);
    },
  };
}

describe("KVCache", () => {
  it("returns null for an unknown key", async () => {
    const cache = new KVCache(fakeKV());
    expect(await cache.get("missing")).toBeNull();
  });

  it("returns a value after set", async () => {
    const cache = new KVCache(fakeKV());
    await cache.set("k", "hello", 300);
    expect(await cache.get("k")).toBe("hello");
  });

  it("passes expirationTtl through to KV put", async () => {
    const kv = fakeKV();
    const putSpy = vi.spyOn(kv, "put");
    const cache = new KVCache(kv);
    await cache.set("k", "v", 120);
    expect(putSpy).toHaveBeenCalledOnce();
    const opts = putSpy.mock.calls[0]?.[2];
    expect(opts?.expirationTtl).toBeGreaterThanOrEqual(60);
    expect(opts?.expirationTtl).toBe(120);
  });

  it("enforces the 60-second minimum expirationTtl", async () => {
    const kv = fakeKV();
    const putSpy = vi.spyOn(kv, "put");
    const cache = new KVCache(kv);
    await cache.set("k", "v", 10); // below KV minimum
    const opts = putSpy.mock.calls[0]?.[2];
    expect(opts?.expirationTtl).toBe(60);
  });
});
