# @protoforge/web

## 0.1.4

### Patch Changes

- [`7b688b3`](https://github.com/HC20251027/protoforge/commit/7b688b3c5686571c079e452ded1b45dcf773b2d7) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Release workflow 全绿验证(第 2 轮)

  ## DevOps

  - **修复 tauri 生产构建找不到前端资源**: `frontendDist` 从 `../src` 改为 `../../web/dist` + 加 `beforeBuildCommand: pnpm --filter @protoforge/web build`。
  - **修复 web 构建 TS 报错**: `ForgeResult` 补 `errors: string[]`、`tsconfig` 加 `vite/client` types、测试文件修严格空检查。
  - 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。

- Updated dependencies [[`7b688b3`](https://github.com/HC20251027/protoforge/commit/7b688b3c5686571c079e452ded1b45dcf773b2d7)]:
  - @protoforge/shared@0.1.4

## 0.1.3

### Patch Changes

- [`5456e3b`](https://github.com/HC20251027/protoforge/commit/5456e3b631998b555aff0502b54e2a4494609f01) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Release workflow 全绿验证

  ## DevOps

  - **修复 release.yml outputs 大小写 bug**: `hasChangesets` → `has_changesets`(step 输出名不匹配导致 tauri job 守卫永远 false)。
  - **version job 直接 commit 到 main**: 替代 changesets/action PR 流程(修 `Resource not accessible by integration`)。
  - **tauri job checkout `ref: main`**: 编译 version bump 后的最新代码。
  - 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。

- Updated dependencies [[`5456e3b`](https://github.com/HC20251027/protoforge/commit/5456e3b631998b555aff0502b54e2a4494609f01)]:
  - @protoforge/shared@0.1.3

## 0.1.2

### Patch Changes

- [`474975f`](https://github.com/HC20251027/protoforge/commit/474975f2848c2b0903febd4e547b6c25b3a9f841) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B2: Release workflow 全绿

  ## DevOps

  - **删除僵尸 changeset**: 清理已消费的 `phase4-b1-tauri-signing.md` / `phase4-p1-and-debt.md`(引用不存在的 `@protoforge/api`,导致 `changeset version` 失败)。
  - **release.yml 修复**: `version` job 加 git author 配置(修 exit 254);`.changeset/config.json` repo 改 `HC20251027/protoforge`、ignore 改 `@protoforge/desktop` 包名。
  - **`@changesets/cli` + `@changesets/changelog-github`** 加进根 devDependencies(修 `Command "changeset" not found`)。
  - **gitleaks 改 local hook**: 用项目内二进制(8.30.1),不再拉 1GB+ docker 镜像。
  - 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。

- Updated dependencies [[`474975f`](https://github.com/HC20251027/protoforge/commit/474975f2848c2b0903febd4e547b6c25b3a9f841)]:
  - @protoforge/shared@0.1.2

## 0.1.1

### Patch Changes

- [`63cbb53`](https://github.com/HC20251027/protoforge/commit/63cbb53840e20a99f2eb7528d4541c41fe6924fe) Thanks [@HC20251027](https://github.com/HC20251027)! - # Phase 4 B1: Tauri 签名密钥 + GitHub Secret 工具链

  ## DevOps

  - **`apps/api/scripts/set_secret.py`** - 用 libsodium (PyNaCl) SealedBox 加密 + GitHub REST API 设仓库 Secret。本地开发者配 `TAURI_SIGNING_PRIVATE_KEY` / `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` 一次的工具。CI release.yml 不依赖此脚本(用 `${{ secrets.* }}` 直接读)。
  - **`apps/api/.tauri/README.md`** - Tauri 签名密钥目录说明。私钥 `*.key` / `*.key.pub` 通过新增的 `.gitignore` 规则不入 git,只能通过 `set_secret.py` 推到 GitHub Secrets。
  - **pre-commit gitleaks 改 local hook** - 用本机或项目 `apps/api/.cache/bin/gitleaks.exe` 二进制跑(8.30.1,约 30 MB),不再拉 1GB+ docker 镜像。Windows + macOS + Linux 一致行为。
  - **`pynacl>=1.6.2`** 加进 `apps/api/pyproject.toml` 的 `dev-dependencies`(只本地脚本需要,产品 bundle 不带)。
  - **`@changesets/cli` + `@changesets/changelog-github`** 加进根 `devDependencies` - 修 GitHub Actions `Apply changesets` step `Command "changeset" not found` 错误。
  - **`.changeset/config.json`** - `repo` 从 `protoforge/protoforge` 占位 改 `HC20251027/protoforge`;`ignore` 从 `apps/desktop` 路径 改 `@protoforge/desktop` 包名。
  - **`apps/api/scripts/{trigger_workflow,list_runs,run_jobs,set_branch_protection}.{py,cmd}`** - GitHub Actions 调试与配置工具(开发者本地,不入产品路径)。

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

- Updated dependencies [[`4083915`](https://github.com/HC20251027/protoforge/commit/4083915b91cf666c1109d42c2b520b418678a9a8)]:
  - @protoforge/shared@0.1.1
