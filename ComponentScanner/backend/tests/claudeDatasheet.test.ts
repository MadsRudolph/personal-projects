// tests/claudeDatasheet.test.ts
import { describe, it, expect, vi } from "vitest";
import {
  ClaudeDatasheetProvider,
  parseGuess,
  looksLikePdfUrl,
} from "../src/datasheet/claudeDatasheet.js";

/** Mock the Anthropic Messages call; returns the given JSON as the model text. */
function anthropicFetch(guessJson: string) {
  return vi.fn(
    async () =>
      new Response(
        JSON.stringify({ content: [{ type: "text", text: guessJson }] }),
        { status: 200 },
      ),
  );
}

function provider(fetchFn: ReturnType<typeof anthropicFetch>) {
  return new ClaudeDatasheetProvider(
    { apiKey: "test", model: "claude-x", enableWebSearch: false },
    fetchFn as unknown as typeof fetch,
  );
}

describe("ClaudeDatasheetProvider", () => {
  it("resolves a manufacturer direct-PDF datasheet", async () => {
    const fetchFn = anthropicFetch(
      JSON.stringify({
        manufacturer: "Texas Instruments",
        datasheetUrl: "https://www.ti.com/lit/ds/symlink/lm358.pdf",
      }),
    );
    const r = await provider(fetchFn).resolve("LM358N");
    expect(r?.manufacturer).toBe("Texas Instruments");
    expect(r?.datasheetUrl).toBe("https://www.ti.com/lit/ds/symlink/lm358.pdf");
  });

  it("accepts a distributor-mirror .pdf URL (for vendors that block downloads)", async () => {
    const fetchFn = anthropicFetch(
      JSON.stringify({
        manufacturer: "STMicroelectronics",
        datasheetUrl: "https://www.mouser.com/datasheet/2/389/l7805cv-1849632.pdf",
      }),
    );
    const r = await provider(fetchFn).resolve("L7805CV");
    expect(r?.datasheetUrl).toContain(".pdf");
    expect(r?.manufacturer).toBe("STMicroelectronics");
  });

  it("returns null when the model finds no datasheet", async () => {
    const fetchFn = anthropicFetch(
      JSON.stringify({ manufacturer: null, datasheetUrl: null }),
    );
    expect(await provider(fetchFn).resolve("NOPART")).toBeNull();
  });

  it("rejects a URL that is not a direct PDF", async () => {
    const fetchFn = anthropicFetch(
      JSON.stringify({ manufacturer: "X", datasheetUrl: "https://x/product/page" }),
    );
    expect(await provider(fetchFn).resolve("X")).toBeNull();
  });
});

describe("looksLikePdfUrl", () => {
  it("accepts http(s) URLs ending in .pdf", () => {
    expect(looksLikePdfUrl("https://www.ti.com/lit/ds/symlink/lm358.pdf")).toBe(true);
    expect(looksLikePdfUrl("https://www.mouser.com/datasheet/2/389/x-123.pdf")).toBe(true);
  });
  it("rejects non-pdf paths and bad URLs", () => {
    expect(looksLikePdfUrl("https://www.st.com/product/l7805")).toBe(false);
    expect(looksLikePdfUrl("not a url")).toBe(false);
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
