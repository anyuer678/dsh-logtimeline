/**
 * Plugin configuration for dsh-logtimeline.
 * @module dsh-logtimeline/config
 */
/** Resolved plugin configuration. */
export interface ResolvedConfig {
    /** Python executable used to run the vendored logtimeline CLI. */
    pythonBin: string;
    /** Hard timeout for a single log query subprocess, in milliseconds. */
    timeoutMs: number;
}
/** Defaults applied when the cordis patch row carries no `config`. */
export declare const DEFAULT_CONFIG: ResolvedConfig;
/** Coerce a raw cordis config row into a resolved config. */
export declare function resolveConfig(raw: unknown): ResolvedConfig;
