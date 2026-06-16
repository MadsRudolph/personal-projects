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
  private fetchFn: typeof fetch;

  constructor(
    private config: ClaudeConfig,
    fetchFn: typeof fetch = fetch,
  ) {
    // Bind to globalThis so the call works on Cloudflare Workers, where calling
    // a detached `fetch` (via `this.fetchFn(...)`) throws "Illegal invocation".
    this.fetchFn = fetchFn.bind(globalThis);
  }

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

    let parsedJson: unknown;
    try {
      parsedJson = JSON.parse(extractJson(text));
    } catch {
      return [];
    }

    const parsed = ReplySchema.safeParse(parsedJson);
    if (!parsed.success) return [];

    const normalized = parsed.data.candidates
      .map((c) => ({ ...c, partNumber: normalizePartNumber(c.partNumber) }))
      .filter((c) => c.partNumber.length > 0)
      .map((c) => CandidateSchema.parse(c));

    // Dedup by partNumber, keeping the highest-confidence entry for each
    const byPart = new Map<string, Candidate>();
    for (const candidate of normalized) {
      const existing = byPart.get(candidate.partNumber);
      if (existing === undefined || candidate.confidence > existing.confidence) {
        byPart.set(candidate.partNumber, candidate);
      }
    }
    return Array.from(byPart.values());
  }
}

/** Pull the first {...} JSON object out of a possibly fenced text reply. */
function extractJson(text: string): string {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end === -1 || end < start) return '{"candidates":[]}';
  return text.slice(start, end + 1);
}
