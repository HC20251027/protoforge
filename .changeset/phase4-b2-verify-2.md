---
'@protoforge/web': patch
'@protoforge/shared': patch
---

# Phase 4 B2: Release workflow 全绿验证(第 2 轮)

## DevOps

- **修复 tauri 生产构建找不到前端资源**: `frontendDist` 从 `../src` 改为 `../../web/dist` + 加 `beforeBuildCommand: pnpm --filter @protoforge/web build`。
- **修复 web 构建 TS 报错**: `ForgeResult` 补 `errors: string[]`、`tsconfig` 加 `vite/client` types、测试文件修严格空检查。
- 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。
