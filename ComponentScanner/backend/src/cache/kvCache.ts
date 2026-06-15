// src/cache/kvCache.ts
import type { Cache } from "./cache.js";

export interface KVNamespaceLike {
  get(key: string): Promise<string | null>;
  put(key: string, value: string, options?: { expirationTtl?: number }): Promise<void>;
}

/** Cache implementation backed by a Cloudflare KV namespace. */
export class KVCache implements Cache {
  constructor(private ns: KVNamespaceLike) {}

  get(key: string): Promise<string | null> {
    return this.ns.get(key);
  }

  set(key: string, value: string, ttlSeconds: number): Promise<void> {
    // Cloudflare KV enforces a minimum TTL of 60 seconds.
    const expirationTtl = Math.max(60, Math.floor(ttlSeconds));
    return this.ns.put(key, value, { expirationTtl });
  }
}
