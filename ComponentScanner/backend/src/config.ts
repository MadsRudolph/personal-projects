// src/config.ts
export interface AppConfig {
  anthropicApiKey: string;
  claudeModel: string;
  nexarToken: string;
  rateLimit: number; // requests per window
  rateWindowSeconds: number;
  identifyCacheTtl: number;
  datasheetCacheTtl: number;
}

type Env = Record<string, string | undefined>;

function required(env: Env, key: string): string {
  const v = env[key];
  if (!v) throw new Error(`missing required env var: ${key}`);
  return v;
}

export function loadConfig(env: Env): AppConfig {
  return {
    anthropicApiKey: required(env, "ANTHROPIC_API_KEY"),
    claudeModel: env.CLAUDE_MODEL ?? "claude-opus-4-8",
    nexarToken: required(env, "NEXAR_TOKEN"),
    rateLimit: Number(env.RATE_LIMIT ?? "60"),
    rateWindowSeconds: Number(env.RATE_WINDOW_SECONDS ?? "60"),
    identifyCacheTtl: Number(env.IDENTIFY_CACHE_TTL ?? "600"),
    datasheetCacheTtl: Number(env.DATASHEET_CACHE_TTL ?? "86400"),
  };
}
