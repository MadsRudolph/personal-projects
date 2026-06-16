// tests/compositeDatasheet.test.ts
import { describe, it, expect, vi } from "vitest";
import { CompositeDatasheetProvider } from "../src/datasheet/compositeDatasheet.js";
import type { DatasheetProvider } from "../src/datasheet/datasheetProvider.js";
import type { Datasheet } from "../src/types.js";

const SHEET: Datasheet = {
  partNumber: "LM358N",
  manufacturer: "Texas Instruments",
  datasheetUrl: "https://www.ti.com/lit/ds/symlink/lm358.pdf",
  keySpecs: [],
};

function provider(impl: () => Promise<Datasheet | null>): DatasheetProvider {
  return { resolve: vi.fn(impl) };
}

describe("CompositeDatasheetProvider", () => {
  it("returns the first non-null result and skips later providers", async () => {
    const second = provider(async () => SHEET);
    const composite = new CompositeDatasheetProvider([
      provider(async () => null),
      second,
      provider(async () => {
        throw new Error("should not be called");
      }),
    ]);
    const r = await composite.resolve("LM358N");
    expect(r?.manufacturer).toBe("Texas Instruments");
  });

  it("falls through when a provider throws", async () => {
    const composite = new CompositeDatasheetProvider([
      provider(async () => {
        throw new Error("nexar boom");
      }),
      provider(async () => SHEET),
    ]);
    expect((await composite.resolve("LM358N"))?.partNumber).toBe("LM358N");
  });

  it("returns null when all providers miss", async () => {
    const composite = new CompositeDatasheetProvider([
      provider(async () => null),
      provider(async () => null),
    ]);
    expect(await composite.resolve("NOPART")).toBeNull();
  });
});
