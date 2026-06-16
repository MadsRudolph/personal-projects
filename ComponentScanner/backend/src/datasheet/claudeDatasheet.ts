// src/datasheet/claudeDatasheet.ts
import type { DatasheetProvider } from "./datasheetProvider.js";
import type { Datasheet } from "../types.js";

export interface ClaudeDatasheetConfig {
  apiKey: string;
  model: string;
  /** Set false to skip the web_search server tool (used as an internal fallback). */
  enableWebSearch?: boolean;
}

interface Guess {
  manufacturer: string | null;
  datasheetUrl: string | null;
}

function prompt(part: string): string {
  return (
    `Find the official manufacturer datasheet (PDF) for the electronic component ` +
    `with part number "${part}". Prefer the manufacturer's own website. ` +
    `Respond with ONLY a JSON object on a single line: ` +
    `{"manufacturer":"<name>","datasheetUrl":"<direct link to the PDF>"}. ` +
    `datasheetUrl MUST be a direct link to the PDF file (ending in .pdf or serving ` +
    `application/pdf), not a product/search page. If you cannot find a real datasheet ` +
    `PDF, respond with {"manufacturer":null,"datasheetUrl":null}.`
  );
}

/**
 * Resolves datasheets by asking Claude (with the web_search server tool) for the
 * manufacturer's datasheet PDF, then validating the URL actually serves a PDF.
 * Uses only the Anthropic API key — no third-party parts account required.
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
    // 1) Fast path: the model answers from its own knowledge (no search) — quick
    //    and accurate for common parts. The URL is validated, so a wrong guess
    //    simply falls through to the search path below.
    const fast = await this.tryResolve(partNumber, false);
    if (fast) return fast;

    // 2) Slower path: let the model web-search for parts it doesn't know.
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
    if (!url) return null;
    // Accept if we can confirm it's a PDF, OR if it's a plausible PDF URL from a
    // known manufacturer whose site blocks automated fetches (e.g. st.com). The
    // app's "Open in browser" fallback handles vendors that block direct download.
    if ((await this.validatePdf(url)) || isTrustedPdfUrl(url)) {
      return {
        partNumber: part,
        manufacturer: guess.manufacturer ?? "Unknown",
        datasheetUrl: url,
        keySpecs: [],
      };
    }
    return null;
  }

  private async ask(part: string, useSearch: boolean): Promise<Guess | null> {
    const tools = useSearch
      ? [{ type: "web_search_20260209", name: "web_search", max_uses: 5 }]
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
        signal: AbortSignal.timeout(useSearch ? 75_000 : 25_000),
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

  /** Confirm the URL actually serves a PDF before handing it to the app. */
  private async validatePdf(url: string): Promise<boolean> {
    try {
      const res = await this.fetchFn(url, {
        method: "GET",
        headers: {
          range: "bytes=0-2047",
          // Some vendor sites (e.g. st.com) 403 requests without a browser UA.
          "user-agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
          accept: "application/pdf,*/*",
        },
        signal: AbortSignal.timeout(15_000),
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
      // Read only the first chunk to check the %PDF magic, then cancel — never
      // buffer a whole (possibly multi-MB) file just to validate it.
      const reader = res.body?.getReader();
      if (!reader) return false;
      const { value } = await reader.read();
      await reader.cancel();
      if (!value) return false;
      const head = new TextDecoder().decode(value.slice(0, 5));
      return head.startsWith("%PDF");
    } catch {
      return false;
    }
  }
}

/** Manufacturer/distributor domains whose datasheet PDFs we trust even when the
 *  site blocks our validation fetch (bot protection). Keep to reputable sources. */
const TRUSTED_DATASHEET_HOSTS = [
  "ti.com",
  "st.com",
  "microchip.com",
  "onsemi.com",
  "infineon.com",
  "nxp.com",
  "analog.com",
  "diodes.com",
  "vishay.com",
  "rohm.com",
  "toshiba.com",
  "renesas.com",
  "nexperia.com",
  "mouser.com",
  "digikey.com",
];

export function isTrustedPdfUrl(url: string): boolean {
  try {
    const u = new URL(url);
    if (u.protocol !== "https:" && u.protocol !== "http:") return false;
    const host = u.hostname.toLowerCase();
    const trusted = TRUSTED_DATASHEET_HOSTS.some(
      (d) => host === d || host.endsWith("." + d),
    );
    return trusted && u.pathname.toLowerCase().endsWith(".pdf");
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
