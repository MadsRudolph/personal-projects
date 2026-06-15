// src/app.ts
import { Hono } from "hono";
import type { VisionProvider } from "./vision/visionProvider.js";
import type { DatasheetProvider } from "./datasheet/datasheetProvider.js";
import type { Cache } from "./cache/cache.js";
import { rateLimit } from "./middleware/rateLimit.js";
import { createIdentifyRoute } from "./routes/identify.js";
import { createDatasheetRoute } from "./routes/datasheet.js";

export interface AppDeps {
  vision: VisionProvider;
  datasheet: DatasheetProvider;
  cache: Cache;
  rateLimit: number;
  rateWindowSeconds: number;
  identifyCacheTtl: number;
  datasheetCacheTtl: number;
}

export function buildApp(deps: AppDeps) {
  const app = new Hono();

  app.get("/health", (c) => c.json({ status: "ok" }));

  app.use(
    "/identify",
    rateLimit({
      cache: deps.cache,
      limit: deps.rateLimit,
      windowSeconds: deps.rateWindowSeconds,
    }),
  );
  app.use(
    "/datasheet",
    rateLimit({
      cache: deps.cache,
      limit: deps.rateLimit,
      windowSeconds: deps.rateWindowSeconds,
    }),
  );

  app.post(
    "/identify",
    createIdentifyRoute({
      vision: deps.vision,
      cache: deps.cache,
      cacheTtl: deps.identifyCacheTtl,
    }),
  );
  app.get(
    "/datasheet",
    createDatasheetRoute({
      datasheet: deps.datasheet,
      cache: deps.cache,
      cacheTtl: deps.datasheetCacheTtl,
    }),
  );

  return app;
}
