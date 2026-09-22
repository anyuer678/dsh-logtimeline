"""Run the upstream LogTimeline test suite against the VENDORED python/ code.

sys.path 优先指向 vendored 目录，确保 import 的是 dsh-logtimeline/python 下的模块
（而非 logtimeline 仓库原代码），验证 vendoring 改动没有破坏任何上游行为。

Offline-safe: no network. If the upstream tests/ tree is absent, exit 0 with a
clear SKIP message (also recorded in COMPATIBILITY.md).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# vendored modules live in <repo>/python (NOT scripts/)
VENDORED = REPO / "python"
# 上游测试目录可通过环境变量 UPSTREAM_TESTS 指定（指向 vendored 来源仓库的 tests/）
UPSTREAM_TESTS = Path(
    os.environ.get("UPSTREAM_TESTS")
    or (REPO.parent / "logtimeline" / "tests")
)

sys.path.insert(0, str(VENDORED))

print(f"vendored dir : {VENDORED}")
print(f"upstream tests: {UPSTREAM_TESTS}")

if not VENDORED.is_dir():
    print(f"SKIP: vendored python tree missing at {VENDORED}")
    raise SystemExit(0)

if not UPSTREAM_TESTS.is_dir():
    print(
        "SKIP: upstream tests tree not found "
        f"({UPSTREAM_TESTS}); set UPSTREAM_TESTS to the logtimeline/tests path. "
        "See COMPATIBILITY.md → Upstream suite."
    )
    raise SystemExit(0)

import pytest  # noqa: E402  — import after path insert / skip gates

print(f"import lq from: {Path(__import__('lq').__file__).resolve()}")
raise SystemExit(pytest.main([str(UPSTREAM_TESTS), "-q"]))
