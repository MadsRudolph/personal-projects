// src/index.ts
import { serve } from "@hono/node-server";
import { buildApp, type AppDeps } from "./app.js";
import { loadConfig } from "./config.js";
import { MemoryCache } from "./cache/memoryCache.js";
import { ClaudeVisionProvider } from "./vision/claudeVision.js";
import { NexarDatasheetProvider } from "./datasheet/nexarDatasheet.js";

function depsFromEnv(env: Record<string, string | undefined>): AppDeps {
  const cfg = loadConfig(env);
  return {
    vision: new ClaudeVisionProvider({
      apiKey: cfg.anthropicApiKey,
      model: cfg.claudeModel,
    }),
    datasheet: new NexarDatasheetProvider({ token: cfg.nexarToken }),
    cache: new MemoryCache(),
    rateLimit: cfg.rateLimit,
    rateWindowSeconds: cfg.rateWindowSeconds,
    identifyCacheTtl: cfg.identifyCacheTtl,
    datasheetCacheTtl: cfg.datasheetCacheTtl,
  };
}

// Cloudflare Workers entry: env is passed per-request.
export default {
  fetch(req: Request, env: Record<string, string | undefined>) {
    return buildApp(depsFromEnv(env)).fetch(req);
  },
};

// Local Node entry: run directly with `npm run dev`.
if (process.env.NODE_ENV !== "test" && process.argv[1]?.includes("index")) {
  const app = buildApp(depsFromEnv(process.env));
  const port = Number(process.env.PORT ?? "8787");
  serve({ fetch: app.fetch, port });
  console.log(`Component Scanner backend listening on :${port}`);
}
