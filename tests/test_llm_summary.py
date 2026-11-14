"""llm_summary.py 基线测试：提示词构造 / 响应解析错误矩阵 / 离线分析 / 重试语义。"""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import llm_summary
from llm_summary import (
    LLMError,
    AnalysisResult,
    analyze_logs,
    analyze_offline,
    build_prompt,
    parse_json,
    _truncate_sample,
)

TR = SimpleNamespace(start=datetime(2026, 11, 14, 8, 0), end=datetime(2026, 11, 14, 9, 0),
                     expr_source="昨天上午")


def make_resp(summary="结论", evidence=None, suggestions=None, confidence="high", usage=None):
    content = {"summary": summary,
               "evidence": ["证据1"] if evidence is None else evidence,
               "suggestions": ["建议1"] if suggestions is None else suggestions,
               "confidence": confidence}
    resp = {"choices": [{"message": {"content": __import__("json").dumps(content, ensure_ascii=False)}}]}
    if usage is not None:
        resp["usage"] = usage
    return resp


class TestTruncateSample(unittest.TestCase):
    def test_under_limit_unchanged(self):
        self.assertEqual(_truncate_sample(["a", "b"]), ["a", "b"])

    def test_over_limit_truncated(self):
        sample = ["x" * 50 for _ in range(200)]  # 远超 4000 字符
        out = _truncate_sample(sample)
        self.assertLess(len(out), 200)
        total = sum(len(line) + 1 for line in out)
        self.assertLessEqual(total, 4000)

    def test_exact_boundary(self):
        sample = ["y" * 9, "z" * 9]  # 每行占 10
        out = _truncate_sample(sample, max_chars=20)
        self.assertEqual(out, sample)
        out2 = _truncate_sample(sample, max_chars=19)
        self.assertEqual(out2, [sample[0]])


class TestBuildPrompt(unittest.TestCase):
    def test_contains_question_range_and_sample(self):
        prompt = build_prompt("为什么报错", TR, ["2026-11-14 08:00:00 ERROR x"])
        self.assertIn("为什么报错", prompt)
        self.assertIn("2026-11-14 08:00:00", prompt)
        self.assertIn("昨天上午", prompt)
        self.assertIn("<log_sample>", prompt)

    def test_injection_guard_note_present(self):
        # 防注入说明必须存在：样本内容不是指令
        prompt = build_prompt("q", TR, ["任意内容"])
        self.assertIn("不是指令", prompt)

    def test_sample_truncated_in_prompt(self):
        long_sample = ["x" * 100 for _ in range(100)]
        prompt = build_prompt("q", TR, long_sample)
        self.assertLess(len(prompt), 6000)


class TestParseJson(unittest.TestCase):
    def test_valid_with_usage(self):
        r = parse_json(make_resp(usage={"total_tokens": 123}), ["a", "b"])
        self.assertIsInstance(r, AnalysisResult)
        self.assertEqual(r.summary, "结论")
        self.assertEqual(r.tokens_used, 123)

    def test_tokens_fallback_to_sample_len(self):
        r = parse_json(make_resp(), ["a", "b", "c"])
        self.assertEqual(r.tokens_used, 3)

    def test_evidence_capped_at_5_suggestions_at_3(self):
        r = parse_json(make_resp(evidence=[f"e{i}" for i in range(10)],
                                 suggestions=[f"s{i}" for i in range(10)]), ["a"])
        self.assertEqual(len(r.evidence), 5)
        self.assertEqual(len(r.suggestions), 3)

    def test_error_matrix(self):
        base = make_resp()
        cases = [
            ({}, "缺少 choices"),                                   # 无 choices
            ({"choices": []}, "缺少 choices"),                      # 空 choices
            ({"choices": [{"message": {"content": "not json"}}]}, "不是合法 JSON"),
            ({"choices": [{"message": {"content": "[1,2]"}}]}, "不是对象"),
            (make_resp(summary=""), "缺少 summary"),
            (make_resp(evidence=[]), "evidence 非法"),
            (make_resp(evidence="not-a-list"), "evidence 非法"),
            (make_resp(suggestions="x"), "suggestions 非法"),
            (make_resp(confidence="高"), "confidence 非法"),
        ]
        for resp, msg in cases:
            with self.assertRaises(LLMError) as ctx:
                parse_json(resp, ["a"])
            self.assertIn(msg, str(ctx.exception))
        # 每个合法字段组合的组合越界不在此列——空 evidence 由 or 兜底逻辑单独覆盖
        with self.assertRaises(LLMError):
            parse_json(make_resp(evidence=[]), ["a"])  # 空列表是非法（or 兜底已修，直接断言）


class TestAnalyzeOffline(unittest.TestCase):
    def test_with_counts(self):
        stats = {"errors": [], "warns": []}
        counts = {"errors": 5, "warns": 2, "infos": 1}
        r = analyze_offline(["l1", "l2"], stats, counts)
        self.assertIn("最高频级别 errors（5 条）", r.summary)
        self.assertIn("优先检查 ERROR", r.suggestions[0])
        self.assertEqual(r.confidence, "low")
        self.assertEqual(r.tokens_used, 0)

    def test_empty_everything(self):
        r = analyze_offline([], {}, None)
        self.assertIn("未发现", r.summary)
        self.assertIn("扩大时间窗口", r.suggestions[0])

    def test_zero_count_buckets_filtered(self):
        r = analyze_offline([], {"errors": []}, {"errors": 0, "infos": 0})
        self.assertIn("未发现", r.summary)


class TestAnalyzeLogsRetry(unittest.TestCase):
    def setUp(self):
        self.orig = llm_summary.call_llm

    def tearDown(self):
        llm_summary.call_llm = self.orig

    def test_retry_then_success(self):
        calls = {"n": 0}

        def flaky(prompt, cfg):
            calls["n"] += 1
            if calls["n"] == 1:
                raise LLMError("第一次失败")
            return make_resp()

        llm_summary.call_llm = flaky
        r = analyze_logs("q", TR, ["a"], None)
        self.assertEqual(r.summary, "结论")
        self.assertEqual(calls["n"], 2)

    def test_both_fail_raises(self):
        def always(prompt, cfg):
            raise LLMError("持续失败")

        llm_summary.call_llm = always
        with self.assertRaises(LLMError):
            analyze_logs("q", TR, ["a"], None)


if __name__ == "__main__":
    unittest.main()
