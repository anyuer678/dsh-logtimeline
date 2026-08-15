"""lq：日志时间戳模糊查询器 CLI 主入口，装配 time_parser/log_filter/llm_summary/config。"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime

from time_parser import TimeParseError, TimeRange, parse_time_range
from log_filter import (FilterResult, LogFormatError, filter_logs, filter_stream,
                        summarize_hits)
from llm_summary import LLMError, analyze_logs, analyze_offline
from config import ConfigError, load_config_from_env

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

try:
    from rich.console import Console
    _console = Console(highlight=False)
except ImportError:
    _console = None

# 剥离 ANSI 转义与控制字符，防日志/LLM 内容终端注入
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u001b]")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _clean(s) -> str:
    s = s if isinstance(s, str) else str(s)
    s = _ANSI_RE.sub("", s)
    return _CTRL_RE.sub("", s)


def build_parser():
    p = argparse.ArgumentParser(prog="lq", description="日志时间戳模糊查询器")
    p.add_argument("time_text", nargs="?", help="自然语言时间描述，如「昨天下午」")
    p.add_argument("--files", nargs="+", default=[], help="日志文件列表")
    p.add_argument("--dir", default=None, help="递归扫描目录")
    p.add_argument("--pattern", default="*.log", help="--dir 下文件名模式")
    p.add_argument("--service", default=None, help="--journalctl 服务名")
    p.add_argument("--journalctl", action="store_true", help="从 journalctl 取日志（仅 Linux/systemd）")
    p.add_argument("--max-lines", type=int, default=500, help="最多返回行数（>=0，0 表示只统计）")
    p.add_argument("--encoding", default="auto",
                   help="日志文件编码：auto（UTF-8 优先，失败回退 GBK）/ utf-8 / gbk 等")
    p.add_argument("--since", default=None, help="解析失败的绝对时间兜底（RFC3339）")
    p.add_argument("--dry-run", action="store_true", help="只打印时间范围与过滤计划")
    p.add_argument("--no-llm", action="store_true", help="离线模式：过滤+统计")
    p.add_argument("--json", action="store_true", help="机器可读 JSON 输出")
    p.add_argument("--timezone", default=None, help="时区名，如 Asia/Shanghai")
    return p


def _emit(text, style=None):
    if _console is not None:
        _console.print(text, style=style)
    else:
        print(text)


def _error(text): print("错误：" + _clean(text), file=sys.stderr)


def _warn(text): print("警告：" + _clean(text), file=sys.stderr)


def _fmt_dt(dt): return dt.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_range(tr):
    return "%s ~ %s（原文：%s，置信度 %.1f）" % (_fmt_dt(tr.start), _fmt_dt(tr.end), tr.expr_source, tr.confidence)


def _load_tz(name):
    if not name: return None
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception as exc:
        _warn("无法加载时区 %r（%s），使用本地时区" % (name, exc))
        return None


def _parse_since(text, tz=None):
    """RFC3339 或纯日期解析；兼容 Python 3.9（fromisoformat 不认纯日期）。

    NOTE(vendored): 原实现直接返回 fromisoformat 结果——带时区后缀（如 +08:00）
    时是 aware datetime，与 parse_time_range 的 naive TimeRange 比较抛 TypeError
    （offset-naive vs offset-aware）。现统一为 naive 墙钟时间，语义与
    parse_time_range 一致（tz 仅用于确定"现在"/目标时区的墙钟时间）。
    """
    s = text.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        dt = None
    if dt is None:
        if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", s):
            try:
                dt = datetime.fromisoformat(s + "T00:00:00")
            except ValueError:
                return None
        else:
            return None
    if dt.tzinfo is not None:
        try:
            dt = dt.astimezone(tz)
        except (ValueError, TypeError):
            dt = dt.astimezone()
        dt = dt.replace(tzinfo=None)
    return dt


def _parse_time(args):
    tz = _load_tz(args.timezone)
    try:
        # parse_time_range 已统一输出 naive（tz 仅确定“现在”的墙钟时间）
        return parse_time_range(args.time_text, tz=tz)
    except TimeParseError as exc:
        _error(str(exc))
        if exc.reasonable_guess is not None:
            _warn("合理猜测：" + _fmt_range(exc.reasonable_guess))
        if not args.since: return None
        since = _parse_since(args.since, tz)
        if since is None:
            _error("--since 不是合法 RFC3339 时间：" + args.since)
            return None
        tr = TimeRange(since, datetime.now(tz), args.time_text, 0.4)
        _warn("已用 --since 兜底：" + _fmt_range(tr))
        return tr


def _collect_paths(args):
    missing = [p for p in args.files if not os.path.isfile(p)]
    paths = [p for p in args.files if os.path.isfile(p)]
    if args.dir:
        if not os.path.isdir(args.dir):
            missing.append(args.dir)
        else:
            for root, _dirs, files in os.walk(args.dir):
                for fn in sorted(files):
                    if fnmatch.fnmatch(fn, args.pattern): paths.append(os.path.join(root, fn))
    # 去重：--files 与 --dir 可能命中同一文件（如 demo.log），按规范化绝对路径去重，
    # 保留首次出现的原始写法，避免同一文件被重复统计/重复计入 file_stats。
    seen, dedup = set(), []
    for p in paths:
        key = os.path.normcase(os.path.abspath(p))
        if key not in seen:
            seen.add(key)
            dedup.append(p)
    return dedup, missing


def _filter_journal(args, tr):
    if sys.platform != "linux":
        _error("--journalctl 仅支持 Linux/systemd 平台（当前系统：%s）" % sys.platform)
        return None
    cmd = ["journalctl"]
    if args.service:
        cmd += ["-u", args.service]
    cmd += ["--since", _fmt_dt(tr.start), "--until", _fmt_dt(tr.end)]
    try:
        # stderr 丢弃避免管道写满阻塞；参数列表形式，无 shell 拼接
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        _error("无法执行 journalctl：%s" % exc)
        return None
    with proc.stdout:
        res = filter_stream(proc.stdout, tr, max_lines=args.max_lines, source="journalctl")
    proc.wait()
    if proc.returncode != 0:
        _error("journalctl 退出码 %d（服务不存在或无权限？该功能仅 Linux/systemd 可用）" % proc.returncode)
        return None
    return res


def _do_filter(args, tr):
    if args.journalctl:
        return _filter_journal(args, tr)
    paths, missing = _collect_paths(args)
    if missing: _error("文件或目录不存在：" + "，".join(missing)); return None
    if not paths: _error("未找到任何日志文件（--dir 下 --pattern 无匹配）"); return None
    return filter_logs(paths, tr, max_lines=args.max_lines, encoding=args.encoding)


def _do_analysis(args, tr, sample, stats, counts):
    if args.no_llm:
        return analyze_offline(sample, stats, counts=counts), 0
    try:
        cfg = load_config_from_env(os.environ)
    except ConfigError as exc:
        _warn("LLM 配置缺失（%s），已改用离线统计；可设置环境变量或使用 --no-llm" % exc)
        return analyze_offline(sample, stats, counts=counts), 3
    _warn("将发送 %d 行样本至 %s（仅本次查询；如需完全本地请用 --no-llm）"
          % (len(sample), cfg.base_url))
    try:
        return analyze_logs(args.time_text, tr, sample, cfg), 0
    except LLMError as exc:
        _error("LLM 归因失败（%s），已输出离线统计" % exc)
        return analyze_offline(sample, stats, counts=counts), 3


def _source_desc(args):
    parts = []
    if args.files:
        parts.append("--files " + " ".join(args.files))
    if args.dir:
        parts.append("--dir %s --pattern %s" % (args.dir, args.pattern))
    if args.journalctl:
        parts.append("--journalctl" + (" -u " + args.service if args.service else ""))
    return "；".join(parts) or "（无）"


def _emit_json(tr, res, analysis, args=None):
    payload = {
        "mode": "dry-run" if res is None else "query",
        "time_range": {"start": _fmt_dt(tr.start), "end": _fmt_dt(tr.end),
                       "expr_source": tr.expr_source, "confidence": tr.confidence},
    }
    if res is None:
        payload["plan"] = {"sources": _source_desc(args), "max_lines": args.max_lines}
    else:
        lines = [{"lineno": ll.lineno,
                  "timestamp": _fmt_dt(ll.timestamp) if ll.timestamp else None,
                  "raw": ll.raw}
                 for ll in res.lines]
        payload["filter"] = {"total_matched": res.total_matched, "truncated": res.truncated,
                             "time_span_found": res.time_span_found,
                             "file_stats": res.file_stats, "file_errors": res.file_errors,
                             "stats": res.stats, "lines": lines}
        payload["analysis"] = None if analysis is None else {
            "summary": analysis.summary, "evidence": analysis.evidence,
            "suggestions": analysis.suggestions, "confidence": analysis.confidence,
            "tokens_used": analysis.tokens_used}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _emit_text(tr, res, stats, analysis):
    _emit("时间范围：" + _fmt_range(tr), style="bold green")
    if res is not None:
        _emit("命中 %d 行（全量命中 %d 行%s）" % (len(res.lines), res.total_matched,
                                               "，已截断" if res.truncated else ""),
              style="yellow")
        _emit("文件统计：" + "；".join("%s: %d 行" % (os.path.basename(k), v)
                                     for k, v in res.file_stats.items()))
        if res.file_errors:
            _warn("部分文件读取失败：" + "；".join("%s（%s）" % (k, v) for k, v in res.file_errors.items()))
        _emit("级别统计（全窗口）：ERROR %d 条 / WARN %d 条 / INFO %d 条 / DEBUG %d 条" % (
            res.stats["errors"], res.stats["warns"], res.stats["infos"], res.stats["debugs"]))
    if analysis is not None:
        _emit("推断：" + _clean(analysis.summary), style="cyan")
        for i, e in enumerate(analysis.evidence, 1):
            _emit("证据 %d) %s" % (i, _clean(e)))
        for s in analysis.suggestions:
            _emit("建议 - " + _clean(s))
        _emit("置信度：%s（tokens 使用 %d）" % (analysis.confidence, analysis.tokens_used))


def _output(tr, res, stats, analysis, args):
    if args.json:
        _emit_json(tr, res, analysis, args)
    else:
        _emit_text(tr, res, stats, analysis)


def main(argv=None):
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    if not args.time_text:
        _error("缺少时间描述参数；用法：lq <时间描述> [--files f...] [--dir d] [--journalctl]")
        return 1
    if not (args.files or args.dir or args.journalctl):
        _error("至少需要一个输入源（--files / --dir / --journalctl）")
        return 1
    if args.max_lines < 0:
        _error("--max-lines 必须 >= 0")
        return 1
    tr = _parse_time(args)
    if tr is None:
        return 1
    if args.dry_run:
        if args.json:
            _emit_json(tr, None, None, args)
        else:
            _emit("时间范围：" + _fmt_range(tr), style="bold green")
            _emit("过滤计划：%s；--max-lines %d" % (_source_desc(args), args.max_lines))
        return 0
    res = _do_filter(args, tr)
    if res is None:
        return 2
    stats = summarize_hits(res.lines, top_n=10)
    if res.total_matched == 0:
        _output(tr, res, stats, None, args)
        return 2
    analysis, code = _do_analysis(args, tr, [ll.raw for ll in res.lines], stats, res.stats)
    _output(tr, res, stats, analysis, args)
    return code


if __name__ == "__main__":
    sys.exit(main())
