/**
 * DSH assembly for dsh-logtimeline: registers the `log_query` tool on the
 * Cordis context. Core logic lives in `query.ts` (framework-free).
 * @module dsh-logtimeline/runtime
 */
import type { Context } from '@deepseek-ai/cordis';
/** Register the `log_query` tool on the given context. */
export declare function registerTool(ctx: Context, rawConfig: unknown): void;
