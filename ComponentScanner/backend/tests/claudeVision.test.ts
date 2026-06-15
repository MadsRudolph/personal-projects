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
});
