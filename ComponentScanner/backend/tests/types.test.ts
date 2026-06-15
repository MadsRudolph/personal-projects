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
