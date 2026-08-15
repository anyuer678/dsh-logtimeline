/**
 * DSH assembly for dsh-logtimeline: registers the `log_query` tool on the
 * Cordis context. Core logic lives in `query.ts` (framework-free).
 * @module dsh-logtimeline/runtime
 */

import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'
import type { LogQueryResult } from './query.ts'
import { runLogQuery } from './query.ts'
import { resolveConfig } from './config.ts'

/** Register the `log_query` tool on the given context. */
export function registerTool(ctx: Context, rawConfig: unknown): void {
  const cfg = resolveConfig(rawConfig)
  ctx.tools.register(defineTool({
    name: 'log_query',
    description: '按中文自然语言时间描述（如「昨天下午」「3小时前」「凌晨12点」「上周三 14:00-15:00」）过滤本地日志文件，返回匹配行、时间范围与级别统计。适合排查「某个时间点发生了什么」类问题。',
    parameters: {
      time_text: { type: 'string', required: true, description: '自然语言时间描述' },
      files: {
        type: 'array',
        items: { type: 'string' },
        description: '日志文件路径列表（绝对路径或相对工作区）',
      },
      dir: { type: 'string', description: '递归扫描的目录' },
      pattern: { type: 'string', description: '--dir 模式下的文件名 glob，默认 *.log' },
      max_lines: { type: 'number', description: '最多返回行数（默认 500；0 = 只统计不返回行）' },
      since: { type: 'string', description: '时间解析失败时的 RFC3339 绝对时间兜底' },
      timezone: { type: 'string', description: 'IANA 时区名，如 Asia/Shanghai' },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          mode: { type: 'string' },
          time_range: {
            type: 'object',
            additionalProperties: false,
            properties: {
              start: { type: 'string' },
              end: { type: 'string' },
              expr_source: { type: 'string' },
              confidence: { type: 'number' },
            },
          },
          filter: {
            type: 'object',
            additionalProperties: false,
            properties: {
              total_matched: { type: 'number' },
              truncated: { type: 'boolean' },
              time_span_found: { type: 'boolean' },
              file_stats: { type: 'object', additionalProperties: true },
              file_errors: { type: 'object', additionalProperties: true },
              stats: { type: 'object', additionalProperties: true },
              lines: {
                type: 'array',
                items: {
                  type: 'object',
                  additionalProperties: false,
                  properties: {
                    lineno: { type: 'number' },
                    timestamp: { oneOf: [{ type: 'string' }, { type: 'null' }] },
                    raw: { type: 'string' },
                  },
                },
              },
            },
          },
          analysis: {
            oneOf: [
              {
                type: 'object',
                additionalProperties: false,
                properties: {
                  summary: { type: 'string' },
                  evidence: { type: 'array', items: { type: 'string' } },
                  suggestions: { type: 'array', items: { type: 'string' } },
                  confidence: { type: 'string' },
                  tokens_used: { type: 'number' },
                },
              },
              { type: 'null' },
            ],
          },
        },
      },
      render: (_args, value) => {
        const r = value as LogQueryResult
        const lines: string[] = []
        lines.push(`时间范围：${r.time_range.start} ~ ${r.time_range.end}（原文：${r.time_range.expr_source}，置信度 ${r.time_range.confidence.toFixed(1)}）`)
        lines.push(`命中 ${r.filter.lines.length} 行（全量命中 ${r.filter.total_matched} 行${r.filter.truncated ? '，已截断' : ''}）`)
        const stats = r.filter.stats
        lines.push(`级别统计：ERROR ${stats.errors} / WARN ${stats.warns} / INFO ${stats.infos} / DEBUG ${stats.debugs}`)
        if (r.filter.file_errors && Object.keys(r.filter.file_errors).length > 0) {
          lines.push(`读取失败：${Object.entries(r.filter.file_errors).map(([k, v]) => `${k}（${v}）`).join('；')}`)
        }
        if (r.filter.lines.length > 0) {
          lines.push('--- 匹配行 ---')
          for (const line of r.filter.lines) {
            lines.push(`[${line.lineno}]${line.timestamp ? ` ${line.timestamp}` : ''} ${line.raw}`)
          }
        }
        if (r.analysis) {
          lines.push('--- 归因 ---')
          lines.push(r.analysis.summary)
          for (const e of r.analysis.evidence) lines.push(`证据：${e}`)
          for (const s of r.analysis.suggestions) lines.push(`建议：${s}`)
        }
        return [{ type: 'text', text: lines.join('\n') }]
      },
    },
    async execute(args, exec) {
      return await runLogQuery(args, cfg, exec.signal)
    },
  }))
}
