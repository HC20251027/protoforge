# ProtoForge Phase 3 — 未解决项(已坦诚记录)

> Phase 3 收官时**没骗你**但你可能没注意的"半完成"项。
> 全部移交 Phase 4 处理。

---

## 1. `detect_hardware()` 没真删

**Phase 3 承诺**:4 档按难度不按硬件 → `engine.py` 不再读 `detect_hardware()`。
**实际状态**:
- ✅ `engine.py` 已删,`forge.py` 注释"不再读 detect_hardware"
- ⚠️ `apps/api/app/proto/profile.py` L19-69 函数**还在**
- ⚠️ `apps/api/app/proto/__init__.py` L6 还在 `from .profile import HardwareProfile, detect_hardware, recommend_ritual` 并在 `__all__` 导出

**Phase 4 修复方案**:
- 删 `profile.py` 中 `detect_hardware()` 和 `recommend_ritual()`
- 删 `__init__.py` 对应导出
- `grep -r "detect_hardware" apps/` 应只剩 `0` 命中(除了历史 commit 注释)

---

## 2. SpliceAI / SpliceTransformer 权重缺失

**Phase 3 承诺**:N1.2 vendor ML 模型权重(ESM2 / SpliceAI / SpliceTransformer)
**实际状态**:
- ✅ ESM2-150M 567MB 已下载,文件 SHA256 校验有
- ⚠️ `apps/api/vendor/models/spliceai/` 只有 `README.md` 占位
- ⚠️ `apps/api/vendor/models/splice-transformer/` 只有 `README.md` 占位

**Phase 4 修复方案**:
- SpliceAI:Keras weights ~1.1GB,从 Illumina 官方仓库下载
- SpliceTransformer-base PyTorch ~1.5GB,从 HuggingFace 下载
- 需要 torch + transformers 依赖(目前 pyproject.toml 已注释)
- 验证:每个模型加载 < 3s,评分与启发式对比误差 < 5%

---

## 3. proto-language `import` 跑不通

**Phase 3 承诺**:N1.1 vendor proto-language 源码
**实际状态**:
- ✅ 物理落地:60+ 文件 + `proto-tools-2.DELETED/` 子模块
- ⚠️ `import proto_language` 失败(15-20 个传递依赖未打包):
  - biotite / biopython / torch / pyrosetta / rdkit / esm / scipy / sklearn
  - 任意一个装不上,整个 import 链断
- 当前是"启发式 + PWM 评分器"代替,核心 255 测试仍可过

**Phase 4 修复方案**:
- 拆成两层:启发式评分(已实现,默认)+ 真 proto-language(可选,玩家主动启用)
- 或:用 `micromamba` 在玩家机器上装生物依赖,跑通了再走真路径
- 或:Phase 5+ 再处理(把核心玩法跑通为先)

---

## 4. Steam Workshop 是 MOCK

**Phase 3 承诺**:通关后自动上传 Steam 创意工坊
**实际状态**:
- ✅ `.protoforge` 打包器 + 离线队列 + 适配层全写完
- ✅ Phase 4 切换指南写在 `apps/api/app/protoforge/steam.md`
- ⚠️ `SteamWorkshopUploader` 是 MOCK,`workshop_id = "mock_{uuid16}"`
- ⚠️ `DEFAULT_PROTOFORGE_APP_ID = 0` 占位(真 Steam app ID 待申请)

**Phase 4 修复方案**:
- 装 `steamworks` Python 包
- 改 `is_steam_running()`:用 psutil 找 steam.exe 进程(已写)+ 进一步读 steam 配置确认登录
- 改 `upload_item()`:用 `steamworks` SDK 调 `ISteamUGC::SubmitItemUpdate`
- 改 `DEFAULT_PROTOFORGE_APP_ID`:玩家自己在 Settings 填
- 配 Tauri 签名私钥(`TAURI_SIGNING_PRIVATE_KEY` GitHub Secret)

---

## 5. API key 加密 base64 fallback

**Phase 3 承诺**:API key 加密
**实际状态**:
- ✅ 优先 `cryptography.fernet.Fernet`(对称加密 + 密钥派生)
- ⚠️ 当前环境**没装** `cryptography`,走 base64 fallback + `UserWarning`
- 密钥来自 `PROTOFORGE_KEY` env var,无则随机生成存 `.protoforge/key`

**Phase 4 修复方案**:
- 装 `cryptography` 到 `apps/api` pyproject.toml
- CI 中也装(dev 依赖加 `[project.optional-dependencies] crypto = ["cryptography>=42"]`)
- 生产环境文档:`export PROTOFORGE_KEY=$(openssl rand -base64 32)` 写入 .env

---

## 6. GGUF magic 字节 bug

**Phase 3 踩坑**:Qwen2.5-7B-Instruct-Q4_K_M 加载器
**实际状态**:
- ⚠️ `apps/api/app/models/loader.py` L177 `_MAGIC_BYTES[".gguf"] = b"GGUF"`
- 真 GGUF v3 应该是 `b"\x03GGUF"`(GGUF 3.0 协议)
- 当前 `try_load` 不严:文件 magic 不匹配时**不报错**而是 warn,fallback 到"weights missing"
- 所以**测试不挂**,但**真模型加载会失败**(静默退化)

**Phase 4 修复方案**:
- 改 `_MAGIC_BYTES[".gguf"] = b"\x03GGUF"`
- 改 `try_load` 路径:magic 不匹配 → `LLMUnavailable`(显式失败,跟 P0-A2 一致)
- 加测试:fake GGUF 文件 + 真 GGUF 文件,各跑一次

---

## 7. FastAPI on_event deprecation

**Phase 3 状态**:
- ⚠️ `apps/api/app/main.py` L41 仍用 `@app.on_event("startup")`(FastAPI 弃用)
- 测试有 Starlette deprecation 警告
- 不影响 213 个测试通过

**Phase 4 修复方案**:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

app = FastAPI(lifespan=lifespan, ...)
```

---

## 8. React Router v7 future flag

**Phase 3 状态**:
- ⚠️ React Router 6.30 已出 v7 future flag 警告
- 不影响 42 个前端测试通过

**Phase 4 修复方案**:
```tsx
<Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
```

---

## 9. vitest act() 警告

**Phase 3 状态**:
- ⚠️ `ForgePage` 测试中 `act(...)` 包装缺失,React 警告但不报错

**Phase 4 修复方案**:
- 测试中 `setState` 后的 `assert` 包在 `await waitFor(() => expect(...))` 里

---

## 10. Tauri 构建链路(Phase 3 跳过)

**Phase 3 状态**:
- ✅ Tauri sidecar 端口对齐、Python 嵌入脚本、tauri.conf.json externalBin/resources 全配
- ⚠️ 没真跑 `pnpm tauri build`(需要 macOS 编译 + Windows 编译 + 完整 8-12GB 资源)
- ⚠️ 没签 Tauri 安装包(需要 `TAURI_SIGNING_PRIVATE_KEY`)

**Phase 4 修复方案**:
- GitHub Actions 加 `release.yml` 跑三平台编译
- 配 GitHub Secrets:`TAURI_SIGNING_PRIVATE_KEY` / `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`
- 真打包一次(预期 8-12GB),验证 `latest.json` + updater 签名

---

## 移交清单(给 Phase 4)

| 优先级 | 项 | 工时估 | 阻塞发版? |
|--------|---|--------|----------|
| P1 | 装 cryptography 升级到 Fernet | 0.5h | ❌(有 fallback) |
| P1 | 修 GGUF magic bug | 0.5h | ⚠️(真模型加载静默失败) |
| P1 | 删 detect_hardware() 残留 | 0.5h | ❌ |
| P2 | 接 Steam steamworks.py 替换 MOCK | 4h | ⚠️(MOCK 可用) |
| P2 | vendor SpliceAI / SpliceTransformer 权重 | 2h | ❌(ESM2 已 vendor) |
| P2 | 跑一次 `pnpm tauri build` 三平台 | 4h + CI 30min | ⚠️(无 .exe 玩家装不了) |
| P3 | proto-language 真 import 跑通 | 8h+ | ❌(启发式已覆盖) |
| P3 | FastAPI on_event → lifespan | 1h | ❌ |
| P3 | React Router v7 future flag | 0.5h | ❌ |
| P3 | vitest act() 警告 | 1h | ❌ |
