// src/types.ts
import { z } from "zod";

export const CandidateSchema = z.object({
  partNumber: z.string().min(1),
  manufacturer: z.string().optional(),
  packageType: z.string().optional(),
  confidence: z.number().min(0).max(1),
});
export type Candidate = z.infer<typeof CandidateSchema>;

export const KeySpecSchema = z.object({
  name: z.string(),
  value: z.string(),
});
export type KeySpec = z.infer<typeof KeySpecSchema>;

export const DatasheetSchema = z.object({
  partNumber: z.string().min(1),
  manufacturer: z.string(),
  datasheetUrl: z.string().url(),
  keySpecs: z.array(KeySpecSchema).default([]),
});
export type Datasheet = z.infer<typeof DatasheetSchema>;

export type IdentifyMode = "single" | "shelf";
