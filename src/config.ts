/**
 * Plugin configuration for dsh-logtimeline.
 * @module dsh-logtimeline/config
 */

/** Resolved plugin configuration. */
export interface ResolvedConfig {
  /** Python executable used to run the vendored logtimeline CLI. */
  pythonBin: string
  /** Hard timeout for a single log query subprocess, in milliseconds. */
  timeoutMs: number
}

/** Defaults applied when the cordis patch row carries no `config`. */
export const DEFAULT_CONFIG: ResolvedConfig = {
  pythonBin: 'python',
  timeoutMs: 120_000,
}

/** Coerce a raw cordis config row into a resolved config. */
export function resolveConfig(raw: unknown): ResolvedConfig {
  const src = (raw ?? {}) as Partial<ResolvedConfig>
  return {
    pythonBin: typeof src.pythonBin === 'string' && src.pythonBin.length > 0
      ? src.pythonBin
      : DEFAULT_CONFIG.pythonBin,
    timeoutMs: typeof src.timeoutMs === 'number' && src.timeoutMs > 0
      ? Math.floor(src.timeoutMs)
      : DEFAULT_CONFIG.timeoutMs,
  }
}
