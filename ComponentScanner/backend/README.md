# Component Scanner Backend

Identifies electronic components from an image and resolves datasheets. Holds all
secret API keys server-side. Runs on Node (dev) and Cloudflare Workers (prod).

## Endpoints

- `GET  /health` → `{ "status": "ok" }`
- `POST /identify` — body `{ imageBase64, mimeType, mode: "single"|"shelf" }`
  → `{ candidates: [{ partNumber, manufacturer?, packageType?, confidence }], cached }`
- `GET  /datasheet?part=PARTNO`
  → `{ partNumber, manufacturer, datasheetUrl, keySpecs: [{name,value}] }` or 404

**Note:** `datasheetUrl` is returned as-is from Nexar; reachability/PDF validation
and fallback resolvers (vision-guessed URL, generic web search) are a planned Phase-1.x enhancement.

## Caching & rate limiting

Result caching uses **Cloudflare Workers KV** in production. Create the namespace and
add it to `wrangler.toml`:

```bash
npx wrangler kv namespace create CACHE
# paste the returned id into wrangler.toml under [[kv_namespaces]]
```

Without a `CACHE` KV binding the backend falls back to **in-memory caching**
(suitable for local dev only — cache is lost on each request cold-start in Workers).

Rate limiting is **per-isolate best-effort in-memory**. Under normal Workers traffic
patterns (one long-lived isolate per region) this is effective, but it is not
globally strict. Strict global rate limiting would require Durable Objects.

## Local development

```bash
npm install
cp .env.example .env   # fill in ANTHROPIC_API_KEY + NEXAR_CLIENT_ID/SECRET
npm run dev            # http://localhost:8787
npm test               # run the test suite
```

## Required secrets

- `ANTHROPIC_API_KEY` — from console.anthropic.com (vision model).
- `NEXAR_CLIENT_ID` / `NEXAR_CLIENT_SECRET` — from a Nexar app with the **Supply**
  scope (free tier at nexar.com). The backend exchanges these for an OAuth2 access
  token automatically (and refreshes it before expiry).

## Deploy to Cloudflare Workers

```bash
npx wrangler login
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put NEXAR_CLIENT_ID
npx wrangler secret put NEXAR_CLIENT_SECRET
npm run deploy
```

The deployed URL is what the Android app's `BACKEND_URL` should point to.
