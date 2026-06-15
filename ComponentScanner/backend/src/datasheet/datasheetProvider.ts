// src/datasheet/datasheetProvider.ts
import type { Datasheet } from "../types.js";

export interface DatasheetProvider {
  /** Returns null when no datasheet can be resolved. */
  resolve(partNumber: string): Promise<Datasheet | null>;
}
