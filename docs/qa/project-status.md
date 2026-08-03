# ProtoForge(原体锻炉) — 项目状态文档

> **本文档是项目的"单一事实来源",每次会话开始先看这里,结束时更新这里。**
> 最后更新: 2026-08-03

---

## 0. 一句话

游戏化的合成生物学众包平台,基于 Stanford Proto 论文(2026)构建。玩家通过锻造蛋白质、设计 DNA、提交 Steam 创意工坊,为科研贡献真实数据。

## 1. 技术架构

| 层 | 位置 | 技术 |
|---|---|---|
| 桌面壳 | `apps/desktop/` | Tauri(侧载 Python sidecar) |
| 前端 | `apps/web/` | React |
| 后端 sidecar | `apps/api/` | Python / FastAPI / 本地 LLM 推理 / 锻造引擎 |
| 共享类型 | `packages/shared/` | 前后端共享 TS 类型 |
| 模型资源 | `apps/api/vendor/` | Qwen2.5-7B GGUF、ESM2、proto-language 工具链 |
| 包管理 | 根 | pnpm monorepo + uv(Python) + changesets |

## 2. 里程碑时间线

| 阶段 | 日期 | 状态 | 关键产出 |
|---|---|---|---|
| Phase 1 | 2026-07-06 ~ | ✅ 完成 | 单机应用 + 1 关(极地耐低温发光菌) |
| Phase 2 | — | ✅ 完成 | 迭代,255 测试奠基 |
| Phase 3 | 2026-07-08 | ✅ 完成 | 6 轮决策落地: Steam 上传 / 3 步引导 / 退出惩罚 / 4 P0 修复 |
| Phase 4 | 2026-07-11 | 🔶 进行中 | A/C/L4 段完成;B 段(CI/CD)剩 B2 未全绿 |
| Phase 5 | 未启动 | ⏳ 规划 | 出真 .exe、真实玩家闭环、4 档难度数据回流 |

## 3. 当前焦点: Phase 4 B 段

| 子项 | 内容 | 状态 | 备注 |
|---|---|---|---|
| B1 | GitHub Secrets + Tauri 签名 | ✅ 完成 | `TAURI_SIGNING_PRIVATE_KEY`(+password) 已设;`set_secret.py` 工具已入库 |
| B2 | release workflow 全绿 | 🔶 挂起 | 修复方案已就绪,见 issue #1(待建) 与计划文档 |
| B4 | changesets 实战 | ✅ 完成 | 本地验证通过,CHANGELOG 0.1.1 已生成 |
| B5 | main 分支保护 | ⏭️ 跳过 | GitHub Free 不支持 branch protection API |

## 4. B2 挂起详情(下次恢复入口)

**根因**: `.changeset/phase4-b1-tauri-signing.md` 和 `.changeset/phase4-p1-and-debt.md` 引用 `@protoforge/api`(Python 包,不在 pnpm workspace),导致 CI `changeset version` 报错。两文件内容已被 CHANGELOG 0.1.1 固化(消费完成),是僵尸文件。

**现状**: main = `efcff97a`,本地与远端一致;工作区有 3 个行尾符噪音 M 文件(无内容差异)。

**恢复步骤**: 按 `docs/superpowers/plans/2026-08-03-phase4-b2-release-green.md` 执行 —— 删僵尸 changeset → 新建正确 changeset(`@protoforge/web` + `@protoforge/shared`)→ push(GFW 重试)→ workflow_dispatch → 监控 4 tauri job 全绿。

**挂起跟踪**: issue #10 (https://github.com/HC20251027/protoforge/issues/10)

**⚠️ Token 备忘**: 2026-08-03 曾因 PAT 嵌 git remote URL 被 GitHub 自动撤销(token 泄露检测)。已换新 token 并更新 remote;若再失效,需用户重新生成(scope: `repo` + `workflow`),并建议改用凭证管理器或 SSH 而非 URL 内嵌。

## 5. 测试基线

- **255 passed**(后端 220 + 前端 35)
- pytest 单次写盘 15GB → 0.6GB(L4 修复)

## 6. 环境备忘

| 项 | 状态 |
|---|---|
| 磁盘 | ~592GB 空闲(C 盘健康) |
| 网络 | GFW 间歇阻断 github.com:443,push 需重试 1-6 次 |
| pre-commit | 已装;gitleaks 改 local hook(项目内二进制 8.30.1),不再卡 docker |
| 监控器 | `.cache/monitor/` 命令追踪机制存在,会话间可查历史命令 |
| pnpm store | 项目内 `.pnpm-store/`(原 D 盘配置已废,已入 .gitignore) |

## 7. 维护约定

1. 每次会话开始: 读本文件 → 了解挂起项 → 决定继续哪个
2. 每次会话结束: 更新状态块 + 时间线 + 挂起详情
3. 完成一个 milestone: 把 `🔶 进行中` 改 `✅ 完成`,日期补全
4. 新阻塞出现: 立即在"挂起详情"记录根因与恢复步骤
5. 文档与代码同 commit,保持单一事实来源
