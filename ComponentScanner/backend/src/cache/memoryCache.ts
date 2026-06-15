// src/cache/memoryCache.ts
import type { Cache } from "./cache.js";

interface Entry {
  value: string;
  expiresAtMs: number;
}

/** In-memory cache. `nowMs` is injectable for deterministic tests. */
export class MemoryCache implements Cache {
  private store = new Map<string, Entry>();
  constructor(private nowMs: () => number = () => Date.now()) {}

  async get(key: string): Promise<string | null> {
    const entry = this.store.get(key);
    if (!entry) return null;
    if (this.nowMs() >= entry.expiresAtMs) {
      this.store.delete(key);
      return null;
    }
    return entry.value;
  }

  async set(key: string, value: string, ttlSeconds: number): Promise<void> {
    this.store.set(key, {
      value,
      expiresAtMs: this.nowMs() + ttlSeconds * 1000,
    });
  }
}
