"""log_filter.py 基线测试：时间戳识别 / 流式过滤 / Top-K / 多文件合并 / 级别分桶。"""
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from log_filter import (
    LogFormatError,
    filter_logs,
    filter_stream,
    iter_filter_lines,
    summarize_hits,
)
from time_parser import TimeRange

DAY = TimeRange(datetime(2026, 11, 14, 0, 0), datetime(2026, 11, 14, 23, 59, 59), "day", 1.0)


def stream(lines):
    return [ll.raw for ll in iter_filter_lines(iter(lines), DAY)]


class TestTimestampDetection(unittest.TestCase):
    def test_formats_recognized(self):
        for line in (
            "2026-11-14 08:00:00 INFO a",
            "2026-11-14T08:00:00 INFO a",
            "14/Nov/2026:08:00:00 +0800 GET /x",
            "Nov 14 08:00 systemd[1]: a",
            "08:00:00 cron: a",
        ):
            self.assertIsNotNone(
                __import__("log_filter").detect_ts_format(line), line)

    def test_plain_line_no_ts(self):
        self.assertIsNone(__import__("log_filter").detect_ts_format("hello world"))

    def test_lineno_and_raw_preserved(self):
        out = iter_filter_lines(iter(["no ts here", "2026-11-14 08:00:00 x"]), DAY)
        rows = list(out)
        self.assertEqual(rows[0].lineno, 1)
        self.assertIsNone(rows[0].timestamp)
        self.assertEqual(rows[1].lineno, 2)
        self.assertEqual(rows[1].timestamp, datetime(2026, 11, 14, 8, 0, 0))


class TestCrossMidnight(unittest.TestCase):
    def test_sequence_advance(self):
        # 无日期格式：本行早于上一行 → 日期 +1
        rows = list(iter_filter_lines(iter(["23:59:00 a", "00:00:30 b"]), DAY))
        self.assertEqual(rows[0].timestamp, datetime(2026, 11, 14, 23, 59, 0))
        self.assertEqual(rows[1].timestamp, datetime(2026, 11, 15, 0, 0, 30))

    def test_dual_day_probe_picks_in_window(self):
        # 窗口跨午夜时，优先取落在窗口内的那一个
        night = TimeRange(datetime(2026, 11, 14, 22, 0), datetime(2026, 11, 15, 6, 0), "n", 1.0)
        rows = list(iter_filter_lines(iter(["00:00:30 b"]), night))
        self.assertEqual(rows[0].timestamp, datetime(2026, 11, 15, 0, 0, 30))

    def test_month_day_format_no_advance(self):
        # "Nov 14 08:00" 自带月日，同日内乱序不做跨日推进
        rows = list(iter_filter_lines(
            iter(["Nov 14 09:00 a", "Nov 14 08:00 b"]), DAY))
        self.assertEqual(rows[1].timestamp, datetime(2026, 11, 14, 8, 0))


class TestFilterStream(unittest.TestCase):
    LINES = [
        "2026-11-13 23:00:00 INFO old",        # 窗口外
        "2026-11-14 08:00:00 INFO start",
        "2026-11-14 08:05:00 ERROR db down",
        "2026-11-14 09:00:00 WARN slow query",
        "plain line without timestamp",
        "2026-11-14 10:00:00 DEBUG done",
    ]

    def test_window_and_stats(self):
        r = filter_stream(self.LINES, DAY)
        self.assertEqual(r.total_matched, 4)
        self.assertFalse(r.truncated)
        self.assertTrue(r.time_span_found)
        self.assertEqual(r.stats, {"errors": 1, "warns": 1, "infos": 1,
                                   "debugs": 1, "others": 0})
        self.assertEqual(r.lines[0].timestamp, datetime(2026, 11, 14, 8, 0, 0))

    def test_topk_truncation_keeps_latest(self):
        r = filter_stream(self.LINES, DAY, max_lines=2)
        self.assertEqual(r.total_matched, 4)
        self.assertTrue(r.truncated)
        self.assertEqual([ll.raw for ll in r.lines],
                         ["2026-11-14 09:00:00 WARN slow query",
                          "2026-11-14 10:00:00 DEBUG done"])

    def test_level_word_boundary(self):
        # "ERRORS"（复数）不进 errors 桶；小写 error 进
        r = filter_stream(["2026-11-14 08:00:00 ERRORS total 5",
                           "2026-11-14 08:01:00 an error occurred"], DAY)
        self.assertEqual(r.stats["errors"], 1)
        self.assertEqual(r.stats["others"], 1)

    def test_empty_input(self):
        r = filter_stream([], DAY)
        self.assertEqual(r.total_matched, 0)
        self.assertFalse(r.time_span_found)


class TestFilterLogs(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory(prefix="lf_")
        self.addCleanup(self.tmp.cleanup)
        self.p1 = str(Path(self.tmp.name) / "a.log")
        self.p2 = str(Path(self.tmp.name) / "b.log")
        Path(self.p1).write_text(
            "2026-11-14 08:00:00 INFO from-a\n2026-11-14 09:00:00 ERROR a-err\n",
            encoding="utf-8")
        Path(self.p2).write_text(
            "2026-11-14 08:30:00 WARN from-b\n", encoding="utf-8")
        self.paths = [self.p1, self.p2]

    def test_merge_sorted_and_file_stats(self):
        r = filter_logs(self.paths, DAY)
        self.assertEqual(r.total_matched, 3)
        self.assertEqual([ll.timestamp.hour for ll in r.lines], [8, 8, 9])  # 跨文件按时间升序
        self.assertEqual(r.file_stats, {self.p1: 2, self.p2: 1})
        self.assertEqual(r.file_errors, {})

    def test_missing_file_recorded_others_continue(self):
        r = filter_logs([str(Path(self.tmp.name) / "nope.log"), self.p2], DAY)
        self.assertIn("nope.log", str(r.file_errors))
        self.assertEqual(r.total_matched, 1)

    def test_gbk_fallback(self):
        p = str(Path(self.tmp.name) / "gbk.log")
        Path(p).write_bytes("2026-11-14 08:00:00 INFO 中文内容\n".encode("gbk"))
        r = filter_logs([p], DAY)
        self.assertEqual(r.total_matched, 1)
        self.assertIn("中文内容", r.lines[0].raw)

    def test_single_missing_file_still_recorded(self):
        # 设计行为：打开失败记入 file_errors（键=完整路径）而不是抛出
        r = filter_logs([str(Path(self.tmp.name) / "missing.log")], DAY)
        self.assertTrue(any("missing.log" in k for k in r.file_errors))
        self.assertEqual(r.total_matched, 0)


class TestKeywordLevelsFiltering(unittest.TestCase):
    """2026-11-14 增强：keyword/levels 过滤参数（窗口 + 关键词 + 级别三重命中）。"""

    LINES = [
        "2026-11-14 08:00:00 INFO user login ok",
        "2026-11-14 08:05:00 ERROR db connection refused",
        "2026-11-14 09:00:00 WARN db slow query",
        "2026-11-14 10:00:00 INFO user logout",
    ]

    def test_keyword_case_insensitive(self):
        r = filter_stream(self.LINES, DAY, keyword="DB")
        self.assertEqual(r.total_matched, 2)
        self.assertEqual(r.stats, {"errors": 1, "warns": 1, "infos": 0,
                                   "debugs": 0, "others": 0})

    def test_levels_only(self):
        r = filter_stream(self.LINES, DAY, levels=["errors", "warns"])
        self.assertEqual(r.total_matched, 2)

    def test_combined_keyword_and_levels(self):
        r = filter_stream(self.LINES, DAY, keyword="db", levels=["warns"])
        self.assertEqual(r.total_matched, 1)
        self.assertEqual(r.lines[0].raw, "2026-11-14 09:00:00 WARN db slow query")

    def test_stats_counts_post_filter(self):
        # stats 是全条件命中后的计数，不是窗口内全量
        r = filter_stream(self.LINES, DAY, levels=["infos"])
        self.assertEqual(r.stats["infos"], 2)
        self.assertEqual(r.stats["errors"], 0)

    def test_unknown_level_raises(self):
        # 拼写错误必须报错，而不是静默过滤掉一切
        with self.assertRaises(ValueError):
            filter_stream(self.LINES, DAY, levels=["error"])  # 正确名是 errors

    def test_filter_logs_with_keyword_and_file_stats(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="lf_kw_") as tmp:
            p1 = str(Path(tmp) / "a.log")
            Path(p1).write_text(
                "2026-11-14 08:00:00 INFO hit here\n"
                "2026-11-14 09:00:00 ERROR miss\n", encoding="utf-8")
            r = filter_logs([p1], DAY, keyword="hit")
            self.assertEqual(r.file_stats[p1], 1)
            self.assertEqual(r.total_matched, 1)


class TestSummarizeHits(unittest.TestCase):
    def test_buckets_and_topn(self):
        from log_filter import LogLine
        lines = [LogLine(i, datetime(2026, 11, 14, 8, i), f"2026-11-14 08:{i:02d}:00 ERROR e{i}")
                 for i in range(15)]
        b = summarize_hits(lines, top_n=10)
        self.assertEqual(len(b["errors"]), 10)
        self.assertEqual(b["warns"], [])


if __name__ == "__main__":
    unittest.main()
