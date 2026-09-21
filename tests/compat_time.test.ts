/**
 * Compatibility / time-expression contract tests for A+ review.
 * Uses the real vendored Python CLI via runLogQuery against fixtures/demo.log.
 */
import { describe, expect, it } from 'vitest'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { runLogQuery } from '../src/query.ts'
import { resolveConfig } from '../src/config.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const fixture = path.resolve(__dirname, 'fixtures', 'demo.log')
const cfg = resolveConfig({})

describe('time expression contract (COMPATIBILITY.md)', () => {
  it('T06 absolute date 2026-07-03 matches fixture day', async () => {
    const r = await runLogQuery(
      { time_text: '2026-07-03', files: [fixture], max_lines: 50 },
      cfg,
      new AbortController().signal,
    )
    expect(r.mode).toBe('query')
    expect(r.filter.total_matched).toBeGreaterThan(0)
    expect(r.time_range.expr_source).toContain('2026-07-03')
  })

  it('T15 unsupported free text fails closed via since fallback or empty — never silent full dump', async () => {
    const r = await runLogQuery(
      {
        time_text: '完全无法理解的描述',
        files: [fixture],
        since: '2026-07-03T09:00:00',
        max_lines: 200,
      },
      cfg,
      new AbortController().signal,
    )
    expect(r.mode).toBe('query')
    // with since fallback, window is constrained — must not return unrelated days unbounded
    expect(r.filter.total_matched).toBeLessThanOrEqual(25)
  })

  it('caps returned lines even when window is large (max_lines safety)', async () => {
    const r = await runLogQuery(
      { time_text: '2026-07-03', files: [fixture], max_lines: 2 },
      cfg,
      new AbortController().signal,
    )
    expect(r.filter.lines.length).toBeLessThanOrEqual(2)
  })

  it('exports runLogQuery for host assembly', async () => {
    const mod = await import('../src/query.ts')
    expect(typeof mod.runLogQuery).toBe('function')
  })
})
