// src/vision/visionProvider.ts
import type { Candidate, IdentifyMode } from "../types.js";

export interface VisionProvider {
  /**
   * @param imageBase64 raw base64 (no data: prefix)
   * @param mimeType e.g. "image/jpeg"
   */
  identify(
    imageBase64: string,
    mimeType: string,
    mode: IdentifyMode,
  ): Promise<Candidate[]>;
}
