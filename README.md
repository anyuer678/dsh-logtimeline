# dsh-logtimeline

Query local log files with **Chinese natural-language time expressions** — [LogTimeline](https://github.com/anyuer678/logtimeline) for [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (dsh).

Ask things like 「昨天下午」「3小时前」「凌晨12点」「上周三 14:00-15:00」and get the matching log lines, the resolved time range, and ERROR/WARN/INFO level stats — fully offline.

## Why

Coding agents constantly need to answer "what happened around 3pm yesterday?". Generic log tools make you write `grep` pipelines and timestamp math by hand. `log_query` resolves the fuzzy Chinese time expression for you and returns structured, machine-readable matches the agent can reason over directly.

## Features

- **Chinese time parsing** — absolute dates (`2026-07-03`, `7月3日 09:15`), relative (`3小时前`, `昨天`, `上周三`), fuzzy windows (`下午`, `凌晨`), and hour ranges (`14:00-15:00`), with a confidence score
- **Multi-format logs** — auto-detected timestamp formats, UTF-8/GBK fallback encoding, streaming filter (no full-file load)
- **Offline by default** — zero third-party Python dependencies; log contents never leave the machine. (The upstream CLI also supports optional LLM attribution via `LLM_BASE_URL`/`LLM_API_KEY`, not exposed here.)
- **Structured output** — canonical JSON (`time_range`, `filter`, `lines`, `stats`) rendered as readable text for the model

## Install

Prerequisites: a dsh profile (`web` or `headless`), and **Python 3.9+** (on Windows, the `py` launcher is auto-detected as a fallback).

**Local / development install** (from a checkout):

```sh
git clone https://github.com/anyuer678/dsh-logtimeline.git
dsh plugin --profile web add file:/path/to/dsh-logtimeline
```

**Community install**: once listed in [awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin), install via the plugin market (GitHub-only plugins are supported):

```sh
dsh plugin --profile web add dshmarket
# then: Settings → Plugin Market → search "dsh-logtimeline" → one-click install
```

Compatibility: tested against `@deepseek-ai/dsh-tools@0.1.0-rc.6` (the current harness release line, e.g. `dsh-base@0.1.0-rc.5`).

## Usage

Once installed, the agent can call the `log_query` tool directly:

> "用 log_query 查一下 demo.log 里昨天下午发生了什么" → `log_query(time_text: "昨天下午", files: ["demo.log"])`

| Parameter | Type | Description |
|---|---|---|
| `time_text` | string (required) | Chinese natural-language time, e.g. 「昨天下午」「3小时前」 |
| `files` | string[] | Log file paths (absolute or workspace-relative) |
| `dir` | string | Directory to scan recursively |
| `pattern` | string | Glob when `dir` is set (default `*.log`) |
| `max_lines` | number | Max lines returned (default 500; `0` = stats only) |
| `since` | string | RFC3339 absolute-time fallback when `time_text` fails to parse |
| `timezone` | string | IANA timezone name, e.g. `Asia/Shanghai` |

The tool runs in **offline mode** by default: it filters precisely (its unique value), and leaves root-cause reasoning to the agent itself. Oversized results are handled by the harness's own spill mechanism (`spill-policy`, 50KB inline budget).

## Architecture

```
src/query.ts      Core logic: subprocess → vendored lq.py --json → parse (framework-free, testable)
src/runtime.ts    DSH assembly: registers log_query via defineTool (ctx.tools)
src/config.ts     Plugin config (pythonBin, timeoutMs)
python/           Vendored LogTimeline CLI (GPL-3.0, see python/VENDORED.md)
tests/            Vitest integration tests running the real vendored Python
```

The plugin shells out to a vendored copy of the LogTimeline Python CLI (`python/lq.py --json --no-llm`), so the battle-tested parsing/filtering logic stays untouched. Vendoring changes are minimal and documented in `python/VENDORED.md`.

## Development

```sh
npm install --legacy-peer-deps   # peer deps are provided by the DSH host runtime
npm run typecheck
npm run test                     # integration tests: real vendored Python + host-assembly smoke
npm run build
python scripts/run-upstream-tests.py   # upstream LogTimeline pytest suite against the vendored code
```

`tests/query.test.ts` runs the real vendored Python CLI against fixture logs; `tests/host.test.ts` loads the built plugin (`lib/`) into a minimal Cordis container, applies it, and validates the canonical value against the `output.schema` contract. Peer packages (`@deepseek-ai/dsh-*`, pinned to the `0.1.0-rc.6` line) are installed as devDependencies so the runtime import chain resolves outside a DSH host.

## License

[GPL-3.0](LICENSE) — derived from [LogTimeline](https://github.com/anyuer678/logtimeline) (GPL-3.0). Copyright (C) 2026 anyuer678.

*This project is not affiliated with DeepSeek. It is a community plugin for the DeepSeek Harness ecosystem.*
