// tests/config.test.ts
import { describe, it, expect } from "vitest";
import { loadConfig } from "../src/config.js";

describe("loadConfig", () => {
  it("parses a complete environment", () => {
    const cfg = loadConfig({
      ANTHROPIC_API_KEY: "sk-x",
      CLAUDE_MODEL: "claude-test",
      NEXAR_CLIENT_ID: "cid",
      NEXAR_CLIENT_SECRET: "csecret",
      RATE_LIMIT: "30",
    });
    expect(cfg.anthropicApiKey).toBe("sk-x");
    expect(cfg.claudeModel).toBe("claude-test");
    expect(cfg.nexarClientId).toBe("cid");
    expect(cfg.nexarClientSecret).toBe("csecret");
    expect(cfg.rateLimit).toBe(30);
  });

  it("applies defaults for optional values", () => {
    const cfg = loadConfig({
      ANTHROPIC_API_KEY: "sk-x",
      NEXAR_CLIENT_ID: "cid",
      NEXAR_CLIENT_SECRET: "csecret",
    });
    expect(cfg.claudeModel).toMatch(/claude/);
    expect(cfg.rateLimit).toBeGreaterThan(0);
  });

  it("throws when a required secret is missing", () => {
    expect(() =>
      loadConfig({ NEXAR_CLIENT_ID: "cid", NEXAR_CLIENT_SECRET: "csecret" }),
    ).toThrow(/ANTHROPIC_API_KEY/);
  });

  it("throws when the Nexar client id is missing", () => {
    expect(() => loadConfig({ ANTHROPIC_API_KEY: "sk-x" })).toThrow(
      /NEXAR_CLIENT_ID/,
    );
  });
});
