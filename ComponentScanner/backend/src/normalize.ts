// src/normalize.ts

/** Collapse a raw marking into a single-line canonical token. */
export function normalizePartNumber(raw: string): string {
  const firstLine = raw.split(/[\r\n]+/)[0] ?? "";
  return firstLine.replace(/\s+/g, "").toUpperCase();
}
