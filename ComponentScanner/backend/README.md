# Component Scanner Backend

Identifies electronic components from an image and resolves datasheets. Holds all
secret API keys server-side. Runs on Node (dev) and Cloudflare Workers (prod).

## Endpoints

- `GET  /health` → `{ "status": "ok" }`
- `POST /identify` — body `{ imageBase64, mimeType, mode: "single"|"shelf" }`
  → `{ candidates: [{ partNumber, manufacturer?, packageType?, confidence }], cached }`
- `GET  /datasheet?part=PARTNO`
  → `{ partNumber, manufacturer, datasheetUrl, keySpecs: [{name,value}] }` or 404

## Local development

```bash
npm install
cp .env.example .env   # fill in ANTHROPIC_API_KEY and NEXAR_TOKEN
npm run dev            # http://localhost:8787
npm test               # run the test suite
```

## Required secrets

- `ANTHROPIC_API_KEY` — from console.anthropic.com (vision model).
- `NEXAR_TOKEN` — Nexar/Octopart bearer token (free tier at nexar.com).

## Deploy to Cloudflare Workers

```bash
npx wrangler login
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put NEXAR_TOKEN
npm run deploy
```

The deployed URL is what the Android app's `BACKEND_URL` should point to.
