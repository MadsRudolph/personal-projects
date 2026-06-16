// tests/claudeDatasheet.test.ts
import { describe, it, expect, vi } from "vitest";
import {
  ClaudeDatasheetProvider,
  parseGuess,
  looksLikePdfUrl,
} from "../src/datasheet/claudeDatasheet.js";

/** Routes the Anthropic Messages call vs. the PDF-validation fetch. */
function routerFetch(opts: {
  guessJson: string;
  pdfStatus?: number;
  pdfContentType?: string;
  pdfBody?: string;
}) {
  return vi.fn(async (url: string | URL | Request) => {
    const u = typeof url === "string" ? url : url.toString();
    if (u.includes("api.anthropic.com")) {
      return new Response(
        JSON.stringify({ content: [{ type: "text", text: opts.guessJson }] }),
        { status: 200 },
      );
    }
    return new Response(opts.pdfBody ?? "%PDF-1.7 ...", {
      status: opts.pdfStatus ?? 200,
      headers: { "content-type": opts.pdfContentType ?? "application/pdf" },
    });
  });
}

function provider(
  fetchFn: ReturnType<typeof routerFetch>,
  enableWebSearch = false,
) {
  return new ClaudeDatasheetProvider(
    { apiKey: "test", model: "claude-x", enableWebSearch },
    fetchFn as unknown as typeof fetch,
  );
}

describe("ClaudeDatasheetProvider", () => {
  it("resolves a confirmed-downloadable manufacturer PDF", async () => {
    const fetchFn = routerFetch({
      guessJson: JSON.stringify({
        manufacturer: "Texas Instruments",
        datasheetUrl: "https://www.ti.com/lit/ds/symlink/lm358.pdf",
      }),
    });
    const r = await provider(fetchFn).resolve("LM358N");
    expect(r?.manufacturer).toBe("Texas Instruments");
    expect(r?.datasheetUrl).toContain(".pdf");
  });

  it("rejects a URL that does not serve a PDF", async () => {
    const fetchFn = routerFetch({
      guessJson: JSON.stringify({
        manufacturer: "X",
        datasheetUrl: "https://x/stub.pdf",
      }),
      pdfContentType: "text/html",
      pdfBody: "<!DOCTYPE html><html>blocked</html>",
    });
    expect(await provider(fetchFn).resolve("X")).toBeNull();
  });

  it("rejects a non-pdf URL without fetching", async () => {
    const fetchFn = routerFetch({
      guessJson: JSON.stringify({ manufacturer: "X", datasheetUrl: "https://x/product/page" }),
    });
    expect(await provider(fetchFn).resolve("X")).toBeNull();
  });

  it("returns null when the model finds no datasheet", async () => {
    const fetchFn = routerFetch({
      guessJson: JSON.stringify({ manufacturer: null, datasheetUrl: null }),
    });
    expect(await provider(fetchFn).resolve("NOPART")).toBeNull();
  });

  it("trusts an Octopart CDN URL from search even when the validator is blocked", async () => {
    const fetchFn = routerFetch({
      guessJson: JSON.stringify({
        manufacturer: "STMicroelectronics",
        datasheetUrl:
          "https://datasheet.octopart.com/L7805CV-STMicroelectronics-datasheet-7264666.pdf",
      }),
      pdfStatus: 403, // datacenter validator blocked, but Octopart serves the phone
    });
    const r = await provider(fetchFn, /* enableWebSearch */ true).resolve("L7805CV");
    expect(r?.datasheetUrl).toContain("datasheet.octopart.com");
    expect(r?.manufacturer).toBe("STMicroelectronics");
  });
});

describe("looksLikePdfUrl", () => {
  it("accepts http(s) URLs ending in .pdf", () => {
    expect(looksLikePdfUrl("https://www.ti.com/lit/ds/symlink/lm358.pdf")).toBe(true);
  });
  it("rejects non-pdf paths and bad URLs", () => {
    expect(looksLikePdfUrl("https://www.st.com/product/l7805")).toBe(false);
    expect(looksLikePdfUrl("not a url")).toBe(false);
  });
});

describe("parseGuess", () => {
  it("extracts JSON embedded in prose", () => {
    const g = parseGuess('ok {"manufacturer":"TI","datasheetUrl":"u"} end');
    expect(g?.datasheetUrl).toBe("u");
  });
  it("returns null on non-JSON", () => {
    expect(parseGuess("no json")).toBeNull();
  });
});
