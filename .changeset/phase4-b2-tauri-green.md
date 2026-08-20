---
'@protoforge/web': patch
'@protoforge/shared': patch
---

# Phase 4 B2: Tauri 三平台编译全绿

## DevOps

- **externalBin 侧车二进制**: `bundle_python.py` 生成 `python-{target-triple}` 命名二进制,`release.yml` 传 `TAURI_TARGET_TRIPLE` 环境变量,修复 Tauri "resource path doesn't exist" 错误。
- **resources glob 修复**: `tauri.conf.json` 用合法 glob(`../api/vendor/`、`binaries/python-bundle/`)替代无效的 `dir/**`。
- **正式图标**: 生成多尺寸 icon.png / icon.ico / icon.icns,替换占位图标。
- 验证 Tauri 三平台(windows / macos x2 / ubuntu)签名编译 + Release 草稿。
