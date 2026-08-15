# 发布清单（Release Checklist）

把 `dsh-logtimeline` 发布到 DSH 生态的完整步骤。每一步都做，缺一不可。

## 0. 前置

- [ ] 已 `npm run build`（`lib/` 产物必须**提交进 git**——`dsh plugin add` 从 git 安装后直接消费 `lib`）
- [ ] `npm run typecheck` 与 `npm run test` 通过

## 1. 推到 GitHub

```sh
git init
git add -A
git commit -m "feat: dsh-logtimeline — LogTimeline for DeepSeek Harness"
git branch -M main
git remote add origin https://github.com/anyuer678/dsh-logtimeline.git
git push -u origin main
```

## 2. 打 `dsh-plugin` topic（关键，官方发现机制）

GitHub 仓库 → Settings → Topics → 添加：

- `dsh-plugin`
- 可选：`dsh`、`deepseek-harness`、`log-analysis`

## 3. 进 awesome-dsh-plugin（流量入口）

向 [awesome-dsh-plugin/awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin) 提 PR，在 **Tools & Capabilities** 分类下加一行（**中英文各一行**）：

```markdown
- [anyuer678/dsh-logtimeline](https://github.com/anyuer678/dsh-logtimeline) - Query local log files with Chinese natural-language time expressions (「昨天下午」「3小时前」→ precise time range + matched lines + level stats, fully offline).
```

```markdown
- [anyuer678/dsh-logtimeline](https://github.com/anyuer678/dsh-logtimeline) - 中文自然语言时间 → 过滤本地日志：时间范围、匹配行、级别统计，完全离线。
```

进列表后会被 `dsh-market`（插件市场）自动收录，用户可 `dsh plugin add dshmarket` 一键安装。

## 4. 社区宣传（反馈来源）

- [ ] DeepSeek Harness Discord（README 里的官方社区链接）发一条插件介绍
- [ ] deepseek-harness 仓库的 GitHub Discussions 发帖
- [ ] 中文社区：V2EX / 掘金 / 即刻（插件中文友好，中文社区命中率高）

## 5. 迭代信号

关注这些指标判断方向对不对：

- star / issue / Discord 反馈
- 如果「日志查询」方向反馈好 → 继续做 `stargrave`（GitHub 仓库健康度）等工具插件，形成「个人工具 → DSH 插件」系列

## 注意事项

- 依赖 Python 3.9+：README 已写明，用户缺 Python 时会在 tool 调用时报清晰错误
- 离线零依赖是卖点：不要为「LLM 归因」默认开 LLM 模式（agent 自己能归因）
- vendored Python 升级流程见 `python/VENDORED.md`
