"""lq.py 离线降级集成测试：LLM 环境缺失时 fail-safe 到离线统计（exit 3，不失败）。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LQ = ROOT / "python" / "lq.py"

LOG = (
    "2026-11-14 08:00:00 ERROR db down\n"
    "2026-11-14 09:00:00 INFO recovered\n"
)


class TestLqOfflineFallback(unittest.TestCase):
    def test_missing_llm_env_falls_back_to_offline(self):
        with tempfile.TemporaryDirectory(prefix="lq_fb_") as tmp:
            log = str(Path(tmp) / "a.log")
            Path(log).write_text(LOG, encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if not k.startswith("LLM_")}
            env.setdefault("SYSTEMROOT", os.environ.get("SYSTEMROOT", ""))
            proc = subprocess.run(
                [sys.executable, str(LQ), "2026-11-14", "--files", log, "--json"],
                capture_output=True, text=True, encoding="utf-8", timeout=60, env=env,
            )
            self.assertEqual(proc.returncode, 3)  # 3 = LLM 缺失已降级为离线
            self.assertIn("离线", proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertIn("离线统计", payload["analysis"]["summary"])
            self.assertEqual(payload["analysis"]["tokens_used"], 0)


if __name__ == "__main__":
    unittest.main()
