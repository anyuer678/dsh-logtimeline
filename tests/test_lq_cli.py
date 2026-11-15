"""lq.py CLI 集成测试：keyword/levels 过滤参数透传（subprocess 走真实链路）。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LQ = ROOT / "python" / "lq.py"

LOG = (
    "2026-11-14 08:00:00 INFO user login ok\n"
    "2026-11-14 08:05:00 ERROR db connection refused\n"
    "2026-11-14 09:00:00 WARN db slow query\n"
    "2026-11-14 10:00:00 INFO user logout\n"
)


def run_lq(*argv):
    proc = subprocess.run(
        [sys.executable, str(LQ), *argv, "--no-llm", "--json"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    return proc


class TestLqKeywordLevels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lq_")
        self.addCleanup(self.tmp.cleanup)
        self.log = str(Path(self.tmp.name) / "a.log")
        Path(self.log).write_text(LOG, encoding="utf-8")

    def test_keyword_filter(self):
        p = run_lq("2026-11-14", "--files", self.log, "--keyword", "db")
        self.assertEqual(p.returncode, 0, p.stderr)
        payload = json.loads(p.stdout)
        self.assertEqual(payload["filter"]["total_matched"], 2)
        self.assertEqual(payload["filter"]["keyword"], "db")

    def test_levels_filter(self):
        p = run_lq("2026-11-14", "--files", self.log, "--levels", "errors,warns")
        self.assertEqual(p.returncode, 0, p.stderr)
        payload = json.loads(p.stdout)
        self.assertEqual(payload["filter"]["total_matched"], 2)
        self.assertEqual(payload["filter"]["levels"], ["errors", "warns"])

    def test_combined(self):
        p = run_lq("2026-11-14", "--files", self.log, "--keyword", "db", "--levels", "warns")
        self.assertEqual(p.returncode, 0, p.stderr)
        payload = json.loads(p.stdout)
        self.assertEqual(payload["filter"]["total_matched"], 1)
        self.assertIn("slow query", payload["filter"]["lines"][0]["raw"])

    def test_no_match_still_emits_json_exit_2(self):
        p = run_lq("2026-11-14", "--files", self.log, "--keyword", "不存在的词")
        self.assertEqual(p.returncode, 2)
        payload = json.loads(p.stdout)
        self.assertEqual(payload["filter"]["total_matched"], 0)

    def test_unknown_level_rejected(self):
        p = run_lq("2026-11-14", "--files", self.log, "--levels", "error")  # 正确名是 errors
        self.assertEqual(p.returncode, 1)
        self.assertIn("未知的日志级别分桶", p.stderr)
        self.assertIn("errors", p.stderr)

    def test_without_keyword_unchanged(self):
        p = run_lq("2026-11-14", "--files", self.log)
        self.assertEqual(p.returncode, 0, p.stderr)
        payload = json.loads(p.stdout)
        self.assertEqual(payload["filter"]["total_matched"], 4)
        self.assertIsNone(payload["filter"]["keyword"])
        self.assertIsNone(payload["filter"]["levels"])


if __name__ == "__main__":
    unittest.main()
