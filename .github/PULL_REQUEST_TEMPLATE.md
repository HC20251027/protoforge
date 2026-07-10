## 变更类型

- [ ] feat (新功能)
- [ ] fix (bug fix)
- [ ] refactor (重构,不改功能)
- [ ] chore (工具链、依赖、CICD)
- [ ] docs (文档)
- [ ] perf (性能)
- [ ] test (测试)

## 涉及范围

- [ ] apps/api (Python FastAPI sidecar)
- [ ] apps/web (React + Vite 前端)
- [ ] apps/desktop (Tauri 2 桌面壳)
- [ ] packages/shared (TS 共享类型)
- [ ] .github / CI / pre-commit / dependabot
- [ ] 文档(README / RUNBOOK / docs/)
- [ ] 数据 / vendor 模型

## 描述

<!--
- 改了什么
- 为什么改
- 关联的 Issue / 决策点
- Phase 3 决策对照(N1/N2/N3/4档/退出惩罚/引导页)— 如相关
-->

## 测试

- [ ] `cd apps/api && uv run pytest`(后端,期望 213 passed)
- [ ] `cd apps/web && pnpm test`(前端,期望 42 passed)
- [ ] `cd apps/api && uv run ruff check .`(后端 lint)
- [ ] `cd apps/web && pnpm lint`(前端 lint)
- [ ] `cd apps/web && pnpm exec tsc --noEmit`(类型检查)
- [ ] 必要时跑了 `pnpm changeset`(见 CONTRIBUTING.md § 4)

## Checklist

- [ ] commit 信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] 大文件 / 权重未入 git(`.protoforge/`、`apps/api/vendor/models/*.safetensors`、`*.gguf`)
- [ ] 没改 `package.json` / `pyproject.toml` 的 `version` 字段(changesets 接管)
- [ ] 引导页 vendor 状态、4 档 segment、退出惩罚 banner、Steam 上传队列四个核心 UI 没动(动了要在描述里说)
- [ ] CI 全绿(web / api / shared 三个 job)

## 影响 / 风险

<!--
- 是否影响玩家体验链路(从引导 → 锻造 → 退出惩罚 → 通关 → 上传 → Gallery)
- 是否需要重启 / 重新初始化数据
- 是否需要 release 流程(打 tag、发 GitHub Release)
-->
