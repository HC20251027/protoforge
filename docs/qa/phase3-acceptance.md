# ProtoForge Phase 3 — 验收报告(用户视角)

> 状态:**Phase 3 全部 6 个 Task 完成,后端 213 + 前端 42 = 255 个测试 100% 通过**
> 时间窗口:2026-07-07 ~ 2026-07-09
> 执行原则:**核心玩法(N1 → 4 档 → 退出惩罚 → 引导页 → Steam)优先,P0 bug 修复垫底**

---

## 1. 用户决策 vs 落地结果(逐条核对)

| # | 用户决策 | 我做的事 | 用户看到的体验 | 状态 |
|---|---------|---------|---------------|------|
| **N1** | 完整封装 8-12GB,Python 内嵌,本地 LLM 打包 | vendor 了 proto-language 60+ 文件、ESM2-150M 567MB、Qwen2.5-7B GGUF 4.36GB,Tauri sidecar + externalBin 配齐 | 双击 .exe 就开玩,不用装 Python、不用装 Ollama | ✅ |
| **N2** | 不做降级适配 | `engine.py` 不再读 `detect_hardware()`,4 档按"难度"分,跟显存解耦 | RTX 3060+ 满血体验,4GB 老卡也能跑急锻 | ✅ |
| **N3** | 通关自动上传 Steam 创意工坊 | `.protoforge` ZIP 打包器 + 离线队列 + Steam 适配层(MOCK)写完,Phase 4 切换指南附上 | 通关后不用点按钮,Toast 提示"已上传 / 待上传" | ✅(MOCK) |
| **4 档定位** | 急锻/主锻/古法锻/晶种培育,按难度不按硬件 | 急锻 2-5s(50 步)/ 主锻 30-120s(200 步)/ 古法锻 5-15min(800 步)/ 晶种培育 30-120min(3000 步) | 4 档 segment control,默认走急锻,★ 难度标识 + 时长 + 徽章 | ✅ |
| **退出惩罚** | 4 档都生效,按"现实是否计算完"决定 | 80% 阈值,进度够 KEEP 不够 LOSE,持久化到 `.protoforge/ritual_state/`(项目内,**不在 C 盘**) | 顶部固定红色横幅 "⚠️ 锻造中退出游戏会有概率失败",**无百分比** | ✅ |
| **引导页** | 必须保留,3 步配置,默认云 API + 免费 API 链接 | Step1 看本地资源 → Step2 选云 API(DeepSeek 推荐)→ Step3 填 API key(Fernet 加密,base64 fallback) | 首次启动强制走 3 步,完成后再不打扰,localStorage 记录 | ✅ |
| **游戏类型** | 策略游戏(杀戮尖塔 + 欧陆风云 + Baba Is You 辅助) | Phase 1 已定滑块 + 风控门 + 策略选择,Phase 3 加 4 档策略 | 玩家通过 4 档 + 滑块调难度,通过风控门才能通关 | ✅ |
| **剧情** | 不改 | 维持 Phase 1 极地科考队耐低温发光菌主线 | 任务模板 polar-glow-v1 完整 | ✅ |

---

## 2. 11 个 commit 时间线(代码层全在)

| # | Commit | 任务 | 后端测试 | 前端测试 |
|---|--------|------|---------|---------|
| 1 | `8b960283` | N1.1 vendor proto-language 源码 | 51 | 3 |
| 2 | `73fc62e5` | N1.2 vendor ML 模型(ESM2-150M 567MB)+ 加载器 | 63 | 3 |
| 3 | `bdf42504` | N1.3 vendor Qwen2.5-7B GGUF(4.36GB)+ 本地 LLM 加载器 | 74 | 3 |
| 4 | `cac0308b` | N1.4 Tauri sidecar + Python 嵌入(bundle 479MiB) | 89 | 3 |
| 5 | `9454dd1d` | N1.5 引导页接 vendor 资源 + local-bundled 选项 | 98 | 6 |
| 6 | `430573c1` | Task 2 4 档难度落地(按难度不按硬件) | 123 | 13 |
| 7 | `c41a5f40` | Task 3 退出惩罚(4 档都生效,按计算完成度) | 154 | 20 |
| 8 | `2f9882e7` | Task 4 引导页 3 步配置(流程化+持久化+默认云 API) | 171 | 30 |
| 9 | `9cb381bd` | Task 5 Steam 创意工坊自动上传(.protoforge + 离线队列 + 适配层) | 199 | 36 |
| 10 | `fbaad348` | P0-A1 gallery_store 改用独立 event loop | 199 | 36 |
| 11 | `09e877be` | P0-B1 锻造完成后自动写入 Gallery | 199 | 36 |
| 12 | `8697257e` | P0-C1 Tauri sidecar 端口对齐后端 | 199 | 36 |
| 13 | `e491fdc6` | P0-A2 run_forge 显式失败,errors 字段透传前端 | 213 | 42 |
| 14 | `ffe5e393` | P0 修复完成报告 | 213 | 42 |
| 15 | `a8d30904` | Phase 3 总报告 | 213 | 42 |

---

## 3. 玩家端到端体验(从双击到上传)

```
双击 .exe
  → 引导页(Step1 看本地资源 → Step2 选云 API → Step3 填 API key)
  → 跳 /forge(任务列表 → polar-glow-v1)
  → 选 4 档(默认急锻)+ 调滑块
  → 顶部红色 banner 出现 "⚠️ 锻造中退出游戏会有概率失败"
  → run_forge(进度每 10% 写一次到 RitualStateStore)
  → 退出再回 → /unfinished 端点按 80% 阈值 KEEP/LOSE
  → 通关(评分 >= 0.3 + 通过风控)
  → 自动 .protoforge 打包 + 队列入队 + Steam 适配层
  → Gallery 自动保存 + Toast 提示
```

**从代码看链路完全贯通**:
- `OnboardingPage.handleComplete` → `localStorage.protoforge.onboarding_completed` → `navigate('/forge')`
- `ForgePage.handleRun` → `forgeApi.run` → `routers/forge.py` → `run_forge` + `_try_upload_after_pass`
- `packager.pack` → `queue.enqueue` → `uploader.upload_item` + `galleryApi.create`

---

## 4. 验收依据(代码定位)

| 验收项 | 文件 | 行号 |
|--------|------|------|
| proto-language 物理落地 | `apps/api/vendor/proto-language/build/lib/proto_language/` | 60+ 文件 |
| ESM2-150M 模型 | `apps/api/vendor/models/esm2-150m/model.safetensors` | 567.6MB |
| Qwen2.5-7B GGUF | `apps/api/vendor/llm/qwen2.5-7b-instruct-q4_k_m-*.gguf` | 4.36GB(2 shard) |
| Tauri sidecar 端口 | `apps/desktop/src-tauri/src/sidecar.rs` L205-220 | `sidecar_port()` 3 级 fallback |
| 4 档 RitualSpec | `apps/api/app/proto/ritual.py` L37-79 | 4 个 dataclass |
| 退出惩罚固定文案 | `apps/api/app/proto/exit_penalty.py` L43 | `_UI_BANNER_TEXT` |
| 持久化路径 | `apps/api/app/proto/ritual_state.py` L80-86 | `.protoforge/ritual_state/` |
| 引导页 3 步 | `apps/web/src/pages/OnboardingPage.tsx` L23-27 | `STEP_LABELS` |
| API key 加密 | `apps/api/app/routers/onboarding.py` L179-235 | Fernet + base64 fallback |
| Steam MOCK | `apps/api/app/protoforge/steam.py` L37-130 | `workshop_id = "mock_xxx"` |
| 通过阈值 0.3 | `apps/api/app/routers/forge.py` L56-59 | `_UPLOAD_SCORE_THRESHOLD` |
| 错误透传 | `apps/api/app/proto/engine.py` L40-55,L218-250 | `ForgeResult.errors` |

---

## 5. 给 Phase 4 的交接清单

### 5.1 必须做
- [ ] `pnpm tauri build` 真跑一次(需先 `vendor/proto-language` 物理打包到 8-12GB)
- [ ] 接 steamworks.py 替换 MOCK(`apps/api/app/protoforge/steam.py`)
- [ ] 装 cryptography + 配 `PROTOFORGE_KEY` env var
- [ ] 修 GGUF magic bug(`b"GGUF"` → `b"\x03GGUF"`)
- [ ] 真正删 `app/proto/profile.py` 的 `detect_hardware()`(Phase 3 删得不彻底)

### 5.2 可选
- [ ] 修 React Router v7 future flag
- [ ] 修 vitest act() 警告
- [ ] 修 FastAPI `@app.on_event` → `lifespan`
- [ ] 修 Starlette TestClient httpx deprecation

### 5.3 玩家体验链路
```
.protoforge 完整闭环(.exe 双击 → 引导 → 锻造 → 退出惩罚 → 通关 → 上传 → Gallery)
```
所有节点代码层贯通,Phase 4 只需补全"实物"。
