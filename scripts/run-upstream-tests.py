"""Run the upstream LogTimeline test suite against the VENDORED python/ code.

sys.path 优先指向 vendored 目录，确保 import 的是 dsh-logtimeline/python 下的模块
（而非 logtimeline 仓库原代码），验证 vendoring 改动没有破坏任何上游行为。
"""
import sys
from pathlib import Path

VENDORED = Path(__file__).resolve().parent
UPSTREAM_TESTS = VENDORED.parent.parent / "logtimeline" / "tests"

sys.path.insert(0, str(VENDORED))

import pytest

print(f"vendored dir : {VENDORED}")
print(f"upstream tests: {UPSTREAM_TESTS}")
print(f"import lq from: {Path(__import__('lq').__file__).resolve()}")
raise SystemExit(pytest.main([str(UPSTREAM_TESTS), "-q"]))
