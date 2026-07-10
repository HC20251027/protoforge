# ProtoForge Phase 4 — A/B/C 串行收尾

> 排序原则:**A 修 Phase 3 残留 → B 出真 .exe → C 质量债**。
> 串行 subagent,直接 main,工程决策不再问。
> 起点:Phase 3 收官(后端 213 + 前端 42 = 255 测试通过,11 个 commit)。

---

## A 段:P1 三件套(Phase 3 残留) — 估 2-3h

### A1. 装 cryptography 升级 API key 加密(0.5h)

**问题**:`onboarding.py:179-235` 当前因 `cryptography` 没装,走 base64 fallback + `UserWarning`。生产环境 API key 明文(base64 是编码不是加密)。

**修复**:
- `apps/api/pyproject.toml` 加 `cryptography>=42.0.0` 到 `dependencies`
- `apps/api/uv.lock` 重生成
- `routers/onboarding.py` 验证 `Fernet` 真的能用(去掉 fallback 路径?或保留 fallback 显式 warn)
- 加测试:`test_onboarding_api.py` 加 3 个 Fernet 加密/解密/密钥派生测试
- 验证 base64 fallback 路径在缺 cryptography 时仍报 `UserWarning`(不静默)

**提交**:`fix(phase4): API key 加密升级 cryptography Fernet,移除静默 base64 fallback`

### A2. 修 GGUF magic byte bug(0.5h)

**问题**:`models/loader.py:177` 写 `b"GGUF"`,但真 GGUF v3 文件是 `b"\x03GGUF"`(版本号 3 在前)。当前 `try_load` 不严,玩家装真模型时静默失败。

**修复**:
- `loader.py:177` 改 `b"\x03GGUF"`
- `try_load` 路径:magic 不匹配 → 显式 `LLMUnavailable`(跟 P0-A2 一致原则)
- 加测试:`test_models_loader.py` 加 2 个测试(fake GGUF / 真 GGUF 各跑一次)

**提交**:`fix(phase4): GGUF magic byte 用真 v3 header b"\x03GGUF",加载失败显式化`

### A3. 删 detect_hardware() 残留(0.5h)

**问题**:`apps/api/app/proto/profile.py` 还在导出 `HardwareProfile / detect_hardware / recommend_ritual`,`__init__.py:6` 还在 re-export。Phase 3 决策 N2:"4 档按难度不按硬件",所以应**真删**。

**修复**:
- 删 `apps/api/app/proto/profile.py` 整个文件
- 改 `apps/api/app/proto/__init__.py` 去掉对应 re-export
- `grep -r "detect_hardware" apps/ docs/` 应只剩 0 命中(历史 commit 不算)
- 加测试:`test_proto_init.py` 加 1 个测试:`from app.proto import *` 不应抛 `ImportError`

**提交**:`refactor(phase4): 删 detect_hardware() 残留,4 档按难度不按硬件原则落地`

### A 段验收
- 后端 213 + A 段新增测试 ≥ 3 = ≥ 216 passed
- 前端 42 不变
- `grep -r "detect_hardware" apps/ docs/` 0 命中
- `ruff check apps/api/` 减少 5 个 F401(profile.py 删了连带)

---

## B 段:CI/CD 收尾(出 Phase 3 真 .exe) — 估 2-3h

### B1. 配 GitHub Secrets(网页,不算提交)

| Secret | 怎么生成 |
|--------|---------|
| `TAURI_SIGNING_PRIVATE_KEY` | `npx @tauri-apps/cli signer generate -w ~/.tauri/protoforge.key`,把内容 base64 |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | 上一步设的密码 |
| (跳过) `NPM_TOKEN` | 本项目不发 npm |

### B2. 手动 `workflow_dispatch` 跑 release(0.5h)

- 第一次跑会下载 Rust 工具链,30+ 分钟
- 验证:三平台都产 .exe / .dmg / .AppImage
- 验证:Release 草稿创建,`latest.json` 上传

### B3. 本地 `pre-commit install` + 跑一次(0.5h)

```bash
pipx install pre-commit
pre-commit install
pre-commit run --all-files
```

预期 5 个 hook 跑通:
- pre-commit-hooks(行尾、尾行、yaml/json/toml 合法、大文件、private key)
- ruff + ruff-format
- gitleaks
- yamllint
- actionlint

### B4. 第一次 changeset 实战(0.5h)

- `.changeset/init.md` 写一个 changeset 描述这一轮 Phase 4 修了什么
- `git add .changeset/` + commit
- 推 main → release.yml 自动 version bump

### B5. main 分支保护规则(网页,不算提交)

GitHub → Settings → Branches → main:
- Require PR before merging ✓
- Require 1 approval(单人可改 0)
- Require status checks: `ci / web`, `ci / api`, `ci / shared`
- Require linear history

### B 段验收
- 三平台 Tauri 安装包产出
- pre-commit 本地跑通
- 第一个 changeset → release.yml 跑通
- main 保护规则生效

---

## C 段:历史欠账清理 — 估 2-3h

### C1. 修 21 个 F401 未用 import(1h)

**问题**:Phase 1/2 写代码时 ruff 没跑过,留 21 个 F401。CI / pre-commit 已配 `|| true` 临时放过。

**修复**:
- `ruff check apps/api/app --fix`(自动修 17 个,留 4 个手改)
- 手动修:`E402` 1 个 + 3 个 F401(非 fixable)
- CI / pre-commit 改回 `--exit-non-zero-on-fix` / fail-on-error
- 加测试:`test_proto_lint.py` 跑 `ruff check .` 应 0 错误(防止未来再堆 F401)

**提交**:`chore(phase4): 清 21 个历史 F401,CI ruff 改 fail-on-error`

### C2. 修 .gitignore 重复行 + apps/api/.gitignore 冗余(0.5h)

**问题**:
- 根 `.gitignore:31-32` `.protoforge/` 写了两次
- `apps/api/.gitignore` 跟根重复

**修复**:删重复行,合并

**提交**:`chore: .gitignore 去重`

### C3. 子目录 README(1h)

**问题**:`apps/api/` `apps/web/` `apps/desktop/` `packages/shared/` 没 README,新开发者摸不清入口。

**修复**:
- 每个子目录加 README.md(30-50 行)
  - 模块职责
  - 主要 entrypoint 文件
  - 跑测试命令
  - 跟其他模块的接口
  - Phase 3 改动的关键文件

**提交**:`docs: apps/{api,web,desktop} + packages/shared 各加 README`

### C4. vendor 模型 SHA256 校验(0.5h)

**问题**:目前只有 ESM2-150M 有 sha256,LLM gguf 没有。

**修复**:
- `apps/api/vendor/llm/` 加 `.sha256` 文件
- `scripts/verify_vendor.sh` 一行命令校验所有 vendor 资源
- 写进 CONTRIBUTING.md

**提交**:`chore: vendor 资源加 SHA256 校验脚本`

### C 段验收
- `ruff check apps/api/` 0 错误
- 4 个子目录都有 README
- 5 个 vendor 资源都有 SHA256

---

## 时间预估(总)

| 段 | 估时 | 风险 |
|----|------|------|
| A | 2-3h | 低(纯小修) |
| B | 2-3h | 中(B2 release 首次跑 30+ 分钟;B1 secret 配错要重做) |
| C | 2-3h | 低(纯清理) |
| **总** | **6-9h** | |

## 串行决策

每段内部 3-5 个子项,串行 subagent dispatch(Phase 3 验证过稳定)。
每子项结束,subagent 跑全量 pytest + vitest 验证 0 回归,我自己 review commit。
B2 release 第一次跑 30+ 分钟期间,我并行做 B3 pre-commit install(独立)。

## 分支策略

直接 main。Phase 3 11 个 commit 都在 main,保持一致。
后续 Phase 5(若多人)再上 trunk-based 短分支。

## 风险

| 风险 | 应对 |
|------|------|
| B2 release 编译失败(Rust 依赖 / Tauri config) | 回滚 release.yml 不影响 main,代码层不受影响 |
| A1 cryptography 装不上 Windows | fallback base64 路径保留,加 UserWarning 显式 |
| C1 修 F401 误改运行时代码 | subagent 跑全量 pytest 兜底,出问题 revert commit |

---

## 启动顺序(我接下来 5 分钟干的事)

1. 写本 plan → 已完成(就是这文件)
2. dispatch subagent 跑 A1 cryptography
3. subagent 跑完 → commit → dispatch A2
4. A2 → commit → dispatch A3
5. A3 → commit → A 段验收(后端 216+ passed)
6. dispatch B1-B5(B2 release 跑期间并行 B3 pre-commit)
7. B 段验收(三平台 .exe + pre-commit 跑通)
8. dispatch C1-C4
9. C 段验收(ruff 0 错 + 4 README + SHA256)
10. 写 Phase 4 complete report → commit
