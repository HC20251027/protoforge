# @protoforge/shared

## 0.1.7

### Patch Changes

- [`87b327f`](https://github.com/HC20251027/protoforge/commit/87b327f0b168e1d924c209512759ae521f313367) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Tauri 三平台编译全绿(第 3 轮)

  ## DevOps

  - **sidecar.rs 类型修复**: `launch_python_sidecar` 中 `tauri-plugin-shell v2` 的 `spawn()` 返回 `Result<(Receiver<CommandEvent>, CommandChild), Error>`,原代码直接当作 `Result<CommandChild, tauri::Error>` 使用导致 `E0308 mismatched types`,四平台全部编译失败。现解构出 `CommandChild` 并将错误映射为 `tauri::Error::Anyhow`。
  - 验证 Tauri 三平台(windows / macos x2 / ubuntu)签名编译 + Release 草稿。

## 0.1.6

### Patch Changes

- [`fdb3940`](https://github.com/HC20251027/protoforge/commit/fdb3940576b49f5c1fcdd053d0639652536c010e) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Tauri 三平台编译全绿(第 2 轮)

  ## DevOps

  - **resources 路径修复**: `tauri.conf.json` 中 `../api/vendor/` 改为 `../../api/vendor/`(资源路径相对 `src-tauri` 解析,原路径指向不存在的 `apps/desktop/api/vendor`,导致 4 平台全部 `resource path doesn't exist`)。
  - **Rust target 安装**: `release.yml` 在构建前加 `rustup target add ${{ matrix.target }}`(macos Intel 在 Apple Silicon runner 上缺 `x86_64-apple-darwin` target)。
  - 验证 Tauri 三平台(windows / macos x2 / ubuntu)签名编译 + Release 草稿。

## 0.1.5

### Patch Changes

- [`eb65a9b`](https://github.com/HC20251027/protoforge/commit/eb65a9bf8a7a16a5e74baa107db90fac330b8a93) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Tauri 三平台编译全绿

  ## DevOps

  - **externalBin 侧车二进制**: `bundle_python.py` 生成 `python-{target-triple}` 命名二进制,`release.yml` 传 `TAURI_TARGET_TRIPLE` 环境变量,修复 Tauri "resource path doesn't exist" 错误。
  - **resources glob 修复**: `tauri.conf.json` 用合法 glob(`../api/vendor/`、`binaries/python-bundle/`)替代无效的 `dir/**`。
  - **正式图标**: 生成多尺寸 icon.png / icon.ico / icon.icns,替换占位图标。
  - 验证 Tauri 三平台(windows / macos x2 / ubuntu)签名编译 + Release 草稿。

## 0.1.4

### Patch Changes

- [`7b688b3`](https://github.com/HC20251027/protoforge/commit/7b688b3c5686571c079e452ded1b45dcf773b2d7) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Release workflow 全绿验证(第 2 轮)

  ## DevOps

  - **修复 tauri 生产构建找不到前端资源**: `frontendDist` 从 `../src` 改为 `../../web/dist` + 加 `beforeBuildCommand: pnpm --filter @protoforge/web build`。
  - **修复 web 构建 TS 报错**: `ForgeResult` 补 `errors: string[]`、`tsconfig` 加 `vite/client` types、测试文件修严格空检查。
  - 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。

## 0.1.3

### Patch Changes

- [`5456e3b`](https://github.com/HC20251027/protoforge/commit/5456e3b631998b555aff0502b54e2a4494609f01) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Release workflow 全绿验证

  ## DevOps

  - **修复 release.yml outputs 大小写 bug**: `hasChangesets` → `has_changesets`(step 输出名不匹配导致 tauri job 守卫永远 false)。
  - **version job 直接 commit 到 main**: 替代 changesets/action PR 流程(修 `Resource not accessible by integration`)。
  - **tauri job checkout `ref: main`**: 编译 version bump 后的最新代码。
  - 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。

## 0.1.2

### Patch Changes

- [`474975f`](https://github.com/HC20251027/protoforge/commit/474975f2848c2b0903febd4e547b6c25b3a9f841) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Release workflow 全绿

  ## DevOps

  - **删除僵尸 changeset**: 清理已消费的 `phase4-b1-tauri-signing.md` / `phase4-p1-and-debt.md`(引用不存在的 `@protoforge/api`,导致 `changeset version` 失败)。
  - **release.yml 修复**: `version` job 加 git author 配置(修 exit 254);`.changeset/config.json` repo 改 `HC20251027/protoforge`、ignore 改 `@protoforge/desktop` 包名。
  - **`@changesets/cli` + `@changesets/changelog-github`** 加进根 devDependencies(修 `Command "changeset" not found`)。
  - **gitleaks 改 local hook**: 用项目内二进制(8.30.1),不再拉 1GB+ docker 镜像。
  - 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。

## 0.1.1

### Patch Changes

- [`4083915`](https://github.com/HC20251027/protoforge/commit/4083915b91cf666c1109d42c2b520b418678a9a8) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4: P1 fixes + quality debt cleanup

  ## Security

  - **API key encryption upgraded to cryptography Fernet** (was base64 fallback). Production API keys now encrypted at rest, key persisted to `.protoforge/.protoforge_key`. base64 fallback retained with explicit `UserWarning` when `cryptography` is missing.

  ## Bug fixes

  - **GGUF v3 magic byte fix**: `loader.py` now reads correct `b"\x03GGUF"` header (was `b"GGUF"`). Players with real Qwen2.5-7B models will no longer see silent load failure; magic mismatch now raises `LLMUnavailable` with explicit message.
  - **detect_hardware() removed**: 4 difficulty tiers are now decoupled from hardware detection per Phase 3 decision N2. `app.proto.profile` module deleted; `from app.proto import *` no longer exports hardware-related symbols.

  ## Quality

  - **21 historical F401 unused imports cleaned** (17 auto-fixed by `ruff --fix`, 4 manual). CI ruff now fails on lint errors (was `|| true`).
  - **CI/CD infrastructure**: 4-job GitHub Actions workflow (web/api/shared/security), release workflow with tauri-action for 3-platform builds, dependabot weekly, CODEOWNERS, PR/issue templates, pre-commit hooks (ruff + gitleaks + yamllint + actionlint).
  - **Vendor SHA256 verification script** (`scripts/verify_vendor.py`) added; all vendor resources now have `.sha256` checksum files.
  - **Subdirectory READMEs** added for `apps/api`, `apps/web`, `apps/desktop`, `packages/shared` to onboard new developers faster.

  ## Testing infrastructure

  - **L4 fixture optimization**: pytest fixtures switched to `min_size_mb=1` injection on `LocalLLMLoader`, reducing single-run pytest disk write from **15 GB → 0.6 GB** (25x reduction). Running the full 220-test suite no longer risks filling the C drive.
