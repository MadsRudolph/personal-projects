// tests/nexarDatasheet.test.ts
import { describe, it, expect, vi } from "vitest";
import { NexarDatasheetProvider } from "../src/datasheet/nexarDatasheet.js";

/**
 * A fake fetch that routes the OAuth token request and the GraphQL request.
 * `graphql` is the JSON body returned for the GraphQL POST.
 */
function routerFetch(opts: {
  graphql: unknown;
  expiresIn?: number;
  graphqlStatus?: number;
}) {
  const fn = vi.fn(async (url: string | URL | Request, _init?: RequestInit) => {
    const u = typeof url === "string" ? url : url.toString();
    if (u.includes("/connect/token")) {
      return new Response(
        JSON.stringify({
          access_token: "fake-access-token",
          expires_in: opts.expiresIn ?? 3600,
          token_type: "Bearer",
        }),
        { status: 200 },
      );
    }
    return new Response(JSON.stringify(opts.graphql), {
      status: opts.graphqlStatus ?? 200,
    });
  });
  return fn;
}

const ONE_RESULT = {
  data: {
    supSearchMpn: {
      results: [
        {
          part: {
            mpn: "LM358N",
            manufacturer: { name: "Texas Instruments" },
            bestDatasheet: { url: "https://www.ti.com/lit/ds/symlink/lm358.pdf" },
            specs: [
              { attribute: { name: "Supply Voltage" }, displayValue: "3-32 V" },
            ],
          },
        },
      ],
    },
  },
};

function makeProvider(fetchFn: ReturnType<typeof routerFetch>, nowMs?: () => number) {
  return new NexarDatasheetProvider(
    { clientId: "cid", clientSecret: "csecret", nowMs },
    fetchFn as unknown as typeof fetch,
  );
}

describe("NexarDatasheetProvider", () => {
  it("fetches a token then resolves a datasheet for a known part", async () => {
    const fetchFn = routerFetch({ graphql: ONE_RESULT });
    const provider = makeProvider(fetchFn);

    const result = await provider.resolve("LM358N");

    expect(result?.manufacturer).toBe("Texas Instruments");
    expect(result?.datasheetUrl).toContain(".pdf");
    expect(result?.keySpecs[0]?.name).toBe("Supply Voltage");
    // one token call + one graphql call
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it("caches the token across calls (token fetched once)", async () => {
    const fetchFn = routerFetch({ graphql: ONE_RESULT });
    const provider = makeProvider(fetchFn);

    await provider.resolve("LM358N");
    await provider.resolve("LM358N");

    const tokenCalls = fetchFn.mock.calls.filter(([u]) =>
      String(u).includes("/connect/token"),
    );
    expect(tokenCalls).toHaveLength(1); // token reused, only graphql called again
    expect(fetchFn).toHaveBeenCalledTimes(3); // 1 token + 2 graphql
  });

  it("refreshes the token after it expires", async () => {
    let now = 1_000_000;
    const fetchFn = routerFetch({ graphql: ONE_RESULT, expiresIn: 120 });
    const provider = makeProvider(fetchFn, () => now);

    await provider.resolve("LM358N"); // token valid until now + (120-60)s
    now += 61_000; // advance past the (early-refreshed) expiry
    await provider.resolve("LM358N");

    const tokenCalls = fetchFn.mock.calls.filter(([u]) =>
      String(u).includes("/connect/token"),
    );
    expect(tokenCalls).toHaveLength(2);
  });

  it("throws when the token request fails", async () => {
    const fetchFn = vi.fn(async () => new Response("nope", { status: 401 }));
    const provider = new NexarDatasheetProvider(
      { clientId: "cid", clientSecret: "bad" },
      fetchFn as unknown as typeof fetch,
    );
    await expect(provider.resolve("LM358N")).rejects.toThrow(/token error/i);
  });

  it("returns null when there are no results", async () => {
    const fetchFn = routerFetch({
      graphql: { data: { supSearchMpn: { results: [] } } },
    });
    const provider = makeProvider(fetchFn);
    expect(await provider.resolve("NOPART")).toBeNull();
  });

  it("returns null when the part has no datasheet URL", async () => {
    const fetchFn = routerFetch({
      graphql: {
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
      },
    });
    const provider = makeProvider(fetchFn);
    expect(await provider.resolve("X")).toBeNull();
  });
});
