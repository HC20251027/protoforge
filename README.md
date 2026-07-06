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
