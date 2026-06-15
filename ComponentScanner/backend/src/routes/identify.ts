// src/routes/identify.ts
import type { Handler } from "hono";
import { z } from "zod";
import type { VisionProvider } from "../vision/visionProvider.js";
import type { Cache } from "../cache/cache.js";

const RequestSchema = z.object({
  imageBase64: z.string().min(1),
  mimeType: z.string().min(1),
  mode: z.enum(["single", "shelf"]).default("single"),
});

export interface IdentifyDeps {
  vision: VisionProvider;
  cache: Cache;
  cacheTtl: number; // seconds
}

/** djb2 hash -> hex; stable, no crypto dependency needed for a cache key. */
function hashKey(s: string): string {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = (h * 33) ^ s.charCodeAt(i);
  return (h >>> 0).toString(16);
}

export function createIdentifyRoute(deps: IdentifyDeps): Handler {
  return async (c) => {
    let raw: unknown;
    try {
      raw = await c.req.json();
    } catch {
      return c.json({ error: "invalid JSON body" }, 400);
    }
    const parsed = RequestSchema.safeParse(raw);
    if (!parsed.success) {
      return c.json({ error: "invalid request", issues: parsed.error.issues }, 400);
    }
    const { imageBase64, mimeType, mode } = parsed.data;

    const cacheKey = `identify:${mode}:${hashKey(imageBase64)}`;
    const cached = await deps.cache.get(cacheKey);
    if (cached) {
      return c.json({ candidates: JSON.parse(cached), cached: true });
    }

    const candidates = await deps.vision.identify(imageBase64, mimeType, mode);
    await deps.cache.set(cacheKey, JSON.stringify(candidates), deps.cacheTtl);
    return c.json({ candidates, cached: false });
  };
}
