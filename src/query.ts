/**
 * Core log query logic: shells out to the vendored logtimeline Python CLI.
 * Framework-free — importable and testable without a DSH host runtime.
 * @module dsh-logtimeline/query
 */

import { execFile } from 'node:child_process'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { ResolvedConfig } from './config.ts'

const PACKAGE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const LQ_SCRIPT = path.join(PACKAGE_DIR, 'python', 'lq.py')

/** Arguments accepted by the `log_query` tool. */
export interface LogQueryArgs {
  /** Chinese natural-language time expression, e.g. 「昨天下午」or「3小时前」. */
  time_text: string
  /** Absolute or workspace-relative log file paths. */
  files?: string[]
  /** Directory to scan recursively. */
  dir?: string
  /** Filename glob when `dir` is set (default `*.log`). */
  pattern?: string
  /** Maximum lines returned (default 500; 0 = stats only). */
  max_lines?: number
  /** RFC3339 absolute-time fallback when the time expression cannot be parsed. */
  since?: string
  /** IANA timezone name, e.g. `Asia/Shanghai`. */
  timezone?: string
}

/** Canonical result of a log query, mirroring `lq --json` output. */
export interface LogQueryResult {
  mode: 'query'
  time_range: {
    start: string
    end: string
    expr_source: string
    confidence: number
  }
  filter: {
    total_matched: number
    truncated: boolean
    time_span_found: boolean
    file_stats: Record<string, number>
    file_errors: Record<string, string>
    stats: { errors: number; warns: number; infos: number; debugs: number }
    lines: Array<{ lineno: number; timestamp: string | null; raw: string }>
  }
  analysis: {
    summary: string
    evidence: string[]
    suggestions: string[]
    confidence: string
    tokens_used: number
  } | null
}

/** Run the vendored logtimeline CLI in offline mode and parse its JSON output. */
export async function runLogQuery(
  args: LogQueryArgs,
  cfg: ResolvedConfig,
  signal: AbortSignal,
): Promise<LogQueryResult> {
  if (!args.time_text || args.time_text.trim().length === 0) {
    throw new Error('log_query 需要 time_text（自然语言时间描述），如「昨天下午」')
  }
  if ((!args.files || args.files.length === 0) && !args.dir) {
    throw new Error('log_query 至少需要一个输入源：files（文件列表）或 dir（目录）')
  }
  const script = await assertLqScript()
  const argv: string[] = [script, args.time_text, '--json', '--no-llm']
  if (args.files && args.files.length > 0) {
    argv.push('--files', ...args.files)
  }
  if (args.dir) argv.push('--dir', args.dir)
  if (args.pattern) argv.push('--pattern', args.pattern)
  if (args.max_lines !== undefined) argv.push('--max-lines', String(Math.max(0, Math.floor(args.max_lines))))
  if (args.since) argv.push('--since', args.since)
  if (args.timezone) argv.push('--timezone', args.timezone)

  const { stdout, stderr } = await execFileAsync(cfg.pythonBin, argv, {
    signal,
    timeout: cfg.timeoutMs,
    maxBuffer: 16 * 1024 * 1024,
    windowsHide: true,
  })

  const text = stdout.trim()
  if (!text) {
    throw new Error(`log_query 无输出（stderr：${trimTail(stderr)}）`)
  }
  try {
    return JSON.parse(text) as LogQueryResult
  } catch (err) {
    throw new Error(`log_query 输出不是合法 JSON：${err instanceof Error ? err.message : String(err)}`)
  }
}

/** Promisified execFile that surfaces the exit code as an error. */
function execFileAsync(
  file: string,
  args: string[],
  opts: { signal: AbortSignal; timeout: number; maxBuffer: number; windowsHide: boolean },
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(file, args, opts, (error, stdout, stderr) => {
      if (error) {
        // Preserve the child's own stderr (Chinese diagnostics) as the message.
        const detail = trimTail(stderr)
        const message = detail || error.message
        reject(new Error(`log_query 执行失败（exit ${(error as NodeJS.ErrnoException).code ?? '?'}）：${message}`))
        return
      }
      resolve({ stdout, stderr })
    })
  })
}

/** Locate the vendored lq.py and fail loudly with a fix hint when missing. */
async function assertLqScript(): Promise<string> {
  try {
    await fs.access(LQ_SCRIPT)
    return LQ_SCRIPT
  } catch {
    throw new Error(`未找到 vendored logtimeline 脚本：${LQ_SCRIPT}（检查包安装是否完整）`)
  }
}

function trimTail(text: string): string {
  const t = text.trim()
  return t.length > 400 ? `${t.slice(-400)}…` : t
}
