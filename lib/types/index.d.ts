/**
 * dsh-logtimeline — LogTimeline for DeepSeek Harness.
 * Query local log files with Chinese natural-language time expressions.
 * @module dsh-logtimeline
 */
import type { Context } from '@deepseek-ai/cordis';
/** Cordis plugin name; keep this stable after publishing. */
export declare const name = "dsh-logtimeline";
/** The tool registry must be ready before this plugin is applied. */
export declare const inject: string[];
export { resolveConfig } from './config.ts';
export type { ResolvedConfig } from './config.ts';
export { registerTool } from './runtime.ts';
export { runLogQuery } from './query.ts';
export type { LogQueryArgs, LogQueryResult } from './query.ts';
/** Register the `log_query` tool with the plugin's own config row. */
export declare function apply(ctx: Context, config?: unknown): void;
