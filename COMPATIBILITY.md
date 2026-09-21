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

Detailed table: [`docs/time-expressions.md`](./docs/time-expressions.md)

| Class | Examples | Status |
|-------|----------|--------|
| Relative day | 昨天下午 / 今天 / 前天 | Supported |
| Relative hours | 3 小时前 / 半小时前 | Supported |
| Absolute | 2026-09-20 14:00 | Supported |
| Ranges | 昨天 9 点到 18 点 | Supported |
| Fuzzy month/year | 去年 / 上个月 | Parser-dependent; see docs |
| Unsupported slang | 「上周摸鱼那天」 | **Not supported** — returns empty/error per core rules |

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

## How to verify locally

```bash
# plugin tests
npm ci && npx vitest run

# optional upstream suite if you have the vendored source tree
python scripts/run-upstream-tests.py
```
