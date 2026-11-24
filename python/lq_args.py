"""把 MCP 工具参数拼成 lq.py 的命令行参数（纯函数，无 mcp 依赖，便于单测）。

单独成模块的原因：mcp_server.py 在 import 时即构造 MCPServer，需要安装 `mcp`
包；参数拼装是最容易出错、也最值得回归测试的一段，抽出来后可被
tests/mcp_args.test.ts 直接以 `python -c` 调用验证。
"""
from __future__ import annotations


def build_log_query_argv(
    time_text: str,
    *,
    files: list[str] | None = None,
    directory: str | None = None,
    pattern: str = "*.log",
    max_lines: int = 200,
    timezone: str | None = None,
) -> list[str]:
    """拼出 `lq.py <time_text> ... --json` 的参数列表（不含解释器与脚本路径）。

    files 必须**一次性**传给 --files：lq.py 的 --files 是 nargs='+'，argparse
    对同一选项重复出现时后者覆盖前者，逐个追加会导致只有最后一个文件生效。
    """
    argv = [time_text, "--max-lines", str(max(int(max_lines), 0)), "--no-llm"]
    if directory:
        argv += ["--dir", str(directory)]
    if files:
        argv += ["--files", *[str(f) for f in files]]
    if pattern and directory:
        argv += ["--pattern", str(pattern)]
    if timezone:
        argv += ["--timezone", str(timezone)]
    return argv


def build_parse_time_argv(time_text: str, *, timezone: str | None = None) -> list[str]:
    """拼出只解析时间范围的 dry-run 参数列表（不读日志）。"""
    argv = [time_text, "--dry-run", "--max-lines", "0", "--no-llm"]
    if timezone:
        argv += ["--timezone", str(timezone)]
    return argv
