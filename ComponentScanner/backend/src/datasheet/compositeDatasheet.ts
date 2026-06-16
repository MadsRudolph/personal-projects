// src/datasheet/compositeDatasheet.ts
import type { DatasheetProvider } from "./datasheetProvider.js";
import type { Datasheet } from "../types.js";

/**
 * Tries each provider in order, returning the first non-null datasheet.
 * A provider that throws is treated as a miss so the next one still runs.
 */
export class CompositeDatasheetProvider implements DatasheetProvider {
  constructor(private providers: DatasheetProvider[]) {}

  async resolve(partNumber: string): Promise<Datasheet | null> {
    for (const provider of this.providers) {
      try {
        const result = await provider.resolve(partNumber);
        if (result) return result;
      } catch {
        // ignore and fall through to the next provider
      }
    }
    return null;
  }
}
