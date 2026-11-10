"""time_parser.py 基线测试（纯 Python，固定 now 保证确定性）。"""
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from time_parser import TimeParseError, parse_time_range

NOW = datetime(2026, 11, 11, 1, 30)  # 周三，2026-11-11 01:30


def p(text, now=NOW):
    return parse_time_range(text, now=now)


class TestAbsolute(unittest.TestCase):
    def test_full_date(self):
        r = p("2026-11-01")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 1), datetime(2026, 11, 2)))
        self.assertEqual(r.confidence, 1.0)

    def test_full_date_time(self):
        r = p("2026-11-01 08:30")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 1, 8, 30),) * 2)

    def test_month_day(self):
        r = p("3月5日")
        self.assertEqual((r.start, r.end), (datetime(2026, 3, 5), datetime(2026, 3, 6)))

    def test_clock_today(self):
        r = p("23:15")
        self.assertEqual(r.start, datetime(2026, 11, 11, 23, 15))


class TestRelative(unittest.TestCase):
    def test_just_now(self):
        r = p("刚刚")
        self.assertEqual((r.start, r.end), (NOW.replace(minute=29), NOW))

    def test_hours_ago_digit(self):
        r = p("3小时前")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 10, 22, 30), NOW))

    def test_hours_ago_chinese(self):
        r = p("两小时前")
        self.assertEqual(r.start, datetime(2026, 11, 10, 23, 30))

    def test_yesterday_whole_day(self):
        r = p("昨天")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 10), datetime(2026, 11, 11)))

    def test_day_before(self):
        r = p("大前天")
        self.assertEqual(r.start, datetime(2026, 11, 8))

    def test_last_week(self):
        # NOW 是周三 2026-11-11，本周一 = 11-09，上周 = 11-02 ~ 11-09
        r = p("上周")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 2), datetime(2026, 11, 9)))

    def test_this_week(self):
        r = p("本周")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 9), datetime(2026, 11, 16)))

    def test_weekday_words(self):
        self.assertEqual(p("上周三").start, datetime(2026, 11, 4))
        self.assertEqual(p("本周五").start, datetime(2026, 11, 13))
        self.assertEqual(p("星期日").start, datetime(2026, 11, 15))


class TestRangeAndFuzzy(unittest.TestCase):
    def test_last_night(self):
        r = p("昨晚")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 10, 18), datetime(2026, 11, 11, 0)))

    def test_tonight_point(self):
        r = p("今晚8点")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 20), datetime(2026, 11, 11, 21)))

    def test_afternoon_range(self):
        r = p("今天下午3点到5点")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 15), datetime(2026, 11, 11, 17)))

    def test_range_with_half(self):
        r = p("下午2点半到4点")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 14, 30), datetime(2026, 11, 11, 16)))

    def test_cross_midnight_range(self):
        r = p("晚上11点到1点")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 23), datetime(2026, 11, 12, 1)))

    def test_fuzzy_window(self):
        r = p("凌晨")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 0), datetime(2026, 11, 11, 5)))

    def test_fuzzy_cross_midnight(self):
        r = p("深夜")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 22), datetime(2026, 11, 12, 3)))


class TestErrors(unittest.TestCase):
    def test_empty(self):
        with self.assertRaises(TimeParseError):
            p("")

    def test_unrecognized(self):
        with self.assertRaises(TimeParseError):
            p("一亿年前")

    def test_invalid_cn_number(self):
        # 两两小时前：非法中文数字组合，必须报错而不是静默解析
        with self.assertRaises(TimeParseError):
            p("两两小时前")


class TestNewExpressions(unittest.TestCase):
    """2026-11-11 增强：补齐常用日历/时长词 + 跨午夜区间修复。"""

    def test_half_hour_ago(self):
        r = p("半小时前")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 1, 0), NOW))

    def test_tomorrow_night(self):
        r = p("明晚")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 12, 18), datetime(2026, 11, 12, 23)))

    def test_tomorrow_night_point(self):
        r = p("明晚8点")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 12, 20), datetime(2026, 11, 12, 21)))

    def test_last_month(self):
        r = p("上个月")
        self.assertEqual((r.start, r.end), (datetime(2026, 10, 1), datetime(2026, 11, 1)))

    def test_this_month_aliases(self):
        for text in ("本月", "这个月", "这月"):
            r = p(text)
            self.assertEqual((r.start, r.end), (datetime(2026, 11, 1), datetime(2026, 12, 1)), text)

    def test_year_expressions(self):
        self.assertEqual((p("去年").start, p("去年").end), (datetime(2025, 1, 1), datetime(2026, 1, 1)))
        self.assertEqual((p("今年").start, p("今年").end), (datetime(2026, 1, 1), datetime(2027, 1, 1)))

    def test_cross_midnight_with_window_regression(self):
        # 回归：修复前 "晚上11点到1点" 的终点被 _adjust_hour 换算成 13 点
        r = p("晚上11点到1点")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 23), datetime(2026, 11, 12, 1)))

    def test_cross_midnight_deep_night(self):
        r = p("深夜11点到2点")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 23), datetime(2026, 11, 12, 2)))

    def test_normal_night_range_unaffected(self):
        r = p("晚上9点到11点")
        self.assertEqual((r.start, r.end), (datetime(2026, 11, 11, 21), datetime(2026, 11, 11, 23)))


if __name__ == "__main__":
    unittest.main()
