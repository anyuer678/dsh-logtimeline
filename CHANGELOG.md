# Changelog

All notable changes to this project will be documented in this file.

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

