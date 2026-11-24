# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-11-24

### Fixed
- **MCP 多文件查询只剩最后一个文件**：`python/mcp_server.py` 逐个追加 `--files`，而 `lq.py` 的 `--files` 是 argparse `nargs='+'`，同一选项重复出现时后者覆盖前者。现改为一次性传全部文件；参数拼装抽到 `python/lq_args.py`，新增 `tests/mcp_args.test.ts` 回归。
- **MCP 未强制离线**：包装层没有向 CLI 传 `--no-llm`，宿主机存在 `LLM_*` 环境变量时会把日志样本发往外部接口，与工具描述「完全离线、日志不出本机」不符。现固定 `--no-llm`。

### Changed
- 适配 DSH `0.2.2-rc.5` 发布线：`dsh-tools` / `dsh-llm` / `dsh-agent` / `dsh-scope` / `dsh-session` / `dsh-session-projection` / `dsh-session-persistence` / `dsh-system-prompt` / `dsh-user-approval` / `dsh-timeout` / `dsh-workspace` / `dsh-util-values` / `dsh-typert-protocol` / `dsh-error` / `dsh-storage` / `dsh-storage-domain` 统一 `0.2.2-rc.5`。
- `@deepseek-ai/cordis` `4.0.4` → `~4.1.0`（`dsh-tools@0.2.2-rc.5` 的 peer 要求）。
- `dsh-code-runtime` 跟随独立线 `0.1.5-rc.3`；`dsh-invariants` 保持 `0.2.0-rc.2`。
- 测试数 57 → 60（新增 3 条 MCP 参数拼装回归）。

### Verified
- `npm run typecheck` 通过；`npm test` 60/60 通过（Node 22.22 / Python 3.13 / Windows）。
- 真实执行验证：两个 fixture 文件的命中行均进入 `file_stats`，`total_matched = 25 + 4 = 29`。

## Unreleased

- a588ad2 ci: 添加依赖安全审计步骤（npm audit / pip-audit）
- d51e2a8 chore: lib/ 编译产物出库、上游测试路径可配置、修正过时注释
- ae30c00 fix: change --since to naive timestamp to fix UTC CI failure
- eddd058 fix: add python3 fallback for Ubuntu CI
- 7beb572 ci: add npm cache clean to prevent stale cache issues
- 1d4f15e ci: clean up debug steps, keep npm cache disabled
- 596a81b debug: upload test output as artifact for diagnosis
- bebbdc1 debug: add environment info to CI, remove npm cache
- 41b259a fix: remove UTF-8 BOM from test fixtures
- e859d82 fix: add missing test fixtures and update .gitignore
- 4403d0a chore: 添加 .nvmrc 与 engines 一致 (22.19.0)
- d4552e0 fix: CI node 版本改用 node-version-file 与 engines 一致
- 6c46c5c ci: 修复为正确的 Node.js 测试流程（vitest）
- bde7343 ci: 添加测试 CI workflow
- 0fa47ca chore: 替换为标准 SPDX MIT 许可证文本
- d4950af docs: 免责声明参考上游 logtimeline 三段式（非商业承诺/风险自担/非生产级）
- 8495c05 docs: 仿 DSH 生态风格重写 README（中英双语 + 徽章 + 使用示例 + 安全节），LICENSE 版权头更新
- f74fc56 fix: align stdout buffer with max_lines cap (64MB); test max_lines clamp and timezone
- f11e09a feat: log tool registration for observability
- b3ecb6b fix: align with harness 0.1.0-rc.6 line; drop invariant companion; python -B (no pycache); py launcher fallback; correct install commands



## [Unreleased]

### Added
- `COMPATIBILITY.md` host/OS/time-expression matrix
- `docs/time-expressions.md` reviewer-facing expression table
- Additional vitest contract checks for query/parse exports

### Notes
- Residual A+ gaps: upstream suite badge automation, host RC pin refresh cadence
