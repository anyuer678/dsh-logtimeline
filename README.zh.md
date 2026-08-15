# dsh-logtimeline

用**中文自然语言时间描述**查询本地日志文件——[LogTimeline](https://github.com/anyuer678/logtimeline) 的 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (dsh) 插件版。

输入「昨天下午」「3小时前」「凌晨12点」「上周三 14:00-15:00」这类表达，返回匹配的日志行、解析出的时间范围与 ERROR/WARN/INFO 级别统计——**完全离线，日志不出本机**。

## 为什么做这个

agent 排查问题时最常问的就是"昨天下午 3 点发生了什么"。通用日志工具要手写 `grep` 管道和时间戳换算；`log_query` 帮你把模糊中文时间表达解析成精确范围，返回结构化结果，agent 直接推理即可。

## 特性

- **中文时间解析**：绝对日期（`2026-07-03`、`7月3日 09:15`）、相对（`3小时前`、`昨天`、`上周三`）、模糊时段（`下午`、`凌晨`）、区间（`14:00-15:00`），带置信度
- **多格式日志**：常见时间戳自动识别、UTF-8/GBK 编码回退、流式过滤不占内存
- **默认离线**：零第三方 Python 依赖，日志数据不出本机
- **结构化输出**：canonical JSON（`time_range` / `filter` / `lines` / `stats`），渲染为模型可读文本

## 安装

前置条件：dsh profile（`web` 或 `headless`）+ **Python 3.9+**（Windows 上自动回退检测 `py` launcher）。

**本地/开发安装**（checkout 后）：

```sh
git clone https://github.com/anyuer678/dsh-logtimeline.git
dsh plugin --profile web add file:/path/to/dsh-logtimeline
```

**社区安装**：进入 [awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin) 列表后，通过插件市场安装（market 支持 GitHub-only 插件）：

```sh
dsh plugin --profile web add dshmarket
# 然后：Settings → Plugin Market → 搜索 dsh-logtimeline → 一键安装
```

兼容性：测试于 `@deepseek-ai/dsh-tools@0.1.0-rc.6`（当前发布线，如 `dsh-base@0.1.0-rc.5`）。

## 使用

安装后 agent 可直接调用 `log_query` 工具，例如：

> "用 log_query 查一下 demo.log 里昨天下午发生了什么" → `log_query(time_text: "昨天下午", files: ["demo.log"])`

| 参数 | 类型 | 说明 |
|---|---|---|
| `time_text` | string（必填） | 中文自然语言时间，如「昨天下午」「3小时前」 |
| `files` | string[] | 日志文件路径（绝对或相对工作区） |
| `dir` | string | 递归扫描的目录 |
| `pattern` | string | `dir` 模式下的文件名 glob（默认 `*.log`） |
| `max_lines` | number | 最多返回行数（默认 500；`0` = 只统计） |
| `since` | string | `time_text` 解析失败时的 RFC3339 绝对时间兜底 |
| `timezone` | string | IANA 时区名，如 `Asia/Shanghai` |

工具默认**离线模式**：它负责精确过滤（独有价值），归因推理交给 agent 自己。

## 架构

```
src/query.ts      核心逻辑：子进程 → vendored lq.py --json → 解析（无框架依赖，可独立测试）
src/runtime.ts    DSH 装配层：defineTool 注册 log_query（ctx.tools）
src/config.ts     插件配置（pythonBin、timeoutMs）
python/           Vendored LogTimeline CLI（GPL-3.0，改动见 python/VENDORED.md）
tests/            跑真实 vendored Python 的集成测试
```

插件通过子进程调用 vendored 的 LogTimeline Python CLI（`python/lq.py --json --no-llm`），沿用其久经测试的解析/过滤逻辑，仅做最小 vendoring 改动（详见 `python/VENDORED.md`）。

## 开发

```sh
npm install --legacy-peer-deps   # peer 依赖由 DSH 宿主运行时提供
npm run typecheck
npm run test                     # 集成测试（真实 vendored Python）
npm run build
```

## License

[GPL-3.0](LICENSE) — 衍生自 [LogTimeline](https://github.com/anyuer678/logtimeline)（GPL-3.0）。Copyright (C) 2026 anyuer678。

*本插件与 DeepSeek 无隶属关系，是 DeepSeek Harness 生态的社区插件。*
