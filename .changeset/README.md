# ProtoForge changesets

> 由 [@changesets/cli](https://github.com/changesets/changesets) 管理,自动生成。
> 玩家可感知的变更请用 `pnpm changeset` 添加。

## 配置
- `baseBranch: main` — changesets PR 默认 target
- `commit: false` — `release.yml` 跑 `pnpm changeset version` + commit
- `access: restricted` — 不公开发 npm(本项目不发布 npm 包)
- `ignore: ["apps/desktop"]` — Tauri 桌面走 `tauri-action` 自己的 tag,不被 changeset 强制 bump

## 开发者工作流
```bash
# 1. 写完代码后,加 changeset
pnpm changeset
# 交互式:选包 → 选 patch/minor/major → 写描述

# 2. 提交(连 changeset 一起)
git add .changeset/
git commit -m "feat(api): add /api/onboarding/state endpoint"

# 3. 推 PR,合 main 后 CI 自动:
#    - changeset version  → bump version + 更新 CHANGELOG.md
#    - tauri-action 编译三平台
#    - 创建 GitHub Release(draft)
```

## 已发布版本
参见根目录 `CHANGELOG.md`(由 changesets 自动生成)。
