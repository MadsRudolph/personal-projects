// src/cache/cache.ts
export interface Cache {
  get(key: string): Promise<string | null>;
  /** ttlSeconds: time-to-live in seconds. */
  set(key: string, value: string, ttlSeconds: number): Promise<void>;
}
