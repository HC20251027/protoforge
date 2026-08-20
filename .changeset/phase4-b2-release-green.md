---
'@protoforge/web': patch
'@protoforge/shared': patch
---

# Phase 4 B2: Release workflow 全绿

## DevOps

- **删除僵尸 changeset**: 清理已消费的 `phase4-b1-tauri-signing.md` / `phase4-p1-and-debt.md`(引用不存在的 `@protoforge/api`,导致 `changeset version` 失败)。
- **release.yml 修复**: `version` job 加 git author 配置(修 exit 254);`.changeset/config.json` repo 改 `HC20251027/protoforge`、ignore 改 `@protoforge/desktop` 包名。
- **`@changesets/cli` + `@changesets/changelog-github`** 加进根 devDependencies(修 `Command "changeset" not found`)。
- **gitleaks 改 local hook**: 用项目内二进制(8.30.1),不再拉 1GB+ docker 镜像。
- 触发完整 release 流水线验证:Tauri 三平台(windows/macos x2/ubuntu)签名编译 + Release 草稿。
