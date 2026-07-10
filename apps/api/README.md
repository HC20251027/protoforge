# ProtoForge API (Python FastAPI Sidecar)

> Phase 3 收官 / 后端 220 passed / Python 3.10-3.12

## 职责

ProtoForge 的 Python 侧车:
- 跑 proto-language 算法(当前:启发式 + PWM 评分器;Phase 4+ 接真 proto-language)
- 封装 ML 模型(ESM2-150M 567MB)
- 封装本地 LLM(Qwen2.5-7B GGUF 4.36GB)
- 玩家数据持久化(SQLite via SQLAlchemy + 异步 aiosqlite)
- API key 加密(cryptography Fernet)

## 入口

- `app/main.py` — FastAPI app 实例,挂载所有 router
- `app/config.py` — pydantic-settings,从环境变量读 `PROTOFORGE_*`
- `app/routers/` — HTTP 端点
- `app/proto/` — 核心算法(锻造 + 4 档 + 退出惩罚)
- `app/models/` — ML 模型加载器(ESM2-150M 等)
- `app/llm/` — 本地 LLM 加载器(Qwen2.5 GGUF)

## 启动

```bash
cd apps/api
uv sync                              # 装依赖
uv run python -m app.main            # 跑(默认 0.0.0.0:7654)
# 或
uv run uvicorn app.main:app --reload --port 7654
```

## 跑测试

```bash
cd apps/api
uv run pytest -q                     # 全量 220 个测试
uv run pytest tests/test_proto_lint.py  # ruff regression 单测
```

## 跑 lint

```bash
cd apps/api
uv run ruff check app                # Phase 4 C1 后 0 错
uv run ruff format --check app
```

## vendor 资源(本地下载,不入 git)

```
apps/api/vendor/
├── proto-language/      # 60+ 文件,Phase 3 N1.1 物理落地
├── models/
│   ├── esm2-150m/       # 567MB,Phase 3 N1.2
│   ├── spliceai/        # Phase 4+ 占位
│   └── splice-transformer/  # Phase 4+ 占位
└── llm/                 # Qwen2.5-7B GGUF,Phase 3 N1.3
```

## 跟其他模块的接口

- 协议:HTTP/JSON(默认 7654 端口)
- CORS:`http://localhost:1420`(Tauri)+ `http://localhost:5173`(Vite)
- 类型定义:`packages/shared/src/types.ts` 镜像 `app/schemas.py`

## Phase 3 关键改动文件

| 文件 | 改动 |
|------|------|
| `app/proto/ritual.py` | 4 档 RitualSpec |
| `app/proto/ritual_state.py` | 退出惩罚状态持久化 |
| `app/proto/exit_penalty.py` | 80% 阈值 KEEP/LOSE |
| `app/proto/engine.py` | MCMC 搜索 + 显式失败(errors 字段) |
| `app/routers/forge.py` | run_forge + 评分 + 上传触发 |
| `app/routers/vendor.py` | 引导页 vendor 状态 |
| `app/routers/onboarding.py` | 3 步配置 + Fernet 加密 |
| `app/protoforge/{packager,queue,steam}.py` | Steam 创意工坊自动上传 |
| `app/gallery_store.py` | 独立 event loop(P0-A1) |

## 调试技巧

```bash
# 启动时打 INFO 日志
PROTOFORGE_LOG_LEVEL=DEBUG uv run python -m app.main

# 改端口(配合 Tauri sidecar PROTOFORGE_API_PORT env)
PROTOFORGE_API_PORT=8765 uv run python -m app.main

# 用 sqlite browser 看 .protoforge/data/protoforge.db
```

## 已知未解决项

详见 `docs/qa/phase3-deferred.md`:
- proto-language 真 import 跑不通(15-20 个传递依赖)
- SpliceAI / SpliceTransformer 权重缺失
- Steam MOCK 待替换
- GGUF magic 字节已修(Phase 4 A2)
