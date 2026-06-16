// src/config.ts
export interface AppConfig {
  anthropicApiKey: string;
  claudeModel: string;
  nexarClientId: string;
  nexarClientSecret: string;
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
    claudeModel: env.CLAUDE_MODEL ?? "claude-sonnet-4-6",
    nexarClientId: required(env, "NEXAR_CLIENT_ID"),
    nexarClientSecret: required(env, "NEXAR_CLIENT_SECRET"),
    rateLimit: Number(env.RATE_LIMIT ?? "60"),
    rateWindowSeconds: Number(env.RATE_WINDOW_SECONDS ?? "60"),
    identifyCacheTtl: Number(env.IDENTIFY_CACHE_TTL ?? "600"),
    datasheetCacheTtl: Number(env.DATASHEET_CACHE_TTL ?? "86400"),
  };
}
