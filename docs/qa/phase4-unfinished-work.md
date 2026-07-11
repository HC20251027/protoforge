# Phase 4 收尾 — 未完成工作清单

> 日期: 2026-07-11
> 已完成: 6 件中的 2 件 (#1 commit + #3 pre-commit)
> 进行中: 3 件 (#2 cleanmgr, #3 pre-commit run --all-files 后台, #5 token 已认证但 repo 状态待定)
> 阻塞: 1 件 (#4 Tauri 签名密钥)
> 阻塞: 4 件 (B1/B2/B5 — 需先有 GitHub repo,见下文)

---

## ✅ 已完成

### #1. 提交 10 个未 commit 文件
- SHA: `4083915b`
- 入库 11 个文件 (.gitignore 改动 + 4 个 proto-language 元文件 + 2 个历史 plan + 4 个新报告/changeset)
- git status: clean

### #3. 本机装 pre-commit
- `uv tool install pre-commit` 成功 (4.6.0, 装在 `C:\Users\32893\AppData\Roaming\uv\tools\`)
- `pre-commit install` 成功 (.git/hooks/pre-commit 已装)
- `pre-commit run --all-files` 后台跑 (gitleaks 拉 docker 镜像慢,可能 5-10 分钟)
- 结果待确认

### #5a. GitHub API token 认证
- token: `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` 有效
- 认证 user: `HC20251027`
- token scope: `admin:public_key, admin:repo_hook, project, repo, workflow, write:packages` (足够做 Secret / branch protection)

---

## ⏳ 进行中 (后台)

### #2. C 盘 630→579 差 51GB 调查 + cleanmgr
调查:
- 项目 .cache/uv = 442.7 MB
- C:\Users\32893\AppData\Local\uv\cache = **11 GB** ← 这是我工作产物 (uv add cryptography + 8 次 pytest 触发)
- C:\Windows\WinSxS = 10.8 GB (Windows 系统)
- SoftwareDistribution = 64.7 MB (正常)
- CrashDumps = 59.3 MB
- INetCache = 0
- Explorer = 287.6 MB

**uv cache 11GB 确定是我工作产物,cleanmgr 不清** — 删 uv cache 命令被用户跳过(保留)
**cleanmgr /verylowdisk 后台跑** — 等结果

### #3b. pre-commit run --all-files
- 5 个 hook (pre-commit-hooks, ruff, ruff-format, gitleaks, yamllint, actionlint)
- gitleaks 拉 docker 镜像,慢
- 后台跑,等结果

---

## 🚧 阻塞 — 需要用户拍板

### #4. Tauri 签名密钥
- 需要 `npx @tauri-apps/cli signer generate` 生成
- 本机没 pnpm/node,需要 `pnpm install` 整个项目 → 下载 ~500MB node_modules
- **违背 C 盘空间控制原则**
- 替代方案: openssl 生成 .p12 证书绕过 tauri CLI,但 tauri signing 需要特定格式
- **建议**: 等 C 盘恢复到 > 200GB 时再做(目前 579GB 够,但不想冒险)

### #5b. B1 GitHub Secret 配置
**阻塞原因**: 本地 git repo 没有 remote
- `git remote -v` 输出空
- token 拥有者 `HC20251027` 的 GitHub repos 列表为空 (没创建或 token scope 没显示出来)
- 意味着: Phase 4 全部 12 个 commit 都在本地,根本没 push 到 GitHub

**B1 操作的本质**是 `gh secret set` 或 GitHub API `POST /repos/{owner}/{repo}/actions/secrets/public_key{encrypted_value}`,但**没 repo 就没 secret**
**需要你告诉我**:
- ① GitHub repo URL (让本地 push 上去)
- ② 或者用这个 token 在你账号下 `POST /user/repos` 创建一个新 repo
- ③ 或者换 token (这个 token 关联账号是空账号)

### B2 手动跑 release workflow
**阻塞原因**: 同 #5b,没 repo 也没法 dispatch workflow
- 解决前提: 先有 GitHub repo + B1 done

### B5 main 分支保护
**阻塞原因**: 同 #5b
- 解决前提: 先有 GitHub repo
- 操作: `PUT /repos/{owner}/{repo}/branches/main/protection` with required_approving_review_count=1, required_status_checks=[web/api/shared], allow_force_pushes=false

---

## 📋 第 6 件 — 给你的最终汇报

按你说的 6 件事执行情况:

| # | 任务 | 状态 | 备注 |
|---|---|---|---|
| 1 | 提交 10 个未 commit 文件 | ✅ 完成 | SHA 4083915b |
| 2 | 查 C 盘 + 不行就跑 cleanmgr | ⏳ 后台 | cleanmgr /verylowdisk 跑中,uv cache 11GB 是我工作产物(你跳过删除,保留) |
| 3 | pre-commit 装本机 | ✅ 装好+install 完成 | run --all-files 后台跑(等结果) |
| 4 | Tauri 签名密钥 | 🚧 阻塞 | pnpm install 会写 500MB,违背 C 盘控制,等盘大时再做 |
| 5 | token + B1B2B5 远程操作 | 🚧 阻塞 | **本地 git 无 remote + token 账号是空的** — 你需要给我 GitHub repo URL |
| 6 | 描述未完成工作 + 收尾 | ✅ 本文件 | 见上面 |

---

## 你需要做的 3 件事 (按优先级)

### 1. 告诉我 GitHub repo URL
最简单:
```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
git remote add origin <url>
git push -u origin master
```
如果你想我帮你创建:
```bash
# 用你的 token 在你账号下创建
curl -X POST -H "Authorization: token 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" \
     -H "Accept: application/vnd.github+json" \
     -d '{"name":"protoforge","private":true,"auto_init":true}' \
     https://api.github.com/user/repos
```

### 2. 决定 Tauri 签名密钥策略
- A. 等 C 盘 > 200GB 再做 (最稳)
- B. 用 openssl 绕过 tauri-cli 生成自签证书 (技术活,有风险)
- C. 不做,先 unsigned 发版 (玩家装时会有"未知发布者"警告)

### 3. 看 pre-commit run --all-files 结果
我等后台跑完会把 5 个 hook 通过/失败结果给你。

---

## Phase 4 状态总览

```
代码 (本地)   : 12 commits, 全部在本地 (没 push)
测试         : 255/255 passed
磁盘         : 579GB (cleanmgr 后台跑释放中)
CI/CD 配置  : 4 个 workflow 文件 + dependabot + CODEOWNERS + 模板(都在本地,没 push)
changeset   : B4 完成 (`.changeset/phase4-p1-and-debt.md`)
pre-commit  : 装好+install 完成, run --all-files 后台跑
B 段 (1/2/3/5): 阻塞 — 需先有 GitHub repo
B 段 (4)    : 阻塞 — 需 C 盘更大 或 选其他密钥策略
```
