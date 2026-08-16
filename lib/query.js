/**
 * Core log query logic: shells out to the vendored logtimeline Python CLI.
 * Framework-free — importable and testable without a DSH host runtime.
 * @module dsh-logtimeline/query
 */
import { execFile } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const PACKAGE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const LQ_SCRIPT = path.join(PACKAGE_DIR, 'python', 'lq.py');
/** 模型可请求的最大行数上限：防止意外拉取海量日志进上下文。 */
const MAX_LINES_CAP = 5_000;
/**
 * 子进程 stdout 缓冲上限：与 MAX_LINES_CAP 对齐。
 * 5000 行 × 常见长日志行（数 KB）可达几十 MB；16MB 会在合法参数下触发
 * maxBuffer exceeded，故取 64MB 留足余量。
 */
const MAX_STDOUT_BUFFER = 64 * 1024 * 1024;
/**
 * 解析 Python 可执行命令候选：显式配置的 pythonBin > `python` > Windows `py -3`。
 * 统一追加 `-B`（不写 __pycache__/.pyc），保证 vendored 目录运行时零 Python 缓存产物。
 * py launcher 需要把 `-3` 作为独立参数传给 py，不能拼进命令串，所以用 [命令, 首参] 元组。
 */
function pythonCandidates(cfg) {
    if (cfg.pythonBin !== 'python')
        return [[cfg.pythonBin, ['-B']]];
    return [
        ['python', ['-B']],
        ['py', ['-3', '-B']],
    ];
}
/** Run the vendored logtimeline CLI in offline mode and parse its JSON output. */
export async function runLogQuery(args, cfg, signal) {
    if (!args.time_text || args.time_text.trim().length === 0) {
        throw new Error('log_query 需要 time_text（自然语言时间描述），如「昨天下午」');
    }
    if ((!args.files || args.files.length === 0) && !args.dir) {
        throw new Error('log_query 至少需要一个输入源：files（文件列表）或 dir（目录）');
    }
    const script = await assertLqScript();
    const argv = [script, args.time_text, '--json', '--no-llm'];
    if (args.files && args.files.length > 0) {
        argv.push('--files', ...args.files);
    }
    if (args.dir)
        argv.push('--dir', args.dir);
    if (args.pattern)
        argv.push('--pattern', args.pattern);
    if (args.max_lines !== undefined) {
        argv.push('--max-lines', String(Math.min(MAX_LINES_CAP, Math.max(0, Math.floor(args.max_lines)))));
    }
    if (args.since)
        argv.push('--since', args.since);
    if (args.timezone)
        argv.push('--timezone', args.timezone);
    // 逐个候选尝试：`python` 不存在时回退 Windows `py -3` launcher；spawn 之外的错误直接抛出
    const { stdout, stderr, code } = await runWithFallback(argv, cfg, signal);
    const text = stdout.trim();
    // 退出码语义（lq.py）：0 成功 · 1 参数错误 · 2 无匹配文件/0 行命中（仍输出合法 JSON）
    // 非零退出码不一定是失败——先尝试解析 stdout；解析失败才按执行失败报错。
    if (!text) {
        throw new Error(`log_query 无输出（exit ${code}；stderr：${trimTail(stderr)}）`);
    }
    try {
        return JSON.parse(text);
    }
    catch (err) {
        throw new Error(`log_query 执行失败（exit ${code}）：${trimTail(stderr) || (err instanceof Error ? err.message : String(err))}`);
    }
}
/** 尝试所有 Python 候选命令，仅对 spawn 缺失（ENOENT）回退到下一个候选。 */
async function runWithFallback(argv, cfg, signal) {
    const candidates = pythonCandidates(cfg);
    let lastError;
    for (const [command, prefix] of candidates) {
        try {
            return await execFileAsync(command, [...prefix, ...argv], {
                signal,
                timeout: cfg.timeoutMs,
                maxBuffer: MAX_STDOUT_BUFFER,
                windowsHide: true,
            });
        }
        catch (err) {
            if (err instanceof Error && err.message.includes('ENOENT')) {
                lastError = err;
                continue;
            }
            throw err;
        }
    }
    throw lastError ?? new Error(`未找到可用的 Python 解释器（尝试过：${candidates.map(([c]) => c).join(', ')}）`);
}
/** Promisified execFile: resolves with stdout/stderr/code, rejects on spawn/signal errors. */
function execFileAsync(file, args, opts) {
    return new Promise((resolve, reject) => {
        execFile(file, args, opts, (error, stdout, stderr) => {
            if (error) {
                const code = error.code;
                // 数字 = 进程已运行并退出（如 2）；字符串 = spawn/取消/超时级失败
                if (typeof code !== 'number') {
                    const err = error;
                    // 真正的外部取消（exec.signal abort）——按 AbortError 身份抛出，供上层区分取消与失败
                    if (code === 'ABORT_ERR' || err.name === 'AbortError') {
                        reject(new DOMException('log_query 已取消', 'AbortError'));
                        return;
                    }
                    // 超时 kill：Node 报 killed=true + signal=SIGTERM，与取消区分开
                    if (err.killed === true) {
                        reject(new Error(`log_query 超时（超过 ${opts.timeout}ms）`));
                        return;
                    }
                    reject(new Error(`log_query 无法启动 ${file}（${code ?? '未知'}）：${error.message}。请确认 Python 3.9+ 已安装并在 PATH 中。`));
                    return;
                }
                // 进程已运行并退出（exit code 非零）：交给调用方按 stdout 解析结果
                resolve({ stdout, stderr, code });
                return;
            }
            resolve({ stdout, stderr, code: 0 });
        });
    });
}
/** Locate the vendored lq.py and fail loudly with a fix hint when missing. */
async function assertLqScript() {
    try {
        await fs.access(LQ_SCRIPT);
        return LQ_SCRIPT;
    }
    catch {
        throw new Error(`未找到 vendored logtimeline 脚本：${LQ_SCRIPT}（检查包安装是否完整）`);
    }
}
function trimTail(text) {
    const t = text.trim();
    return t.length > 400 ? `${t.slice(-400)}…` : t;
}
//# sourceMappingURL=query.js.map