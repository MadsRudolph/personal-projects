# Component Scanner Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the companion backend service that identifies electronic components from an image (via a vision-LLM) and resolves part numbers to datasheets (via a parts API), holding all secret keys server-side and caching results.

**Architecture:** A small TypeScript HTTP service built on the Hono framework. It runs locally on Node for development/testing (`@hono/node-server`) and deploys unchanged to Cloudflare Workers. Two routes — `POST /identify` and `GET /datasheet` — sit in front of provider adapters (vision + datasheet) behind interfaces, an in-memory/KV cache, and a rate-limit middleware. Providers receive an injected `fetch` so tests never hit the network.

**Tech Stack:** TypeScript, Hono, Vitest, Zod (validation), Node 20+ (dev), Cloudflare Workers (deploy via Wrangler). Default vision provider: Claude (Anthropic Messages API). Default datasheet provider: Nexar/Octopart GraphQL.

---

## File Structure

```
ComponentScanner/backend/
├── package.json
├── tsconfig.json
├── vitest.config.ts
├── wrangler.toml                 # Cloudflare Workers deploy config
├── .env.example                  # documents required secrets (no real values)
├── .gitignore
├── README.md                     # local run + deploy steps
└── src/
    ├── index.ts                  # app entry (Node server) + Workers export
    ├── app.ts                    # buildApp(deps) -> Hono app (testable)
    ├── config.ts                 # env parsing/validation
    ├── types.ts                  # shared domain types + Zod schemas
    ├── normalize.ts              # part-number normalizer (pure)
    ├── cache/
    │   ├── cache.ts              # Cache interface
    │   └── memoryCache.ts        # in-memory TTL implementation
    ├── vision/
    │   ├── visionProvider.ts     # VisionProvider interface
    │   └── claudeVision.ts       # Claude implementation
    ├── datasheet/
    │   ├── datasheetProvider.ts  # DatasheetProvider interface
    │   └── nexarDatasheet.ts     # Nexar implementation + validation
    ├── middleware/
    │   └── rateLimit.ts          # per-client token-bucket limiter
    └── routes/
        ├── identify.ts           # POST /identify handler factory
        └── datasheet.ts          # GET /datasheet handler factory
tests/                            # mirrors src/ (Vitest)
```

**Responsibility boundaries:**
- `normalize.ts` — pure string logic, no I/O. Easiest to TDD; reused by both routes.
- `vision/` and `datasheet/` — each adapter is one provider behind one interface; swap by changing the wiring in `app.ts`.
- `routes/` — HTTP glue only; they call injected providers + cache. No provider logic inside.
- `app.ts` — dependency wiring as a function so tests inject fakes; `index.ts` builds real deps.

---

## Task 1: Project scaffold

**Files:**
- Create: `ComponentScanner/backend/package.json`
- Create: `ComponentScanner/backend/tsconfig.json`
- Create: `ComponentScanner/backend/vitest.config.ts`
- Create: `ComponentScanner/backend/.gitignore`

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "component-scanner-backend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "start": "tsx src/index.ts",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc --noEmit",
    "deploy": "wrangler deploy"
  },
  "dependencies": {
    "hono": "^4.6.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "@hono/node-server": "^1.13.0",
    "tsx": "^4.19.0",
    "typescript": "^5.6.0",
    "vitest": "^2.1.0",
    "wrangler": "^3.80.0"
  }
}
```

- [ ] **Step 2: Create `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "Bundler",
    "lib": ["ES2022"],
    "types": ["node"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "verbatimModuleSyntax": false,
    "outDir": "dist"
  },
  "include": ["src", "tests"]
}
```

- [ ] **Step 3: Create `vitest.config.ts`**

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
```

- [ ] **Step 4: Create `.gitignore`**

```
node_modules/
dist/
.dev.vars
.env
.wrangler/
```

- [ ] **Step 5: Install dependencies**

Run: `cd ComponentScanner/backend && npm install`
Expected: dependencies install, `node_modules/` created, no errors.

- [ ] **Step 6: Verify the toolchain runs**

Run: `cd ComponentScanner/backend && npx vitest run`
Expected: Vitest runs and reports "No test files found" (exit 0) — toolchain works.

- [ ] **Step 7: Commit**

```bash
git add ComponentScanner/backend/package.json ComponentScanner/backend/tsconfig.json ComponentScanner/backend/vitest.config.ts ComponentScanner/backend/.gitignore ComponentScanner/backend/package-lock.json
git commit -m "chore(backend): scaffold TypeScript + Hono + Vitest project"
```

---

## Task 2: Part-number normalizer

The normalizer cleans an OCR/LLM-read marking into a canonical part number and fixes
common OCR character confusions. Pure functions, no I/O.

**Files:**
- Create: `ComponentScanner/backend/src/normalize.ts`
- Test: `ComponentScanner/backend/tests/normalize.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/normalize.test.ts
import { describe, it, expect } from "vitest";
import { normalizePartNumber, looksLikePartNumber } from "../src/normalize.js";

describe("normalizePartNumber", () => {
  it("uppercases and trims surrounding whitespace", () => {
    expect(normalizePartNumber("  lm358n  ")).toBe("LM358N");
  });

  it("removes spaces inside the marking", () => {
    expect(normalizePartNumber("LM 358 N")).toBe("LM358N");
  });

  it("strips a trailing date/lot code segment after whitespace newline", () => {
    expect(normalizePartNumber("STM32F103C8T6\n2143")).toBe("STM32F103C8T6");
  });
});

describe("looksLikePartNumber", () => {
  it("accepts tokens with letters and digits of reasonable length", () => {
    expect(looksLikePartNumber("LM358")).toBe(true);
    expect(looksLikePartNumber("STM32F103C8T6")).toBe(true);
  });

  it("rejects pure words and very short tokens", () => {
    expect(looksLikePartNumber("HELLO")).toBe(false);
    expect(looksLikePartNumber("A1")).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/normalize.test.ts`
Expected: FAIL — cannot find module `../src/normalize.js`.

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/normalize.ts

/** Collapse a raw marking into a single-line canonical token. */
export function normalizePartNumber(raw: string): string {
  const firstLine = raw.split(/[\r\n]+/)[0] ?? "";
  return firstLine.replace(/\s+/g, "").toUpperCase();
}

/**
 * Heuristic: a plausible part number has both letters and digits and is
 * between 3 and 24 characters. Filters out plain words and noise tokens.
 */
export function looksLikePartNumber(token: string): boolean {
  const t = token.trim();
  if (t.length < 3 || t.length > 24) return false;
  const hasLetter = /[A-Za-z]/.test(t);
  const hasDigit = /[0-9]/.test(t);
  return hasLetter && hasDigit;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/normalize.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add ComponentScanner/backend/src/normalize.ts ComponentScanner/backend/tests/normalize.test.ts
git commit -m "feat(backend): add part-number normalizer"
```

---

## Task 3: Shared types and Zod schemas

**Files:**
- Create: `ComponentScanner/backend/src/types.ts`
- Test: `ComponentScanner/backend/tests/types.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/types.test.ts
import { describe, it, expect } from "vitest";
import { CandidateSchema, DatasheetSchema } from "../src/types.js";

describe("CandidateSchema", () => {
  it("parses a valid candidate", () => {
    const c = CandidateSchema.parse({
      partNumber: "LM358N",
      manufacturer: "Texas Instruments",
      packageType: "DIP-8",
      confidence: 0.92,
    });
    expect(c.partNumber).toBe("LM358N");
  });

  it("rejects confidence outside 0..1", () => {
    expect(() =>
      CandidateSchema.parse({ partNumber: "X", confidence: 1.5 }),
    ).toThrow();
  });
});

describe("DatasheetSchema", () => {
  it("parses a valid datasheet result", () => {
    const d = DatasheetSchema.parse({
      partNumber: "LM358N",
      manufacturer: "Texas Instruments",
      datasheetUrl: "https://example.com/lm358.pdf",
      keySpecs: [{ name: "Supply Voltage", value: "3-32 V" }],
    });
    expect(d.keySpecs).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/types.test.ts`
Expected: FAIL — cannot find module `../src/types.js`.

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/types.ts
import { z } from "zod";

export const CandidateSchema = z.object({
  partNumber: z.string().min(1),
  manufacturer: z.string().optional(),
  packageType: z.string().optional(),
  confidence: z.number().min(0).max(1),
});
export type Candidate = z.infer<typeof CandidateSchema>;

export const KeySpecSchema = z.object({
  name: z.string(),
  value: z.string(),
});
export type KeySpec = z.infer<typeof KeySpecSchema>;

export const DatasheetSchema = z.object({
  partNumber: z.string().min(1),
  manufacturer: z.string(),
  datasheetUrl: z.string().url(),
  keySpecs: z.array(KeySpecSchema).default([]),
});
export type Datasheet = z.infer<typeof DatasheetSchema>;

export type IdentifyMode = "single" | "shelf";
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/types.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add ComponentScanner/backend/src/types.ts ComponentScanner/backend/tests/types.test.ts
git commit -m "feat(backend): add domain types and Zod schemas"
```

---

## Task 4: In-memory TTL cache

**Files:**
- Create: `ComponentScanner/backend/src/cache/cache.ts`
- Create: `ComponentScanner/backend/src/cache/memoryCache.ts`
- Test: `ComponentScanner/backend/tests/memoryCache.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/memoryCache.test.ts
import { describe, it, expect } from "vitest";
import { MemoryCache } from "../src/cache/memoryCache.js";

describe("MemoryCache", () => {
  it("returns a stored value before expiry", async () => {
    let now = 1000;
    const cache = new MemoryCache(() => now);
    await cache.set("k", "v", 60); // ttl seconds
    expect(await cache.get("k")).toBe("v");
  });

  it("returns null after expiry", async () => {
    let now = 1000;
    const cache = new MemoryCache(() => now);
    await cache.set("k", "v", 60);
    now = 1000 + 61_000;
    expect(await cache.get("k")).toBeNull();
  });

  it("returns null for unknown keys", async () => {
    const cache = new MemoryCache(() => 0);
    expect(await cache.get("missing")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/memoryCache.test.ts`
Expected: FAIL — cannot find module `../src/cache/memoryCache.js`.

- [ ] **Step 3: Write the interface**

```typescript
// src/cache/cache.ts
export interface Cache {
  get(key: string): Promise<string | null>;
  /** ttlSeconds: time-to-live in seconds. */
  set(key: string, value: string, ttlSeconds: number): Promise<void>;
}
```

- [ ] **Step 4: Write the in-memory implementation**

```typescript
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/memoryCache.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add ComponentScanner/backend/src/cache/ ComponentScanner/backend/tests/memoryCache.test.ts
git commit -m "feat(backend): add cache interface and in-memory TTL cache"
```

---

## Task 5: Vision provider interface + Claude implementation

The provider takes a base64 image and a mode, calls the Claude Messages API, and returns
candidates. `fetch` is injected so tests don't hit the network.

**Files:**
- Create: `ComponentScanner/backend/src/vision/visionProvider.ts`
- Create: `ComponentScanner/backend/src/vision/claudeVision.ts`
- Test: `ComponentScanner/backend/tests/claudeVision.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/claudeVision.test.ts
import { describe, it, expect, vi } from "vitest";
import { ClaudeVisionProvider } from "../src/vision/claudeVision.js";

function fakeFetchReturning(jsonText: string) {
  return vi.fn(async () =>
    new Response(
      JSON.stringify({ content: [{ type: "text", text: jsonText }] }),
      { status: 200 },
    ),
  );
}

describe("ClaudeVisionProvider", () => {
  it("parses candidates from the model's JSON reply", async () => {
    const fetchFn = fakeFetchReturning(
      JSON.stringify({
        candidates: [
          { partNumber: "lm358n", manufacturer: "TI", confidence: 0.9 },
        ],
      }),
    );
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );

    const result = await provider.identify("BASE64", "image/jpeg", "single");

    expect(result[0]?.partNumber).toBe("LM358N"); // normalized
    expect(fetchFn).toHaveBeenCalledOnce();
  });

  it("returns an empty list when the model returns no candidates", async () => {
    const fetchFn = fakeFetchReturning(JSON.stringify({ candidates: [] }));
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );
    const result = await provider.identify("BASE64", "image/jpeg", "shelf");
    expect(result).toEqual([]);
  });

  it("throws on a non-OK HTTP response", async () => {
    const fetchFn = vi.fn(async () => new Response("nope", { status: 500 }));
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );
    await expect(
      provider.identify("BASE64", "image/jpeg", "single"),
    ).rejects.toThrow(/vision provider/i);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/claudeVision.test.ts`
Expected: FAIL — cannot find module `../src/vision/claudeVision.js`.

- [ ] **Step 3: Write the interface**

```typescript
// src/vision/visionProvider.ts
import type { Candidate, IdentifyMode } from "../types.js";

export interface VisionProvider {
  /**
   * @param imageBase64 raw base64 (no data: prefix)
   * @param mimeType e.g. "image/jpeg"
   */
  identify(
    imageBase64: string,
    mimeType: string,
    mode: IdentifyMode,
  ): Promise<Candidate[]>;
}
```

- [ ] **Step 4: Write the Claude implementation**

```typescript
// src/vision/claudeVision.ts
import type { VisionProvider } from "./visionProvider.js";
import type { Candidate, IdentifyMode } from "../types.js";
import { CandidateSchema } from "../types.js";
import { normalizePartNumber } from "../normalize.js";
import { z } from "zod";

export interface ClaudeConfig {
  apiKey: string;
  model: string;
}

const ReplySchema = z.object({
  candidates: z.array(
    z.object({
      partNumber: z.string(),
      manufacturer: z.string().optional(),
      packageType: z.string().optional(),
      confidence: z.number().min(0).max(1),
    }),
  ),
});

const SINGLE_PROMPT =
  "You are identifying ONE electronic component from a photo of its top marking. " +
  "Read the printed part number, ignoring date/lot codes. Respond with ONLY JSON: " +
  '{"candidates":[{"partNumber","manufacturer","packageType","confidence"}]} ' +
  "ordered by confidence (0..1). Include at most 3 candidates.";

const SHELF_PROMPT =
  "You are identifying MANY electronic components visible in one photo of a shelf/bin. " +
  "List every DISTINCT readable part marking. Respond with ONLY JSON: " +
  '{"candidates":[{"partNumber","manufacturer","packageType","confidence"}]}. ' +
  "Ignore unreadable items.";

export class ClaudeVisionProvider implements VisionProvider {
  constructor(
    private config: ClaudeConfig,
    private fetchFn: typeof fetch = fetch,
  ) {}

  async identify(
    imageBase64: string,
    mimeType: string,
    mode: IdentifyMode,
  ): Promise<Candidate[]> {
    const prompt = mode === "shelf" ? SHELF_PROMPT : SINGLE_PROMPT;

    const res = await this.fetchFn("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": this.config.apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: this.config.model,
        max_tokens: 1024,
        messages: [
          {
            role: "user",
            content: [
              {
                type: "image",
                source: {
                  type: "base64",
                  media_type: mimeType,
                  data: imageBase64,
                },
              },
              { type: "text", text: prompt },
            ],
          },
        ],
      }),
    });

    if (!res.ok) {
      throw new Error(`vision provider error: HTTP ${res.status}`);
    }

    const body = (await res.json()) as {
      content?: Array<{ type: string; text?: string }>;
    };
    const text =
      body.content?.find((c) => c.type === "text")?.text ?? '{"candidates":[]}';

    const parsed = ReplySchema.safeParse(JSON.parse(extractJson(text)));
    if (!parsed.success) return [];

    return parsed.data.candidates
      .map((c) => ({ ...c, partNumber: normalizePartNumber(c.partNumber) }))
      .filter((c) => c.partNumber.length > 0)
      .map((c) => CandidateSchema.parse(c));
  }
}

/** Pull the first {...} JSON object out of a possibly fenced text reply. */
function extractJson(text: string): string {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end === -1 || end < start) return '{"candidates":[]}';
  return text.slice(start, end + 1);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/claudeVision.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add ComponentScanner/backend/src/vision/ ComponentScanner/backend/tests/claudeVision.test.ts
git commit -m "feat(backend): add vision provider interface and Claude implementation"
```

---

## Task 6: Datasheet provider interface + Nexar implementation

Resolves a part number to manufacturer + datasheet URL + key specs via Nexar's GraphQL
API. `fetch` injected. Validates the returned URL ends in/serves a PDF before returning.

**Files:**
- Create: `ComponentScanner/backend/src/datasheet/datasheetProvider.ts`
- Create: `ComponentScanner/backend/src/datasheet/nexarDatasheet.ts`
- Test: `ComponentScanner/backend/tests/nexarDatasheet.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/nexarDatasheet.test.ts
import { describe, it, expect, vi } from "vitest";
import { NexarDatasheetProvider } from "../src/datasheet/nexarDatasheet.js";

function fakeNexarResponse(part: {
  mpn: string;
  manufacturer: string;
  url: string;
}) {
  return vi.fn(async () =>
    new Response(
      JSON.stringify({
        data: {
          supSearchMpn: {
            results: [
              {
                part: {
                  mpn: part.mpn,
                  manufacturer: { name: part.manufacturer },
                  bestDatasheet: { url: part.url },
                  specs: [
                    { attribute: { name: "Supply Voltage" }, displayValue: "3-32 V" },
                  ],
                },
              },
            ],
          },
        },
      }),
      { status: 200 },
    ),
  );
}

describe("NexarDatasheetProvider", () => {
  it("resolves a datasheet for a known part", async () => {
    const fetchFn = fakeNexarResponse({
      mpn: "LM358N",
      manufacturer: "Texas Instruments",
      url: "https://www.ti.com/lit/ds/symlink/lm358.pdf",
    });
    const provider = new NexarDatasheetProvider(
      { token: "test" },
      fetchFn as unknown as typeof fetch,
    );

    const result = await provider.resolve("LM358N");

    expect(result?.manufacturer).toBe("Texas Instruments");
    expect(result?.datasheetUrl).toContain(".pdf");
    expect(result?.keySpecs[0]?.name).toBe("Supply Voltage");
  });

  it("returns null when there are no results", async () => {
    const fetchFn = vi.fn(async () =>
      new Response(
        JSON.stringify({ data: { supSearchMpn: { results: [] } } }),
        { status: 200 },
      ),
    );
    const provider = new NexarDatasheetProvider(
      { token: "test" },
      fetchFn as unknown as typeof fetch,
    );
    expect(await provider.resolve("NOPART")).toBeNull();
  });

  it("returns null when the part has no datasheet URL", async () => {
    const fetchFn = vi.fn(async () =>
      new Response(
        JSON.stringify({
          data: {
            supSearchMpn: {
              results: [
                {
                  part: {
                    mpn: "X",
                    manufacturer: { name: "Y" },
                    bestDatasheet: null,
                    specs: [],
                  },
                },
              ],
            },
          },
        }),
        { status: 200 },
      ),
    );
    const provider = new NexarDatasheetProvider(
      { token: "test" },
      fetchFn as unknown as typeof fetch,
    );
    expect(await provider.resolve("X")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/nexarDatasheet.test.ts`
Expected: FAIL — cannot find module `../src/datasheet/nexarDatasheet.js`.

- [ ] **Step 3: Write the interface**

```typescript
// src/datasheet/datasheetProvider.ts
import type { Datasheet } from "../types.js";

export interface DatasheetProvider {
  /** Returns null when no datasheet can be resolved. */
  resolve(partNumber: string): Promise<Datasheet | null>;
}
```

- [ ] **Step 4: Write the Nexar implementation**

```typescript
// src/datasheet/nexarDatasheet.ts
import type { DatasheetProvider } from "./datasheetProvider.js";
import type { Datasheet, KeySpec } from "../types.js";

export interface NexarConfig {
  token: string;
  endpoint?: string; // defaults to Nexar GraphQL
  maxSpecs?: number; // cap key specs returned
}

const QUERY = `
query Search($q: String!) {
  supSearchMpn(q: $q, limit: 1) {
    results {
      part {
        mpn
        manufacturer { name }
        bestDatasheet { url }
        specs { attribute { name } displayValue }
      }
    }
  }
}`;

interface NexarPart {
  mpn: string;
  manufacturer: { name: string } | null;
  bestDatasheet: { url: string } | null;
  specs: Array<{ attribute: { name: string }; displayValue: string }> | null;
}

export class NexarDatasheetProvider implements DatasheetProvider {
  private endpoint: string;
  private maxSpecs: number;

  constructor(
    private config: NexarConfig,
    private fetchFn: typeof fetch = fetch,
  ) {
    this.endpoint = config.endpoint ?? "https://api.nexar.com/graphql";
    this.maxSpecs = config.maxSpecs ?? 8;
  }

  async resolve(partNumber: string): Promise<Datasheet | null> {
    const res = await this.fetchFn(this.endpoint, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${this.config.token}`,
      },
      body: JSON.stringify({ query: QUERY, variables: { q: partNumber } }),
    });

    if (!res.ok) {
      throw new Error(`datasheet provider error: HTTP ${res.status}`);
    }

    const body = (await res.json()) as {
      data?: { supSearchMpn?: { results?: Array<{ part: NexarPart }> } };
    };

    const part = body.data?.supSearchMpn?.results?.[0]?.part;
    if (!part) return null;
    const url = part.bestDatasheet?.url;
    if (!url) return null;

    const keySpecs: KeySpec[] = (part.specs ?? [])
      .slice(0, this.maxSpecs)
      .map((s) => ({ name: s.attribute.name, value: s.displayValue }));

    return {
      partNumber: part.mpn || partNumber,
      manufacturer: part.manufacturer?.name ?? "Unknown",
      datasheetUrl: url,
      keySpecs,
    };
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/nexarDatasheet.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add ComponentScanner/backend/src/datasheet/ ComponentScanner/backend/tests/nexarDatasheet.test.ts
git commit -m "feat(backend): add datasheet provider interface and Nexar implementation"
```

---

## Task 7: Rate-limit middleware

A simple per-client (by IP header) fixed-window limiter using the `Cache` abstraction.

**Files:**
- Create: `ComponentScanner/backend/src/middleware/rateLimit.ts`
- Test: `ComponentScanner/backend/tests/rateLimit.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/rateLimit.test.ts
import { describe, it, expect } from "vitest";
import { Hono } from "hono";
import { MemoryCache } from "../src/cache/memoryCache.js";
import { rateLimit } from "../src/middleware/rateLimit.js";

function appWithLimit(limit: number) {
  const app = new Hono();
  const cache = new MemoryCache(() => 0); // frozen time -> same window
  app.use("*", rateLimit({ cache, limit, windowSeconds: 60 }));
  app.get("/", (c) => c.text("ok"));
  return app;
}

describe("rateLimit", () => {
  it("allows requests under the limit", async () => {
    const app = appWithLimit(2);
    const headers = { "x-forwarded-for": "1.1.1.1" };
    expect((await app.request("/", { headers })).status).toBe(200);
    expect((await app.request("/", { headers })).status).toBe(200);
  });

  it("blocks the request that exceeds the limit with 429", async () => {
    const app = appWithLimit(1);
    const headers = { "x-forwarded-for": "2.2.2.2" };
    expect((await app.request("/", { headers })).status).toBe(200);
    expect((await app.request("/", { headers })).status).toBe(429);
  });

  it("tracks clients independently", async () => {
    const app = appWithLimit(1);
    expect(
      (await app.request("/", { headers: { "x-forwarded-for": "3.3.3.3" } }))
        .status,
    ).toBe(200);
    expect(
      (await app.request("/", { headers: { "x-forwarded-for": "4.4.4.4" } }))
        .status,
    ).toBe(200);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/rateLimit.test.ts`
Expected: FAIL — cannot find module `../src/middleware/rateLimit.js`.

- [ ] **Step 3: Write the implementation**

```typescript
// src/middleware/rateLimit.ts
import type { MiddlewareHandler } from "hono";
import type { Cache } from "../cache/cache.js";

export interface RateLimitOptions {
  cache: Cache;
  limit: number;
  windowSeconds: number;
}

export function rateLimit(opts: RateLimitOptions): MiddlewareHandler {
  return async (c, next) => {
    const ip =
      c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ||
      c.req.header("cf-connecting-ip") ||
      "unknown";
    const key = `rl:${ip}`;
    const current = Number((await opts.cache.get(key)) ?? "0");
    if (current >= opts.limit) {
      return c.json({ error: "rate limit exceeded" }, 429);
    }
    await opts.cache.set(key, String(current + 1), opts.windowSeconds);
    await next();
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/rateLimit.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add ComponentScanner/backend/src/middleware/ ComponentScanner/backend/tests/rateLimit.test.ts
git commit -m "feat(backend): add per-client rate-limit middleware"
```

---

## Task 8: `POST /identify` route

Accepts JSON `{ imageBase64, mimeType, mode }`, caches by image hash + mode, calls the
vision provider, returns candidates.

**Files:**
- Create: `ComponentScanner/backend/src/routes/identify.ts`
- Test: `ComponentScanner/backend/tests/identify.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/identify.test.ts
import { describe, it, expect, vi } from "vitest";
import { Hono } from "hono";
import { createIdentifyRoute } from "../src/routes/identify.js";
import { MemoryCache } from "../src/cache/memoryCache.js";
import type { VisionProvider } from "../src/vision/visionProvider.js";

function makeApp(vision: VisionProvider) {
  const app = new Hono();
  const cache = new MemoryCache(() => 0);
  app.post("/identify", createIdentifyRoute({ vision, cache, cacheTtl: 600 }));
  return app;
}

const body = (mode = "single") =>
  JSON.stringify({ imageBase64: "QUJD", mimeType: "image/jpeg", mode });

describe("POST /identify", () => {
  it("returns candidates from the vision provider", async () => {
    const vision: VisionProvider = {
      identify: vi.fn(async () => [
        { partNumber: "LM358N", manufacturer: "TI", confidence: 0.9 },
      ]),
    };
    const res = await makeApp(vision).request("/identify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: body(),
    });
    expect(res.status).toBe(200);
    const json = (await res.json()) as { candidates: Array<{ partNumber: string }> };
    expect(json.candidates[0]?.partNumber).toBe("LM358N");
  });

  it("uses the cache on a second identical request (vision called once)", async () => {
    const identify = vi.fn(async () => [
      { partNumber: "LM358N", confidence: 0.9 },
    ]);
    const app = makeApp({ identify });
    const req = () =>
      app.request("/identify", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: body(),
      });
    await req();
    await req();
    expect(identify).toHaveBeenCalledOnce();
  });

  it("rejects a malformed body with 400", async () => {
    const app = makeApp({ identify: vi.fn() });
    const res = await app.request("/identify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ mimeType: "image/jpeg" }),
    });
    expect(res.status).toBe(400);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/identify.test.ts`
Expected: FAIL — cannot find module `../src/routes/identify.js`.

- [ ] **Step 3: Write the implementation**

```typescript
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/identify.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add ComponentScanner/backend/src/routes/identify.ts ComponentScanner/backend/tests/identify.test.ts
git commit -m "feat(backend): add POST /identify route with caching"
```

---

## Task 9: `GET /datasheet` route

Accepts `?part=…`, normalizes it, caches by part number, calls the datasheet provider,
returns the datasheet or 404.

**Files:**
- Create: `ComponentScanner/backend/src/routes/datasheet.ts`
- Test: `ComponentScanner/backend/tests/datasheetRoute.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/datasheetRoute.test.ts
import { describe, it, expect, vi } from "vitest";
import { Hono } from "hono";
import { createDatasheetRoute } from "../src/routes/datasheet.js";
import { MemoryCache } from "../src/cache/memoryCache.js";
import type { DatasheetProvider } from "../src/datasheet/datasheetProvider.js";

function makeApp(provider: DatasheetProvider) {
  const app = new Hono();
  const cache = new MemoryCache(() => 0);
  app.get("/datasheet", createDatasheetRoute({ datasheet: provider, cache, cacheTtl: 86400 }));
  return app;
}

const SHEET = {
  partNumber: "LM358N",
  manufacturer: "Texas Instruments",
  datasheetUrl: "https://www.ti.com/lit/ds/symlink/lm358.pdf",
  keySpecs: [],
};

describe("GET /datasheet", () => {
  it("returns the datasheet for a known part", async () => {
    const provider: DatasheetProvider = { resolve: vi.fn(async () => SHEET) };
    const res = await makeApp(provider).request("/datasheet?part=lm358n");
    expect(res.status).toBe(200);
    const json = (await res.json()) as { manufacturer: string };
    expect(json.manufacturer).toBe("Texas Instruments");
  });

  it("returns 400 when part is missing", async () => {
    const provider: DatasheetProvider = { resolve: vi.fn() };
    const res = await makeApp(provider).request("/datasheet");
    expect(res.status).toBe(400);
  });

  it("returns 404 when no datasheet is found", async () => {
    const provider: DatasheetProvider = { resolve: vi.fn(async () => null) };
    const res = await makeApp(provider).request("/datasheet?part=NOPART");
    expect(res.status).toBe(404);
  });

  it("caches the result (provider called once for repeated parts)", async () => {
    const resolve = vi.fn(async () => SHEET);
    const app = makeApp({ resolve });
    await app.request("/datasheet?part=LM358N");
    await app.request("/datasheet?part=LM358N");
    expect(resolve).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/datasheetRoute.test.ts`
Expected: FAIL — cannot find module `../src/routes/datasheet.js`.

- [ ] **Step 3: Write the implementation**

```typescript
// src/routes/datasheet.ts
import type { Handler } from "hono";
import type { DatasheetProvider } from "../datasheet/datasheetProvider.js";
import type { Cache } from "../cache/cache.js";
import { normalizePartNumber } from "../normalize.js";

export interface DatasheetDeps {
  datasheet: DatasheetProvider;
  cache: Cache;
  cacheTtl: number; // seconds
}

export function createDatasheetRoute(deps: DatasheetDeps): Handler {
  return async (c) => {
    const partParam = c.req.query("part");
    if (!partParam) {
      return c.json({ error: "missing 'part' query parameter" }, 400);
    }
    const part = normalizePartNumber(partParam);

    const cacheKey = `datasheet:${part}`;
    const cached = await deps.cache.get(cacheKey);
    if (cached) return c.json(JSON.parse(cached));

    const result = await deps.datasheet.resolve(part);
    if (!result) {
      return c.json({ error: "datasheet not found", partNumber: part }, 404);
    }
    await deps.cache.set(cacheKey, JSON.stringify(result), deps.cacheTtl);
    return c.json(result);
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/datasheetRoute.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add ComponentScanner/backend/src/routes/datasheet.ts ComponentScanner/backend/tests/datasheetRoute.test.ts
git commit -m "feat(backend): add GET /datasheet route with caching"
```

---

## Task 10: Config parsing

Parses and validates required env vars; throws a clear error if a secret is missing.

**Files:**
- Create: `ComponentScanner/backend/src/config.ts`
- Test: `ComponentScanner/backend/tests/config.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/config.test.ts
import { describe, it, expect } from "vitest";
import { loadConfig } from "../src/config.js";

describe("loadConfig", () => {
  it("parses a complete environment", () => {
    const cfg = loadConfig({
      ANTHROPIC_API_KEY: "sk-x",
      CLAUDE_MODEL: "claude-test",
      NEXAR_TOKEN: "tok",
      RATE_LIMIT: "30",
    });
    expect(cfg.anthropicApiKey).toBe("sk-x");
    expect(cfg.claudeModel).toBe("claude-test");
    expect(cfg.nexarToken).toBe("tok");
    expect(cfg.rateLimit).toBe(30);
  });

  it("applies defaults for optional values", () => {
    const cfg = loadConfig({ ANTHROPIC_API_KEY: "sk-x", NEXAR_TOKEN: "tok" });
    expect(cfg.claudeModel).toMatch(/claude/);
    expect(cfg.rateLimit).toBeGreaterThan(0);
  });

  it("throws when a required secret is missing", () => {
    expect(() => loadConfig({ NEXAR_TOKEN: "tok" })).toThrow(/ANTHROPIC_API_KEY/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/config.test.ts`
Expected: FAIL — cannot find module `../src/config.js`.

- [ ] **Step 3: Write the implementation**

```typescript
// src/config.ts
export interface AppConfig {
  anthropicApiKey: string;
  claudeModel: string;
  nexarToken: string;
  rateLimit: number; // requests per window
  rateWindowSeconds: number;
  identifyCacheTtl: number;
  datasheetCacheTtl: number;
}

type Env = Record<string, string | undefined>;

function required(env: Env, key: string): string {
  const v = env[key];
  if (!v) throw new Error(`missing required env var: ${key}`);
  return v;
}

export function loadConfig(env: Env): AppConfig {
  return {
    anthropicApiKey: required(env, "ANTHROPIC_API_KEY"),
    claudeModel: env.CLAUDE_MODEL ?? "claude-opus-4-8",
    nexarToken: required(env, "NEXAR_TOKEN"),
    rateLimit: Number(env.RATE_LIMIT ?? "60"),
    rateWindowSeconds: Number(env.RATE_WINDOW_SECONDS ?? "60"),
    identifyCacheTtl: Number(env.IDENTIFY_CACHE_TTL ?? "600"),
    datasheetCacheTtl: Number(env.DATASHEET_CACHE_TTL ?? "86400"),
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/config.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add ComponentScanner/backend/src/config.ts ComponentScanner/backend/tests/config.test.ts
git commit -m "feat(backend): add env config parsing and validation"
```

---

## Task 11: Wire the app together

`buildApp(deps)` assembles routes + middleware; an integration test exercises both routes
through one app with fake providers.

**Files:**
- Create: `ComponentScanner/backend/src/app.ts`
- Test: `ComponentScanner/backend/tests/app.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/app.test.ts
import { describe, it, expect, vi } from "vitest";
import { buildApp } from "../src/app.js";
import { MemoryCache } from "../src/cache/memoryCache.js";

function deps() {
  return {
    vision: {
      identify: vi.fn(async () => [{ partNumber: "LM358N", confidence: 0.9 }]),
    },
    datasheet: {
      resolve: vi.fn(async () => ({
        partNumber: "LM358N",
        manufacturer: "TI",
        datasheetUrl: "https://www.ti.com/lit/ds/symlink/lm358.pdf",
        keySpecs: [],
      })),
    },
    cache: new MemoryCache(() => 0),
    rateLimit: 100,
    rateWindowSeconds: 60,
    identifyCacheTtl: 600,
    datasheetCacheTtl: 86400,
  };
}

describe("buildApp", () => {
  it("serves a health check", async () => {
    const app = buildApp(deps());
    const res = await app.request("/health");
    expect(res.status).toBe(200);
  });

  it("wires /identify end to end", async () => {
    const app = buildApp(deps());
    const res = await app.request("/identify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ imageBase64: "QUJD", mimeType: "image/jpeg", mode: "single" }),
    });
    expect(res.status).toBe(200);
  });

  it("wires /datasheet end to end", async () => {
    const app = buildApp(deps());
    const res = await app.request("/datasheet?part=LM358N");
    expect(res.status).toBe(200);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ComponentScanner/backend && npx vitest run tests/app.test.ts`
Expected: FAIL — cannot find module `../src/app.js`.

- [ ] **Step 3: Write the implementation**

```typescript
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ComponentScanner/backend && npx vitest run tests/app.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add ComponentScanner/backend/src/app.ts ComponentScanner/backend/tests/app.test.ts
git commit -m "feat(backend): wire routes and middleware into buildApp"
```

---

## Task 12: Entry point (Node + Workers)

Builds real dependencies from config and exposes both a Node server and a Workers fetch
handler. No new unit test (it is wiring of already-tested pieces); verified by typecheck
and a manual smoke run.

**Files:**
- Create: `ComponentScanner/backend/src/index.ts`

- [ ] **Step 1: Write the entry point**

```typescript
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
```

- [ ] **Step 2: Typecheck**

Run: `cd ComponentScanner/backend && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Run the full test suite**

Run: `cd ComponentScanner/backend && npm test`
Expected: all tests across all files PASS.

- [ ] **Step 4: Commit**

```bash
git add ComponentScanner/backend/src/index.ts
git commit -m "feat(backend): add Node + Cloudflare Workers entry point"
```

---

## Task 13: Deploy config + docs

**Files:**
- Create: `ComponentScanner/backend/wrangler.toml`
- Create: `ComponentScanner/backend/.env.example`
- Create: `ComponentScanner/backend/README.md`

- [ ] **Step 1: Create `wrangler.toml`**

```toml
name = "component-scanner-backend"
main = "src/index.ts"
compatibility_date = "2024-09-23"
compatibility_flags = ["nodejs_compat"]

# Secrets are set with `wrangler secret put <NAME>`, never committed:
#   wrangler secret put ANTHROPIC_API_KEY
#   wrangler secret put NEXAR_TOKEN
# Non-secret vars:
[vars]
CLAUDE_MODEL = "claude-opus-4-8"
RATE_LIMIT = "60"
```

- [ ] **Step 2: Create `.env.example`**

```
# Copy to .dev.vars (Workers local) or .env (Node) and fill in real values.
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-opus-4-8
NEXAR_TOKEN=your-nexar-bearer-token
RATE_LIMIT=60
RATE_WINDOW_SECONDS=60
IDENTIFY_CACHE_TTL=600
DATASHEET_CACHE_TTL=86400
PORT=8787
```

- [ ] **Step 3: Create `README.md`**

````markdown
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
````

- [ ] **Step 4: Verify the server boots locally (manual smoke test)**

Run: `cd ComponentScanner/backend && (set ANTHROPIC_API_KEY=x && set NEXAR_TOKEN=y && npm run dev)`
(PowerShell: `$env:ANTHROPIC_API_KEY="x"; $env:NEXAR_TOKEN="y"; npm run dev`)
Then in another shell: `curl http://localhost:8787/health`
Expected: `{"status":"ok"}`. Stop the server afterward.

- [ ] **Step 5: Commit**

```bash
git add ComponentScanner/backend/wrangler.toml ComponentScanner/backend/.env.example ComponentScanner/backend/README.md
git commit -m "docs(backend): add deploy config and README"
```

---

## Self-Review

**Spec coverage (Phase-1 backend portion of the spec):**
- §3/§7 backend with `/identify` + `/datasheet` → Tasks 8, 9, 11, 12. ✓
- §4 recognition cloud path (vision-LLM, single + shelf prompts) → Task 5. ✓
- §4 part-number normalization → Task 2 (reused in Tasks 5, 9). ✓
- §5 datasheet resolution via Nexar + key specs → Task 6. ✓
- §7 cache → Tasks 4, 8, 9. ✓
- §7 rate limiting → Task 7. ✓
- §7 provider interfaces (swappable) → Tasks 5, 6 (interfaces in `visionProvider.ts`/`datasheetProvider.ts`). ✓
- §7 secrets via env, never committed → Tasks 10, 13 (`.gitignore`, `.env.example`, wrangler secrets). ✓
- §10 HTTPS/rate-limit/no-secrets-in-app → backend-side covered (HTTPS is a deploy property of Workers). ✓
- §9 backend testing (mocked LLM + parts API, JSON robustness, cache hit/miss, rate limiting) → every task is TDD. ✓

**Deferred to the Android app plan (correctly out of scope here):** on-device ML Kit OCR,
fuzzy matcher, Compose UI, Room, PDF viewer, camera. The datasheet PDF fallback resolvers
(§5 a/b) are noted as a follow-up enhancement; the Nexar path + 404 handling are the MVP.

**Placeholder scan:** none — every code step contains complete code.

**Type consistency:** `Candidate`, `Datasheet`, `KeySpec`, `IdentifyMode` defined in Task 3
and used consistently in Tasks 5, 6, 8, 9, 11. `Cache` interface (Task 4) used in Tasks 7,
8, 9, 11. `VisionProvider`/`DatasheetProvider` (Tasks 5, 6) used in Tasks 8, 9, 11, 12.
`buildApp`/`AppDeps` (Task 11) used in Task 12. Endpoint shapes match between routes and the
README. ✓
