"""dsh-logtimeline MCP server：把 lq.py 的自然语言时间日志查询包成 MCP 工具。

启动：python -m mcp_server（或 python python/mcp_server.py），stdio 传输。
工具：
  log_query —— 中文自然语言时间表达式查日志（如「昨天下午」「3小时前」），
               返回 JSON：时间范围 + 命中行 + ERROR/WARN/INFO 统计。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from mcp.server.mcpserver import MCPServer

_LQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lq.py")
_OUTPUT_CAP = 4000

server = MCPServer("dsh-logtimeline")


def _run_lq(extra: list[str]) -> dict:
    cmd = [sys.executable, _LQ, *extra, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    payload: dict = {"exit_code": proc.returncode}
    if out:
        try:
            payload["result"] = json.loads(out)
        except json.JSONDecodeError:
            payload["stdout"] = out[:_OUTPUT_CAP]
    if err:
        payload["stderr"] = err[:1000]
    if len(json.dumps(payload, ensure_ascii=False)) > _OUTPUT_CAP:
        text = json.dumps(payload, ensure_ascii=False)
        payload = {"exit_code": proc.returncode, "stdout": text[:_OUTPUT_CAP], "truncated": True}
    return payload


@server.tool(
    name="log_query",
    description=(
        "用中文自然语言时间表达式查询本机日志文件。"
        "例句：log_query(time_text='昨天下午', dir='/var/log')、"
        "log_query(time_text='3小时前', files=['app.log'])。"
        "返回 JSON：解析出的时间范围、命中行、ERROR/WARN/INFO 统计。完全离线，日志不出本机。"
    ),
)
def log_query(
    time_text: str,
    dir: str | None = None,
    files: list[str] | None = None,
    pattern: str = "*.log",
    max_lines: int = 200,
    timezone: str | None = None,
) -> dict:
    extra = [time_text, "--max-lines", str(max(int(max_lines), 0))]
    if dir:
        extra += ["--dir", str(dir)]
    if files:
        for f in files:
            extra += ["--files", str(f)]
    if pattern and dir:
        extra += ["--pattern", str(pattern)]
    if timezone:
        extra += ["--timezone", str(timezone)]
    return _run_lq(extra)


@server.tool(
    name="parse_time",
    description=(
        "只解析中文自然语言时间表达式（如「凌晨12点」「上周三 14:00-15:00」），"
        "返回解析出的绝对时间范围（dry-run，不读日志）。"
    ),
)
def parse_time(time_text: str, timezone: str | None = None) -> dict:
    extra = [time_text, "--dry-run", "--max-lines", "0"]
    if timezone:
        extra += ["--timezone", str(timezone)]
    return _run_lq(extra)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
