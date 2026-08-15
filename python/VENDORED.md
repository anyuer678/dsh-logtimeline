# Vendored logtimeline (Python)

`python/` 下的 Python 源码 vendored 自 [anyuer678/logtimeline](https://github.com/anyuer678/logtimeline)（commit `61a1dc7`，GPL-3.0），原样保留其许可证条款。

## 文件清单

| 文件 | 职责 |
|---|---|
| `lq.py` | CLI 入口（参数解析、退出码） |
| `time_parser.py` | 中文自然语言 → 时间范围（纯函数，零依赖） |
| `log_filter.py` | 多文件流式过滤 + 级别统计（纯标准库） |
| `llm_summary.py` | LLM 归因 / 离线统计 |
| `config.py` | 环境变量配置 |

`webui.py`（Web UI）与测试目录未 vendored：DSH 插件场景使用 CLI + `--json` 输出，不需要内嵌 Web UI。

## 唯一改动

`llm_summary.py`：

1. 删除顶层 `import httpx`，改为 `call_llm` 函数内惰性导入（加 `# NOTE(vendored)` 注释）。
   **原因**：让离线模式（`--no-llm` / `analyze_offline`）零第三方依赖——DSH 插件安装后无需 `pip install` 即可使用。LLM 归因模式仍需要 `httpx`。
2. 新增 `from __future__ import annotations`（原文件无此导入）。
   **原因**：函数签名注解 `Optional[httpx.Client]` 在模块加载时求值，即使惰性导入，没有该行仍会因注解求值要求 `httpx`。该导入使所有注解惰性化（Python 3.9+）。

`lq.py`：

3. `_parse_since` 修复：RFC3339 带时区后缀（如 `+08:00`）时返回 aware datetime，与 `parse_time_range` 的 naive `TimeRange` 比较会抛 `TypeError: can't compare offset-naive and offset-aware datetimes`。现统一转 naive 墙钟时间（新增 `tz` 参数，语义与 `parse_time_range` 一致）。

## 同步上游

升级 vendored 代码时：重新复制上游文件 → 重新应用上述改动（llm_summary 两处 + lq.py 一处）→ 运行 `npx vitest run`（`tests/query.test.ts` 覆盖真实 Python 集成路径，含 `--since` 时区用例）验证。
