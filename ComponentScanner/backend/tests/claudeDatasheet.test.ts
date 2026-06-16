// tests/claudeDatasheet.test.ts
import { describe, it, expect, vi } from "vitest";
import {
  ClaudeDatasheetProvider,
  parseGuess,
} from "../src/datasheet/claudeDatasheet.js";

const PDF_URL = "https://www.ti.com/lit/ds/symlink/lm358.pdf";

/** Routes the Anthropic Messages call vs. the PDF-validation fetch. */
function routerFetch(opts: {
  guessJson: string;
  pdfStatus?: number;
  pdfContentType?: string;
}) {
  return vi.fn(async (url: string | URL | Request) => {
    const u = typeof url === "string" ? url : url.toString();
    if (u.includes("api.anthropic.com")) {
      return new Response(
        JSON.stringify({ content: [{ type: "text", text: opts.guessJson }] }),
        { status: 200 },
      );
    }
    // PDF validation request
    return new Response("%PDF-1.7 ...", {
      status: opts.pdfStatus ?? 200,
      headers: { "content-type": opts.pdfContentType ?? "application/pdf" },
    });
  });
}

function provider(fetchFn: ReturnType<typeof routerFetch>) {
  return new ClaudeDatasheetProvider(
    { apiKey: "test", model: "claude-x", enableWebSearch: false },
    fetchFn as unknown as typeof fetch,
  );
}

describe("ClaudeDatasheetProvider", () => {
  it("resolves a validated PDF datasheet", async () => {
    const fetchFn = routerFetch({
      guessJson: JSON.stringify({
        manufacturer: "Texas Instruments",
        datasheetUrl: PDF_URL,
      }),
    });
    const r = await provider(fetchFn).resolve("LM358N");
    expect(r?.manufacturer).toBe("Texas Instruments");
    expect(r?.datasheetUrl).toBe(PDF_URL);
  });

  it("returns null when the model finds no datasheet", async () => {
    const fetchFn = routerFetch({
      guessJson: JSON.stringify({ manufacturer: null, datasheetUrl: null }),
    });
    expect(await provider(fetchFn).resolve("NOPART")).toBeNull();
  });

  it("returns null when the URL fails validation (404)", async () => {
    const fetchFn = routerFetch({
      guessJson: JSON.stringify({ manufacturer: "TI", datasheetUrl: PDF_URL }),
      pdfStatus: 404,
    });
    expect(await provider(fetchFn).resolve("LM358N")).toBeNull();
  });

  it("rejects a URL that does not serve a PDF", async () => {
    const fetchFn = vi.fn(async (url: string | URL | Request) => {
      const u = typeof url === "string" ? url : url.toString();
      if (u.includes("api.anthropic.com")) {
        return new Response(
          JSON.stringify({
            content: [
              {
                type: "text",
                text: JSON.stringify({ manufacturer: "X", datasheetUrl: "https://x/page.html" }),
              },
            ],
          }),
          { status: 200 },
        );
      }
      return new Response("<html>not a pdf</html>", {
        status: 200,
        headers: { "content-type": "text/html" },
      });
    });
    expect(
      await provider(fetchFn as unknown as ReturnType<typeof routerFetch>).resolve("X"),
    ).toBeNull();
  });
});

describe("parseGuess", () => {
  it("extracts JSON embedded in prose", () => {
    const g = parseGuess('Here it is: {"manufacturer":"TI","datasheetUrl":"u"} done');
    expect(g?.manufacturer).toBe("TI");
    expect(g?.datasheetUrl).toBe("u");
  });

  it("returns null on non-JSON", () => {
    expect(parseGuess("no json here")).toBeNull();
  });
});
