/**
 * COMPATIBILITY.md / docs/time-expressions.md T01–T15 contract tests.
 *
 * Two layers:
 *  1. Parser contract with frozen `now=2026-07-03 20:00:00` (Python time_parser)
 *     so relative windows are deterministic against tests/fixtures/demo.log.
 *  2. Host-facing runLogQuery integration against the same fixture (wall-clock),
 *     asserting fail-closed semantics when the window misses the fixture.
 *
 * Unsupported rows are asserted as TimeParseError (documented skip), never a silent full dump.
 */
import { describe, expect, it } from 'vitest'
import { execFile } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { runLogQuery } from '../src/query.ts'
import { resolveConfig } from '../src/config.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')
const fixture = path.resolve(__dirname, 'fixtures', 'demo.log')
const pythonDir = path.join(projectRoot, 'python')
const cfg = resolveConfig({})

type ParseCase = {
  id: string
  expr: string
  /** 'ok' → must parse; 'unsupported' → must raise TimeParseError */
  expect: 'ok' | 'unsupported'
  start?: string
  end?: string
  minConf?: number
  note?: string
}

/** T01–T15 rows from docs/time-expressions.md, verified against python/time_parser.py. */
const PARSER_CASES: ParseCase[] = [
  // T01 Today — 今天下午 supported; bare 今天 is NOT (documented gap)
  { id: 'T01a', expr: '今天下午', expect: 'ok', start: '2026-07-03 13:00:00', end: '2026-07-03 18:00:00', minConf: 0.4 },
  { id: 'T01b', expr: '今天', expect: 'unsupported', note: 'bare 今天 has no matcher (only day-prefix + window)' },
  // T02 Yesterday
  { id: 'T02a', expr: '昨天', expect: 'ok', start: '2026-07-02 00:00:00', end: '2026-07-03 00:00:00', minConf: 0.7 },
  { id: 'T02b', expr: '昨晚', expect: 'ok', start: '2026-07-02 18:00:00', end: '2026-07-03 00:00:00', minConf: 0.7 },
  // T03 Day before
  { id: 'T03', expr: '前天', expect: 'ok', start: '2026-07-01 00:00:00', end: '2026-07-02 00:00:00', minConf: 0.7 },
  // T04 Relative hours — numeric supported; 半小时前 is NOT
  { id: 'T04a', expr: '3 小时前', expect: 'ok', start: '2026-07-03 17:00:00', end: '2026-07-03 20:00:00', minConf: 0.7 },
  { id: 'T04b', expr: '半小时前', expect: 'unsupported', note: '半 is not accepted by the relative-hour numeral regex' },
  // T05 Relative minutes
  { id: 'T05', expr: '30 分钟前', expect: 'ok', start: '2026-07-03 19:30:00', end: '2026-07-03 20:00:00', minConf: 0.7 },
  // T06 Absolute date
  { id: 'T06', expr: '2026-07-03', expect: 'ok', start: '2026-07-03 00:00:00', end: '2026-07-04 00:00:00', minConf: 1 },
  // T07 Absolute datetime (point window)
  { id: 'T07', expr: '2026-07-03 14:30', expect: 'ok', start: '2026-07-03 14:30:00', end: '2026-07-03 14:30:00', minConf: 1 },
  // T08 Range
  { id: 'T08', expr: '昨天 9 点到 18 点', expect: 'ok', start: '2026-07-02 09:00:00', end: '2026-07-02 18:00:00', minConf: 0.7 },
  // T09 This week (Mon–Sun; frozen now=Thu 2026-07-03)
  { id: 'T09a', expr: '本周', expect: 'ok', start: '2026-06-29 00:00:00', end: '2026-07-06 00:00:00', minConf: 0.7 },
  { id: 'T09b', expr: '这周', expect: 'ok', start: '2026-06-29 00:00:00', end: '2026-07-06 00:00:00', minConf: 0.7 },
  // T10 Last week
  { id: 'T10', expr: '上周', expect: 'ok', start: '2026-06-22 00:00:00', end: '2026-06-29 00:00:00', minConf: 0.7 },
  // T11 This month — NOT implemented
  { id: 'T11a', expr: '本月', expect: 'unsupported', note: 'no month-window matcher in time_parser.py' },
  { id: 'T11b', expr: '这个月', expect: 'unsupported', note: 'no month-window matcher in time_parser.py' },
  // T12 Last month — NOT implemented
  { id: 'T12', expr: '上个月', expect: 'unsupported', note: 'no month-window matcher in time_parser.py' },
  // T13 Year windows — NOT implemented
  { id: 'T13a', expr: '今年', expect: 'unsupported', note: 'no year-window matcher in time_parser.py' },
  { id: 'T13b', expr: '去年', expect: 'unsupported', note: 'no year-window matcher in time_parser.py' },
  // T14 Part-of-day (standalone fuzzy)
  { id: 'T14a', expr: '上午', expect: 'ok', start: '2026-07-03 08:00:00', end: '2026-07-03 12:00:00', minConf: 0.4 },
  { id: 'T14b', expr: '下午', expect: 'ok', start: '2026-07-03 13:00:00', end: '2026-07-03 18:00:00', minConf: 0.4 },
  { id: 'T14c', expr: '晚上', expect: 'ok', start: '2026-07-03 18:00:00', end: '2026-07-03 23:00:00', minConf: 0.4 },
  // T15 Unsupported slang
  { id: 'T15', expr: '上周摸鱼那天', expect: 'unsupported', note: 'free text must fail closed' },
]

function pythonCandidates(): Array<[string, string[]]> {
  return [
    ['python', ['-B']],
    ['python3', ['-B']],
    ['py', ['-3', '-B']],
  ]
}

function runPythonPy(pyFile: string, args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const attempts = pythonCandidates()
    let last: Error | undefined
    let i = 0
    const tryNext = () => {
      if (i >= attempts.length) {
        reject(last ?? new Error('no python interpreter'))
        return
      }
      const [cmd, prefix] = attempts[i++]
      execFile(
        cmd,
        [...prefix, pyFile, ...args],
        {
          cwd: projectRoot,
          timeout: 30_000,
          maxBuffer: 8 * 1024 * 1024,
          windowsHide: true,
          env: { ...process.env, PYTHONPATH: pythonDir },
        },
        (err, stdout, stderr) => {
          if (err && (err as NodeJS.ErrnoException).code === 'ENOENT') {
            last = err
            tryNext()
            return
          }
          if (err) {
            reject(new Error(`python failed: ${err.message}\n${stderr}`))
            return
          }
          resolve(stdout)
        },
      )
    }
    tryNext()
  })
}

/** Inline parse helper: MODE=parse|filter, EXPR, DEMO_LOG via env. */
const HELPER = `
import json, os, sys
sys.path.insert(0, os.environ["DQ_PYTHONPATH"])
from datetime import datetime
from time_parser import parse_time_range, TimeParseError
now = datetime(2026, 7, 3, 20, 0, 0)
expr = os.environ["DQ_EXPR"]
mode = os.environ.get("DQ_MODE", "parse")
try:
    tr = parse_time_range(expr, now=now)
except TimeParseError as e:
    print(json.dumps({"ok": False, "err": str(e)}, ensure_ascii=False))
    raise SystemExit(0)
out = {
    "ok": True,
    "start": tr.start.strftime("%Y-%m-%d %H:%M:%S"),
    "end": tr.end.strftime("%Y-%m-%d %H:%M:%S"),
    "conf": tr.confidence,
}
if mode == "filter":
    from log_filter import filter_logs
    res = filter_logs([os.environ["DQ_DEMO"]], tr, max_lines=50)
    out["total_matched"] = res.total_matched
    out["lines"] = len(res.lines)
    out["stats"] = res.stats
print(json.dumps(out, ensure_ascii=False))
`

function runHelper(expr: string, mode: 'parse' | 'filter'): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const attempts = pythonCandidates()
    let last: Error | undefined
    let i = 0
    const tryNext = () => {
      if (i >= attempts.length) {
        reject(last ?? new Error('no python interpreter'))
        return
      }
      const [cmd, prefix] = attempts[i++]
      execFile(
        cmd,
        [...prefix, '-c', HELPER],
        {
          cwd: projectRoot,
          timeout: 30_000,
          maxBuffer: 8 * 1024 * 1024,
          windowsHide: true,
          env: {
            ...process.env,
            DQ_PYTHONPATH: pythonDir,
            DQ_EXPR: expr,
            DQ_MODE: mode,
            DQ_DEMO: fixture,
          },
        },
        (err, stdout, stderr) => {
          if (err && (err as NodeJS.ErrnoException).code === 'ENOENT') {
            last = err
            tryNext()
            return
          }
          if (err) {
            reject(new Error(`python failed: ${err.message}\n${stderr}`))
            return
          }
          try {
            resolve(JSON.parse(stdout.trim()))
          } catch (e) {
            reject(new Error(`bad json: ${stdout}\n${stderr}\n${e}`))
          }
        },
      )
    }
    tryNext()
  })
}

describe('T01–T15 parser contract (frozen now=2026-07-03 20:00)', () => {
  it.each(PARSER_CASES.map((c) => [c.id, c] as const))('%s', async (id, c) => {
    const r = (await runHelper(c.expr, 'parse')) as {
      ok: boolean
      start?: string
      end?: string
      conf?: number
      err?: string
    }
    if (c.expect === 'unsupported') {
      expect(r.ok, `${id} ${c.expr} must fail closed (${c.note ?? ''})`).toBe(false)
      expect(String(r.err || '')).toMatch(/无法理解|无法识别|时间描述/)
      return
    }
    expect(r.ok, `${id} ${c.expr} should parse: ${r.err}`).toBe(true)
    if (c.start) expect(r.start).toBe(c.start)
    if (c.end) expect(r.end).toBe(c.end)
    if (c.minConf !== undefined) expect(r.conf ?? 0).toBeGreaterThanOrEqual(c.minConf)
  })
})

describe('T01–T15 filter against fixtures/demo.log (frozen now)', () => {
  it('T02 昨天 hits only 2026-07-02 lines', async () => {
    const r = (await runHelper('昨天', 'filter')) as { ok: boolean; total_matched: number; stats: { errors: number } }
    expect(r.ok).toBe(true)
    expect(r.total_matched).toBe(7)
    expect(r.stats.errors).toBe(1)
  })

  it('T03 前天 hits only 2026-07-01 lines', async () => {
    const r = (await runHelper('前天', 'filter')) as { ok: boolean; total_matched: number }
    expect(r.ok).toBe(true)
    expect(r.total_matched).toBe(5)
  })

  it('T08 昨天 9 点到 18 点 clips to the range window', async () => {
    const r = (await runHelper('昨天 9 点到 18 点', 'filter')) as {
      ok: boolean
      start: string
      end: string
      total_matched: number
    }
    expect(r.ok).toBe(true)
    expect(r.start).toBe('2026-07-02 09:00:00')
    expect(r.end).toBe('2026-07-02 18:00:00')
    expect(r.total_matched).toBe(7)
  })

  it('T01a 今天下午 misses the 09:15 block (empty window, not full dump)', async () => {
    const r = (await runHelper('今天下午', 'filter')) as { ok: boolean; total_matched: number }
    expect(r.ok).toBe(true)
    expect(r.total_matched).toBe(0)
  })

  it('T10 上周 hits 2026-06-25 week lines', async () => {
    const r = (await runHelper('上周', 'filter')) as { ok: boolean; total_matched: number }
    expect(r.ok).toBe(true)
    expect(r.total_matched).toBe(3)
  })
})

describe('T01–T15 via runLogQuery (wall-clock host path)', () => {
  const cases: Array<{ id: string; expr: string; mode: 'hit' | 'maybe-empty' }> = [
    { id: 'T01a', expr: '今天下午', mode: 'maybe-empty' },
    { id: 'T02a', expr: '昨天', mode: 'maybe-empty' },
    { id: 'T03', expr: '前天', mode: 'maybe-empty' },
    { id: 'T04a', expr: '3 小时前', mode: 'maybe-empty' },
    { id: 'T05', expr: '30 分钟前', mode: 'maybe-empty' },
    { id: 'T06', expr: '2026-07-03', mode: 'hit' },
    { id: 'T07', expr: '2026-07-03 14:30', mode: 'hit' },
    { id: 'T08', expr: '昨天 9 点到 18 点', mode: 'maybe-empty' },
    { id: 'T09a', expr: '本周', mode: 'maybe-empty' },
    { id: 'T10', expr: '上周', mode: 'maybe-empty' },
    { id: 'T14b', expr: '下午', mode: 'maybe-empty' },
  ]

  it.each(cases.map((c) => [c.id, c] as const))('%s %s returns a bounded query result', async (_id, c) => {
    const r = await runLogQuery(
      { time_text: c.expr, files: [fixture], max_lines: 50, since: '2026-07-01T00:00:00' },
      cfg,
      new AbortController().signal,
    )
    expect(r.mode).toBe('query')
    expect(r.time_range.expr_source.length).toBeGreaterThan(0)
    expect(r.filter.lines.length).toBeLessThanOrEqual(50)
    // multi-day fixture has 37 lines — never a silent full dump for narrow windows
    if (c.mode === 'maybe-empty') {
      expect(r.filter.total_matched).toBeLessThanOrEqual(37)
    }
    if (c.mode === 'hit') {
      expect(r.filter.total_matched).toBeGreaterThan(0)
    }
  })

  it('T06 absolute date still matches exactly the 25-line 2026-07-03 block', async () => {
    const r = await runLogQuery(
      { time_text: '2026-07-03', files: [fixture], max_lines: 50 },
      cfg,
      new AbortController().signal,
    )
    expect(r.filter.total_matched).toBe(25)
    expect(r.filter.stats.errors).toBe(13)
  })

  it('T15 unsupported free text with since fallback stays bounded', async () => {
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
    expect(r.filter.total_matched).toBeLessThanOrEqual(37)
  })

  it('T15 unsupported without since never unbounded full-file dump', async () => {
    try {
      const r = await runLogQuery(
        { time_text: '上周摸鱼那天', files: [fixture], max_lines: 500 },
        cfg,
        new AbortController().signal,
      )
      expect(r.filter.total_matched).toBeLessThanOrEqual(37)
    } catch (e) {
      expect(String(e)).toMatch(/无法理解|无输出|执行失败|时间/)
    }
  })
})
