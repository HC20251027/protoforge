# Changelog

> 由 [@changesets/cli](https://github.com/changesets/changesets) 自动生成。
> 玩家可感知的变更在 PR 合入 main 时,会被 `.github/workflows/release.yml` 收集并写入此文件。

## 格式
```
## <version> (<发布日期>)

### Patch Changes
- ...

### Minor Changes
- ...

### Major Changes
- ...
```

## 手动维护区(Phase 3 之前的累积)

### Phase 3 (2026-07-09)

- **feat(core): N1 完整封装** — vendor proto-language 60+ 文件、ESM2-150M 模型(567MB)、Qwen2.5-7B GGUF(4.36GB),Tauri sidecar 嵌入 Python 解释器,玩家双击 .exe 直接玩,无网络等待
- **feat(ritual): 4 档难度落地** — 急锻(2-5s) / 主锻(30-120s) / 古法锻(5-15min) / 晶种培育(30-120min),按难度不按硬件,默认走急锻
- **feat(ritual): 退出惩罚** — 4 档都生效,80% 阈值 KEEP/LOSE,顶部固定红色横幅 "⚠️ 锻造中退出游戏会有概率失败",**无百分比**
- **feat(onboarding): 3 步配置** — vendor 状态检测 → LLM 选择(默认云 API)→ API key 配置,Fernet 加密(base64 fallback)
- **feat(steam): 创意工坊自动上传** — 通关后 `.protoforge` 打包 + 离线队列 + Steam 适配层(MOCK,Phase 4 接真),玩家不点按钮
- **fix: P0-A1** — `gallery_store` 改独立 event loop,不再阻塞主 loop
- **fix: P0-B1** — 锻造完成后自动写入 Gallery(核心循环最后一环)
- **fix: P0-C1** — Tauri sidecar 端口对齐后端 `PROTOFORGE_API_PORT` env
- **fix: P0-A2** — `run_forge` 显式失败,`errors: list[str]` 字段透传前端,红色 banner

**测试**:后端 213 passed(从 51 起) + 前端 42 passed(从 3 起),共 255 个测试

详见:
- `docs/qa/phase3-acceptance.md` — 验收报告
- `docs/qa/phase3-deferred.md` — 未解决项清单
- `docs/qa/phase3-p0-fixes.md` — P0 修复总结
- `docs/superpowers/plans/2026-07-07-protoforge-phase3.md` — Phase 3 计划原文

### Phase 2 (2026-07-07)

- **feat(forge): natural_language 字段** — 玩家在 forge 页输入自然语言描述,服务端先调 translate 再 forge,一步到位
- **feat(scorer): SpliceTransformer PWM 评分** — 基于位置权重矩阵的 donor/acceptor 打分,无需 torch
- **feat(llm): LLMProvider 抽象** — `chat(messages, temperature, max_tokens, config)`,CloudProvider / LocalProvider / DisabledProvider 三个实现
- **feat(translate): NL 翻译** — 自然语言描述 → 滑块参数

### Phase 1 (2026-07-06)

- **chore: 项目骨架** — pnpm monorepo,3 apps(api / web / desktop)+ 1 shared 包
- **feat(api): FastAPI sidecar** — 极地耐冷萤光任务模板 + MCMC 搜索 + PWM 评分
- **feat(web): React + Vite** — 主页 / 任务 / 锻造 / 风控门 / 作品库
- **feat(desktop): Tauri 2 桌面壳** — 把 web 包成 .exe,集成 Python sidecar
