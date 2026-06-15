// src/normalize.ts

/** Collapse a raw marking into a single-line canonical token. */
export function normalizePartNumber(raw: string): string {
  const firstLine = raw.split(/[\r\n]+/)[0] ?? "";
  return firstLine.replace(/\s+/g, "").toUpperCase();
}

/**
 * Heuristic: a plausible part number has both letters and digits and is
 * between 3 and 24 characters. Filters out plain words and noise tokens.
 */
export function looksLikePartNumber(token: string): boolean {
  const t = token.trim();
  if (t.length < 3 || t.length > 24) return false;
  const hasLetter = /[A-Za-z]/.test(t);
  const hasDigit = /[0-9]/.test(t);
  return hasLetter && hasDigit;
}
