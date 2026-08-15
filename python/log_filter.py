"""log_filter：日志时间戳识别、时间范围流式过滤、命中行摘要。零外部依赖。"""
from __future__ import annotations

import heapq
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Iterator, Optional, Sequence, Tuple


@dataclass
class LogLine:
    lineno: int
    timestamp: Optional[datetime]
    raw: str


@dataclass
class FilterResult:
    lines: list[LogLine]                 # 窗口内命中行（时间升序，最多 max_lines 条）
    total_matched: int                   # 全量命中数（截断前）
    truncated: bool                      # 是否超出 max_lines
    time_span_found: bool                # 是否至少一行带时间戳
    file_stats: dict[str, int]           # {文件名: 命中行数}
    file_errors: dict[str, str] = field(default_factory=dict)   # {文件名: 错误信息}
    stats: dict[str, int] = field(default_factory=dict)         # 全量级别计数


class LogFormatError(ValueError):
    """日志文件无法打开或时间戳无法识别。"""


_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
_MONTH_ALT = "|".join(_MONTHS)

_TIMESTAMP_PATTERNS: list[tuple[re.Pattern, str]] = [
    # 2026-07-03 12:30:45
    (re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) "
                r"(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})"),
     "%Y-%m-%d %H:%M:%S"),
    # 2026-07-03T12:30:45（ISO T 分隔）
    (re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T"
                r"(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})"),
     "%Y-%m-%dT%H:%M:%S"),
    # 03/Jul/2026:12:30:45（Nginx 格式）
    (re.compile(r"(?P<day>\d{1,2})/(?P<month>" + _MONTH_ALT + r")/(?P<year>\d{4}):"
                r"(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})"),
     "%d/%b/%Y:%H:%M:%S"),
    # Jul 03 12:30（英文月缩写，年份锚定 tr.start 所在年）
    (re.compile(r"(?<![A-Za-z])(?P<month>" + _MONTH_ALT + r") (?P<day>\d{1,2}) "
                r"(?P<hour>\d{1,2}):(?P<min>\d{2})(?!\d)"),
     "%b %d %H:%M"),
    # 12:30:45（日期锚定 tr.start 所在日）
    (re.compile(r"(?<![\d:])(?P<hour>\d{1,2}):(?P<min>\d{2}):(?P<sec>\d{2})(?!\d)"),
     "%H:%M:%S"),
]

# 需要跨午夜锚定推进的格式：仅完全无日期的 HH:MM:SS。
# 注意："%b %d %H:%M" 自带月日（只缺年份），不做序列推进，否则同日内
# 时间早于前一行（乱序/混合格式）会被误判为次日。
_DAYLESS_FORMATS = {"%H:%M:%S"}

_LEVELS = (("ERROR", "errors"), ("WARN", "warns"), ("INFO", "infos"), ("DEBUG", "debugs"))


def _extract_timestamp(pattern: re.Pattern, fmt: str, line: str,
                       anchor: datetime) -> Optional[datetime]:
    """按命名捕获组从行中提取 datetime；缺字段用 anchor 补齐。"""
    m = pattern.search(line)
    if m is None:
        return None
    g = m.groupdict()
    try:
        year = int(g["year"]) if g.get("year") else anchor.year
        month_s = g.get("month")
        if month_s and month_s.isalpha():
            month = _MONTHS.get(month_s)
        else:
            month = int(month_s) if month_s else anchor.month
        day = int(g["day"]) if g.get("day") else anchor.day
        hour = int(g["hour"])
        minute = int(g["min"])
        second = int(g["sec"]) if g.get("sec") else 0
    except (TypeError, ValueError):
        return None
    if month is None:
        return None
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def detect_ts_format(first_line: str) -> Optional[Tuple[re.Pattern, str]]:
    """返回首个命中的 (正则, strptime 格式)；无法识别返回 None。"""
    for pattern, fmt in _TIMESTAMP_PATTERNS:
        if pattern.search(first_line):
            return pattern, fmt
    return None


def _open_log(path: str, encoding: str = "auto", errors: str = "replace"):
    """打开日志文件；encoding='auto' 时先按 UTF-8 严格试读，失败回退 GBK。"""
    try:
        if encoding and encoding.lower() != "auto":
            return open(path, "r", encoding=encoding, errors=errors)
        fh = open(path, "r", encoding="utf-8", errors="strict")
        try:
            fh.readline()
            fh.seek(0)
            return fh
        except UnicodeDecodeError:
            fh.close()
            return open(path, "r", encoding="gbk", errors="replace")
    except OSError as exc:
        raise LogFormatError(
            f"无法打开日志文件 {path!r}：{exc.strerror or exc}") from exc


def iter_filter_lines(lines: Iterable[str], tr) -> Iterator[LogLine]:
    """从行迭代器流式解析 LogLine（文件级主格式探测 + 跨午夜/双日锚定）。

    对缺日期的格式（HH:MM:SS / "Jul 03 12:30"）：
    - 若本行时间早于上一行（序列推进），日期 +1（文件跨午夜场景）；
    - 再做双日探测：优先取落在查询窗口内的那一个（窗口跨午夜时无首行上下文也不漏）。
    """
    detected = None
    pattern = fmt = None
    last_ts = None  # 仅由 time-only 行维护的序列上下文
    for lineno, line in enumerate(lines, 1):
        raw = line.rstrip("\r\n") if isinstance(line, str) else str(line).rstrip("\r\n")
        if detected is None:
            detected = detect_ts_format(raw)
            if detected is not None:
                pattern, fmt = detected
        ts, fmt_used = None, None
        if pattern is not None:
            m = pattern.search(raw)
            if m is not None:
                fmt_used, ts = fmt, _extract_timestamp(pattern, fmt, raw, tr.start)
            else:
                d2 = detect_ts_format(raw)
                if d2 is not None:
                    p2, f2 = d2
                    fmt_used, ts = f2, _extract_timestamp(p2, f2, raw, tr.start)
        if ts is not None and fmt_used in _DAYLESS_FORMATS:
            if last_ts is not None and ts < last_ts:
                ts += timedelta(days=1)
            ts1 = ts + timedelta(days=1)
            in0 = tr.start <= ts < tr.end
            in1 = tr.start <= ts1 < tr.end
            if in1 and not in0:
                ts = ts1
            elif in0 and in1 and last_ts is not None:
                if abs(ts1 - last_ts) < abs(ts - last_ts):
                    ts = ts1
            last_ts = ts
        yield LogLine(lineno, ts, raw)


def iter_filter_log(path: str, tr, *, encoding: str = "auto",
                    errors: str = "replace") -> Iterator[LogLine]:
    """流式逐行 yield LogLine（自动编码探测）；无法识别时间戳的行 timestamp 为 None。"""
    with _open_log(path, encoding, errors) as fh:
        yield from iter_filter_lines(fh, tr)


def _level_key(raw: str) -> str:
    """按词边界识别日志级别，返回分桶名。"""
    upper = raw.upper()
    for kw, name in _LEVELS:
        if re.search(r"\b" + kw + r"\b", upper):
            return name
    return "others"


class _TopKStats:
    """流式 Top-K（按时间戳保留最大 max_lines 条）+ 全量计数，内存 O(max_lines)。"""

    def __init__(self, max_lines: int):
        self.k = max_lines
        self.heap: list[tuple] = []
        self.seq = 0
        self.total = 0
        self.found = False
        self.stats = {"errors": 0, "warns": 0, "infos": 0, "debugs": 0, "others": 0}

    def add(self, ll: LogLine, tr) -> None:
        if ll.timestamp is None:
            return
        self.found = True
        if tr.start <= ll.timestamp < tr.end:
            self.total += 1
            self.stats[_level_key(ll.raw)] += 1
            heapq.heappush(self.heap, (ll.timestamp, self.seq, ll))
            self.seq += 1
            if len(self.heap) > self.k:
                heapq.heappop(self.heap)

    def result(self, file_stats: dict, file_errors: dict) -> FilterResult:
        ordered = sorted(self.heap, key=lambda t: (t[0], t[1]))
        lines = [ll for _t, _s, ll in ordered]
        return FilterResult(
            lines=lines, total_matched=self.total,
            truncated=self.total > self.k, time_span_found=self.found,
            file_stats=file_stats, file_errors=file_errors, stats=self.stats)


def filter_stream(lines: Iterable[str], tr, *, max_lines: int = 500,
                  source: str = "stream") -> FilterResult:
    """对行迭代器（如 journalctl stdout）做窗口过滤 + Top-K + 全量统计。"""
    acc = _TopKStats(max_lines)
    for ll in iter_filter_lines(lines, tr):
        acc.add(ll, tr)
    return acc.result({source: acc.total}, {})


def filter_logs(paths: Sequence[str], tr, *, max_lines: int = 500,
                encoding: str = "auto", errors: str = "replace") -> FilterResult:
    """多文件流式过滤合并：窗口内行按时间升序保留最后 max_lines 条，全量统计。

    - 内存峰值 O(max_lines)，与文件总行数无关（GB 级日志不 OOM）；
    - 单文件打开/读取失败记入 file_errors 并继续处理其余文件。
    """
    acc = _TopKStats(max_lines)
    file_stats = {}
    file_errors = {}
    for path in paths:
        count = 0
        try:
            for ll in iter_filter_log(path, tr, encoding=encoding, errors=errors):
                if ll.timestamp is not None and tr.start <= ll.timestamp < tr.end:
                    count += 1
                    acc.add(ll, tr)
        except LogFormatError as exc:
            file_errors[str(path)] = str(exc)
        file_stats[str(path)] = count
    return acc.result(file_stats, file_errors)


def summarize_hits(lines: Sequence[LogLine], top_n: int = 10) -> dict[str, list[str]]:
    """按日志级别分桶（词边界识别），每桶取前 top_n 条原文。"""
    buckets = {"errors": [], "warns": [], "infos": [], "debugs": [], "others": []}
    for ll in lines:
        key = _level_key(ll.raw)
        if len(buckets[key]) < top_n:
            buckets[key].append(ll.raw)
    return buckets
