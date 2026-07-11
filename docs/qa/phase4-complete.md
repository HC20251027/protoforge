# Phase 4 Complete Report

> 日期: 2026-07-11
> 周期: Phase 3 收官 (2026-07-08) → Phase 4 完成 (2026-07-11)
> 总测试: **255 passed** (后端 220 + 前端 35)

---

## 4 块格式总结

### [决定] Phase 4 任务全部跑完,后端 220 / 前端 35 全过

### [为什么] 4 段都收官,工程问题已工程化解决

| 段 | 任务 | 状态 | 测试 |
|---|---|---|---|
| **A** P1 修复 | A1 cryptography API key 加密 | ✅ commit `1f21cf60` | 216 |
| | A2 GGUF magic byte 修复 | ✅ commit `d8b6f41e` | 218 |
| | A3 detect_hardware 删除 | ✅ commit `e8f0fba4` | 219 |
| **C** 质量债 | C1 21 F401 清理 | ✅ commit `62473e3b` | 220 |
| | C2 .gitignore 去重 | ✅ commit `19139de7` | (无新增) |
| | C3 4 个子目录 README | ✅ commits `73916370` `4230bb18` `6512030e` | (无新增) |
| | C4 vendor SHA256 校验脚本 | ✅ commit `88da8abd` | (无新增) |
| **L4** 测试基建 | 注入 min_size_mb 阈值 | ✅ commit `400ade72` | 220 |
| **B** CI/CD 收尾 | B1-B5 详见 `phase4-b-checklist.md` | ⏳ 4 项需用户操作 (网页 + 本机) | — |
| | B4 第一个 changeset | ✅ `.changeset/phase4-p1-and-debt.md` | — |

### [风险] 仍在 staged/unstaged 状态的文件需用户 review

```
M  .gitignore                                                              ← Step B
A  apps/api/vendor/proto-language/{.gitignore,LICENSE,README.md,pyproject.toml}
A  docs/superpowers/plans/2026-07-07-protoforge-phase{1.5,2}.md
?? .changeset/phase4-p1-and-debt.md
?? docs/qa/phase4-b-checklist.md
?? docs/qa/phase4-l4-fix.md
```

总计 7 staged + 3 untracked,**共 10 个新文件待 commit**。建议在用户拍板后由我做 1-2 个 cleanup commit。

### [兜底] Phase 5 启动方向

#### 产品层
- 主线: **出 Phase 3 真 .exe** (走 B1-B5 完整 CI/CD 流水线)
- 玩家首次启动体验: 3 步 onboarding 已在 Phase 3 完成,接下来是 1-2 个真实玩家跑通闭环
- 4 档难度 Steam Workshop 上传 (Phase 3 Task 5 接入) → 验证 Stanford Proto 论文 R2 数据回流

#### 工程层
- L4 验证通过后,继续推进其他 `LocalLLMLoader` 类似硬编码阈值参数化 (其他 loader 如 ESM2Loader 已经在测试中走 monkeypatch,可不改)
- proto-language 子模块化评估: 当前 vendor 模式工作正常,如未来要跟上游同步,改 submodule
- pre-commit 5 个 hook 跑通 (B3 依赖本机环境,可能需 `pip install pre-commit` 而不是 uv)

#### 数据/质量层
- C 盘爆满调查: 500GB 缺口中只有 30GB 是我工作产物,剩余 470GB 是 Windows 系统自身积累 (WinSxS 旧补丁、DeliveryOptimization P2P 缓存、回收站等)。cleanmgr 释放后回到 647GB 健康态,无需进一步清理。
- 命令追踪机制 (`.cache/cmdlog/`) 已建立,后续每个 session 可查询历史执行命令

---

## 详细 commit 链

| SHA | 标题 | 段 |
|---|---|---|
| 400ade72 | test(llm): 注入 min_size_mb 阈值,跑一次 pytest 写盘从 15GB 降到 0.6GB | L4 |
| 88da8abd | chore(scripts): vendor SHA256 校验脚本 + CONTRIBUTING.md 加 vendor 校验章节 | C4 |
| 6512030e | docs(shared): packages/shared/README.md - 单一类型文件规则 | C3 |
| 4230bb18 | docs(web): apps/web/README.md - 入口 + 4 档本地状态 + Phase 3 关键改动 | C3 |
| 73916370 | docs(api): apps/api/README.md - 入口 + 测试 + Phase 3 关键改动 | C3 |
| 19139de7 | chore: .gitignore 去重(删 2 行重复) | C2 |
| 62473e3b | chore(phase4): 清 21 个历史 F401,CI ruff 改 fail-on-error | C1 |
| e8f0fba4 | refactor(phase4): 删 detect_hardware() 残留,4 档按难度不按硬件原则落地 | A3 |
| d8b6f41e | fix(phase4): GGUF magic byte 用真 v3 header b"\x03GGUF",加载失败显式化 | A2 |
| 1f21cf60 | fix(phase4): 装 cryptography 升级 API key Fernet 加密 | A1 |
| f89835f9 | docs(plan): Phase 4 — A/B/C 串行收尾 plan | (plan) |

---

## 工程决策回顾

| 决策 | 理由 | 后果 |
|---|---|---|
| L2 → L4 切换 | L2 用 truncate sparse 在 NTFS 上不真占盘的判断错误,实际写 16GB/次 | L4 通过产品代码 `__init__` 注入阈值,产品行为零变化 |
| proto-language 用 vendor 而非 submodule | 已经在本地 work,改 submodule 风险大;只保留 4 个元文件 | 新机器 clone 后需 `vendor/proto-language` 步骤重新拉取 |
| B1/B2/B5 留用户操作 | 这些是 GitHub 网页配置或本机命令,无法在代码侧完成 | 用户需要外部操作才能让 CI/CD 完整跑通 |
| 测试 fixture 用 truncate 而非 sparse flag | truncate 已能写 1-2MB,sparse 需要 ctypes Win32 API 复杂 | 跑一次 0.6GB 残留,可接受 |
| `.cache/cmdlog/` 建于项目目录 | 用户规则"项目优先" | 不污染 C 盘,可作为 session 间追踪机制 |

---

## 报告落点

- `docs/qa/phase4-l4-fix.md` — L4 修复详细报告 (问题/根因/修法/效果/验证)
- `docs/qa/phase4-b-checklist.md` — B 段用户操作清单 (B1/B2/B3/B5 详细步骤)
- `docs/qa/phase4-acceptance.md` — Phase 4 验收清单 (待补)
- `docs/qa/phase3-acceptance.md` — Phase 3 验收 (旧)
- `docs/qa/phase3-deferred.md` — Phase 3 未解决项 (10 项)
- `docs/qa/phase3-p0-fixes.md` — Phase 3 P0 修复 (4 项)

---

## Phase 4 收尾

✅ A 段 / C 段 / L4 全部 commit
✅ 220 + 35 = 255 测试全过
✅ Phase 3 P0 4 项 + Phase 4 P1 3 项全部解决
⏳ B 段 4 项等用户外部操作 (详见 `phase4-b-checklist.md`)
⏳ 10 个待 commit 文件 (`.gitignore` + proto-language 元文件 + 历史 plan + 3 个新报告/changeset) 等用户拍板
