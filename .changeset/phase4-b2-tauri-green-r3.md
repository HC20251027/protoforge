---
'@protoforge/web': patch
'@protoforge/shared': patch
---

# Phase 4 B2: Tauri 三平台编译全绿(第 3 轮)

## DevOps

- **sidecar.rs 类型修复**: `launch_python_sidecar` 中 `tauri-plugin-shell v2` 的 `spawn()` 返回 `Result<(Receiver<CommandEvent>, CommandChild), Error>`,原代码直接当作 `Result<CommandChild, tauri::Error>` 使用导致 `E0308 mismatched types`,四平台全部编译失败。现解构出 `CommandChild` 并将错误映射为 `tauri::Error::Anyhow`。
- 验证 Tauri 三平台(windows / macos x2 / ubuntu)签名编译 + Release 草稿。