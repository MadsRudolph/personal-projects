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
