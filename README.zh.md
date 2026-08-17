<p align="center">
  <strong>🐳 dsh-logtimeline</strong>
</p>
<p align="center">
  <em>用中文自然语言时间描述查询本地日志 —— LogTimeline 的 DeepSeek Harness (dsh) 插件版。</em>
</p>

<p align="center">
  <strong>简体中文</strong> | <a href="README.md">English</a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-GPL--3.0-blue.svg"></a>
  <a href="https://github.com/anyuer678/logtimeline"><img alt="上游" src="https://img.shields.io/badge/powered%20by-LogTimeline-42b883"></a>
  <a href="https://awesome-dsh-plugin.com"><img alt="Awesome DSH Plugin" src="https://awesome-dsh-plugin.com/badge.svg"></a>
  <img alt="测试" src="https://img.shields.io/badge/tests-13%20passed-brightgreen">
  <img alt="离线" src="https://img.shields.io/badge/offline--first-4b6fff">
</p>

---

输入「昨天下午」「3小时前」「凌晨12点」「上周三 14:00-15:00」——返回匹配的日志行、解析出的时间范围与 ERROR/WARN/INFO 级别统计。**完全离线，日志不出本机。**

## 为什么做这个

agent 排查问题时最常问的就是"昨天下午 3 点发生了什么"。通用日志工具要手写 `grep` 管道和时间戳换算；`log_query` 帮你把模糊中文时间表达解析成精确范围，返回**结构化、机器可读**的结果，agent 直接推理即可——不用再从终端输出里抠文字。

## 特性

| | |
|---|---|
| 🕐 **中文时间解析** | 绝对日期（`2026-07-03`、`7月3日 09:15`）、相对（`3小时前`、`昨天`、`上周三`）、模糊时段（`下午`、`凌晨`）、区间（`14:00-15:00`），带置信度 |
| 📄 **多格式日志** | 常见时间戳自动识别、UTF-8/GBK 编码回退、流式过滤不占内存（30 万行约 2.4 秒） |
| 🔒 **默认离线** | 零第三方 Python 依赖，日志数据不出本机 |
| 🧩 **结构化输出** | canonical JSON（`time_range` / `filter` / `lines` / `stats`），渲染为模型可读文本；超大结果由 harness 的 50KB spill 机制兜底 |

## 安装

**前置条件**：dsh profile（`web` 或 `headless`）+ 机器上有 **Python 3.9+**（Windows 无 `python` 命令时自动回退 `py -3`）。

**本地/开发安装**（checkout 后）：

```sh
git clone https://github.com/anyuer678/dsh-logtimeline.git
dsh plugin --profile web add file:/path/to/dsh-logtimeline
```

**社区安装**——进入 [awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin) 列表后，通过插件市场一键装（market 支持 GitHub-only 插件）：

```sh
dsh plugin --profile web add dshmarket
# 然后：Settings → Plugin Market → 搜索 dsh-logtimeline → 一键安装
```

**兼容性**：测试于 `@deepseek-ai/dsh-tools@0.1.0-rc.6`（当前发布线，如 `dsh-base@0.1.0-rc.5`）。

## 使用

直接让 agent 调用即可，无需特殊语法：

> 用 log_query 查一下 demo.log 里 2026-07-03 的 ERROR 情况

```jsonc
// log_query(time_text: "2026-07-03", files: ["demo.log"])
{
  "time_range": { "start": "2026-07-03 00:00:00", "end": "2026-07-04 00:00:00", "confidence": 1.0 },
  "filter": {
    "total_matched": 25,
    "stats": { "errors": 13, "warns": 5, "infos": 7, "debugs": 0 },
    "lines": [ /* 最多 max_lines 行：{lineno, timestamp, raw} */ ]
  }
}
```

### 参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `time_text` | string（**必填**） | 中文自然语言时间，如「昨天下午」「3小时前」 |
| `files` | string[] | 日志文件路径（绝对或相对工作区） |
| `dir` | string | 递归扫描的目录 |
| `pattern` | string | `dir` 模式下的文件名 glob（默认 `*.log`） |
| `max_lines` | number | 最多返回行数（默认 500；`0` = 只统计；上限 5000） |
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

插件通过子进程调用 vendored 的 [LogTimeline](https://github.com/anyuer678/logtimeline) Python CLI（`python/lq.py --json --no-llm`），沿用其久经测试的解析/过滤逻辑，仅做最小 vendoring 改动（详见 `python/VENDORED.md`）。

## 开发

```sh
npm install --legacy-peer-deps   # peer 依赖由 DSH 宿主运行时提供
npm run typecheck
npm run test                     # 集成测试（真实 vendored Python + 宿主装配冒烟）
npm run build
python scripts/run-upstream-tests.py   # 用 vendored 代码跑上游 124 例 pytest
```

`tests/query.test.ts` 用 fixture 日志跑真实 vendored Python；`tests/host.test.ts` 把编译产物（`lib/`）加载进最小 cordis 容器，验证 apply、execute 与 `output.schema` 契约。peer 包（`@deepseek-ai/dsh-*`，0.1.0-rc.6 线）装在 devDependencies，使独立环境下运行时 import 链可解析。

## 安全与隐私

- **不碰 key**：插件不读取、不存储、不发送任何 API key，无出网请求——日志分析 100% 本地
- **日志不外泄**：日志行只作为工具结果返回给 agent（模型），不发送到任何其他位置
- **路径受控**：只读模型通过 `files`/`dir` 传入的路径；工具只读，不写不删日志
- **输出卫生**：日志行中的控制字符 / ANSI 转义在渲染时剥离

## 免责声明

本插件是 DeepSeek Harness 生态的社区插件，**与 DeepSeek 无隶属关系**。本项目仅供学习交流与演示用途，不构成任何形式的商业服务或技术承诺。软件按「现状」提供，不作任何明示或暗示的保证，包括但不限于适销性、特定用途适用性与非侵权性。

您理解并同意：使用本项目即表示您自行承担全部风险。如您在使用过程中发现缺陷或问题，欢迎通过 GitHub Issues 反馈，但作者不因使用本软件所直接或间接产生的任何损失（包括但不限于数据丢失、业务中断、第三方索赔）承担责任。

本项目以功能演示与学习交流为主要目的，其架构设计、安全基线、容错机制与性能表现均未按生产级标准进行验证与加固，**不适用于实际生产环境或关键业务场景**。任何将本项目部署于生产系统、对外提供服务、或将其接入真实业务工作流的做法，均属使用者的自主决策行为；由此产生的任何直接或间接不良后果，包括但不限于服务中断、数据损坏或泄露、业务损失、合规风险、以及因依赖本软件而引发的第三方纠纷，**开发者均不承担任何责任**。日志分析结论仅供参考，请结合原始日志人工复核后再做决策。若您确有生产级使用需求，请在充分评估与自行加固（包括但不限于安全审计、压力测试、代码审查）后，自行承担相应风险。

## License

[GPL-3.0](LICENSE) — 衍生自 [LogTimeline](https://github.com/anyuer678/logtimeline)（GPL-3.0）。Copyright (C) 2026 anyuer678。
