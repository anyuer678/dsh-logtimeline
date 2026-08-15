/**
 * dsh-logtimeline — LogTimeline for DeepSeek Harness.
 * Query local log files with Chinese natural-language time expressions.
 * @module dsh-logtimeline
 */
import { registerTool } from "./runtime.js";
/** Cordis plugin name; keep this stable after publishing. */
export const name = 'dsh-logtimeline';
/** The tool registry must be ready before this plugin is applied. */
export const inject = ['tools'];
export { resolveConfig } from "./config.js";
export { registerTool } from "./runtime.js";
export { runLogQuery } from "./query.js";
/** Register the `log_query` tool with the plugin's own config row. */
export function apply(ctx, config) {
    registerTool(ctx, config);
}
//# sourceMappingURL=index.js.map