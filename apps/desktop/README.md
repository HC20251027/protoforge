# ProtoForge Desktop (Tauri 2.x)

桌面壳 — 用 Tauri 2 启动 WebView 加载 React 前端,通过 `tauri-plugin-shell`
调用本地 Python 侧车(Phase 1.5 实装;Phase 1 仅占位)。

## 文件结构

```
apps/desktop/
├── src-tauri/                 # Rust 端
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── build.rs
│   ├── capabilities/default.json
│   ├── icons/icon.png         # 占位图
│   └── src/
│       ├── main.rs
│       └── lib.rs
├── scripts/make_icon.py       # 生成占位图标
└── package.json
```

## 开发流程

```powershell
# 1) 启 Python 侧车(单独 terminal)
cd apps/api
python -m uvicorn app.main:app --port 7654

# 2) 启 Tauri dev(会自动起 Vite 5173 + 编译 Rust 桌面壳)
cd apps/desktop
pnpm install
pnpm tauri dev
```

## Phase 1 状态

- ✅ 配置文件 / Cargo manifest / capabilities
- ✅ Rust 入口 + ping 命令占位
- ⏳ 真实侧车 spawn(Phase 1.5):通过 `tauri-plugin-shell` 在 `setup()` 中拉起
  `python -m uvicorn app.main:app --port 7655`(端口避免冲突),
  等 health 200 后再打开 WebView。

## 已知 Windows 问题

- `cargo check` 在长路径 + 中文/空格目录 + 某些防病毒组合下会抛
  `os error 998` 删除临时文件失败;规避:把 `CARGO_TARGET_DIR` 指向短路径
  并临时关闭实时防护。
- 首次 `pnpm tauri dev` 会下载/编译 ~300 个 crate,需要 5-15 分钟,
  之后增量编译秒级。
