# ProtoForge(原体锻炉)

游戏化的合成生物学众包平台。基于 Stanford Proto 论文(2026)构建。

## 当前阶段

Phase 1:单机 Tauri 桌面应用 + 1 关(极地科考队的耐低温发光菌)。

## 系统要求

- **Python**:3.10+ (Phase 1 玩家本地装)
- **Node.js**:20+ (开发用)
- **pnpm**:9+ (开发用)
- **GPU**(可选):NVIDIA 8GB+ 独显(RTX 3060 起),无 GPU 走 CPU 降级路径

## 安装(开发)

```bash
pnpm install
cd apps/api && uv sync && cd ../..
pnpm dev
```

## 目录约定

- `.protoforge/` - 玩家本机数据(SQLite、序列、模型缓存),**不进 git**
- `apps/api/` - Python sidecar
- `apps/web/` - React 前端
- `apps/desktop/` - Tauri 桌面壳
- `packages/shared/` - 前后端共享 TS 类型

## 文档

- 设计: `docs/superpowers/specs/2026-07-06-protoforge-design.md`
- 游戏: `docs/superpowers/specs/2026-07-06-protoforge-gdd.md`
- 计划: `docs/superpowers/plans/2026-07-06-protoforge-phase1.md`
- 跑通手册: `docs/RUNBOOK.md`
- 玩家贡献: [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- Phase 3 验收: `docs/qa/phase3-acceptance.md`
- Phase 3 未解决项: `docs/qa/phase3-deferred.md`

## CI/CD

- GitHub Actions:[`.github/workflows/ci.yml`](./.github/workflows/ci.yml) web / api / shared 三 job + 安全扫描
- 发布:[`.github/workflows/release.yml`](./.github/workflows/release.yml) changesets 自动版本 + Tauri 三平台编译
- 依赖更新:[`.github/dependabot.yml`](./.github/dependabot.yml) npm / pip / github-actions 三生态 weekly
- 本地 hooks:[`.pre-commit-config.yaml`](./.pre-commit-config.yaml) ruff + gitleaks + yamllint + actionlint(秒级,不影响 commit)
