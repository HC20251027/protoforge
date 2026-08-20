---
'@protoforge/web': patch
'@protoforge/shared': patch
---

# Phase 4 B2: Tauri 三平台编译全绿(第 2 轮)

## DevOps

- **resources 路径修复**: `tauri.conf.json` 中 `../api/vendor/` 改为 `../../api/vendor/`(资源路径相对 `src-tauri` 解析,原路径指向不存在的 `apps/desktop/api/vendor`,导致 4 平台全部 `resource path doesn't exist`)。
- **Rust target 安装**: `release.yml` 在构建前加 `rustup target add ${{ matrix.target }}`(macos Intel 在 Apple Silicon runner 上缺 `x86_64-apple-darwin` target)。
- 验证 Tauri 三平台(windows / macos x2 / ubuntu)签名编译 + Release 草稿。
