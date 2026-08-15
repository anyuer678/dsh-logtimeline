/**
 * Plugin configuration for dsh-logtimeline.
 * @module dsh-logtimeline/config
 */
/** Defaults applied when the cordis patch row carries no `config`. */
export const DEFAULT_CONFIG = {
    pythonBin: 'python',
    timeoutMs: 120_000,
};
/** Coerce a raw cordis config row into a resolved config. */
export function resolveConfig(raw) {
    const src = (raw ?? {});
    return {
        pythonBin: typeof src.pythonBin === 'string' && src.pythonBin.length > 0
            ? src.pythonBin
            : DEFAULT_CONFIG.pythonBin,
        timeoutMs: typeof src.timeoutMs === 'number' && src.timeoutMs > 0
            ? Math.floor(src.timeoutMs)
            : DEFAULT_CONFIG.timeoutMs,
    };
}
//# sourceMappingURL=config.js.map