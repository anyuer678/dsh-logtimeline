/**
 * dsh-logtimeline — LogTimeline for DeepSeek Harness.
 * Query local log files with Chinese natural-language time expressions.
 * @module dsh-logtimeline
 */

import type { Context } from '@deepseek-ai/cordis'
import { registerTool } from './runtime.ts'

/** Cordis plugin name; keep this stable after publishing. */
export const name = 'dsh-logtimeline'

/** The tool registry must be ready before this plugin is applied. */
export const inject: string[] = ['tools']

export { resolveConfig } from './config.ts'
export type { ResolvedConfig } from './config.ts'
export { registerTool } from './runtime.ts'
export { runLogQuery } from './query.ts'
export type { LogQueryArgs, LogQueryResult } from './query.ts'

/** Register the `log_query` tool with the plugin's own config row. */
export function apply(ctx: Context, config?: unknown): void {
  registerTool(ctx, config)
}
