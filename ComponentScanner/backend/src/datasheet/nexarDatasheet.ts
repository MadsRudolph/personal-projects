// src/datasheet/nexarDatasheet.ts
import type { DatasheetProvider } from "./datasheetProvider.js";
import type { Datasheet, KeySpec } from "../types.js";

export interface NexarConfig {
  token: string;
  endpoint?: string; // defaults to Nexar GraphQL
  maxSpecs?: number; // cap key specs returned
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

export class NexarDatasheetProvider implements DatasheetProvider {
  private endpoint: string;
  private maxSpecs: number;

  constructor(
    private config: NexarConfig,
    private fetchFn: typeof fetch = fetch,
  ) {
    this.endpoint = config.endpoint ?? "https://api.nexar.com/graphql";
    this.maxSpecs = config.maxSpecs ?? 8;
  }

  async resolve(partNumber: string): Promise<Datasheet | null> {
    const res = await this.fetchFn(this.endpoint, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${this.config.token}`,
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
