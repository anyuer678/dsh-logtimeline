/**
 * MCP 参数拼装回归测试（真实 Python，无 mcp 包依赖）。
 *
 * 背景：python/mcp_server.py 旧实现逐个追加 `--files`，而 lq.py 的 --files 是
 * argparse `nargs='+'` —— 同一选项重复出现时后者覆盖前者，导致多文件只剩最后
 * 一个生效。这里同时锁住两个事实：
 *   1. 拼装结果里 `--files` 只出现一次，且带全部文件；
 *   2. 真正跑 lq.py 时，每个文件的命中都进入 file_stats。
 */
import { describe, expect, it } from 'vitest'
import { execFile } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')
const pythonDir = path.join(projectRoot, 'python')
const fixture = (name: string) => path.join(projectRoot, 'tests', 'fixtures', name)

const PYTHON_CANDIDATES: Array<[string, string[]]> = [
  ['python', []],
  ['python3', []],
  ['py', ['-3']],
]

/** 依次尝试 python / python3 / py -3，仅对 ENOENT（解释器不存在）回退。 */
function runPython(command: string, args: string[], cwd: string): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(command, args, { cwd, timeout: 30_000, windowsHide: true }, (error, stdout, stderr) => {
      if (error) {
        reject(Object.assign(error, { stdout, stderr }))
        return
      }
      resolve({ stdout, stderr })
    })
  })
}

async function python(args: string[], cwd = pythonDir): Promise<string> {
  let lastError: unknown
  for (const [command, prefix] of PYTHON_CANDIDATES) {
    try {
      const { stdout } = await runPython(command, [...prefix, ...args], cwd)
      return stdout
    } catch (err) {
      const code = (err as NodeJS.ErrnoException).code
      if (code === 'ENOENT') {
        lastError = err
        continue
      }
      throw err
    }
  }
  throw lastError ?? new Error('未找到可用的 Python 解释器')
}

const BUILD_ARGV = [
  '-c',
  'import json,sys; from lq_args import build_log_query_argv; ' +
    'print(json.dumps(build_log_query_argv(sys.argv[1], files=sys.argv[2:])))',
]

describe('MCP log_query 参数拼装', () => {
  it('多个文件只在 --files 中出现一次，且全部保留', async () => {
    const stdout = await python([...BUILD_ARGV, '2026-07-03', 'a.log', 'b.log', 'c.log'])
    const argv = JSON.parse(stdout) as string[]

    expect(argv.filter((a) => a === '--files')).toHaveLength(1)
    const at = argv.indexOf('--files')
    expect(argv.slice(at + 1)).toEqual(['a.log', 'b.log', 'c.log'])
  })

  it('离线承诺：参数里带 --no-llm', async () => {
    const stdout = await python([...BUILD_ARGV, '昨天下午', 'app.log'])
    expect(JSON.parse(stdout)).toContain('--no-llm')
  })

  it('真实执行时两个 fixture 都进 file_stats（旧实现只有最后一个）', async () => {
    const demo = fixture('demo.log')
    const dated = fixture('dated.log')
    const argv = JSON.parse(await python([...BUILD_ARGV, '2026-07-03', demo, dated])) as string[]

    const lqScript = path.join(pythonDir, 'lq.py')
    const stdout = await python([lqScript, ...argv, '--json'], projectRoot)
    const result = JSON.parse(stdout)

    expect(Object.keys(result.filter.file_stats)).toEqual(
      expect.arrayContaining([demo, dated]),
    )
    expect(result.filter.file_stats[demo]).toBe(25)
    expect(result.filter.file_stats[dated]).toBe(4)
    expect(result.filter.total_matched).toBe(29)
  })
})
