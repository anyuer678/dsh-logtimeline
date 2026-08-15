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
    const { stdout, stderr } = await execFileAsync(cfg.pythonBin, argv, {
        signal,
        timeout: cfg.timeoutMs,
        maxBuffer: 16 * 1024 * 1024,
        windowsHide: true,
    });
    const text = stdout.trim();
    // 退出码语义（lq.py）：0 成功 · 1 参数错误 · 2 无匹配文件/0 行命中（仍输出合法 JSON）
    // 非零退出码不一定是失败——先尝试解析 stdout；解析失败才按执行失败报错。
    if (!text) {
        throw new Error(`log_query 无输出（exit ${lastExitCode ?? '?'}；stderr：${trimTail(stderr)}）`);
    }
    try {
        return JSON.parse(text);
    }
    catch (err) {
        throw new Error(`log_query 执行失败（exit ${lastExitCode ?? '?'}）：${trimTail(stderr) || (err instanceof Error ? err.message : String(err))}`);
    }
}
/** 最近一次子进程退出码（供错误消息回显；成功路径不关心）。 */
let lastExitCode;
/** Promisified execFile: resolves with stdout/stderr/code, rejects only on spawn/signal errors. */
function execFileAsync(file, args, opts) {
    return new Promise((resolve, reject) => {
        execFile(file, args, opts, (error, stdout, stderr) => {
            if (error) {
                const code = error.code;
                // 数字 = 进程已运行并退出（如 2）；字符串 = spawn 级失败（如 "ENOENT"）
                if (typeof code !== 'number') {
                    reject(new Error(`log_query 无法启动 ${file}（${code ?? '未知'}）：${error.message}。请确认 Python 3.9+ 已安装并在 PATH 中。`));
                    return;
                }
                // 进程已运行并退出（exit code 非零）：交给调用方按 stdout 解析结果
                lastExitCode = code;
                resolve({ stdout, stderr, code });
                return;
            }
            lastExitCode = 0;
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