// tests/claudeVision.test.ts
import { describe, it, expect, vi } from "vitest";
import { ClaudeVisionProvider } from "../src/vision/claudeVision.js";

function fakeFetchReturning(jsonText: string) {
  return vi.fn(async () =>
    new Response(
      JSON.stringify({ content: [{ type: "text", text: jsonText }] }),
      { status: 200 },
    ),
  );
}

describe("ClaudeVisionProvider", () => {
  it("parses candidates from the model's JSON reply", async () => {
    const fetchFn = fakeFetchReturning(
      JSON.stringify({
        candidates: [
          { partNumber: "lm358n", manufacturer: "TI", confidence: 0.9 },
        ],
      }),
    );
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );

    const result = await provider.identify("BASE64", "image/jpeg", "single");

    expect(result[0]?.partNumber).toBe("LM358N"); // normalized
    expect(fetchFn).toHaveBeenCalledOnce();
  });

  it("returns an empty list when the model returns no candidates", async () => {
    const fetchFn = fakeFetchReturning(JSON.stringify({ candidates: [] }));
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );
    const result = await provider.identify("BASE64", "image/jpeg", "shelf");
    expect(result).toEqual([]);
  });

  it("throws on a non-OK HTTP response", async () => {
    const fetchFn = vi.fn(async () => new Response("nope", { status: 500 }));
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );
    await expect(
      provider.identify("BASE64", "image/jpeg", "single"),
    ).rejects.toThrow(/vision provider/i);
  });

  it("parses JSON when surrounded by prose text", async () => {
    const fetchFn = fakeFetchReturning(
      'Sure! Here is the result: {"candidates":[{"partNumber":"NE555","confidence":0.8}]} Hope that helps!',
    );
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );
    const result = await provider.identify("BASE64", "image/jpeg", "single");
    expect(result[0]?.partNumber).toBe("NE555");
  });

  it("parses JSON from a fenced code block", async () => {
    const fetchFn = fakeFetchReturning(
      '```json\n{"candidates":[{"partNumber":"ATmega328P","confidence":0.95}]}\n```',
    );
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );
    const result = await provider.identify("BASE64", "image/jpeg", "single");
    expect(result[0]?.partNumber).toBe("ATMEGA328P");
  });

  it("returns [] without throwing for a completely non-JSON reply", async () => {
    const fetchFn = fakeFetchReturning("I cannot identify any components in this image.");
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );
    const result = await provider.identify("BASE64", "image/jpeg", "single");
    expect(result).toEqual([]);
  });

  it("deduplicates candidates by partNumber keeping highest confidence", async () => {
    const fetchFn = fakeFetchReturning(
      JSON.stringify({
        candidates: [
          { partNumber: "lm358n", manufacturer: "TI", confidence: 0.7 },
          { partNumber: "LM358N", manufacturer: "TI", confidence: 0.95 },
        ],
      }),
    );
    const provider = new ClaudeVisionProvider(
      { apiKey: "test", model: "claude-x" },
      fetchFn as unknown as typeof fetch,
    );
    const result = await provider.identify("BASE64", "image/jpeg", "single");
    expect(result).toHaveLength(1);
    expect(result[0]?.partNumber).toBe("LM358N");
    expect(result[0]?.confidence).toBe(0.95);
  });
});
