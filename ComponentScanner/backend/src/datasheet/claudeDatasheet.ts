// src/datasheet/claudeDatasheet.ts
import type { DatasheetProvider } from "./datasheetProvider.js";
import type { Datasheet } from "../types.js";

export interface ClaudeDatasheetConfig {
  apiKey: string;
  model: string;
  /** Set false to skip the web_search server tool (used in tests / fallback). */
  enableWebSearch?: boolean;
}

interface Guess {
  manufacturer: string | null;
  datasheetUrl: string | null;
}

function prompt(part: string): string {
  return (
    `Give the direct URL to the datasheet PDF for the electronic component with ` +
    `part number "${part}". Prefer the manufacturer's official PDF. Many manufacturer ` +
    `sites (e.g. st.com) block automated access, so a copy of the SAME datasheet hosted ` +
    `by a major distributor that allows direct download (e.g. mouser.com/datasheet/..., ` +
    `media.digikey.com/...) is equally good and often more reliable. The URL MUST point ` +
    `straight at the PDF bytes — it must end in ".pdf". Only give a URL you are confident ` +
    `actually exists. Respond with ONLY a JSON object on one line: ` +
    `{"manufacturer":"<name>","datasheetUrl":"<direct .pdf link>"}. If you do not know a ` +
    `real datasheet PDF for this exact part, respond {"manufacturer":null,"datasheetUrl":null}.`
  );
}

/**
 * Resolves datasheets by asking Claude for the manufacturer/distributor datasheet
 * PDF URL. Uses only the Anthropic API key. We deliberately do NOT fetch-validate
 * the URL server-side: this runs on Cloudflare's datacenter IPs, which vendors and
 * distributors (st.com, mouser.com, …) block — so validation produces false
 * negatives and discards URLs the phone (residential IP) can actually download.
 * The app downloads the PDF directly and falls back to "Open in browser" when a
 * site blocks even the phone.
 */
export class ClaudeDatasheetProvider implements DatasheetProvider {
  private fetchFn: typeof fetch;

  constructor(
    private config: ClaudeDatasheetConfig,
    fetchFn: typeof fetch = fetch,
  ) {
    // Bind to globalThis for Cloudflare Workers (avoids "Illegal invocation").
    this.fetchFn = fetchFn.bind(globalThis);
  }

  async resolve(partNumber: string): Promise<Datasheet | null> {
    // Fast path: the model answers from its own knowledge (no search) — a few
    // seconds, and it knows canonical URLs for common parts/distributors.
    const fast = await this.tryResolve(partNumber, false);
    if (fast) return fast;

    // Fallback: only if the model produced nothing, let it web-search.
    if (this.config.enableWebSearch !== false) {
      return this.tryResolve(partNumber, true);
    }
    return null;
  }

  private async tryResolve(
    part: string,
    useSearch: boolean,
  ): Promise<Datasheet | null> {
    const guess = await this.ask(part, useSearch);
    const url = guess?.datasheetUrl;
    if (!url || !looksLikePdfUrl(url)) return null;
    return {
      partNumber: part,
      manufacturer: guess.manufacturer ?? "Unknown",
      datasheetUrl: url,
      keySpecs: [],
    };
  }

  private async ask(part: string, useSearch: boolean): Promise<Guess | null> {
    const tools = useSearch
      ? [{ type: "web_search_20260209", name: "web_search", max_uses: 2 }]
      : undefined;

    let messages: Array<{ role: string; content: unknown }> = [
      { role: "user", content: prompt(part) },
    ];

    for (let i = 0; i < 4; i++) {
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
          ...(tools ? { tools } : {}),
          messages,
        }),
        signal: AbortSignal.timeout(useSearch ? 45_000 : 22_000),
      });

      if (!res.ok) return null;

      const body = (await res.json()) as {
        stop_reason?: string;
        content?: Array<{ type: string; text?: string }>;
      };

      if (body.stop_reason === "pause_turn" && body.content) {
        // Server tool loop paused — re-send with the assistant turn appended.
        messages = [...messages, { role: "assistant", content: body.content }];
        continue;
      }

      const text = (body.content ?? [])
        .filter((b) => b.type === "text")
        .map((b) => b.text ?? "")
        .join("\n");
      return parseGuess(text);
    }
    return null;
  }
}

export function looksLikePdfUrl(url: string): boolean {
  try {
    const u = new URL(url);
    if (u.protocol !== "https:" && u.protocol !== "http:") return false;
    return u.pathname.toLowerCase().endsWith(".pdf");
  } catch {
    return false;
  }
}

export function parseGuess(text: string): Guess | null {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end === -1 || end < start) return null;
  try {
    const o = JSON.parse(text.slice(start, end + 1)) as Partial<Guess>;
    return {
      manufacturer: o.manufacturer ?? null,
      datasheetUrl: o.datasheetUrl ?? null,
    };
  } catch {
    return null;
  }
}
