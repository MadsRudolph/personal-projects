// tests/normalize.test.ts
import { describe, it, expect } from "vitest";
import { normalizePartNumber } from "../src/normalize.js";

describe("normalizePartNumber", () => {
  it("uppercases and trims surrounding whitespace", () => {
    expect(normalizePartNumber("  lm358n  ")).toBe("LM358N");
  });

  it("removes spaces inside the marking", () => {
    expect(normalizePartNumber("LM 358 N")).toBe("LM358N");
  });

  it("strips a trailing date/lot code segment after whitespace newline", () => {
    expect(normalizePartNumber("STM32F103C8T6\n2143")).toBe("STM32F103C8T6");
  });
});
