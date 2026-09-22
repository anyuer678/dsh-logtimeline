# Compatibility Matrix

`dsh-logtimeline` is a **DeepSeek Harness (DSH) plugin**. Host packages evolve quickly;
this file records what this repository claims to support and how we verify.

## Plugin package

| Field | Value |
|-------|--------|
| Plugin id | `dsh-logtimeline` |
| Entry | `src/index.ts` (DSH assembly) + framework-agnostic `src/query.ts` |
| Vendored CLI | `python/` (see `python/VENDORED.md`) |
| License | GPL-3.0 |

## Host / DSH line

| Host package | Supported | Notes |
|--------------|-----------|--------|
| `@deepseek-ai/dsh-tools` (RC / cordis patch line) | **Best-effort** | Host APIs may break; pin versions in your project lockfile |
| Older stable DSH without `defineTool` schema | **No** | Plugin registers tools via current defineTool contract |
| Non-DSH Python CLI only | **Partial** | Use `python/lq.py` offline without host |

Exact host commit / version pins used in CI:

| Date | Host / runner | CI signal |
|------|----------------|-----------|
| 2026-09 | GitHub Actions Test + secret-scan | See badge / Actions latest run on `main` |

> If Actions is green on `main`, the **in-repo vitest + security tests** passed.
> Upstream vendored Python suite (see `python/VENDORED.md`) is run when
> `scripts/run-upstream-tests.py` is executed in an environment with the upstream tree.

## Language / OS

| Item | Support |
|------|---------|
| Node | 18+ (CI uses current LTS on Actions) |
| Python | 3.10+ for vendored CLI (`py` launcher on Windows) |
| OS | Linux CI primary; Windows path probing supported via `py` |
| Network | **Not required** for log query (offline-first) |

## Time expression support (summary)

Detailed table: [`docs/time-expressions.md`](./docs/time-expressions.md).
Contract tests: `tests/compat_time.test.ts` (T01–T15 against `tests/fixtures/demo.log`).

| ID | Class | Examples | Status |
|----|-------|----------|--------|
| T01 | Relative day (today) | 今天下午 | **Supported** (day + part-of-day) |
| T01b | Bare 今天 | 今天 | **Not supported** — parser has no whole-day "today" matcher (only day-prefix + window). Use 今天下午 / 今天上午 or an absolute date. |
| T02 | Relative day (yesterday) | 昨天 / 昨晚 | Supported |
| T03 | Day before | 前天 | Supported |
| T04 | Relative hours | 3 小时前 | Supported |
| T04b | 半小时前 | 半小时前 | **Not supported** — relative numeral class is digits/一二两三四五六七八九十, not 半. Use 30 分钟前. |
| T05 | Relative minutes | 30 分钟前 | Supported |
| T06 | Absolute date | 2026-07-03 | Supported |
| T07 | Absolute datetime | 2026-07-03 14:30 | Supported |
| T08 | Ranges | 昨天 9 点到 18 点 | Supported |
| T09 | This week | 本周 / 这周 | Supported (Mon–Sun window) |
| T10 | Last week | 上周 | Supported |
| T11 | This month | 本月 / 这个月 | **Not supported** — no month-window matcher |
| T12 | Last month | 上个月 | **Not supported** — no month-window matcher |
| T13 | Year windows | 今年 / 去年 | **Not supported** — no year-window matcher |
| T14 | Part-of-day | 上午 / 下午 / 晚上 | Supported (fuzzy windows) |
| T15 | Unsupported slang | 「上周摸鱼那天」 | **Not supported** — fail closed (error / bounded guess); never a silent full-file scan |

## Security / output limits (plugin)

| Limit | Default intent |
|-------|----------------|
| max lines | capped (see `src/query.ts` / README; historically 5000) |
| stdout buffer | hard cap to avoid memory blowup |
| ANSI / control chars | stripped |
| timeout | enforced on CLI invoke |
| Path traversal | denied outside allowed roots when host applies sandbox |

## Breaking-change policy

1. Host tool-schema changes → bump plugin minor + update this matrix + CHANGELOG.
2. Vendored CLI upstream sync → must refresh `python/VENDORED.md` commit pin.
3. Dropping a host line → mark **No** here before code removal.

## Upstream suite

| Item | Status |
|------|--------|
| Vendored `python/` tree | Present (see `python/VENDORED.md`) |
| Upstream `logtimeline/tests/` tree | **Not in this workspace** |
| `scripts/run-upstream-tests.py` | Offline-safe; **skips** with exit 0 when upstream `tests/` is absent |

This environment has no upstream `logtimeline/tests/` checkout, so the 124-case
upstream pytest suite is **skipped** here. To run it elsewhere:

```bash
UPSTREAM_TESTS=/path/to/logtimeline/tests python scripts/run-upstream-tests.py
```

The script puts `python/` first on `sys.path` so the suite exercises the
**vendored** modules, not a different logtimeline install. In-repo vitest
(`tests/query.test.ts`, `tests/compat_time.test.ts`) is the always-on gate.

## How to verify locally

```bash
# plugin tests (builds lib/ first so host.test.ts finds it)
npm ci && npm test

# vitest only (after an existing build)
npm run test:only

# optional upstream suite if you have the vendored source tree
python scripts/run-upstream-tests.py
```
