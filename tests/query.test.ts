/**
 * Integration tests for the core log query logic.
 * Runs the real vendored Python CLI against a small fixture log.
 */
import { describe, expect, it } from 'vitest'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { runLogQuery } from '../src/query.ts'
import { resolveConfig } from '../src/config.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const fixture = path.resolve(__dirname, 'fixtures', 'demo.log')
const cfg = resolveConfig({})

describe('runLogQuery (real vendored Python)', () => {
  it('parses an absolute date and returns matched lines with stats', async () => {
    const r = await runLogQuery(
      { time_text: '2026-07-03', files: [fixture], max_lines: 200 },
      cfg,
      new AbortController().signal,
    )
    expect(r.mode).toBe('query')
    expect(r.time_range.expr_source).toBe('2026-07-03')
    expect(r.time_range.confidence).toBeGreaterThanOrEqual(1)
    expect(r.filter.total_matched).toBe(25)
    expect(r.filter.lines.length).toBe(25)
    expect(r.filter.stats.errors).toBe(13)
    expect(r.filter.lines[0]).toMatchObject({
      lineno: 1,
      timestamp: '2026-07-03 09:15:00',
    })
  })

  it('max_lines=0 returns stats only', async () => {
    const r = await runLogQuery(
      { time_text: '7月3日', files: [fixture], max_lines: 0 },
      cfg,
      new AbortController().signal,
    )
    expect(r.filter.total_matched).toBe(25)
    expect(r.filter.lines.length).toBe(0)
  })

  it('max_lines truncates returned lines but keeps total_matched', async () => {
    const r = await runLogQuery(
      { time_text: '2026-07-03', files: [fixture], max_lines: 3 },
      cfg,
      new AbortController().signal,
    )
    expect(r.filter.truncated).toBe(true)
    expect(r.filter.lines.length).toBe(3)
    expect(r.filter.total_matched).toBe(25)
  })

  it('falls back to --since when the time text is unparsable', async () => {
    const r = await runLogQuery(
      { time_text: '完全无法理解的描述', files: [fixture], since: '2026-07-03T09:00:00' },
      cfg,
      new AbortController().signal,
    )
    // naive 墙钟时间：时区后缀被归一化，不抛 offset-naive vs aware 错误
    expect(r.time_range.start).toBe('2026-07-03 09:00:00')
  })

  it('returns an empty result when nothing matches (upstream exit 2, not an error)', async () => {
    // 上游 lq.py 在 0 命中时退出码为 2，但 stdout 仍是合法 JSON——必须作为成功结果返回
    // 用全量明确日期时间戳的 fixture：查询 2026-01-01 必然 0 命中
    const dated = path.resolve(__dirname, 'fixtures', 'dated.log')
    const r = await runLogQuery(
      { time_text: '2026-01-01', files: [dated] },
      cfg,
      new AbortController().signal,
    )
    expect(r.filter.total_matched).toBe(0)
    expect(r.filter.lines.length).toBe(0)
    expect(r.filter.stats).toMatchObject({ errors: 0, others: 0 })
  })

  it('runs concurrent queries without cross-talk (smoke)', async () => {
    // 并发冒烟：一个 0 命中（exit 2）+ 一个正常命中（exit 0），验证基本并发不串。
    // 注意：成功路径不读取退出码，真正的退出码隔离回归要靠错误路径单测（execFileAsync 私有）。
    const dated = path.resolve(__dirname, 'fixtures', 'dated.log')
    const [empty, hit] = await Promise.all([
      runLogQuery({ time_text: '2026-01-01', files: [dated] }, cfg, new AbortController().signal),
      runLogQuery({ time_text: '2026-07-03', files: [fixture], max_lines: 10 }, cfg, new AbortController().signal),
    ])
    expect(empty.filter.total_matched).toBe(0)
    expect(hit.filter.total_matched).toBe(25)
  })

  it('reports a timeout (not cancellation) when the query exceeds the budget', async () => {
    // 5ms 预算：Python 冷启动 + 文件过滤不可能在 5ms 内完成，稳定触发 execFile 超时 kill
    const fast = resolveConfig({ timeoutMs: 5 })
    await expect(
      runLogQuery({ time_text: '2026-07-03', files: [fixture] }, fast, new AbortController().signal),
    ).rejects.toThrow(/超时/)
  })

  it('rejects with an AbortError when the signal is aborted', async () => {
    const ac = new AbortController()
    ac.abort() // 已取消的 signal：execFile 立即以 AbortError 失败
    await expect(
      runLogQuery({ time_text: '2026-07-03', files: [fixture] }, cfg, ac.signal),
    ).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('clamps an oversized max_lines instead of failing', async () => {
    // 999999 会被 clamp 到 5000：不炸、正常返回（demo.log 只有 25 行）
    const r = await runLogQuery(
      { time_text: '2026-07-03', files: [fixture], max_lines: 999_999 },
      cfg,
      new AbortController().signal,
    )
    expect(r.filter.total_matched).toBe(25)
    expect(r.filter.lines.length).toBe(25)
  })

  it('honors an explicit timezone', async () => {
    const r = await runLogQuery(
      { time_text: '2026-07-03', files: [fixture], timezone: 'Asia/Shanghai', max_lines: 5 },
      cfg,
      new AbortController().signal,
    )
    expect(r.filter.total_matched).toBe(25)
  })

  it('scans a directory recursively with a glob pattern', async () => {
    const r = await runLogQuery(
      { time_text: '2026-07-03', dir: path.dirname(fixture), pattern: 'demo.log', max_lines: 10 },
      cfg,
      new AbortController().signal,
    )
    expect(r.filter.total_matched).toBe(25)
  })
})

describe('runLogQuery validation', () => {
  it('rejects an empty time text', async () => {
    await expect(
      runLogQuery({ time_text: '  ' }, cfg, new AbortController().signal),
    ).rejects.toThrow(/time_text/)
  })

  it('rejects when no input source is given', async () => {
    await expect(
      runLogQuery({ time_text: '昨天' }, cfg, new AbortController().signal),
    ).rejects.toThrow(/files|dir/)
  })

  it('rejects when the log file does not exist', async () => {
    await expect(
      runLogQuery(
        { time_text: '2026-07-03', files: [path.join(path.dirname(fixture), 'missing.log')] },
        cfg,
        new AbortController().signal,
      ),
    ).rejects.toThrow(/不存在/)
  })
})
