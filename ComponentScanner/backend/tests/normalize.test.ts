// tests/normalize.test.ts
import { describe, it, expect } from "vitest";
import { normalizePartNumber, looksLikePartNumber } from "../src/normalize.js";

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

describe("looksLikePartNumber", () => {
  it("accepts tokens with letters and digits of reasonable length", () => {
    expect(looksLikePartNumber("LM358")).toBe(true);
    expect(looksLikePartNumber("STM32F103C8T6")).toBe(true);
  });

  it("rejects pure words and very short tokens", () => {
    expect(looksLikePartNumber("HELLO")).toBe(false);
    expect(looksLikePartNumber("A1")).toBe(false);
  });
});
