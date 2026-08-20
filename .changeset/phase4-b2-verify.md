---
'@protoforge/web': patch
'@protoforge/shared': patch
---

# Phase 4 B2: Release workflow 全绿验证

## DevOps

- **修复 release.yml outputs 大小写 bug**: `hasChangesets` → `has_changesets`(step 输出名不匹配导致 tauri job 守卫永远 false)。
- **version job 直接 commit 到 main**: 替代 changesets/action PR 流程(修 `Resource not accessible by integration`)。
- **tauri job checkout `ref: main`**: 编译 version bump 后的最新代码。
- 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。
