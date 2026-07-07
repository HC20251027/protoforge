# ProtoForge Phase 3 — 玩家旅程端到端贯通

> 目标:让玩家从下载 .exe → 完成关卡 → 看到作品 → 上传 Steam 创意工坊,端到端跑通,无白屏 / 404 / 数据丢失任何一个断点
> 起点:Phase 2 完成(后端 51 passed,前端 3 passed),但有 4 个 P0 代码 bug 必须修
> 范围:只修 P0 4 项(代码层面),不引入新功能
> 不修 P1+ 项(等 Phase 3.5/4)

---

## Task 1: P0 C1 — Tauri 端口不一致修复

### 问题描述
- `apps/web/vite.config.ts` proxy 写 `/api → http://127.0.0.1:7654`
- `apps/desktop/src-tauri/src/sidecar.rs` sidecar 实际监听 **7655**
- **Tauri 打包后** Vite proxy 不生效(只 dev 模式有效),生产 100% 不可用
- 玩家下载 .exe 双击 → 进入游戏 → 看到登录页 → 点"开始游戏" → 白屏 / 404

### 修复方案(选最简)
1. **统一端口**:`PROTOFORGE_API_PORT` 单一来源,sidecar 与 vite proxy 都读这个 env,默认 7654
2. **Tauri 生产用 absolute URL**:sidecar 启动时把端口写到 `app_data_dir/api_port.json`,前端 build 时通过 `__TAURI_IPC__` 读
3. **失败 fallback**:sidecar 启动失败时,Tauri 弹"API 服务启动失败"提示而非白屏

### 涉及文件
- `apps/web/vite.config.ts`(改端口来源)
- `apps/desktop/src-tauri/src/sidecar.rs`(写端口文件)
- `apps/desktop/src-tauri/src/commands.rs`(暴露读端口的命令)
- `apps/web/src/lib/api.ts`(读端口 → 构造 base URL)
- `apps/desktop/src-tauri/tauri.conf.json`(确认配置)

### 验收
- [ ] 端口 7654 在 dev 和 prod 一致
- [ ] Tauri release 模式下能正常调 API
- [ ] sidecar 启动失败时 Tauri 弹错误而非白屏
- [ ] 后端 51 passed 不变
- [ ] 前端 3 passed 不变

---

## Task 2: P0 B1 — RiskGatePage 通关后自动保存到 Gallery

### 问题描述
- `apps/web/src/pages/RiskGatePage.tsx` 通关后只 `navigate("/gallery")`
- **没有** `galleryApi.create()` 调用
- 玩家通关后作品**只活在内存,刷新就丢**
- `apps/web/src/lib/api.ts` 已有 `galleryApi.create()` 但调用点 = 0

### 修复方案
1. **RiskGatePage 答完所有题 → 提交判定 → 通过 → 调 `galleryApi.create()`**
2. **保存内容**:run_id + intron 序列 + fasta + 评分 + 任务 ID + 玩家通关时间
3. **错误处理**:save 失败弹 toast,玩家重试;不阻塞 navigate 到 gallery 页
4. **localStorage 缓存**:玩家最近一次通关结果,刷新页面仍能看到

### 涉及文件
- `apps/web/src/pages/RiskGatePage.tsx`(主改)
- `apps/web/src/lib/api.ts`(加 `getRecentRun` 缓存接口)
- `apps/web/src/pages/GalleryPage.tsx`(空状态加引导)
- `apps/web/src/components/Toast.tsx`(新增全局 toast 组件,供风险门失败用)

### 验收
- [ ] 通关后自动调 galleryApi.create,玩家不点按钮
- [ ] Gallery 页面能看到刚保存的作品
- [ ] 失败有 toast 提示,不白屏
- [ ] localStorage 缓存生效(刷新仍在)
- [ ] 新增 2-3 个 vitest 测试覆盖 RiskGatePage 自动保存
- [ ] 后端 51 passed 不变
- [ ] 前端 3 → 5 passed

---

## Task 3: P0 A1 — Gallery router 改 async def

### 问题描述
- `apps/api/app/routers/gallery.py` 用 `def` 不是 `async def`
- 底层 `gallery_store.add/list_all/get` 是 sync wrapper,内部 `asyncio.run(_add_sqlite(req))`
- TestClient 跑 anyio 线程,不暴露
- **生产用 uvicorn 单 loop 模式**,FastAPI 在 event loop 线程跑 sync handler,`asyncio.run()` 立刻抛 `RuntimeError: asyncio.run() cannot be called from a running event loop`

### 修复方案
1. **改 `routers/gallery.py` 全部路由为 `async def`**
2. **改 `gallery_store.py` 把 sync wrapper 删掉,直接提供 `async` 函数**(`_add_sqlite` / `_list_sqlite` / `_get_sqlite`)
3. **新增 1 个测试**:用真实 event loop 调 `add_artifact`,确保不抛 `RuntimeError`

### 涉及文件
- `apps/api/app/routers/gallery.py`(改 async)
- `apps/api/app/gallery_store.py`(改 async,删 sync wrapper)
- `apps/api/tests/test_gallery_api.py`(加 event-loop 测试)

### 验收
- [ ] 路由全部 async
- [ ] 真实 event loop 跑通不爆 RuntimeError
- [ ] 后端 51 → 52 passed
- [ ] 前端不变

---

## Task 4: P0 A2 — run_forge 静默退化修复

### 问题描述
- `apps/api/app/proto/engine.py:104-110` 有 4 个静默退化:
  1. `_load_template(mission_id)` 找不到只 `print` 警告就继续 → typo mission_id 拿到 0 长 intron
  2. MCMC step=0 时 `last_score` 是 None,代码用 `if last_score is not None: cur = last_score` 跳过 → step=0 等同 preference 一次生成
  3. seed 参数对 standard/ancient/crystal 仪式没生效(seed 只传进 `_generate_intron`,MCMC 的随机状态没 seed)
  4. PWM 评分返回 None 时静默走零权重

### 修复方案
1. **#1**:`_load_template` 找不到直接 `raise ValueError(f"mission template {id} not found")` — 跟 router 现有 404 行为一致
2. **#2**:MCMC step=0 时 `cur_score = _score(generator, seed_seq)`,正常初始化 last_score
3. **#3**:MCMC 入口加 `rng = random.Random(seed + iteration)`,确保 seed 真的生效
4. **#4**:PWM 评分返回 None 时 `raise ValueError("scorer returned None")`,router 返 500

### 涉及文件
- `apps/api/app/proto/engine.py`(主改)
- `apps/api/tests/test_engine_smoke.py`(加 4 个回归测试,各覆盖 1 个静默退化)

### 验收
- [ ] typo mission_id 抛 ValueError(不是 0 长 intron)
- [ ] MCMC step=0 真的跑 1 步(不是 0 步)
- [ ] seed=42 两次跑同 mission 结果一致(可重现)
- [ ] PWM 失败抛 ValueError(不是静默)
- [ ] 后端 51 → 55 passed
- [ ] 前端不变

---

## 全量验证(所有 4 个 Task 完成后)

- [ ] 后端 55 passed
- [ ] 前端 5 passed
- [ ] 前端 build 成功
- [ ] 4 个 P0 全部 commit 落地
- [ ] RUNBOOK 更新到 Phase 3a
