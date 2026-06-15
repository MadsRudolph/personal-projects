# Component Scanner — Design

**Date:** 2026-06-15
**Status:** Approved-pending (design review)

## 1. Purpose

An Android app for electronic-engineering students. Point the camera at a chip (or a
whole shelf of components in a shop) and the app identifies the part from its printed
marking, then resolves and displays the manufacturer datasheet as an in-app, scrollable,
zoomable PDF (pinouts, ratings, classifications).

Two primary use cases:

1. **Identify one** — read the marking on a single component and open its datasheet.
2. **Scan shelf** — point at a wall/bin of many components (e.g. a row of MOSFETs in a
   shop) and get a tappable list of every identified part, each linking to its datasheet.

## 2. Non-goals (v1)

- No user accounts / login.
- No BOM management, pricing, or purchasing.
- No schematic capture or PCB features.
- No iOS app (Android only).
- Not optimized to run fully offline for datasheet retrieval (OCR works offline; datasheet
  fetch needs network).

## 3. Architecture overview

Two deployable units:

```
                          ┌────────────────────────────────────────────┐
  Android app (Kotlin)    │            Backend (TypeScript)             │
  ────────────────────    │            ─────────────────────            │
  CameraX preview/frames   │   POST /identify   (image -> candidates)   │
  ML Kit OCR (on-device) ──┼─▶ GET  /datasheet  (part  -> sheet+specs)  │
  Compose UI               │                                            │
  Retrofit client ─────────┼─▶  Vision-LLM (Claude, swappable)          │
  Room + file cache        │    Parts API (Nexar/Octopart)              │
  In-app PDF viewer        │    Cache (KV/edge) + rate limiting         │
                          └────────────────────────────────────────────┘
```

**Why a backend (production requirement):** secret API keys must never ship in an APK
(APKs are trivially decompiled). The backend holds the vision-LLM key and the parts-API
key, caches lookups (N students scanning the same part = 1 upstream call), enforces rate
limits, and lets us swap LLM/datasheet providers without releasing a new app build.

## 4. Recognition pipeline (hybrid)

### Identify-one (fast path, mostly offline)

1. CameraX streams frames to **ML Kit Text Recognition v2** (on-device, free).
2. A **part-number extractor** pulls candidate tokens from OCR text using heuristics
   (alphanumeric runs, common IC marking patterns, manufacturer prefixes/logos hints).
3. A **normalizer + fuzzy matcher** cleans the token (strip date/lot codes, fix common
   OCR confusions like 0/O, 1/I/l, 5/S, 8/B) and scores candidates.
4. If confidence ≥ threshold → resolve datasheet immediately.
5. If confidence is low, or the user taps **Deep scan** → capture one high-resolution
   still, POST to backend `/identify`, vision-LLM returns normalized candidate(s) with
   manufacturer, package, and confidence.

### Scan-shelf (cloud path)

1. Capture one high-res still, POST to `/identify` with `mode=shelf`.
2. Vision-LLM is prompted to enumerate **every distinct visible part marking** and return
   a list of `{partNumber, manufacturer?, confidence, boundingBoxHint?}`.
3. App shows a tappable list; each row resolves to its datasheet on demand.

### Manual fallback

A manual part-number entry field is always available (used when recognition fails or the
marking is unreadable). It resolves a datasheet via the same `/datasheet` path.

## 5. Datasheet resolution

- Backend `/datasheet?part=…` resolves part number → manufacturer → datasheet PDF URL +
  key specs via **Nexar/Octopart** (free tier; account key required).
- Fallbacks if the parts API misses: (a) vision-LLM's guessed manufacturer + datasheet
  URL, (b) a generic datasheet web-search resolver. Results are validated as a reachable
  PDF before being returned.
- The app downloads the PDF, caches it to local file storage (keyed by part number), and
  renders it with a scroll/pinch-zoom PDF viewer (Android `PdfRenderer` or
  AndroidPdfViewer library).

## 6. Android app modules & components

- **camera** — CameraX setup, frame analyzer, still capture, torch/zoom controls.
- **ocr** — ML Kit wrapper, part-number extractor, normalizer, fuzzy matcher.
- **data** — Retrofit API client, Room database, file cache, repositories.
- **ui** — Compose screens: Scan (mode toggle Identify ↔ Shelf), Result, PDF viewer,
  History/Saved, Manual-entry, Settings (backend URL, provider info).
- **di** — Hilt modules.

### Room schema

- `ScanHistory(id, partNumber, manufacturer, timestamp, thumbnailPath, datasheetUrl)`
- `CachedDatasheet(partNumber PK, localPath, fetchedAt)`
- `KnownPart(partNumber PK, manufacturer, aliases)` — optional offline fast-match seed
  (Phase 3).

## 7. Backend design

- **Stack:** TypeScript on a serverless platform (Cloudflare Workers or Vercel — free
  tier, edge cache). Swappable.
- **Endpoints:**
  - `POST /identify` — multipart image + `mode` (`single` | `shelf`) → `{ candidates: [{partNumber, manufacturer?, packageType?, confidence}] }`.
  - `GET /datasheet?part=…` — → `{ partNumber, manufacturer, datasheetUrl, keySpecs[] }`.
- **Vision-LLM adapter:** provider interface with a Claude implementation (default),
  Gemini implementation behind the same interface. Prompted for strict JSON output.
- **Datasheet adapter:** Nexar/Octopart implementation behind an interface, with the
  fallback resolvers above.
- **Cache:** KV store keyed by image hash (identify) and part number (datasheet), with TTL.
- **Rate limiting** per client to control cost/abuse.
- **Secrets** via platform env vars; never committed.

## 8. Error handling

| Situation | Behavior |
|-----------|----------|
| Offline | OCR still reads text; datasheet fetch retries with backoff; clear offline banner. |
| Low recognition confidence | Show ranked candidates + manual-entry option. |
| No datasheet found | Show "not found", keep manual entry / try alternate part. |
| Camera permission denied | Rationale dialog + deep-link to app settings. |
| Backend/LLM error or timeout | Graceful message, retry; fall back to on-device result if any. |
| Corrupt/oversized image | Client-side downscale before upload; reject > size cap. |

## 9. Testing strategy

- **Unit (app):** part-number extractor, normalizer (OCR-confusion fixes), fuzzy matcher,
  repository logic with mocked API.
- **Unit (backend):** endpoint handlers with mocked LLM + parts API, JSON-parsing
  robustness, cache hit/miss, rate limiting.
- **Instrumented (app):** camera flow smoke test, PDF render, navigation.
- **Recognition accuracy harness:** a small labeled set of real chip photos run against
  the OCR/extraction pipeline to catch regressions and tune thresholds.

## 10. Security & privacy

- No secrets in the app; all privileged calls go through the backend.
- Images sent to the backend are processed transiently for identification; document
  retention/caching policy (cache by hash for cost; configurable TTL; no PII expected).
- HTTPS everywhere; backend rate-limited.

## 11. Build phases

- **Phase 1 — MVP:** Identify-one (on-device OCR + cloud fallback) → datasheet resolve →
  in-app PDF viewer → scan history. Backend `/identify` + `/datasheet` with caching.
- **Phase 2 — Scan shelf:** multi-component enumeration mode + list UI.
- **Phase 3 — Polish:** offline seed part-DB, favorites/collections, sharing, settings,
  accuracy tuning.

## 12. What the user must supply

- An **Anthropic API key** (Claude vision) for the backend.
- A **Nexar/Octopart account key** (free tier) for datasheets.
- A place to deploy the backend (Cloudflare/Vercel free tier; exact steps provided).
- Android Studio for building/running the app.

## 13. Key decisions (locked)

- Native Android (Kotlin + Jetpack Compose), not cross-platform.
- Hybrid recognition: on-device ML Kit OCR + cloud vision-LLM fallback.
- Companion serverless backend holds all secrets and caches lookups.
- Datasheets via a parts Search API (Nexar/Octopart) with fallbacks.
- Default vision provider: Claude (provider-swappable behind an interface).
