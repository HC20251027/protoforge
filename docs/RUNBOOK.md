# ProtoForge 跑通手册(Phase 2)

目标:从干净环境到看见 UI 上的"原体锻炉"页面,所有 51 个后端测试 + 3 个前端测试通过。

## 1. 前置依赖

| 工具       | 版本           | 用途              |
|-----------|---------------|------------------|
| Node      | >= 20         | pnpm 8 + Vite    |
| pnpm      | >= 8          | workspace 包管理 |
| Python    | 3.10 – 3.12   | 侧车运行时        |
| Rust      | 1.78+         | Tauri 编译(可选) |

侧车只依赖纯 Python 包,**无需 torch / biopython**。已锁定到:
fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, aiosqlite, httpx, numpy, pytest。
其中 numpy 是 SpliceTransformer 评分器(PWM 实现)的运行时依赖。

## 2. 安装

```powershell
# 仓库根
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'

# 启用 pnpm(用 corepack)
corepack enable
corepack prepare pnpm@8.15.0 --activate

# 装前端依赖(2-5 分钟)
pnpm install --store-dir .pnpm-store

# 装侧车依赖(到用户级 site-packages,避免污染全局 site)
python -m pip install --user `
  fastapi 'uvicorn[standard]' pydantic pydantic-settings `
  sqlalchemy aiosqlite httpx numpy pytest pytest-asyncio
```

## 3. 跑测试

```powershell
# 侧车
cd apps/api
python -m pytest -q        # 期望:51 passed

# 前端
cd ..\web
pnpm test                  # 期望:3 passed
pnpm build                 # 期望:✓ built in 5-10s
```

## 4. 启服务

```powershell
# 终端 1:Python 侧车
cd apps\api
python -m uvicorn app.main:app --reload --port 7654

# 终端 2:React 前端
cd apps\web
pnpm dev
```

打开 http://localhost:5173 应看到:
- 主页标题"原体锻炉 ProtoForge"
- 侧车状态显示"ok"
- 导航栏有:主页 / 任务 / LLM 配置 / 作品库

## 5. 玩家完整旅程(手动冒烟)

1. 点"任务"→ 看到"极地耐冷萤光(PolarYeast)"卡片
2. 点卡片进入 `/missions/polar-glow-v1/forge`
3. 可选:在 NL 框输入"严格一点",点"翻译成参数" → 滑块自动跳到严苛值
4. 点"开始锻造" → 看到动画 + ScoreRadar + 染色序列
5. 点"进入风险门 →"
6. 答完 2 道题(可在 spec 模板里查"correct"值),点"提交判定"→ ✓ 通过
7. 点"查看作品库" → 看到刚保存的 artifact

## 6. 桌面壳(Tauri 2,可选)

```powershell
cd apps\desktop
pnpm install
# 单独 terminal 启侧车
cd ..\..\apps\api
python -m uvicorn app.main:app --port 7655
# 回到 desktop 目录
cd ..\..\apps\desktop
pnpm tauri dev
```

> 首次启动会下载 + 编译 ~300 个 Rust crate,需要 5-15 分钟;
> 之后增量编译秒级。
> Windows 上若遇 `os error 998`,设
> `$env:CARGO_TARGET_DIR='C:\cargo-target\protoforge'` 后重试。

## 7. 当前测试覆盖一览

- `tests/test_health.py` × 2 — 健康检查
- `tests/test_polar_template.py` × 1 — 任务模板加载
- `tests/test_engine_smoke.py` × 3 — proto 引擎 smoke + MCMC + generator 差异
- `tests/test_scorer_abstraction.py` × 7 — 评分器抽象 + transformer 回退
- `tests/test_forge_api.py` × 7 — `/api/forge/*` 路由(含 natural_language)
- `tests/test_missions_risk_api.py` × 6 — missions + risk gate
- `tests/test_gallery_api.py` × 5 — gallery API(内存)
- `tests/test_gallery_sqlite.py` × 2 — gallery SQLite 后端
- `tests/test_onboarding_api.py` × 5 — onboarding 3 provider
- `tests/test_translate_api.py` × 5 — NL 翻译
- `tests/test_e2e_player_journey.py` × 2 — 端到端玩家旅程
- `tests/test_llm_chat.py` × 4 — 新增:LLMProvider.chat() 抽象层
- 前端:Home × 3

## 8. 已知边界(Phase 2)

- 启发式评分:仍是默认 scorer;SpliceTransformerScorer 现在有真 PWM 实现(基于位置权重矩阵的 donor/acceptor 打分,无需 torch),可通过环境变量 `PROTOFORGE_SPLICER=transformer` 切换。
- LLM 翻译 / chat() 抽象层 → 完整:`LLMProvider` 基类已补 `chat(messages, temperature, max_tokens, config)`,`CloudProvider` / `LocalProvider` / `DisabledProvider` 三个实现;`translate.py` 改为统一调用 `provider.chat()` 而非自己 `httpx.post()`。
- MCMC 搜索:仍简化版(单点突变 + Metropolis 温度接受),非真实生物搜索;Phase 3 可接真 transformer 打分(已留好接口)。
- Tauri sidecar:已实装(`sidecar.rs` 的 spawn + health 轮询);`cargo check` 在 Windows 长路径 + Defender 环境下仍可能遇 `os error 998`,需设 `CARGO_TARGET_DIR` 到短路径。
- 新增:numpy 是 SpliceTransformer 评分器的运行时依赖(`pyproject.toml` 中 `numpy>=1.26`)。
- 新增:`ForgeRequest.natural_language` 字段 — 玩家在 forge 页输入自然语言描述后,服务端先调 translate 再 forge,一步到位(无需客户端两步调用)。
- 数据目录默认在项目目录下的 `.protoforge/data/`,可通过 `PROTOFORGE_DATA_DIR` 覆盖。
