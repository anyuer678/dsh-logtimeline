"""中文自然语言时间描述解析为 [start, end] 时间范围（纯函数，零外部依赖）。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo


@dataclass(frozen=True)
class TimeRange:
    """解析结果：起止时间、原始表达式与置信度。"""
    start: datetime
    end: datetime
    expr_source: str
    confidence: float


class TimeParseError(ValueError):
    """解析失败，message 为中文提示（回显给用户），带 reasonable_guess: TimeRange|None。"""

    def __init__(self, message: str, reasonable_guess: TimeRange | None = None):
        super().__init__(message)
        self.reasonable_guess = reasonable_guess


FUZZY_WINDOWS = {
    "凌晨": (0, 5), "清晨": (5, 8), "上午": (8, 12), "中午": (11, 13),
    "午后": (12, 15), "下午": (13, 18), "晚上": (18, 23), "深夜": (22, 3),
    "饭点": (11, 13), "大半夜": (23, 2),
}
RELATIVE_UNITS = {"分钟": 60, "小时": 3600, "天": 86400, "周": 604800}

_CN = "一二两三四五六七八九十"
_NUM = r"\d{1,2}|[" + _CN + r"]{1,3}"
_WIN = "大半夜|晚上|深夜|清晨|中午|午后|下午|饭点|凌晨|上午|晚"
_RANGE_RE = re.compile(
    r"^\s*(?P<win>" + _WIN + r")?\s*"
    r"(?P<h1>" + _NUM + r")\s*[点时:：]?\s*(?:(?P<half1>半)|(?P<m1>" + _NUM + r")\s*分?)?\s*"
    r"(?:到|至|~|～|-|—)\s*"
    r"(?P<h2>" + _NUM + r")\s*[点时:：]?\s*(?:(?P<half2>半)|(?P<m2>" + _NUM + r")\s*分?)?\s*$"
)
_POINT_RE = re.compile(
    r"^\s*(?P<win>" + _WIN + r")?\s*"
    r"(?P<h1>" + _NUM + r")\s*[点时:：]\s*(?:(?P<half1>半)|(?P<m1>" + _NUM + r")\s*分?)?\s*多?\s*$"
)
_WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5,
            "日": 6, "天": 6, "1": 0, "2": 1, "3": 2, "4": 3,
            "5": 4, "6": 5, "7": 6}
_CN_DIGIT = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}


def parse_time_range(text: str, *, now: datetime | None = None,
                     tz: tzinfo | None = None) -> TimeRange:
    """唯一入口：把中文时间描述解析为时间范围，失败抛 TimeParseError。"""
    if now is None:
        now = datetime.now(tz)
    elif tz is not None:
        now = now.astimezone(tz)
    # 统一输出 naive 墙钟时间：tz 仅用于确定"现在"，避免返回 aware/naive 混合
    # 导致下游（如 log_filter）直接比较时抛 TypeError。
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    s = text.strip()
    if not s:
        raise TimeParseError("时间描述为空")
    guess = TimeRange(now - timedelta(hours=1), now, s, 0.4)
    try:
        for matcher in (_match_absolute, _match_relative, _match_range, _match_fuzzy):
            result = matcher(s, now)
            if result is not None:
                return result
    except (ValueError, OverflowError) as exc:
        # 非法中文数字组合等（如"两两小时前"）：不让 ValueError 冒泡，转中文解析错误
        raise TimeParseError(
            "时间描述包含无法理解的成分（%s）：%s" % (exc, s), guess) from exc
    raise TimeParseError("无法理解时间描述：" + s, guess)


def _match_absolute(s: str, now: datetime) -> TimeRange | None:
    """匹配绝对时间表达（含日期时间戳 / 月日 / 时刻），置信度 1.0。"""
    s = s.strip()
    today = now.date()
    try:
        m = re.fullmatch(
            r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[ T]+(\d{1,2})[:：](\d{2})(?::(\d{2}))?)?",
            s)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if m.group(4) is not None:
                t = datetime(y, mo, d, int(m.group(4)), int(m.group(5)), int(m.group(6) or 0))
                return TimeRange(t, t, s, 1.0)
            return _whole_day(date(y, mo, d), s, 1.0)
        m = re.fullmatch(
            r"(" + _NUM + r")月(" + _NUM + r")[日号]?(?:[ T]+(\d{1,2})[:：](\d{2})(?::(\d{2}))?)?",
            s)
        if m:
            mo, d = _num(m.group(1)), _num(m.group(2))
            if m.group(3) is not None:
                t = datetime(today.year, mo, d, int(m.group(3)), int(m.group(4)), int(m.group(5) or 0))
                return TimeRange(t, t, s, 1.0)
            return _whole_day(date(today.year, mo, d), s, 1.0)
        m = re.fullmatch(r"(\d{1,2})[:：](\d{2})(?::(\d{2}))?", s)
        if m:
            t = datetime(today.year, today.month, today.day,
                         int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
            return TimeRange(t, t, s, 1.0)
    except ValueError:
        return None
    return None


def _match_relative(s: str, now: datetime) -> TimeRange | None:
    """匹配相对时间表达（n分钟前/昨天/上周X/上周），置信度 0.7。"""
    s = s.strip()
    today = now.date()
    if s == "刚刚":
        return TimeRange(now - timedelta(minutes=1), now, s, 0.7)
    m = re.fullmatch(r"(\d{1,4}|[" + _CN + r"]{1,3})\s*(分钟|小时|天|周)\s*前", s)
    if m:
        sec = _num(m.group(1)) * RELATIVE_UNITS[m.group(2)]
        return TimeRange(now - timedelta(seconds=sec), now, s, 0.7)
    if s == "昨天":
        return _whole_day(today - timedelta(days=1), s)
    if s == "前天":
        return _whole_day(today - timedelta(days=2), s)
    if s == "大前天":
        return _whole_day(today - timedelta(days=3), s)
    if s == "上周":
        monday = today - timedelta(days=today.weekday())
        start = datetime(monday.year, monday.month, monday.day) - timedelta(days=7)
        return TimeRange(start, datetime(monday.year, monday.month, monday.day), s, 0.7)
    if s in ("本周", "这周"):
        monday = today - timedelta(days=today.weekday())
        start = datetime(monday.year, monday.month, monday.day)
        return TimeRange(start, start + timedelta(days=7), s, 0.7)
    m = re.fullmatch(r"(?:上|本|这|前)?(?:周|星期)([一二三四五六日天1-7])", s)
    if m:
        monday = today - timedelta(days=today.weekday())
        target = monday + timedelta(days=_WEEKDAY[m.group(1)])
        if s.startswith(("上", "前")):
            target -= timedelta(days=7)
        return _whole_day(target, s)
    return None


def _match_range(s: str, now: datetime) -> TimeRange | None:
    """匹配范围表达（日期词+时段/数字区间），置信度按主导词取。"""
    s = s.strip()
    today = now.date()
    if s == "昨晚":
        d = today - timedelta(days=1)
        start = datetime(d.year, d.month, d.day, 18, 0)
        return TimeRange(start, start + timedelta(hours=6), s, 0.7)
    if s == "今晚":
        start = datetime(today.year, today.month, today.day, 18, 0)
        return TimeRange(start, start + timedelta(hours=5), s, 0.7)
    base, rest, has_day, night = _extract_day(s, now)
    if rest in FUZZY_WINDOWS:
        a, b = FUZZY_WINDOWS[rest]
        start = datetime(base.year, base.month, base.day, a, 0)
        end = datetime(base.year, base.month, base.day, b, 0)
        if b <= a:
            end += timedelta(days=1)
        return TimeRange(start, end, s, 0.7 if has_day else 0.4)
    m = _RANGE_RE.fullmatch(rest)
    if m:
        win = m.group("win")
        if night and win is None:
            win = "晚"
        h1, mi1 = _point(m, "1")
        h2, mi2 = _point(m, "2")
        if win:
            h1, h2 = _adjust_hour(win, h1), _adjust_hour(win, h2)
        elif h1 >= 12 and h2 < 12 and h2 + 12 > h1:
            h2 += 12
        start = datetime(base.year, base.month, base.day, h1, mi1)
        end = datetime(base.year, base.month, base.day, h2, mi2)
        if end <= start:
            end += timedelta(days=1)
        return TimeRange(start, end, s, 0.7 if has_day else 1.0)
    m = _POINT_RE.fullmatch(rest)
    if m:
        win = m.group("win")
        if night and win is None:
            win = "晚"
        h1, mi1 = _point(m, "1")
        if win:
            h1 = _adjust_hour(win, h1)
        start = datetime(base.year, base.month, base.day, h1, mi1)
        return TimeRange(start, start + timedelta(hours=1), s, 0.7 if has_day else 1.0)
    return None


def _match_fuzzy(s: str, now: datetime) -> TimeRange | None:
    """匹配模糊时段词（凌晨/下午/深夜等，可带日期前缀），置信度 0.4。"""
    s = s.strip()
    base, rest, _has_day, _night = _extract_day(s, now)
    if rest not in FUZZY_WINDOWS:
        return None
    a, b = FUZZY_WINDOWS[rest]
    start = datetime(base.year, base.month, base.day, a, 0)
    end = datetime(base.year, base.month, base.day, b, 0)
    if b <= a:
        end += timedelta(days=1)
    return TimeRange(start, end, s, 0.4)


def _extract_day(s: str, now: datetime):
    """解析日期前缀，返回 (锚点日期, 剩余时间串, 是否含日期词, 是否夜间语境)。"""
    today = now.date()
    if s.startswith("今晚"):
        return today, s[2:].strip(), True, True
    if s.startswith("昨晚"):
        return today - timedelta(days=1), s[2:].strip(), True, True
    for word, delta in (("大前天", -3), ("前天", -2), ("昨天", -1), ("今天", 0), ("明天", 1)):
        if s.startswith(word):
            return today + timedelta(days=delta), s[len(word):].strip(), True, False
    m = re.match(r"^(上|本|这|前)?(?:周|星期)([一二三四五六日天1-7])", s)
    if m:
        monday = today - timedelta(days=today.weekday())
        target = monday + timedelta(days=_WEEKDAY[m.group(2)])
        if m.group(1) in ("上", "前"):
            target -= timedelta(days=7)
        return target, s[m.end():].strip(), True, False
    return today, s.strip(), False, False


def _adjust_hour(win: str, h: int) -> int:
    """按窗口词把 12 小时制数字换算为 24 小时制。"""
    if win is None:
        return h
    if win in ("深夜", "大半夜"):
        if h >= 12:
            return h - 12
        if h > 3:
            return h + 12
        return h
    if win in ("凌晨", "清晨"):
        return 0 if h == 12 else h
    if win in ("上午",):
        return h
    if win in ("中午", "饭点"):
        return h + 12 if h < 11 else h
    return h + 12 if h < 12 else h


def _point(m: re.Match, tag: str) -> tuple[int, int]:
    """从正则匹配中取 (小时, 分钟)。"""
    h = _num(m.group("h" + tag))
    if m.group("half" + tag):
        return h, 30
    mi = m.group("m" + tag)
    return h, (_num(mi) if mi is not None else 0)


def _whole_day(d: date, s: str, conf: float = 0.7) -> TimeRange:
    """构造某日全天范围。"""
    start = datetime(d.year, d.month, d.day)
    return TimeRange(start, start + timedelta(days=1), s, conf)


def _num(x: str | None) -> int:
    """阿拉伯或中文数字字符串转整数。"""
    if x is None:
        return 0
    return int(x) if x.isdigit() else _cn2int(x)


def _cn2int(s: str) -> int:
    """中文数字（一~九、十、十一~二十三、两）转整数；无法识别抛 ValueError。

    注意：不能静默返回 0（否则"两两小时前"会被解析成"刚刚"），必须让上层
    匹配失败并最终转 TimeParseError。
    """
    if s in _CN_DIGIT:
        return _CN_DIGIT[s]
    if s.startswith("十"):
        return 10 + (_cn2int(s[1:]) if len(s) > 1 else 0)
    if "十" in s:
        a, b = s.split("十", 1)
        va = _cn2int(a) if a else 0
        vb = _cn2int(b) if b else 0
        return va * 10 + vb
    raise ValueError("无法识别中文数字：%s" % s)
