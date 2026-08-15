/**
 * Core log query logic: shells out to the vendored logtimeline Python CLI.
 * Framework-free — importable and testable without a DSH host runtime.
 * @module dsh-logtimeline/query
 */
import type { ResolvedConfig } from './config.ts';
/** Arguments accepted by the `log_query` tool. */
export interface LogQueryArgs {
    /** Chinese natural-language time expression, e.g. 「昨天下午」or「3小时前」. */
    time_text: string;
    /** Absolute or workspace-relative log file paths. */
    files?: string[];
    /** Directory to scan recursively. */
    dir?: string;
    /** Filename glob when `dir` is set (default `*.log`). */
    pattern?: string;
    /** Maximum lines returned (default 500; 0 = stats only). */
    max_lines?: number;
    /** RFC3339 absolute-time fallback when the time expression cannot be parsed. */
    since?: string;
    /** IANA timezone name, e.g. `Asia/Shanghai`. */
    timezone?: string;
}
/** Canonical result of a log query, mirroring `lq --json` output. */
export interface LogQueryResult {
    mode: 'query';
    time_range: {
        start: string;
        end: string;
        expr_source: string;
        confidence: number;
    };
    filter: {
        total_matched: number;
        truncated: boolean;
        time_span_found: boolean;
        file_stats: Record<string, number>;
        file_errors: Record<string, string>;
        stats: {
            errors: number;
            warns: number;
            infos: number;
            debugs: number;
            others: number;
        };
        lines: Array<{
            lineno: number;
            timestamp: string | null;
            raw: string;
        }>;
    };
    analysis: {
        summary: string;
        evidence: string[];
        suggestions: string[];
        confidence: string;
        tokens_used: number;
    } | null;
}
/** Run the vendored logtimeline CLI in offline mode and parse its JSON output. */
export declare function runLogQuery(args: LogQueryArgs, cfg: ResolvedConfig, signal: AbortSignal): Promise<LogQueryResult>;
