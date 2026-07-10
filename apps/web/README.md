# ProtoForge Web (React 18 + Vite + TypeScript)

> Phase 3 收官 / 前端 42 passed / React 18 + Vite 5 + Tailwind

## 职责

ProtoForge 玩家 UI:
- 引导页(3 步配置,vendor 状态 → LLM → API key)
- 任务列表 + 任务详情
- 锻造页(4 档选择 + 滑块 + 实时评分)
- 风险门(策略选择 → 通关判定)
- 作品库(自动保存 + 上传状态)
- 路由:`/onboarding` → `/` → `/missions/:id/forge` → `/risk-gate` → `/gallery`

## 入口

- `src/main.tsx` — React 入口
- `src/App.tsx` — 路由 + 布局
- `src/pages/` — 6 个页面
- `src/components/` — 7 个共享组件
- `src/lib/api.ts` — FastAPI 客户端(所有 HTTP 调用)
- `src/lib/types.ts` — 旧版类型定义(以 `packages/shared/src/types.ts` 为准)

## 启动

```bash
# 根目录
pnpm install
pnpm --filter @protoforge/web dev   # Vite dev 5173 端口
```

## 跑测试

```bash
cd apps/web
pnpm test                           # vitest 42 passed
pnpm test --coverage                # 覆盖率
```

## 跑 lint + 类型

```bash
cd apps/web
pnpm lint                           # ESLint
pnpm exec tsc --noEmit              # TypeScript 类型检查
```

## 4 档难度(本地状态)

`localStorage.protoforge.ritual` — 默认 `urgent`

```ts
import type { ForgeRitual } from '@protoforge/shared';
type ForgeRitual = 'urgent' | 'standard' | 'ancient' | 'crystal';
```

## Phase 3 关键改动文件

| 文件 | 改动 |
|------|------|
| `src/pages/OnboardingPage.tsx` | 3 步配置 |
| `src/pages/ForgePage.tsx` | 4 档 segment + run_forge + Gallery 自动保存 + 退出 banner + 上传 toast |
| `src/pages/RiskGatePage.tsx` | 风险门 + 通关判定 |
| `src/components/ForgingBanner.tsx` | "⚠️ 锻造中退出游戏会有概率失败" 红色横幅 |
| `src/lib/api.ts` | FastAPI 客户端(所有端点) |

## 跟其他模块的接口

- HTTP: `http://localhost:7654`(FastAPI sidecar)
- Tauri 桌面:`tauri://localhost`
- 共享类型: `import type { ... } from '@protoforge/shared'`

## 调试技巧

```bash
# Vite dev 端口冲突时
pnpm --filter @protoforge/web dev --port 5174

# React DevTools
# 装浏览器扩展即可,vite 自动 source map

# 模拟引导页未完成
localStorage.removeItem('protoforge.onboarding_completed')
```

## 已知未解决项

- React Router v7 future flag 警告(Phase 4 P3)
- vitest act() 警告(Phase 4 P3)
