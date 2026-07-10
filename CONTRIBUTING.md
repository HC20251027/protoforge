# 提交前请看
- 现有 issue / PR,避免重复
- 现有 `docs/`,尤其是 `docs/qa/phase3-deferred.md`(未解决项清单)

# 这个项目是什么
ProtoForge(原体锻炉):游戏化的合成生物学众包平台,基于 Stanford Proto 论文(2026)构建。
玩家通过滑块 + 4 档难度(急锻/主锻/古法锻/晶种培育)设计内含子序列,通过风险门,通关后自动上传 Steam 创意工坊。
当前阶段:Phase 3 收官,后端 213 + 前端 42 = 255 测试通过。**核心玩法完整,P0 bug 全修**。

# 开发环境
- **Node**:>= 20(用 `corepack enable` 启用 pnpm)
- **pnpm**:>= 9(`packageManager` 字段已锁 9.12.0)
- **Python**:3.10 - 3.12(用 `uv`,**不要**用 pip)
- **Rust**:1.78+(Tauri 编译用,**不要**手改 `Cargo.toml` 不必要的依赖)
- **OS**:Windows 10+ / macOS 12+ / Ubuntu 22.04+

# 1. 准备
```bash
# 仓库根
git clone <repo-url> && cd <repo-dir>
corepack enable && corepack prepare pnpm@9.12.0 --activate

# 装 JS 依赖(2-5 分钟)
pnpm install --store-dir .pnpm-store

# 装 Python 依赖
cd apps/api && uv sync && cd ../..

# 装 pre-commit hooks(只需一次)
pipx install pre-commit  # 或 uv tool install pre-commit
pre-commit install
```

# 2. 分支策略
本项目用 **Trunk-Based + 短期 feature 分支**(< 3 天合入或 close):
- `main` — 唯一长寿命分支,默认受保护,需 PR
- `feat/xxx` / `fix/xxx` — 开发者短期分支

**不要**用 `develop` / `release/*` / `hotfix/*`(GitFlow,本项目不需要)。

# 3. 提交规范 — Conventional Commits
```
<type>(<scope>): <subject>

<body>(可选)

<footer>(可选)
```

`type` 必须是:
- `feat` — 新功能 → minor
- `fix` — bug fix → patch
- `refactor` / `chore` / `docs` / `perf` / `test` / `style` — patch
- `feat!` / `fix!` — 含 `BREAKING CHANGE:` → major

`scope` 例子:`api` / `web` / `desktop` / `shared` / `ci` / `docs`

**例子**:
- `feat(api): add /api/onboarding/state endpoint`
- `fix(desktop): align sidecar port with backend PROTOFORGE_API_PORT`
- `docs(qa): add phase3-deferred.md`

# 4. 发版流程 — changesets
**玩家可感知的变更必须配 changeset**:
```bash
pnpm changeset
# 交互式:选 "哪些包" + "patch/minor/major" + 写描述
# → 生成 .changeset/random-name.md
git add .changeset/
git commit -m "feat(api): ..."
```

推到 `main` 后,`.github/workflows/release.yml` 会:
1. 自动把所有 changeset 合并 → bump `package.json` / `pyproject.toml` version
2. 生成 `CHANGELOG.md`
3. 编译 Tauri 三平台安装包(macOS x2 / Ubuntu / Windows)
4. 推 GitHub Release(draft)

**不要**手改 `package.json` / `pyproject.toml` 的 `version` 字段(changesets 接管)。
**不要**直接 `git tag` + push(由 `release.yml` 自动化)。

# 5. 跑测试
```bash
# 后端(213 个测试)
cd apps/api && uv run pytest -q

# 前端(42 个测试)
cd apps/web && pnpm test

# Lint + 类型
cd apps/web && pnpm lint
cd apps/web && pnpm exec tsc --noEmit
cd apps/api && uv run ruff check .
```

# 6. 数据 / 仓库
以下**绝不入 git**(已在 `.gitignore`):
- `.protoforge/` — 玩家数据(SQLite、序列、模型缓存)
- `apps/api/vendor/models/**/*.safetensors|h5|pt|gguf` — 权重(本地下载由 README + sha256 校验)
- `apps/api/vendor/llm/*.gguf` — Qwen2.5-7B LLM 权重
- `apps/desktop/src-tauri/target/` — Rust 编译产物
- `apps/desktop/src-tauri/binaries/python-bundle/` — Python 嵌入产物(走 `scripts/bundle_python.py` 重建)

# 7. 玩家体验链路(改动前自检)
改动前先想清楚:这次改动会动到玩家哪条链路?
```
引导页 (3 步) → /forge 任务列表 → polar-glow-v1 → 4 档 segment → 调滑块
  → 红色 banner 出现 → run_forge → 进度写 RitualStateStore
  → /unfinished 按 80% 阈值 KEEP/LOSE → RiskGatePage
  → 通过 → .protoforge 打包 + 队列入队 + Steam 上传
  → Gallery 自动保存 + Toast 提示
```

详细节点见 `docs/qa/phase3-acceptance.md`。

# 8. 提交前 Checklist
- [ ] `pre-commit run --all-files` 全过(本地)
- [ ] `uv run pytest` + `pnpm test` 全过
- [ ] `uv run ruff check .` + `pnpm lint` 全过
- [ ] commit 信息符合 Conventional Commits
- [ ] 玩家可感知变更加了 `pnpm changeset`
- [ ] 大文件 / 权重未入 git
- [ ] PR 描述对应了 `.github/PULL_REQUEST_TEMPLATE.md` 的所有 section

# 9. 找不到答案时
1. 看 `docs/qa/phase3-deferred.md` — Phase 3 未解决项清单
2. 看 `docs/RUNBOOK.md` — 跑通手册
3. 看 `docs/superpowers/plans/2026-07-07-protoforge-phase3.md` — Phase 3 计划原文
4. 看 `apps/api/` / `apps/web/` / `apps/desktop/` 各目录的 README(待补)
5. 提 issue,选对应模板(bug / feature)
