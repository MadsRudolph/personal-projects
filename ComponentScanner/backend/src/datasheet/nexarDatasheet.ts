// src/datasheet/nexarDatasheet.ts
import type { DatasheetProvider } from "./datasheetProvider.js";
import type { Datasheet, KeySpec } from "../types.js";

export interface NexarConfig {
  clientId: string;
  clientSecret: string;
  endpoint?: string; // defaults to Nexar GraphQL
  tokenEndpoint?: string; // defaults to Nexar OAuth token endpoint
  maxSpecs?: number; // cap key specs returned
  nowMs?: () => number; // injectable clock for token-expiry tests
}

const QUERY = `
query Search($q: String!) {
  supSearchMpn(q: $q, limit: 1) {
    results {
      part {
        mpn
        manufacturer { name }
        bestDatasheet { url }
        specs { attribute { name } displayValue }
      }
    }
  }
}`;

interface NexarPart {
  mpn: string;
  manufacturer: { name: string } | null;
  bestDatasheet: { url: string } | null;
  specs: Array<{ attribute: { name: string }; displayValue: string }> | null;
}

interface CachedToken {
  value: string;
  expiresAtMs: number;
}

/**
 * Resolves datasheets via Nexar's Supply GraphQL API. Nexar uses OAuth2
 * client-credentials: we exchange the Client ID + Secret for a short-lived
 * access token, cache it, and refresh automatically before it expires.
 */
export class NexarDatasheetProvider implements DatasheetProvider {
  private endpoint: string;
  private tokenEndpoint: string;
  private maxSpecs: number;
  private now: () => number;
  private cachedToken: CachedToken | null = null;

  constructor(
    private config: NexarConfig,
    private fetchFn: typeof fetch = fetch,
  ) {
    this.endpoint = config.endpoint ?? "https://api.nexar.com/graphql";
    this.tokenEndpoint =
      config.tokenEndpoint ?? "https://identity.nexar.com/connect/token";
    this.maxSpecs = config.maxSpecs ?? 8;
    this.now = config.nowMs ?? (() => Date.now());
  }

  /** Get a valid bearer token, fetching/refreshing via client-credentials as needed. */
  private async getToken(): Promise<string> {
    const now = this.now();
    if (this.cachedToken && now < this.cachedToken.expiresAtMs) {
      return this.cachedToken.value;
    }

    const res = await this.fetchFn(this.tokenEndpoint, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "client_credentials",
        client_id: this.config.clientId,
        client_secret: this.config.clientSecret,
      }).toString(),
    });

    if (!res.ok) {
      throw new Error(`nexar token error: HTTP ${res.status}`);
    }

    const json = (await res.json()) as {
      access_token: string;
      expires_in?: number;
    };
    if (!json.access_token) {
      throw new Error("nexar token error: no access_token in response");
    }

    // Refresh 60s early to avoid edge-of-expiry failures. Default 1h if unspecified.
    const ttlSeconds = (json.expires_in ?? 3600) - 60;
    this.cachedToken = {
      value: json.access_token,
      expiresAtMs: now + Math.max(0, ttlSeconds) * 1000,
    };
    return json.access_token;
  }

  async resolve(partNumber: string): Promise<Datasheet | null> {
    const token = await this.getToken();

    const res = await this.fetchFn(this.endpoint, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query: QUERY, variables: { q: partNumber } }),
    });

    if (!res.ok) {
      throw new Error(`datasheet provider error: HTTP ${res.status}`);
    }

    const body = (await res.json()) as {
      data?: { supSearchMpn?: { results?: Array<{ part: NexarPart }> } };
    };

    const part = body.data?.supSearchMpn?.results?.[0]?.part;
    if (!part) return null;
    const url = part.bestDatasheet?.url;
    if (!url) return null;

    const keySpecs: KeySpec[] = (part.specs ?? [])
      .slice(0, this.maxSpecs)
      .map((s) => ({ name: s.attribute.name, value: s.displayValue }));

    return {
      partNumber: part.mpn || partNumber,
      manufacturer: part.manufacturer?.name ?? "Unknown",
      datasheetUrl: url,
      keySpecs,
    };
  }
}
