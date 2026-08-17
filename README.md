<p align="center">
  <strong>🐳 dsh-logtimeline</strong>
</p>
<p align="center">
  <em>Query local log files with Chinese natural-language time expressions — LogTimeline for DeepSeek Harness.</em>
</p>

<p align="center">
  <a href="README.zh.md"><strong>简体中文</strong></a> | <a href="README.md">English</a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-GPL--3.0-blue.svg"></a>
  <a href="https://github.com/anyuer678/logtimeline"><img alt="Upstream" src="https://img.shields.io/badge/powered%20by-LogTimeline-42b883"></a>
  <a href="https://awesome-dsh-plugin.com"><img alt="Awesome DSH Plugin" src="https://awesome-dsh-plugin.com/badge.svg"></a>
  <img alt="Tests" src="https://img.shields.io/badge/tests-13%20passed-brightgreen">
  <img alt="Offline" src="https://img.shields.io/badge/offline-first-4b6fff">
</p>

---

Ask 「昨天下午」「3小时前」「凌晨12点」「上周三 14:00-15:00」 — get the matching log lines, the resolved time range, and ERROR/WARN/INFO level stats. **Fully offline. Logs never leave the machine.**

## Why

Coding agents constantly need to answer *"what happened around 3pm yesterday?"*. Generic log tools make you hand-write `grep` pipelines and timestamp math. `log_query` resolves the fuzzy Chinese time expression for you and returns **structured, machine-readable matches** the agent can reason over directly — no parsing prose out of terminal output.

## Features

| | |
|---|---|
| 🕐 **Chinese time parsing** | Absolute dates (`2026-07-03`, `7月3日 09:15`), relative (`3小时前`, `昨天`, `上周三`), fuzzy windows (`下午`, `凌晨`), hour ranges (`14:00-15:00`) — each with a confidence score |
| 📄 **Multi-format logs** | Auto-detected timestamp formats, UTF-8/GBK encoding fallback, streaming filter (no full-file load, ~2.4s per 300k lines) |
| 🔒 **Offline by default** | Zero third-party Python dependencies; log contents never leave the machine |
| 🧩 **Structured output** | Canonical JSON (`time_range`, `filter`, `lines`, `stats`) rendered as readable text for the model, spill-safe under the harness's 50KB inline budget |

## Install

**Prerequisites**: a dsh profile (`web` or `headless`) + **Python 3.9+** on the machine (on Windows, the `py` launcher is auto-detected when `python` is missing).

**Local / development** (from a checkout):

```sh
git clone https://github.com/anyuer678/dsh-logtimeline.git
dsh plugin --profile web add file:/path/to/dsh-logtimeline
```

**Community install** — once listed in [awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin), install via the plugin market (GitHub-only plugins are supported):

```sh
dsh plugin --profile web add dshmarket
# then: Settings → Plugin Market → search "dsh-logtimeline" → one-click install
```

**Compatibility**: tested against `@deepseek-ai/dsh-tools@0.1.0-rc.6` (current harness release line, e.g. `dsh-base@0.1.0-rc.5`).

## Usage

Tell the agent to use the tool — no special syntax needed:

> 用 log_query 查一下 demo.log 里 2026-07-03 的 ERROR 情况

```jsonc
// log_query(time_text: "2026-07-03", files: ["demo.log"])
{
  "time_range": { "start": "2026-07-03 00:00:00", "end": "2026-07-04 00:00:00", "confidence": 1.0 },
  "filter": {
    "total_matched": 25,
    "stats": { "errors": 13, "warns": 5, "infos": 7, "debugs": 0 },
    "lines": [ /* up to max_lines rows: {lineno, timestamp, raw} */ ]
  }
}
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `time_text` | string **(required)** | Chinese natural-language time, e.g. 「昨天下午」「3小时前」 |
| `files` | string[] | Log file paths (absolute or workspace-relative) |
| `dir` | string | Directory to scan recursively |
| `pattern` | string | Glob when `dir` is set (default `*.log`) |
| `max_lines` | number | Max lines returned (default 500; `0` = stats only; capped at 5000) |
| `since` | string | RFC3339 absolute-time fallback when `time_text` fails to parse |
| `timezone` | string | IANA timezone name, e.g. `Asia/Shanghai` |

The tool runs in **offline mode by default**: it filters precisely (its unique value), and leaves root-cause reasoning to the agent itself.

## Architecture

```
src/query.ts      Core logic: subprocess → vendored lq.py --json → parse (framework-free, testable)
src/runtime.ts    DSH assembly: registers log_query via defineTool (ctx.tools)
src/config.ts     Plugin config (pythonBin, timeoutMs)
python/           Vendored LogTimeline CLI (GPL-3.0, see python/VENDORED.md)
tests/            Vitest integration tests running the real vendored Python
```

The plugin shells out to a vendored copy of the [LogTimeline](https://github.com/anyuer678/logtimeline) Python CLI (`python/lq.py --json --no-llm`), so the battle-tested parsing/filtering logic stays untouched. Vendoring changes are minimal and documented in `python/VENDORED.md`.

## Development

```sh
npm install --legacy-peer-deps   # peer deps are provided by the DSH host runtime
npm run typecheck
npm run test                     # integration tests: real vendored Python + host-assembly smoke
npm run build
python scripts/run-upstream-tests.py   # upstream LogTimeline pytest suite against the vendored code
```

`tests/query.test.ts` runs the real vendored Python CLI against fixture logs; `tests/host.test.ts` loads the built plugin (`lib/`) into a minimal Cordis container, applies it, and validates the canonical value against the `output.schema` contract. Peer packages (`@deepseek-ai/dsh-*`, pinned to the `0.1.0-rc.6` line) are installed as devDependencies so the runtime import chain resolves outside a DSH host.

## Security & Privacy

- **No key handling**: the plugin reads no API keys, stores no credentials, and makes no outbound calls — log analysis is 100% local
- **No log exfiltration**: log lines are returned to the agent (the model) as tool results, never sent anywhere else
- **Path scoping**: only the paths the model passes (via `files`/`dir`) are read; the tool is read-only, it never writes or deletes log files
- **Output hygiene**: control characters / ANSI escapes in log lines are stripped from rendered output

## Disclaimer

This is a community plugin for the DeepSeek Harness ecosystem and is **not affiliated with DeepSeek**. It is provided for learning and demonstration purposes and does not constitute any form of commercial service or technical commitment. The software is provided "as is", without warranty of any kind, express or implied, including but not limited to merchantability, fitness for a particular purpose, and non-infringement.

By using this project you acknowledge that you assume all risk. If you find defects or issues, please report them via GitHub Issues; however, the author shall not be liable for any direct or indirect losses arising from the use of this software (including but not limited to data loss, business interruption, or third-party claims).

This project has not been validated or hardened to production-grade standards (architecture, security baseline, fault tolerance, or performance) and is **not suitable for production or critical environments**. Deploying it to production systems, exposing it as a service, or integrating it into real business workflows is your own decision, and any resulting adverse outcomes (service interruption, data corruption or leakage, business loss, compliance risks, third-party disputes) are your sole responsibility. Log analysis results are for reference only — always verify against the original log files before acting on them. If you need production-grade usage, harden it yourself (security audit, load testing, code review) and bear the associated risk.

## License

[GPL-3.0](LICENSE) — derived from [LogTimeline](https://github.com/anyuer678/logtimeline) (GPL-3.0). Copyright (C) 2026 anyuer678.
