# @protoforge/shared (TS 共享类型)

> Phase 3 收官 / 单文件包 / 用于 apps/web 和 apps/api(Python 端镜像)

## 职责

ProtoForge 前后端共享类型定义:
- 让前端 `import type` 跟后端 Pydantic schema 自动同步
- 避免字段名 / 枚举值漂移

## 入口

- `src/types.ts` — 唯一文件,所有类型定义

## 导出

```ts
import type {
  LLMProvider,           // 'cloud' | 'local' | 'disabled'
  CellLine,              // 'HEK293' | 'HeLa' | 'Jurkat' | 'PolarYeast' | 'MarsMoss'
  ForgeRitual,           // 'urgent' | 'standard' | 'ancient' | 'crystal'
  MissionLevel,          // 'tutorial' | 'delegation' | 'network' | 'tricky' | 'free'
  MissionScenario,       // 'polar' | 'ocean' | 'soil' | 'lunar' | 'custom'
  // ... 滑块 / 风险门 / 评分 / 退出惩罚 / 上传状态
} from '@protoforge/shared';
```

## 怎么用

### 前端
```ts
import type { ForgeRitual } from '@protoforge/shared';
const ritual: ForgeRitual = 'urgent';
```

### 后端镜像
后端 `apps/api/app/schemas.py` 镜像这份类型;**字段名以后端 Pydantic 为准**,前端若有偏差,在 `src/types.ts` 改正。

## 跟其他模块的接口

- 消费者:`apps/web` 通过 `pnpm install` 拉
- 后端镜像:`apps/api/app/schemas.py` 手动同步(Phase 4 改用 `pydantic-to-typescript` 自动生成)

## 规则

1. **加新类型前先看 `apps/api/app/schemas.py` 有没有**
2. **改类型时同时改两边**
3. **不允许在这写业务逻辑** — 只放类型

## Phase 3 关键类型

| 类型 | 用途 |
|------|------|
| `ForgeRitual` | 4 档难度 |
| `LLMProvider` | 引导页 LLM 选择 |
| `CellLine` / `MissionLevel` / `MissionScenario` | 任务配置 |

## 已知未解决项

- 后端类型镜像手工同步,Phase 4 改自动
