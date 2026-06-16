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

const BROWSER_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

/** Hosts confirmed to serve real, directly-downloadable datasheet PDFs to normal
 *  clients (so the phone can fetch + render them in-app), even if our datacenter
 *  validator is blocked. Octopart's CDN covers a very large part catalogue. */
function isDirectPdfHost(url: string): boolean {
  try {
    return new URL(url).hostname.toLowerCase() === "datasheet.octopart.com";
  } catch {
    return false;
  }
}

function prompt(part: string): string {
  return (
    `Give the URL to a DIRECTLY DOWNLOADABLE datasheet PDF for the electronic ` +
    `component with part number "${part}". ` +
    `Strongly prefer a URL on "datasheet.octopart.com" — that CDN hosts real, ` +
    `directly-downloadable datasheet PDFs for most parts and is the most reliable ` +
    `source. The manufacturer's own official PDF (e.g. ti.com/lit/...) is also good ` +
    `when it allows direct download. Avoid product/search pages and distributor pages ` +
    `that require a browser (mouser.com, st.com product pages), which serve HTML, not ` +
    `the PDF. The URL MUST end in ".pdf". Respond with ONLY a JSON object on one line: ` +
    `{"manufacturer":"<name>","datasheetUrl":"<direct .pdf link>"}. If you cannot find a ` +
    `real downloadable PDF, respond {"manufacturer":null,"datasheetUrl":null}.`
  );
}

/**
 * Resolves datasheets by asking Claude (with web search) for a directly-downloadable
 * datasheet PDF, preferring Octopart's CDN. Returned URLs are either confirmed by a
 * server-side fetch, or are on a host known to serve real PDFs to the phone — so the
 * app can render every datasheet in-app.
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
    // Fast path: model answers from knowledge (no search). Confirmed-downloadable
    // only, so memory hallucinations and HTML stubs are rejected and fall through.
    const fast = await this.tryResolve(partNumber, false);
    if (fast) return fast;

    // Search path: real URLs (incl. Octopart CDN) via web search.
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

    // Accept if our server fetch confirms a PDF, OR (on the search path) if it's a
    // real URL on a host known to serve direct PDFs to the phone even when the
    // datacenter validator is blocked.
    const ok =
      (await this.validatePdf(url)) || (useSearch && isDirectPdfHost(url));
    if (!ok) return null;
    return {
      partNumber: part,
      manufacturer: guess.manufacturer ?? "Unknown",
      datasheetUrl: url,
      keySpecs: [],
    };
  }

  /** Confirm the URL actually serves PDF bytes (browser UA; reads only a sniff). */
  private async validatePdf(url: string): Promise<boolean> {
    try {
      const res = await this.fetchFn(url, {
        method: "GET",
        headers: {
          range: "bytes=0-2047",
          "user-agent": BROWSER_UA,
          accept: "application/pdf,*/*",
        },
        signal: AbortSignal.timeout(12_000),
        redirect: "follow",
      });
      if (!res.ok && res.status !== 206) {
        await res.body?.cancel?.();
        return false;
      }
      const ct = (res.headers.get("content-type") ?? "").toLowerCase();
      if (ct.includes("pdf")) {
        await res.body?.cancel?.();
        return true;
      }
      const reader = res.body?.getReader();
      if (!reader) return false;
      const { value } = await reader.read();
      await reader.cancel();
      if (!value) return false;
      return new TextDecoder().decode(value.slice(0, 5)).startsWith("%PDF");
    } catch {
      return false;
    }
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
          max_tokens: 768,
          ...(tools ? { tools } : {}),
          messages,
        }),
        signal: AbortSignal.timeout(useSearch ? 50_000 : 22_000),
      });

      if (!res.ok) return null;

      const body = (await res.json()) as {
        stop_reason?: string;
        content?: Array<{ type: string; text?: string }>;
      };

      if (body.stop_reason === "pause_turn" && body.content) {
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
