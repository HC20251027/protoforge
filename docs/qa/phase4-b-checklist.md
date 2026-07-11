# Phase 4 B 段 (CI/CD 收尾) 操作手册

> 日期: 2026-07-11
> 状态: B4 完成,B1/B2/B3/B5 待用户在外部环境操作

---

## ✅ B4. 第一个 changeset (已完成)

文件: `.changeset/phase4-p1-and-debt.md`

内容: 描述 Phase 4 修了什么 (API key 加密、GGUF magic、detect_hardware 删除、21 F401 清理、CI/CD 基础设施、L4 fixture 优化)。

`.changeset` 目录结构:
```
.changeset/
├── config.json
├── README.md
└── phase4-p1-and-debt.md  ← 新增
```

推 main 后,`release.yml` 会自动读取,触发 `pnpm changeset version` → 自动 bump `apps/api` `apps/web` `packages/shared` 版本号。

---

## ⏳ B1. 配 GitHub Secrets (用户操作,网页)

去 GitHub → Settings → Secrets and variables → Actions → New repository secret

| Secret 名 | 值 | 生成方法 |
|---|---|---|
| `TAURI_SIGNING_PRIVATE_KEY` | (base64 字符串) | `npx @tauri-apps/cli signer generate -w ~/.tauri/protoforge.key` 然后 `base64 -w 0 < ~/.tauri/protoforge.key` |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | (生成时设的密码) | 上一步生成时设的密码 |

**不要 commit `~/.tauri/protoforge.key` 到 git!**

---

## ⏳ B2. 手动 workflow_dispatch 跑 release (用户操作,GitHub 网页)

去 GitHub → Actions → Release → Run workflow → 选 main → Run

- 第一次跑要下载 Rust 工具链,30+ 分钟
- 验证 3 平台产物:
  - Windows: `.exe` + `.msi`
  - macOS: `.dmg` + `.app`
  - Linux: `.AppImage` + `.deb`
- 验证 release 草稿自动创建
- 验证 `latest.json` 上传到 release assets

---

## ⏳ B3. 本地 pre-commit install (用户操作,本机命令)

> pre-commit 依赖 Python 工具链,本机已有 Python 3.12 + pip 即可。

```bash
# 方法 1: 直接用 pip (需要先把 pip 加到 PATH)
pip install pre-commit

# 方法 2: 用 uv 装到项目工具 (推荐,符合"项目优先"原则)
uv tool install pre-commit

# 然后
cd <repo-root>
pre-commit install                # 把 hook 装到 .git/hooks/
pre-commit run --all-files        # 全量跑 5 个 hook
```

预期 5 个 hook 跑通:
- pre-commit-hooks (行尾、尾行、yaml/json/toml 合法、大文件、private key)
- ruff + ruff-format
- gitleaks
- yamllint
- actionlint

**问题**: 本机 `uvx pre-commit` 卡在依赖解析(可能 1+ 分钟,网络/PyPI 慢)。如果卡死:
```bash
# 终止后改用 pip 直接装
pip install pre-commit
# 或
python -m pip install pre-commit
```

---

## ⏳ B5. main 分支保护规则 (用户操作,GitHub 网页)

去 GitHub → Settings → Branches → Branch protection rules → main → Edit

- [x] Require a pull request before merging
- [x] Require 1 approval (单人可改 0)
- [x] Require status checks to pass before merging
  - `ci / web`
  - `ci / api`
  - `ci / shared`
- [ ] Require linear history (不勾,允许 merge commit)
- [x] Do not allow bypassing the above settings

---

## 验收清单 (用户操作完后)

- [ ] B1 2 个 Secret 都已配
- [ ] B2 workflow_dispatch 跑通,3 平台产物都已上传
- [ ] B3 pre-commit install + run --all-files 全过
- [ ] B5 main 分支保护已生效
- [ ] B4 changeset 推 main → release.yml 自动 version bump 跑通

任一项卡住,把错误信息贴回来我帮你看。
