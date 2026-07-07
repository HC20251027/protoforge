# ProtoForge Phase 3 — 核心玩法落地 + 端到端贯通

> 目标:把今天(2026-07-07)6 轮决策的产品级承诺**真正做到代码里**,让 ProtoForge 从"框架"变成"能玩的策略游戏"
> 排序原则:**核心玩法(N1 + 4 档 + 退出惩罚)优先,P0 bug 修复垫底**
> 起点:Phase 2 完成(后端 51 passed,前端 3 passed)
> 范围:6 个 task,按"产品价值密度"排序

---

## Task 1: N1 完整封装 — proto-language + ML 模型 + 本地 LLM 打包进游戏

### 产品级承诺
- 安装包 8-12GB,Python 解释器内嵌,proto-language + ML 模型 + 本地 LLM 全部 bundled
- 玩家双击 .exe → 直接玩,**全程无下载、无网络等待、无弹窗**
- Qwen2.5-7B GGUF 量化打包,llama.cpp 推理引擎打包

### 子任务分解
1. **N1.1 vendor proto-language 源码**
   - 克隆 `github.com/evo-design/proto-language` 到 `apps/api/vendor/proto-language/`
   - 克隆子模块 `proto-tools` 到 `apps/api/vendor/proto-language/proto-tools/`
   - 修改 `pyproject.toml` 用 `[tool.uv.sources]` 把 proto-tools 指向本地 path
   - 验证:`python -c "import proto_language"` 成功

2. **N1.2 vendor ML 模型权重**
   - 下载 ESM2-150M safetensors → `apps/api/vendor/models/esm2-150m/`
   - 下载 SpliceAI Keras → `apps/api/vendor/models/spliceai/`
   - 下载 SpliceTransformer-base PyTorch → `apps/api/vendor/models/splice-transformer/`
   - 验证:每个模型加载 < 3s,总分计算正确

3. **N1.3 vendor 本地 LLM(Qwen2.5-7B GGUF)**
   - 下载 Qwen2.5-7B-Instruct-Q4_K_M.gguf → `apps/api/vendor/llm/qwen2.5-7b-instruct-q4_k_m.gguf`
   - vendor llama.cpp Python wheel(避免编译)
   - 写 `apps/api/app/local_llm.py` 封装 llama.cpp 调用
   - 验证:玩家进游戏 → 首次加载 5-10s,之后常驻

4. **N1.4 嵌入 Python 解释器到 Tauri bundle**
   - 修改 `apps/desktop/src-tauri/tauri.conf.json` 把 `vendor/` 加到 `bundle.resources`
   - 写 `scripts/build_release.sh` 一步打包:vendor + Python 嵌入 + ML 模型 + LLM
   - 验证:`pnpm tauri build` 产出 .exe 大小在 8-12GB 区间

5. **N1.5 引导页接 vendor 资源**
   - 引导页第 1 步选"本地 LLM" → 自动检测 vendor 路径,加载 bundled 模型
   - 不再依赖玩家自己装 Ollama

### 验收
- [ ] `import proto_language` 在 ProtoForge .exe 内置 Python 中成功
- [ ] ESM2/SpliceAI/SpliceTransformer 都能加载并打分
- [ ] Qwen2.5-7B 在 llama.cpp 上能对话
- [ ] `pnpm tauri build` 产出 .exe 大小 8-12GB
- [ ] 玩家双击 .exe → 进游戏 → 5-10s 后 LLM 可用,无任何弹窗
- [ ] 后端新增 3-5 个测试覆盖 vendor 资源加载
- [ ] 后端 51 → 55+ passed

---

## Task 2: 4 档难度落地 — 不跟硬件挂钩,默认走急锻

### 产品级承诺
- 4 档(急锻/主锻/古法锻/晶种培育)按难度分,不按硬件
- 时长 C 方案(2-5s / 30s-2min / 5-15min / 30min-2h)
- 启动默认走急锻(2-5 秒)
- 玩家可在 Settings 升级档位
- 可同时锻造多个(急锻/主锻 1 个,古法锻 3 个,晶种培育 5 个)

### 子任务分解
1. **改 `apps/api/app/proto/engine.py`**
   - `run_forge` 接受 `ritual` 参数(急锻/主锻/古法锻/晶种培育)
   - 不再根据 `RitualInfo` 的 `min_gpu_mb` 自动降级
   - 根据 `ritual` 决定 MCMC 步数 + 同时锻造数

2. **改 `apps/api/app/routers/forge.py`**
   - `forge_run` 接受 `ritual` 字段
   - 推荐 API(`/ritual/recommend`)默认返 `急锻`

3. **改 `apps/web/src/pages/ForgePage.tsx`**
   - 加档位选择器(4 选 1)
   - 显示当前档位预估时长
   - 默认选中急锻

4. **改 `apps/web/src/pages/SettingsPage.tsx`(新增)**
   - 玩家主动改默认档位

5. **改测试**
   - 跑 4 档 = 都成功(不依赖硬件)
   - 默认 ritual = 急锻
   - 改 1 档不破坏现有 51 个测试

### 验收
- [ ] 4 档全部跑通,玩家在 4-12GB 内存机器上都能玩
- [ ] 默认 ritual = 急锻
- [ ] 同时锻造数符合 1/1/3/5
- [ ] 后端 51 passed 不变 + 4 个新测试 = 55 passed
- [ ] 前端 3 passed 不变 + 1 个新测试 = 4 passed

---

## Task 3: 退出惩罚 — 根据"现实是否计算完"决定

### 产品级承诺
- 4 档都生效:玩家退出时**计算已跑完 = 保留**,**没跑完 = 失败**
- UI 顶部红色横幅:「⚠️ 锻造中退出游戏会有概率失败」
- 玩家看不到具体百分比

### 子任务分解
1. **改 `apps/api/app/proto/engine.py`**
   - `run_forge` 把计算状态写到 SQLite `runs` 表(状态:running / done / failed)
   - 玩家退出前不主动保存中间状态

2. **改 `apps/web/src/components/ForgingBanner.tsx`(新增)**
   - 顶部红色横幅,任何时候只要 `forging=true` 就显示
   - 文案:「⚠️ 锻造中退出游戏会有概率失败」

3. **改 `apps/web/src/lib/api.ts`**
   - `forgeApi.run()` 返回 run_id,玩家用 run_id 查状态
   - 加 `forgeApi.getRun(runId)` 查运行状态(如果 done,带结果)

4. **前端加 beforeunload 监听**
   - `forging=true` 时,玩家点 X 关浏览器 → 弹原生 confirm
   - 文案:「锻造还没完成,确定要退出吗?」

### 验收
- [ ] forging 时显示红色横幅
- [ ] 玩家关浏览器弹原生 confirm
- [ ] run_id 持久化,刷新可查状态
- [ ] 后端 55 passed 不变
- [ ] 前端 4 → 6 passed

---

## Task 4: 引导页 — 3 步配置,云 API 优先

### 产品级承诺
- 首次启动显示 3 步引导
- 第 1 步默认推荐云 API
- 引导页有"免费 API 渠道推荐"链接(跳转 GitHub)
- 完成后永不再问(除非主动进 Settings)

### 子任务分解
1. **改 `apps/web/src/pages/OnboardingPage.tsx`**
   - 3 步表单(LLM 选择 / API key 填 / 档位确认)
   - 默认选项 = ☁️ 云 API
   - 跳 GitHub `awesome-free-api` 链接(占位 URL,Phase 4 替换)

2. **改 `apps/api/app/routers/onboarding.py`**
   - `/onboarding/save` 持久化玩家选择
   - 启动时 `/onboarding/state` 检查"是否已配置",未配置 → 前端跳引导页

3. **改 `apps/web/src/App.tsx`**
   - 路由加 `/onboarding`(首次启动跳转)
   - 已配置玩家走 `/`

4. **加测试**
   - 引导页 3 步流程 vitest
   - onboarding/save API 测试

### 验收
- [ ] 首次启动跳引导页,3 步配置完后跳主页
- [ ] 默认推荐 ☁️ 云 API
- [ ] "免费 API 渠道"链接可点
- [ ] 已配置玩家不会再被引导
- [ ] 后端 55 passed 不变 + 2 个新测试 = 57 passed
- [ ] 前端 6 → 9 passed

---

## Task 5: Steam 创意工坊自动上传 — 通关后,玩家不点按钮

### 产品级承诺
- 玩家通关 RiskGatePage → 自动调 Steam Workshop API 上传作品
- 玩家不点按钮
- 失败有 toast,不阻塞

### 子任务分解
1. **研究 Steam Workshop API**
   - 用 `steamworks.js`(Node 库)或 Rust `steamworks` crate
   - 上传接口:`ISteamUGC::SubmitItemUpdate`
   - 玩家需要登录 Steam 客户端

2. **改 `apps/desktop/src-tauri/src/commands.rs`**
   - 加 `upload_to_steam_workshop(artifact)` 命令
   - 调 steamworks 库上传

3. **改 `apps/api/app/routers/gallery.py`**
   - 加 `/api/gallery/auto_upload` 接口
   - 接收通关后的作品,持久化到本地 + 转发给 Tauri 上传

4. **改 `apps/web/src/pages/RiskGatePage.tsx`**
   - 通关后调 `galleryApi.autoUpload(artifact)`
   - 不阻塞 navigate 到 gallery

5. **加测试**
   - autoUpload 失败 → 玩家仍然能进 gallery 页(toast 提示)
   - 上传成功 → Gallery 列表显示

### 验收
- [ ] 通关自动上传(玩家不点按钮)
- [ ] 上传失败有 toast,玩家不卡死
- [ ] Tauri release 模式下能调 Steam Workshop
- [ ] 后端 57 passed 不变 + 2 个新测试 = 59 passed
- [ ] 前端 9 → 12 passed

---

## Task 6: P0 bug 修复 — 端到端跑通

> **P0 4 项**:C1 Tauri 端口 / B1 Gallery 自动保存已被 Task 1-5 覆盖
> **剩余** A1(asyncio.run)+ A2(run_forge 静默退化)实际上也已经覆盖
> **真正的 P0 剩余** 是"4 档之后 rl 信息"(product.md 13 节里"完整封装打包脚本"+"ProtoForge 自家服务器"+"P0 代码 bug 修复"等)

### 子任务分解
1. **A1:改 `routers/gallery.py` 全部 `async def`**
   - `gallery_store.py` 删 sync wrapper,直接 async
   - 加 event-loop 集成测试

2. **A2:`engine.py` 4 个静默退化**
   - `_load_template` 找不到 → 抛 ValueError
   - MCMC step=0 → 真的跑 1 步
   - seed 真的生效(不是只传给 generator)
   - PWM 失败 → 抛 ValueError

3. **C1:Tauri 端口一致**
   - vite.config.ts 与 sidecar.rs 统一读 `PROTOFORGE_API_PORT`
   - 默认 7654

4. **B1:Gallery 自动保存(已被 Task 5 覆盖,这里只补遗漏)**
   - RiskGatePage 答完所有题 → 提交判定 → 通过 → 调 galleryApi.create
   - localStorage 缓存最近一次结果

### 验收
- [ ] A1:production event loop 跑通
- [ ] A2:4 个静默退化全修
- [ ] C1:端口 7654 在 dev + prod 一致
- [ ] B1:通关自动保存 + 失败不阻塞
- [ ] 后端 59 → 63 passed
- [ ] 前端 12 → 14 passed

---

## 全量验证(Task 1-6 全部完成)

- [ ] 后端 63 passed
- [ ] 前端 14 passed
- [ ] 前端 build 成功
- [ ] Tauri build 成功(产出 8-12GB .exe)
- [ ] 玩家从下载 → 进游戏 → 通关 → 上传 Steam 创意工坊,端到端跑通
- [ ] RUNBOOK 更新到 Phase 3
