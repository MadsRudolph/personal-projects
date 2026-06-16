// src/index.ts
import { serve } from "@hono/node-server";
import { buildApp, type AppDeps } from "./app.js";
import { loadConfig } from "./config.js";
import { MemoryCache } from "./cache/memoryCache.js";
import { KVCache, type KVNamespaceLike } from "./cache/kvCache.js";
import { ClaudeVisionProvider } from "./vision/claudeVision.js";
import { NexarDatasheetProvider } from "./datasheet/nexarDatasheet.js";
import { ClaudeDatasheetProvider } from "./datasheet/claudeDatasheet.js";
import { CompositeDatasheetProvider } from "./datasheet/compositeDatasheet.js";

function isKVNamespaceLike(v: unknown): v is KVNamespaceLike {
  return typeof v === "object" && v !== null && typeof (v as Record<string, unknown>)["get"] === "function";
}

function depsFromEnv(env: Record<string, unknown>): AppDeps {
  // loadConfig expects string | undefined values; cast non-string KV binding out.
  const stringEnv: Record<string, string | undefined> = {};
  for (const [k, v] of Object.entries(env)) {
    if (typeof v === "string" || v === undefined) {
      stringEnv[k] = v;
    }
  }

  const cfg = loadConfig(stringEnv);

  const cache: AppDeps["cache"] = isKVNamespaceLike(env["CACHE"])
    ? new KVCache(env["CACHE"])
    : new MemoryCache();

  // Rate-limit store is always in-memory (per-isolate best-effort).
  // Strict global rate limiting would require Durable Objects.
  const rateLimitStore = new MemoryCache();

  return {
    vision: new ClaudeVisionProvider({
      apiKey: cfg.anthropicApiKey,
      model: cfg.claudeModel,
    }),
    datasheet: new CompositeDatasheetProvider([
      // Nexar first (structured specs) — used when the account has quota.
      new NexarDatasheetProvider({
        clientId: cfg.nexarClientId,
        clientSecret: cfg.nexarClientSecret,
      }),
      // Fallback: Claude finds + validates a manufacturer datasheet PDF.
      new ClaudeDatasheetProvider({
        apiKey: cfg.anthropicApiKey,
        model: cfg.claudeModel,
      }),
    ]),
    cache,
    rateLimitStore,
    rateLimit: cfg.rateLimit,
    rateWindowSeconds: cfg.rateWindowSeconds,
    identifyCacheTtl: cfg.identifyCacheTtl,
    datasheetCacheTtl: cfg.datasheetCacheTtl,
  };
}

// Cloudflare Workers entry: build the app once per isolate lifetime.
let cachedApp: ReturnType<typeof buildApp> | undefined;
export default {
  fetch(req: Request, env: Record<string, unknown>) {
    cachedApp ??= buildApp(depsFromEnv(env));
    return cachedApp.fetch(req);
  },
};

// Local Node entry: run directly with `npm run dev`.
if (process.env.NODE_ENV !== "test" && process.argv[1]?.includes("index")) {
  const app = buildApp(depsFromEnv(process.env));
  const port = Number(process.env.PORT ?? "8787");
  serve({ fetch: app.fetch, port });
  console.log(`Component Scanner backend listening on :${port}`);
}
