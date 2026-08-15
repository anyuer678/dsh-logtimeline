/**
 * Host-assembly integration test: loads the BUILT plugin (lib/index.js) into a
 * minimal Cordis container, applies it, and exercises the registered tool
 * end-to-end (real vendored Python) with schema-contract validation.
 *
 * Honest caveats: `ctx.tools` is mocked (in the real DSH host the tools
 * service is assembled by app-boot); peer packages are installed as
 * devDependencies because `npm --legacy-peer-deps` skips auto-installing them.
 * Run `npm run build` before this test so lib/ matches src/.
 */
import { describe, expect, it } from 'vitest'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')
const u = (p: string) => pathToFileURL(path.resolve(p)).href

describe('host assembly (built plugin in a cordis container)', () => {
  it('loads, applies, registers log_query, and its canonical value passes the schema contract', async () => {
    // 1. 加载编译产物（验证 @deepseek-ai/cordis + @deepseek-ai/dsh-tools 运行时链可解析）
    const mod = await import(u(path.join(projectRoot, 'lib', 'index.js')))
    expect(typeof mod.apply).toBe('function')
    expect(mod.name).toBe('dsh-logtimeline')
    expect(mod.inject).toContain('tools')

    // 2. 最小 cordis 容器 + mock tools service
    const { Context } = await import(u(path.join(projectRoot, 'node_modules', '@deepseek-ai', 'cordis', 'lib', 'index.js')))
    let registered: any = null
    const ctx = new Context()
    ctx.tools = { register: (def: unknown) => { registered = def } }

    // 3. apply
    mod.apply(ctx, { pythonBin: 'python', timeoutMs: 60_000 })
    expect(registered).not.toBeNull()

    // 4. 工具定义形状：parameters 是编译后的 raw JSON Schema
    const props = registered.parameters?.properties ?? {}
    expect(Object.keys(props)).toEqual(
      expect.arrayContaining(['time_text', 'files', 'dir', 'pattern', 'max_lines', 'since', 'timezone']),
    )
    expect(registered.parameters.required).toContain('time_text')
    expect(typeof registered.execute).toBe('function')
    expect(typeof registered.output.render).toBe('function')

    // 5. 端到端：真实 execute（vendored Python）+ schema 契约校验
    const fixture = path.join(projectRoot, 'tests', 'fixtures', 'dated.log')
    const exec = { signal: new AbortController().signal }
    const result = await registered.execute(
      { time_text: '2026-07-03', files: [fixture], max_lines: 3 },
      exec,
    )
    expect(result.filter.total_matched).toBe(4)
    expect(result.filter.lines.length).toBe(3)

    const { validateArgs } = await import(u(path.join(projectRoot, 'node_modules', '@deepseek-ai', 'dsh-tools', 'lib', 'index.js')))
    const errors = validateArgs({ value: registered.output.schema }, { value: result })
    expect(errors).toEqual([])
  })
})
