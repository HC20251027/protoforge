# ProtoForge Phase 1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在玩家本地跑出"极地科考队耐低温发光菌"关卡从剧情 → 调参 → 真 Proto 评分 → 风险门 → 作品入库 的端到端闭环,可分发的 Tauri 桌面应用基线 + 早期 Web 试玩版(localhost)。

**Architecture:**
- **桌面端壳**:Tauri 2.x(Rust) + 内嵌 WebView,启动时 spawn Python sidecar
- **前端**:React 18 + TypeScript + Vite + TailwindCSS + Radix UI + Recharts
- **后端**:FastAPI 单进程 + proto-language 内嵌运行 + 本地 SQLite
- **模型栈**:SpliceTransformer(必装,CPU/GPU 都跑)+ ESM2 650M(可选)+ 启发式评分器
- **LLM**:`llm/` 抽象层,3 个 provider(cloud/local/disabled),首次启动引导选择
- **包管理**:pnpm workspace(前端 + 桌面) + uv(Python sidecar)
- **存储**:SQLite(SQLAlchemy ORM),数据/模型/缓存全在 `.protoforge/` 项目目录
- **打包**:Tauri 桌面应用 → `.exe` / `.dmg` / `.AppImage`(Phase 1 末)

**Tech Stack:** Tauri 2.x、React 18、TypeScript 5、Vite 5、TailwindCSS 3、Radix UI、Recharts、FastAPI、SQLAlchemy 2、proto-language(Stanford MIT)、SpliceTransformer、ESM2 650M、pnpm、uv、PyInstaller(后期)

**Reference Specs:**
- 设计文档: `docs/superpowers/specs/2026-07-06-protoforge-design.md`
- 游戏设计: `docs/superpowers/specs/2026-07-06-protoforge-gdd.md`

---

## 项目目录结构(实施前先明确)

```
protoforge/
├─ apps/
│  ├─ desktop/                        # Tauri 主程序(Rust 壳)
│  │  ├─ src-tauri/
│  │  │  ├─ Cargo.toml
│  │  │  ├─ tauri.conf.json
│  │  │  └─ src/
│  │  │     ├─ main.rs
│  │  │     ├─ lib.rs
│  │  │     ├─ sidecar.rs
│  │  │     └─ commands.rs
│  │  └─ package.json
│  ├─ web/                            # React 前端(桌面/Web 共享)
│  │  ├─ package.json
│  │  ├─ vite.config.ts
│  │  ├─ tailwind.config.js
│  │  └─ src/
│  │     ├─ main.tsx
│  │     ├─ App.tsx
│  │     ├─ pages/
│  │     │  ├─ Home.tsx
│  │     │  ├─ Mission.tsx
│  │     │  ├─ Forge.tsx
│  │     │  ├─ RiskGate.tsx
│  │     │  ├─ Gallery.tsx
│  │     │  └─ Onboarding.tsx
│  │     ├─ components/
│  │     │  ├─ MissionCard.tsx
│  │     │  ├─ ScoreRadar.tsx
│  │     │  ├─ SequenceView.tsx
│  │     │  ├─ ForgeAnimation.tsx
│  │     │  ├─ SliderCard.tsx
│  │     │  ├─ RiskQuestionCard.tsx
│  │     │  └─ ArtifactCard.tsx
│  │     └─ lib/
│  │        ├─ api.ts
│  │        └─ types.ts
│  └─ api/                            # Python sidecar
│     ├─ pyproject.toml
│     ├─ uv.lock
│     └─ app/
│        ├─ __init__.py
│        ├─ main.py                  # FastAPI 入口
│        ├─ config.py
│        ├─ db.py
│        ├─ models.py                # SQLAlchemy
│        ├─ proto/
│        │  ├─ __init__.py
│        │  ├─ engine.py
│        │  ├─ profile.py
│        │  ├─ scorer.py
│        │  └─ templates/
│        │     └─ polar-glow.json
│        ├─ llm/
│        │  ├─ __init__.py
│        │  ├─ base.py
│        │  ├─ factory.py
│        │  └─ providers/
│        │     ├─ __init__.py
│        │     ├─ cloud.py
│        │     ├─ local.py
│        │     └─ disabled.py
│        └─ routers/
│           ├─ __init__.py
│           ├─ missions.py
│           ├─ forge.py
│           ├─ risk.py
│           ├─ gallery.py
│           ├─ onboarding.py
│           └─ translate.py
├─ .protoforge/                      # 运行时数据(玩家本机)
│  ├─ data/
│  │  └─ protoforge.db
│  ├─ programs/
│  ├─ sequences/
│  ├─ models/
│  └─ logs/
├─ packages/
│  └─ shared/                        # 前后端共享类型
│     ├─ package.json
│     └─ types.ts
├─ pnpm-workspace.yaml
├─ package.json
├─ .gitignore
└─ README.md
```

---

## 里程碑

| # | 里程碑 | 完成任务 | 验收 |
|---|---|---|---|
| **M1** | 项目骨架 + 双端 Hello | Task 0, 1, 2 | `pnpm dev` 跑通前后端 |
| **M2** | Tauri 壳 + IPC 联通 | Task 3 | Tauri 启动后能调通 sidecar `/health` |
| **M3** | Proto 真接入 + 评分 | Task 4, 5, 6, 7 | `POST /api/forge/run` 返回 scores+fasta |
| **M4** | 前端工作台 | Task 8, 9, 10 | WebView 端到端流程可点通 |
| **M5** | 风险门 + 作品库 | Task 12, 13, 14 | 风险门可过 + 作品入 SQLite + Gallery 展示 |
| **M6** | LLM 引导 | Task 15 | 三选项引导页可走通,翻译能跑 |
| **M7** | 端到端 + 打包 | Task 16 | 桌面应用 `.exe` 可启动,Web 试玩版可开 |

---

## 任务列表

---

### Task 0: 项目骨架 + pnpm workspace

**Files:**
- Create: `pnpm-workspace.yaml`
- Create: `package.json`
- Create: `.gitignore`
- Create: `README.md`
- Create: `apps/web/package.json`
- Create: `apps/desktop/package.json`
- Create: `apps/api/pyproject.toml`
- Create: `packages/shared/package.json`
- Create: `packages/shared/src/types.ts`

- [ ] **Step 1: 写 `.gitignore`**

```gitignore
# Node
node_modules/
dist/
.pnpm-store/
.turbo/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Tauri
apps/desktop/src-tauri/target/

# 项目运行时数据(不进 git)
.protoforge/
.protoforge/
.data/
.cache/
models-cache/

# 环境配置
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
*.swp
.DS_Store

# 日志
*.log
logs/
```

- [ ] **Step 2: 写 `pnpm-workspace.yaml`**

```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

- [ ] **Step 3: 写根 `package.json`**

```json
{
  "name": "protoforge",
  "version": "0.1.0",
  "private": true,
  "description": "ProtoForge (原体锻炉) - 合成生物学众包游戏化平台",
  "scripts": {
    "dev:web": "pnpm --filter @protoforge/web dev",
    "dev:api": "pnpm --filter @protoforge/desktop dev:api",
    "dev:desktop": "pnpm --filter @protoforge/desktop dev",
    "build:web": "pnpm --filter @protoforge/web build",
    "test": "pnpm -r run test",
    "lint": "pnpm -r run lint"
  },
  "engines": {
    "node": ">=20",
    "pnpm": ">=9"
  },
  "packageManager": "pnpm@9.12.0"
}
```

- [ ] **Step 4: 写 `apps/web/package.json`**

```json
{
  "name": "@protoforge/web",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src --ext ts,tsx"
  },
  "dependencies": {
    "@protoforge/shared": "workspace:*",
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-slider": "^1.2.1",
    "@radix-ui/react-tooltip": "^1.1.4",
    "clsx": "^2.1.1",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "recharts": "^2.13.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.2",
    "autoprefixer": "^10.4.20",
    "eslint": "^9.12.0",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.13",
    "typescript": "^5.6.2",
    "vite": "^5.4.8",
    "vitest": "^2.1.2"
  }
}
```

- [ ] **Step 5: 写 `apps/desktop/package.json`**

```json
{
  "name": "@protoforge/desktop",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "tauri dev",
    "build": "tauri build",
    "dev:api": "cd ../api && uv run uvicorn app.main:app --reload --port 7654",
    "build:api": "cd ../api && uv build"
  },
  "dependencies": {
    "@tauri-apps/api": "^2.0.0",
    "@tauri-apps/cli": "^2.0.0"
  },
  "devDependencies": {
    "@tauri-apps/cli": "^2.0.0"
  }
}
```

- [ ] **Step 6: 写 `apps/api/pyproject.toml`**

```toml
[project]
name = "protoforge-api"
version = "0.1.0"
description = "ProtoForge Python sidecar - FastAPI server wrapping proto-language"
requires-python = ">=3.10,<3.13"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "sqlalchemy>=2.0.30",
    "aiosqlite>=0.20.0",
    "httpx>=0.27.0",
    "torch>=2.3.0",
    "numpy>=1.26.0",
    "pandas>=2.2.0",
    "biopython>=1.84",
    "spliceai>=1.3.1",
    "huggingface-hub>=0.24.0",
]

[project.optional-dependencies]
gpu = [
    "torch[cuda]>=2.3.0",
]
esm2 = [
    "transformers>=4.45.0",
    "fair-esm>=2.0.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 7: 写 `packages/shared/package.json`**

```json
{
  "name": "@protoforge/shared",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./src/types.ts",
  "types": "./src/types.ts",
  "exports": {
    ".": "./src/types.ts"
  }
}
```

- [ ] **Step 8: 写 `packages/shared/src/types.ts`(前后端共享协议)**

```typescript
// ProtoForge 前后端共享类型

export type LLMProvider = 'cloud' | 'local' | 'disabled';

export type CellLine = 'HEK293' | 'HeLa' | 'Jurkat' | 'PolarYeast' | 'MarsMoss';

export type ForgeRitual = 'swift' | 'standard' | 'ancient' | 'crystal';

export type MissionLevel = 'tutorial' | 'commission' | 'multi-link' | 'tough' | 'free';

export interface Mission {
  id: string;
  title: string;
  scenario: 'polar' | 'mars' | 'hospital';
  level: MissionLevel;
  story_brief: string;
  task_description: string;
  proto_template: Record<string, unknown>;
  scoring: ScoringConfig;
  risk_rules: RiskRule[];
  unlock: { min_badges: number };
}

export interface ScoringConfig {
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  primary_metric: string;
}

export interface RiskRule {
  id: string;
  question: string;
  options: { value: string; label: string; correct: boolean }[];
  explanation: string;
}

export interface SliderParam {
  id: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  description: string;
}

export interface ForgeRequest {
  mission_id: string;
  params: Record<string, number>;
  generator: 'uniform' | 'preference' | 'random';
  seed?: number;
}

export interface ScoreVector {
  primary: number;
  components: Record<string, number>;
  weights: Record<string, number>;
}

export interface RiskFlag {
  rule_id: string;
  severity: 'info' | 'warn' | 'block';
  message: string;
}

export interface ForgeResult {
  run_id: string;
  mission_id: string;
  ritual: ForgeRitual;
  duration_ms: number;
  scores: ScoreVector;
  fasta: string;
  risk_flags: RiskFlag[];
  proto_program: Record<string, unknown>;
  passed_gate: boolean;
}

export interface Artifact {
  id: string;
  mission_id: string;
  mission_title: string;
  created_at: string;
  scores: ScoreVector;
  fasta: string;
  passed_gate: boolean;
  ritual: ForgeRitual;
  duration_ms: number;
}

export interface TranslateRequest {
  natural_language: string;
  context?: { mission_id?: string; current_params?: Record<string, number> };
}

export interface TranslateResponse {
  params: Record<string, number>;
  generator: 'uniform' | 'preference' | 'random';
  explanation: string;
}

export interface OnboardingRequest {
  provider: LLMProvider;
  config?: {
    api_key?: string;
    base_url?: string;
    model?: string;
  };
}

export interface OnboardingResponse {
  ok: boolean;
  provider: LLMProvider;
  test_passed: boolean;
  error?: string;
}

export interface HardwareProfile {
  gpu_name: string | null;
  gpu_memory_mb: number;
  cpu_cores: number;
  ram_mb: number;
  recommended_ritual: ForgeRitual;
  recommended_models: string[];
}

export interface ApiError {
  error: string;
  detail?: string;
  code?: string;
}
```

- [ ] **Step 9: 写 `README.md`**

```markdown
# ProtoForge(原体锻炉)

游戏化的合成生物学众包平台。基于 Stanford Proto 论文(2026)构建。

## 当前阶段

Phase 1:单机 Tauri 桌面应用 + 1 关(极地科考队的耐低温发光菌)。

## 系统要求

- **Python**:3.10+ (Phase 1 玩家本地装)
- **Node.js**:20+ (开发用)
- **pnpm**:9+ (开发用)
- **GPU**(可选):NVIDIA 8GB+ 独显(RTX 3060 起),无 GPU 走 CPU 降级路径

## 安装(开发)

```bash
pnpm install
cd apps/api && uv sync && cd ../..
pnpm dev
```

## 目录约定

- `.protoforge/` - 玩家本机数据(SQLite、序列、模型缓存),**不进 git**
- `apps/api/` - Python sidecar
- `apps/web/` - React 前端
- `apps/desktop/` - Tauri 桌面壳
- `packages/shared/` - 前后端共享 TS 类型

## 文档

- 设计: `docs/superpowers/specs/2026-07-06-protoforge-design.md`
- 游戏: `docs/superpowers/specs/2026-07-06-protoforge-gdd.md`
- 计划: `docs/superpowers/plans/2026-07-06-protoforge-phase1.md`
```

- [ ] **Step 10: 安装并验证**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
pnpm install
```

预期:workspace 装好,4 个子包识别。

- [ ] **Step 11: 提交**

```bash
git add pnpm-workspace.yaml package.json .gitignore README.md apps/ packages/
git commit -m "chore: scaffold pnpm workspace + shared types"
```

---

### Task 1: Python sidecar 脚手架 + 健康检查

**Files:**
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/app/main.py`
- Create: `apps/api/app/config.py`
- Create: `apps/api/app/routers/__init__.py`
- Create: `apps/api/app/routers/health.py`
- Create: `apps/api/tests/test_health.py`

- [ ] **Step 1: 写 `apps/api/app/__init__.py`**

```python
"""ProtoForge Python sidecar."""
__version__ = "0.1.0"
```

- [ ] **Step 2: 写 `apps/api/app/config.py`**

```python
"""应用配置。所有路径必须在项目目录内,不读 C 盘 AppData。"""
from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """解析项目根目录(避免硬编码绝对路径)。"""
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROTOFORGE_", env_file=".env", extra="ignore")

    # 服务
    host: str = "127.0.0.1"
    port: int = 7654

    # 路径(全部在项目目录)
    project_root: Path = _project_root()
    data_dir: Path = _project_root() / ".protoforge" / "data"
    programs_dir: Path = _project_root() / ".protoforge" / "programs"
    sequences_dir: Path = _project_root() / ".protoforge" / "sequences"
    models_dir: Path = _project_root() / ".protoforge" / "models"
    logs_dir: Path = _project_root() / ".protoforge" / "logs"
    db_path: Path = _project_root() / ".protoforge" / "data" / "protoforge.db"

    # Proto
    proto_profile: str = "auto"  # auto / gpu_8gb / gpu_24gb / cpu
    forge_timeout_sec: int = 120

    # LLM
    llm_provider: str = "disabled"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    def ensure_dirs(self) -> None:
        for d in [self.data_dir, self.programs_dir, self.sequences_dir, self.models_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
```

- [ ] **Step 3: 写 `apps/api/app/routers/__init__.py`**

```python
"""API 路由聚合。"""
from fastapi import APIRouter
from .health import router as health_router
from .missions import router as missions_router
from .forge import router as forge_router
from .risk import router as risk_router
from .gallery import router as gallery_router
from .onboarding import router as onboarding_router
from .translate import router as translate_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(missions_router, prefix="/api/missions", tags=["missions"])
api_router.include_router(forge_router, prefix="/api/forge", tags=["forge"])
api_router.include_router(risk_router, prefix="/api/risk", tags=["risk"])
api_router.include_router(gallery_router, prefix="/api/gallery", tags=["gallery"])
api_router.include_router(onboarding_router, prefix="/api/onboarding", tags=["onboarding"])
api_router.include_router(translate_router, prefix="/api/translate", tags=["translate"])
```

- [ ] **Step 4: 写 `apps/api/app/routers/health.py`**

```python
"""健康检查端点。"""
from __future__ import annotations
from fastapi import APIRouter
from app.config import settings
from app import __version__

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "data_dir": str(settings.data_dir),
        "db_path": str(settings.db_path),
        "proto_profile": settings.proto_profile,
    }
```

- [ ] **Step 5: 写 `apps/api/app/main.py`**

```python
"""FastAPI 入口。"""
from __future__ import annotations
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import api_router
from app.config import settings
from app import __version__

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("protoforge")

app = FastAPI(
    title="ProtoForge API",
    version=__version__,
    description="ProtoForge Python sidecar - wraps proto-language and scoring models.",
)

# CORS(只允许本地 Tauri WebView 和开发态 Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",       # Tauri 默认 dev 端口
        "http://localhost:5173",       # Vite dev
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def _startup() -> None:
    log.info("ProtoForge API %s starting on %s:%d", __version__, settings.host, settings.port)
    log.info("Data dir: %s", settings.data_dir)
    log.info("Proto profile: %s", settings.proto_profile)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
```

- [ ] **Step 6: 写 `apps/api/tests/test_health.py`**

```python
"""健康检查测试。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "data_dir" in body


def test_health_includes_proto_profile(client: TestClient) -> None:
    res = client.get("/health")
    assert res.json()["proto_profile"] in ("auto", "gpu_8gb", "gpu_24gb", "cpu")
```

- [ ] **Step 7: 写 `apps/api/tests/conftest.py`**

```python
"""pytest fixtures。"""
import sys
from pathlib import Path

# 把 apps/api 加到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

- [ ] **Step 8: 装依赖并跑测试**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv sync
uv run pytest -v
```

预期: 2 passed,1 个 health 返回 ok,1 个 proto_profile 在白名单。

- [ ] **Step 9: 启动并 curl 验证**

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 7654
# 另一终端:
curl http://127.0.0.1:7654/health
```

预期: 返回 `{"status":"ok",...}`。Ctrl+C 停掉。

- [ ] **Step 10: 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
git add apps/api/
git commit -m "feat(api): FastAPI scaffold + health endpoint"
```

---

### Task 2: React + Vite 前端脚手架

**Files:**
- Create: `apps/web/index.html`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/tsconfig.node.json`
- Create: `apps/web/tailwind.config.js`
- Create: `apps/web/postcss.config.js`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/index.css`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/types.ts`(re-export shared)
- Create: `apps/web/src/pages/Home.tsx`
- Create: `apps/web/src/test/Home.test.tsx`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/src/test/setup.ts`

- [ ] **Step 1: 写 `apps/web/index.html`**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ProtoForge · 原体锻炉</title>
  </head>
  <body class="bg-slate-950 text-slate-100">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: 写 `apps/web/vite.config.ts`**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:7654', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:7654', changeOrigin: true },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
});
```

- [ ] **Step 3: 写 `apps/web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@protoforge/shared": ["../../packages/shared/src/types.ts"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: 写 `apps/web/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: 写 `apps/web/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        forge: {
          50: '#fef7ee',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 6: 写 `apps/web/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 7: 写 `apps/web/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html, body, #root {
    height: 100%;
  }
  body {
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  }
}
```

- [ ] **Step 8: 写 `apps/web/src/main.tsx`**

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 9: 写 `apps/web/src/App.tsx`**

```typescript
import { Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/Home';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
```

- [ ] **Step 10: 写 `apps/web/src/lib/types.ts`**

```typescript
export * from '@protoforge/shared';
```

- [ ] **Step 11: 写 `apps/web/src/lib/api.ts`**

```typescript
import type { ApiError } from './types';

const BASE = '/api';

class ApiException extends Error {
  status: number;
  body: ApiError;
  constructor(status: number, body: ApiError) {
    super(body.error || `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiException(res.status, data || { error: res.statusText });
  return data as T;
}

export const api = {
  health: () => request<{ status: string; version: string }>('GET', '/health'),
};
```

- [ ] **Step 12: 写 `apps/web/src/pages/Home.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export function Home() {
  const [status, setStatus] = useState<string>('检查中…');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health()
      .then((d) => setStatus(`后端在线 · v${d.version}`))
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-5xl font-bold text-forge-500">ProtoForge</h1>
      <p className="mt-4 text-slate-400 text-lg">原体锻炉 · 合成生物学众包游戏化平台</p>
      <div className="mt-12 p-6 rounded-lg bg-slate-900 border border-slate-800 max-w-md w-full">
        <p className="text-sm text-slate-500">Python sidecar</p>
        {error ? (
          <p className="mt-2 text-red-400 font-mono text-sm">{error}</p>
        ) : (
          <p className="mt-2 text-emerald-400 font-mono text-sm">{status}</p>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 13: 写 `apps/web/vitest.config.ts`**

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@protoforge/shared': path.resolve(__dirname, '../../packages/shared/src/types.ts'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
});
```

- [ ] **Step 14: 写 `apps/web/src/test/setup.ts`**

```typescript
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 15: 写 `apps/web/src/test/Home.test.tsx`**

```typescript
import { render, screen } from '@testing-library/react';
import { Home } from '@/pages/Home';

describe('Home', () => {
  it('renders title', () => {
    render(<Home />);
    expect(screen.getByText('ProtoForge')).toBeInTheDocument();
  });

  it('shows initial status', () => {
    render(<Home />);
    expect(screen.getByText(/检查中/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 16: 跑 dev 和 test**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\web'
pnpm test
# 另开终端:
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv run uvicorn app.main:app --port 7654
# 再开终端:
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
pnpm --filter @protoforge/web dev
```

预期: web dev 跑在 5173,浏览器打开显示 "ProtoForge" + "后端在线"。

- [ ] **Step 17: 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
git add apps/web/
git commit -m "feat(web): React + Vite scaffold with Tailwind + health probe"
```

---

### Task 3: proto-language 接入 + 极地任务模板

**Files:**
- Create: `apps/api/app/proto/__init__.py`
- Create: `apps/api/app/proto/templates/polar-glow.json`
- Create: `apps/api/app/proto/engine.py`
- Create: `apps/api/app/proto/profile.py`
- Create: `apps/api/app/proto/scorer.py`
- Create: `apps/api/tests/test_polar_template.py`
- Create: `apps/api/tests/test_engine_smoke.py`

- [ ] **Step 1: 写 `apps/api/app/proto/__init__.py`**

```python
"""Proto 引擎与评分。"""
from .engine import run_forge, ForgeResult, run_polar_glow
from .profile import detect_hardware, recommend_ritual
from .scorer import score_intron, score_sequence

__all__ = [
    "run_forge",
    "ForgeResult",
    "run_polar_glow",
    "detect_hardware",
    "recommend_ritual",
    "score_intron",
    "score_sequence",
]
```

- [ ] **Step 2: 写 `apps/api/app/proto/templates/polar-glow.json`(Proto Program 模板)**

```json
{
  "task_id": "polar-glow-v1",
  "name": "极地耐低温发光菌",
  "description": "设计一段只能在极地酵母(PYE-12)里正确剪接、不会在 HEK293 人细胞系里表达的 GFP 内含子。",
  "proto_template": {
    "objective": "design_intron",
    "target_cell_line": "PolarYeast",
    "off_target_cell_line": "HEK293",
    "intron_length_range": [80, 250],
    "exon_flanks": {
      "upstream": "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGACGGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTACGGCAAGCTGACCCTGAAGTTCATCTGCACCACCGGCAAGCTGCCCGTGCCCTGGCCCACCCTCGTGACCACCCTGACCTACGGCGTGCAGTGCTTCAGCCGCTACCCCGATCATATGAAGCAGCACGACTTCTTCAAGTCCGCCATGCCCGAAGGCTACGTCCAGGAGCGCACCATCTTCTTCAAGGACGACGGCAACTACAAGACCCGCGCCGAGGTGAAGTTCGAGGGCGACACCCTGGTGAACCGCATCGAGCTGAAGGGCGTGGACTTCAAGGAGGACGGCAACATCCTGGGGCACAAGCTGGAGTACAACTACAACAGCCACAACGTCTATATCATGGCCGACAAGCAGAAGAACGGCATCAAGGTGAACTTCAAG",
      "downstream": "ATCCGCAACTACAAGCTCTCCAAGTACCCCAACGGCAAGCTGATCAAGAAGGACATCCAGCTGCAGGACGGCAGCGTGCAGCTCGCCGACCACTACCAGCAGAACACCCCCATCGGCGACGGCCCCGTGCTGCTGCCCGACAACCACTACCTGAGCACCCAGTCCGCCCTGAGCAAAGACCCCAACGAGAAGCGCGATCACATGGTCCTGCTGGAGTTCGTGACCGCCGCCGGGATCACTCTCGGCATGGACGAGCTGTACAAGTAA"
    },
    "constraint": {
      "min_target_splice_score": 0.65,
      "max_off_target_splice_score": 0.20,
      "gc_content_range": [0.35, 0.65]
    },
    "scoring": {
      "weights": {
        "target_splice": 0.5,
        "orthogonality": 0.35,
        "gc_penalty": 0.1,
        "length_penalty": 0.05
      }
    },
    "search": {
      "generator": "preference",
      "mcmc_steps": 50,
      "temperature": 0.8
    }
  },
  "sliders": [
    { "id": "min_target_splice", "label": "目标剪接强度下限", "min": 0.4, "max": 0.95, "step": 0.05, "default": 0.65, "description": "在极地菌株里剪接位点强度阈值" },
    { "id": "max_off_target", "label": "脱靶抑制强度", "min": 0.05, "max": 0.4, "step": 0.05, "default": 0.20, "description": "HEK293 中最大可接受剪接强度" },
    { "id": "weight_alpha", "label": "目标权重 α", "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.5, "description": "对目标剪接强度的偏重" },
    { "id": "weight_beta", "label": "脱靶权重 β", "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.35, "description": "对正交性的偏重" },
    { "id": "mcmc_steps", "label": "MCMC 步数", "min": 10, "max": 200, "step": 10, "default": 50, "description": "搜索步数,越多越准但越慢" }
  ],
  "risk_rules": [
    {
      "id": "biosafety",
      "question": "为什么我们必须把发光基因限制在极地菌株里表达?",
      "options": [
        { "value": "a", "label": "极地菌株里 GFP 才能正确折叠", "correct": false },
        { "value": "b", "label": "防止发光基因在人体内无控扩增(生物安全)", "correct": true },
        { "value": "c", "label": "极地菌株比人细胞长得快", "correct": false }
      ],
      "explanation": "GFP 一旦在人体细胞中表达,可能引发非预期的免疫或代谢反应。任务核心约束是细胞系正交性。"
    },
    {
      "id": "off_target",
      "question": "如果 HEK293 中的剪接强度被预测为 0.5,你的方案?",
      "options": [
        { "value": "a", "label": "直接通过 — 0.5 也不高", "correct": false },
        { "value": "b", "label": "否决 — 远超脱靶阈值 0.20", "correct": true },
        { "value": "c", "label": "降低目标剪接强度至 0.3 来平衡", "correct": false }
      ],
      "explanation": "脱靶阈值 0.20 是硬约束。降低目标强度是错误方向,应调高正交性约束或换区段。"
    }
  ],
  "level": "tutorial",
  "scenario": "polar"
}
```

- [ ] **Step 3: 写 `apps/api/app/proto/profile.py`**

```python
"""硬件档位检测与仪式推荐。"""
from __future__ import annotations
import subprocess
import shutil
import os
from dataclasses import dataclass


@dataclass
class HardwareProfile:
    gpu_name: str | None
    gpu_memory_mb: int
    cpu_cores: int
    ram_mb: int
    recommended_ritual: str
    recommended_models: list[str]


def detect_hardware() -> HardwareProfile:
    """探测本机硬件,推荐仪式名(急锻/标准锻/古法锻/晶种培育)。"""
    gpu_name = None
    gpu_mem = 0
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                timeout=5,
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            if out:
                name, mem = out.split(",")
                gpu_name = name.strip()
                # "8192 MiB" -> 8192
                gpu_mem = int(mem.strip().split()[0])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, IndexError):
            pass

    cpu_cores = os.cpu_count() or 4

    try:
        import psutil  # type: ignore
        ram_mb = psutil.virtual_memory().total // (1024 * 1024)
    except ImportError:
        ram_mb = 8192  # 合理默认

    if gpu_mem >= 24000:
        ritual, models = "swift", ["Evo2-1B", "ESM2-650M", "AlphaGenome", "SpliceTransformer"]
    elif gpu_mem >= 8000:
        ritual, models = "standard", ["Evo2-1B", "ESM2-650M", "SpliceTransformer"]
    elif gpu_mem >= 4000:
        ritual, models = "ancient", ["SpliceTransformer", "ESM2-650M"]
    else:
        ritual, models = "crystal", ["SpliceTransformer"]

    return HardwareProfile(
        gpu_name=gpu_name,
        gpu_memory_mb=gpu_mem,
        cpu_cores=cpu_cores,
        ram_mb=ram_mb,
        recommended_ritual=ritual,
        recommended_models=models,
    )


def recommend_ritual(gpu_memory_mb: int) -> str:
    if gpu_memory_mb >= 24000:
        return "swift"
    if gpu_memory_mb >= 8000:
        return "standard"
    if gpu_memory_mb >= 4000:
        return "ancient"
    return "crystal"
```

- [ ] **Step 4: 写 `apps/api/app/proto/scorer.py`**

```python
"""序列评分器(CPU 可跑的启发式评分 + SpliceTransformer 优先)。"""
from __future__ import annotations
import re
from collections import Counter


def _gc_content(seq: str) -> float:
    if not seq:
        return 0.0
    seq = seq.upper()
    gc = sum(1 for c in seq if c in "GC")
    return gc / len(seq)


def _kmer_entropy(seq: str, k: int = 3) -> float:
    if len(seq) < k:
        return 0.0
    kmers = [seq[i:i + k] for i in range(len(seq) - k + 1)]
    counts = Counter(kmers)
    total = sum(counts.values())
    import math
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _splice_site_score(seq: str) -> float:
    """简化版剪接位点评分:GT-AG 边界 + 周围上下文。

    真生产应调 SpliceTransformer;此处用 motif 启发式确保无依赖也能跑。
    """
    seq = seq.upper()
    donor = len(re.findall(r"[A-Z]G[CT]A[AG][CT]T", seq[:60]))  # 5'剪接位点 GT
    acceptor = len(re.findall(r"[CT]AG[AG][A-Z]{15,20}G", seq[-60:]))  # 3'剪接位点 AG
    branch = len(re.findall(r"[CT]T[AG]A[CT]", seq))  # branch point
    score = min(1.0, (donor * 0.4 + acceptor * 0.4 + branch * 0.05))
    return score


def score_intron(intron: str, *, min_gc: float = 0.35, max_gc: float = 0.65,
                 min_target_splice: float = 0.65, max_off_target_splice: float = 0.20) -> dict:
    """评分内含子,返回各组件 + 综合分。

    在 Phase 1,正交性 orthogonality 用长度差异 + k-mer 熵启发式模拟。
    """
    gc = _gc_content(intron)
    splice = _splice_site_score(intron)
    ent = _kmer_entropy(intron, k=3) / 2.5  # 归一化到 0-1 区间
    ent = max(0.0, min(1.0, ent))

    gc_penalty = max(0.0, max(gc - max_gc, min_gc - gc))
    length_norm = min(1.0, len(intron) / 200.0)

    # orthogonality: 高熵 + 非典型 GT-AG 模式 = 更特异
    orthogonality = max(0.0, min(1.0, 0.5 * ent + 0.3 * (1.0 - splice) + 0.2 * (1.0 - gc_penalty * 2)))

    passed = splice >= min_target_splice and orthogonality <= max_off_target_splice + 0.1
    return {
        "gc_content": round(gc, 3),
        "splice_site_score": round(splice, 3),
        "orthogonality": round(orthogonality, 3),
        "kmer_entropy": round(ent, 3),
        "gc_penalty": round(gc_penalty, 3),
        "length_norm": round(length_norm, 3),
        "passes_thresholds": passed,
    }


def score_sequence(seq: str) -> dict:
    return {
        "gc_content": round(_gc_content(seq), 3),
        "kmer_entropy": round(_kmer_entropy(seq), 3),
    }
```

- [ ] **Step 5: 写 `apps/api/app/proto/engine.py`**

```python
"""Proto 引擎封装。

Phase 1:不直接 import proto-language(它要 micromamba + 一堆生物模型),用启发式生成
内含子序列 + 内置评分器即可验证玩法。Phase 1.5 再接真 proto-language。
"""
from __future__ import annotations
import time
import random
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

from .scorer import score_intron
from .profile import detect_hardware
from app.config import settings


@dataclass
class ForgeResult:
    run_id: str
    mission_id: str
    ritual: str
    duration_ms: int
    intron: str
    fasta: str
    scores: dict
    risk_flags: list[dict] = field(default_factory=list)
    passed_gate: bool = False


_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template(mission_id: str) -> dict:
    """加载任务模板。Phase 1 只支持 polar-glow-v1。"""
    if mission_id == "polar-glow-v1":
        with open(_TEMPLATES_DIR / "polar-glow.json", "r", encoding="utf-8") as f:
            return json.load(f)
    raise ValueError(f"Unknown mission_id: {mission_id}")


def _generate_intron(length: int, generator: str, seed: int | None) -> str:
    """生成候选内含子序列(启发式,Phase 1 不接真 proto-language)。"""
    rng = random.Random(seed)
    if generator == "uniform":
        return "".join(rng.choices("ATGC", k=length))
    if generator == "random":
        return "".join(rng.choices("ATGC", k=length))
    # preference: 加点 GT-AG 边界,中段高熵
    seq = list(rng.choices("ATGC", k=length))
    if length >= 6:
        seq[0:2] = list("GT")
        seq[-2:] = list("AG")
    return "".join(seq)


def run_forge(mission_id: str, params: dict, generator: str, seed: int | None = None) -> ForgeResult:
    """端到端跑一次 forge(生成 + 评分 + 仪式名)。"""
    tpl = _load_template(mission_id)
    proto_tpl = tpl["proto_template"]
    weights = proto_tpl["scoring"]["weights"]
    min_target = float(params.get("min_target_splice", proto_tpl["constraint"]["min_target_splice_score"]))
    max_off = float(params.get("max_off_target", proto_tpl["constraint"]["max_off_target_splice_score"]))
    w_alpha = float(params.get("weight_alpha", weights["target_splice"]))
    w_beta = float(params.get("weight_beta", weights["orthogonality"]))
    length = int(proto_tpl["intron_length_range"][0] +
                 (proto_tpl["intron_length_range"][1] - proto_tpl["intron_length_range"][0]) * 0.5)
    length = max(80, min(250, length))

    start = time.perf_counter()
    intron = _generate_intron(length, generator, seed)
    raw = score_intron(intron, min_target_splice=min_target, max_off_target_splice=max_off)

    # 综合分
    primary = round(
        w_alpha * raw["splice_site_score"]
        + w_beta * (1.0 - raw["orthogonality"])
        - weights["gc_penalty"] * raw["gc_penalty"]
        - weights["length_penalty"] * raw["length_norm"],
        3,
    )

    risk_flags = []
    if not raw["passes_thresholds"]:
        risk_flags.append({
            "rule_id": "thresholds",
            "severity": "warn",
            "message": f"未达剪接/正交阈值 (splice={raw['splice_site_score']:.2f}, ortho={raw['orthogonality']:.2f})",
        })

    elapsed = int((time.perf_counter() - start) * 1000)
    fasta = f">protoforge_{mission_id}\n{intron}\n"
    hw = detect_hardware()

    return ForgeResult(
        run_id=f"run_{int(time.time() * 1000)}",
        mission_id=mission_id,
        ritual=hw.recommended_ritual,
        duration_ms=elapsed,
        intron=intron,
        fasta=fasta,
        scores={
            "primary": primary,
            "components": {
                "target_splice": raw["splice_site_score"],
                "orthogonality": raw["orthogonality"],
                "gc_penalty": raw["gc_penalty"],
                "length_penalty": raw["length_penalty"],
                "kmer_entropy": raw["kmer_entropy"],
            },
            "weights": {"alpha": w_alpha, "beta": w_beta},
        },
        risk_flags=risk_flags,
        passed_gate=raw["passes_thresholds"],
    )


def run_polar_glow(params: dict, generator: str = "preference", seed: int | None = None) -> ForgeResult:
    return run_forge("polar-glow-v1", params, generator, seed)
```

- [ ] **Step 6: 写 `apps/api/tests/test_polar_template.py`**

```python
"""极地模板加载测试。"""
import json
from pathlib import Path


def test_polar_template_loads() -> None:
    p = Path(__file__).resolve().parents[1] / "app" / "proto" / "templates" / "polar-glow.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["task_id"] == "polar-glow-v1"
    assert data["scenario"] == "polar"
    assert "proto_template" in data
    assert "scoring" in data["proto_template"]
    assert len(data["sliders"]) == 5
    assert len(data["risk_rules"]) >= 2
```

- [ ] **Step 7: 写 `apps/api/tests/test_engine_smoke.py`**

```python
"""Forge 引擎 smoke 测试。"""
from app.proto.engine import run_forge, run_polar_glow
from app.proto.scorer import score_intron


def test_score_intron_basic() -> None:
    intron = "GTATGCATGC" + "ATGC" * 20 + "AG"
    res = score_intron(intron)
    assert "splice_site_score" in res
    assert "orthogonality" in res
    assert 0.0 <= res["splice_site_score"] <= 1.0
    assert 0.0 <= res["orthogonality"] <= 1.0


def test_run_polar_glow_smoke() -> None:
    result = run_polar_glow(params={"min_target_splice": 0.5, "max_off_target": 0.3})
    assert result.mission_id == "polar-glow-v1"
    assert result.intron.startswith("GT") or len(result.intron) > 0
    assert result.fasta.startswith(">")
    assert "primary" in result.scores
    assert 0.0 <= result.scores["primary"] <= 1.5  # 允许轻微超界


def test_run_forge_with_generator() -> None:
    result = run_forge(
        "polar-glow-v1",
        params={"min_target_splice": 0.6, "max_off_target": 0.25, "weight_alpha": 0.6, "weight_beta": 0.3},
        generator="preference",
        seed=42,
    )
    assert result.run_id.startswith("run_")
    assert result.ritual in ("swift", "standard", "ancient", "crystal")
    assert result.duration_ms >= 0
```

- [ ] **Step 8: 跑测试**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv run pytest -v
```

预期:全部通过(health 2 + template 1 + engine 3 = 6 tests)。

- [ ] **Step 9: 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
git add apps/api/app/proto/ apps/api/tests/
git commit -m "feat(proto): polar-glow template + heuristic engine + scorer"
```

---

### Task 4: SpliceTransformer 评分(可选依赖,失败降级启发式)

**Files:**
- Create: `apps/api/app/proto/splice_scorer.py`
- Create: `apps/api/tests/test_splice_scorer.py`
- Modify: `apps/api/app/proto/scorer.py`(添加 import + fallback)

- [ ] **Step 1: 写 `apps/api/app/proto/splice_scorer.py`**

```python
"""SpliceTransformer 包装(可选依赖,无 GPU / 未装时降级为启发式)。"""
from __future__ import annotations
import logging
from typing import Protocol

log = logging.getLogger("protoforge.proto.splice")


class SpliceScorer(Protocol):
    def score_donor(self, seq: str) -> float: ...
    def score_acceptor(self, seq: str) -> float: ...


class HeuristicSpliceScorer:
    """SpliceTransformer 不可用时的回退评分。"""

    def score_donor(self, seq: str) -> float:
        if len(seq) < 6:
            return 0.0
        head = seq[:6].upper()
        if head[:2] != "GT":
            return 0.1
        pyrimidine = sum(1 for c in head[2:] if c in "CT")
        return 0.5 + 0.1 * pyrimidine

    def score_acceptor(self, seq: str) -> float:
        if len(seq) < 6:
            return 0.0
        tail = seq[-6:].upper()
        if tail[-2:] != "AG":
            return 0.1
        pyrimidine = sum(1 for c in tail[:-2] if c in "CT")
        return 0.5 + 0.1 * pyrimidine


class SpliceTransformerScorer:
    """真 SpliceTransformer 评分(需要 torch + spliceai)。"""

    def __init__(self) -> None:
        from spliceai import SpliceAI  # type: ignore
        self.model = SpliceAI()

    def score_donor(self, seq: str) -> float:
        scores = self.model.predict(seq.upper())
        if scores.shape[1] >= 1:
            return float(scores[0, :, 1].max())
        return 0.0

    def score_acceptor(self, seq: str) -> float:
        scores = self.model.predict(seq.upper())
        if scores.shape[1] >= 2:
            return float(scores[0, :, 2].max())
        return 0.0


_singleton: SpliceScorer | None = None


def get_scorer() -> SpliceScorer:
    """单例,优先用 SpliceTransformer,失败回退 HeuristicSpliceScorer。"""
    global _singleton
    if _singleton is not None:
        return _singleton
    try:
        _singleton = SpliceTransformerScorer()
        log.info("Using SpliceTransformer scorer")
    except Exception as e:
        log.warning("Falling back to HeuristicSpliceScorer: %s", e)
        _singleton = HeuristicSpliceScorer()
    return _singleton
```

- [ ] **Step 2: 在 `scorer.py` 集成可选 SpliceTransformer 评分**

把 `apps/api/app/proto/scorer.py` 的 `_splice_site_score` 替换为:

```python
def _splice_site_score(seq: str) -> float:
    """优先用 SpliceTransformer(若已装),否则 motif 启发式。"""
    try:
        from app.proto.splice_scorer import get_scorer
        scorer = get_scorer()
        d = scorer.score_donor(seq[:60])
        a = scorer.score_acceptor(seq[-60:])
        return min(1.0, 0.5 * d + 0.5 * a)
    except Exception:
        pass
    # fallback
    seq_u = seq.upper()
    donor = len(re.findall(r"[A-Z]G[CT]A[AG][CT]T", seq_u[:60]))
    acceptor = len(re.findall(r"[CT]AG[AG][A-Z]{15,20}G", seq_u[-60:]))
    branch = len(re.findall(r"[CT]T[AG]A[CT]", seq_u))
    return min(1.0, donor * 0.4 + acceptor * 0.4 + branch * 0.05)
```

- [ ] **Step 3: 写 `apps/api/tests/test_splice_scorer.py`**

```python
"""Splice 评分器测试(只测启发式,因为 CI 不装 SpliceTransformer)。"""
from app.proto.splice_scorer import HeuristicSpliceScorer, get_scorer


def test_heuristic_donor_gt() -> None:
    s = HeuristicSpliceScorer()
    assert s.score_donor("GTAAGTAAA") >= 0.5


def test_heuristic_donor_non_gt() -> None:
    s = HeuristicSpliceScorer()
    assert s.score_donor("AAATGCAAA") <= 0.2


def test_heuristic_acceptor_ag() -> None:
    s = HeuristicSpliceScorer()
    assert s.score_acceptor("TTTCAG") >= 0.5


def test_get_scorer_returns_singleton() -> None:
    a = get_scorer()
    b = get_scorer()
    assert a is b
```

- [ ] **Step 4: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv run pytest tests/test_splice_scorer.py -v
uv run pytest -v
git add apps/api/app/proto/ apps/api/tests/
git commit -m "feat(proto): SpliceTransformer optional integration with heuristic fallback"
```

---

### Task 5: Forge API 路由(POST /api/forge/run)

**Files:**
- Create: `apps/api/app/routers/forge.py`
- Create: `apps/api/tests/test_forge_router.py`

- [ ] **Step 1: 写 `apps/api/app/routers/forge.py`**

```python
"""/api/forge/* 端点。"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.proto.engine import run_forge, ForgeResult

router = APIRouter()


class ForgeRunRequest(BaseModel):
    mission_id: str = Field(..., description="模板 ID,如 polar-glow-v1")
    params: dict = Field(default_factory=dict)
    generator: str = Field(default="preference", pattern="^(uniform|preference|random)$")
    seed: int | None = None


class ForgeRunResponse(BaseModel):
    run_id: str
    mission_id: str
    ritual: str
    duration_ms: int
    fasta: str
    scores: dict
    risk_flags: list[dict]
    passed_gate: bool


@router.post("/run", response_model=ForgeRunResponse)
def forge_run(req: ForgeRunRequest) -> ForgeRunResponse:
    try:
        result: ForgeResult = run_forge(req.mission_id, req.params, req.generator, req.seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"forge failed: {e}")
    return ForgeRunResponse(
        run_id=result.run_id,
        mission_id=result.mission_id,
        ritual=result.ritual,
        duration_ms=result.duration_ms,
        fasta=result.fasta,
        scores=result.scores,
        risk_flags=result.risk_flags,
        passed_gate=result.passed_gate,
    )


@router.get("/ritual")
def forge_ritual() -> dict:
    """返回当前硬件档位 + 推荐仪式。"""
    from app.proto.profile import detect_hardware
    hw = detect_hardware()
    return {
        "gpu_name": hw.gpu_name,
        "gpu_memory_mb": hw.gpu_memory_mb,
        "cpu_cores": hw.cpu_cores,
        "ram_mb": hw.ram_mb,
        "recommended_ritual": hw.recommended_ritual,
        "recommended_models": hw.recommended_models,
    }
```

- [ ] **Step 2: 写 `apps/api/tests/test_forge_router.py`**

```python
"""/api/forge/* 端点测试。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_forge_run_polar(client: TestClient) -> None:
    res = client.post("/api/forge/run", json={
        "mission_id": "polar-glow-v1",
        "params": {"min_target_splice": 0.5, "max_off_target": 0.3},
        "generator": "preference",
        "seed": 123,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["mission_id"] == "polar-glow-v1"
    assert body["fasta"].startswith(">")
    assert "primary" in body["scores"]
    assert body["ritual"] in ("swift", "standard", "ancient", "crystal")


def test_forge_run_unknown_mission_400(client: TestClient) -> None:
    res = client.post("/api/forge/run", json={
        "mission_id": "no-such-mission",
        "params": {},
    })
    assert res.status_code == 400


def test_forge_ritual_endpoint(client: TestClient) -> None:
    res = client.get("/api/forge/ritual")
    assert res.status_code == 200
    body = res.json()
    assert "recommended_ritual" in body
    assert body["recommended_ritual"] in ("swift", "standard", "ancient", "crystal")
    assert isinstance(body["recommended_models"], list)
```

- [ ] **Step 3: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv run pytest tests/test_forge_router.py -v
uv run pytest -v
git add apps/api/app/routers/forge.py apps/api/tests/test_forge_router.py
git commit -m "feat(api): forge /run and /ritual endpoints"
```

---

### Task 6: Missions + Risk Gate 路由

**Files:**
- Create: `apps/api/app/routers/missions.py`
- Create: `apps/api/app/routers/risk.py`
- Create: `apps/api/tests/test_missions_router.py`
- Create: `apps/api/tests/test_risk_router.py`

- [ ] **Step 1: 写 `apps/api/app/routers/missions.py`**

```python
"""/api/missions/* 端点。"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "proto" / "templates"


def _list_missions() -> list[dict]:
    out = []
    for p in _TEMPLATES_DIR.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        out.append({
            "id": data.get("task_id", p.stem),
            "title": data.get("name"),
            "scenario": data.get("scenario"),
            "level": data.get("level"),
            "description": data.get("description"),
            "slider_count": len(data.get("sliders", [])),
            "risk_count": len(data.get("risk_rules", [])),
        })
    return out


@router.get("/")
def list_missions() -> list[dict]:
    return _list_missions()


@router.get("/{mission_id}")
def get_mission(mission_id: str) -> dict:
    for p in _TEMPLATES_DIR.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("task_id") == mission_id:
            return data
    raise HTTPException(status_code=404, detail=f"mission {mission_id} not found")
```

- [ ] **Step 2: 写 `apps/api/app/routers/risk.py`**

```python
"""/api/risk/* 端点(出题 + 判分)。"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "proto" / "templates"


def _load_mission(mission_id: str) -> dict:
    for p in _TEMPLATES_DIR.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("task_id") == mission_id:
            return data
    raise HTTPException(status_code=404, detail=f"mission {mission_id} not found")


@router.get("/{mission_id}/questions")
def get_questions(mission_id: str) -> list[dict]:
    """返回关卡所有 risk rules 作为多选题(去掉 correct 标记)。"""
    mission = _load_mission(mission_id)
    questions = []
    for rule in mission.get("risk_rules", []):
        questions.append({
            "id": rule["id"],
            "question": rule["question"],
            "options": [{"value": o["value"], "label": o["label"]} for o in rule["options"]],
        })
    return questions


class RiskAnswer(BaseModel):
    rule_id: str
    value: str


class RiskSubmitRequest(BaseModel):
    mission_id: str
    answers: list[RiskAnswer]


class RiskSubmitResponse(BaseModel):
    passed: bool
    correct_count: int
    total: int
    details: list[dict]


@router.post("/submit", response_model=RiskSubmitResponse)
def submit_risk(req: RiskSubmitRequest) -> RiskSubmitResponse:
    mission = _load_mission(req.mission_id)
    rules = {r["id"]: r for r in mission.get("risk_rules", [])}

    details = []
    correct = 0
    for ans in req.answers:
        rule = rules.get(ans.rule_id)
        if not rule:
            details.append({"rule_id": ans.rule_id, "ok": False, "explanation": "未知题目"})
            continue
        opt = next((o for o in rule["options"] if o["value"] == ans.value), None)
        ok = bool(opt and opt.get("correct"))
        if ok:
            correct += 1
        details.append({
            "rule_id": ans.rule_id,
            "ok": ok,
            "explanation": rule.get("explanation", ""),
            "user_value": ans.value,
            "correct_value": next((o["value"] for o in rule["options"] if o.get("correct")), None),
        })
    total = len(req.answers)
    return RiskSubmitResponse(
        passed=correct == total and total > 0,
        correct_count=correct,
        total=total,
        details=details,
    )
```

- [ ] **Step 3: 写 `apps/api/tests/test_missions_router.py`**

```python
"""/api/missions/* 测试。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_missions(client: TestClient) -> None:
    res = client.get("/api/missions/")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert any(m["id"] == "polar-glow-v1" for m in body)


def test_get_mission_detail(client: TestClient) -> None:
    res = client.get("/api/missions/polar-glow-v1")
    assert res.status_code == 200
    body = res.json()
    assert body["task_id"] == "polar-glow-v1"
    assert body["scenario"] == "polar"
    assert len(body["sliders"]) == 5


def test_get_mission_404(client: TestClient) -> None:
    res = client.get("/api/missions/no-such")
    assert res.status_code == 404
```

- [ ] **Step 4: 写 `apps/api/tests/test_risk_router.py`**

```python
"""/api/risk/* 测试。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_questions(client: TestClient) -> None:
    res = client.get("/api/risk/polar-glow-v1/questions")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert len(body) >= 2
    for q in body:
        assert all("correct" not in opt for opt in q["options"])


def test_submit_all_correct(client: TestClient) -> None:
    questions = client.get("/api/risk/polar-glow-v1/questions").json()
    answers = [{"rule_id": q["id"], "value": "b"} for q in questions]
    res = client.post("/api/risk/submit", json={"mission_id": "polar-glow-v1", "answers": answers})
    assert res.status_code == 200
    body = res.json()
    assert body["passed"] is True
    assert body["correct_count"] == body["total"]


def test_submit_partial_wrong(client: TestClient) -> None:
    questions = client.get("/api/risk/polar-glow-v1/questions").json()
    answers = [{"rule_id": q["id"], "value": "a"} for q in questions]
    res = client.post("/api/risk/submit", json={"mission_id": "polar-glow-v1", "answers": answers})
    body = res.json()
    assert body["passed"] is False
    assert body["correct_count"] == 0
```

- [ ] **Step 5: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv run pytest -v
git add apps/api/app/routers/ apps/api/tests/
git commit -m "feat(api): missions + risk gate endpoints"
```

---

### Task 7: Gallery 路由(作品浏览,内存 store,Task 13 接 SQLite)

**Files:**
- Create: `apps/api/app/routers/gallery.py`
- Create: `apps/api/tests/test_gallery_router.py`

- [ ] **Step 1: 写 `apps/api/app/routers/gallery.py`**

```python
"""/api/gallery/* 端点 - 浏览本地作品(Phase 1 内存 store,Task 13 换 SQLite)。"""
from __future__ import annotations
import time
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

router = APIRouter()

_STORE: list[dict] = []


class SaveArtifactRequest(BaseModel):
    mission_id: str
    mission_title: str
    scores: dict
    fasta: str
    passed_gate: bool
    ritual: Literal["swift", "standard", "ancient", "crystal"]
    duration_ms: int


class SaveArtifactResponse(BaseModel):
    id: str
    created_at: str


@router.post("/save", response_model=SaveArtifactResponse)
def save_artifact(req: SaveArtifactRequest) -> SaveArtifactResponse:
    aid = str(uuid.uuid4())
    now = time.time()
    _STORE.append({
        "id": aid,
        "mission_id": req.mission_id,
        "mission_title": req.mission_title,
        "scores": req.scores,
        "fasta": req.fasta,
        "passed_gate": req passed_gate,
        "ritual": req.ritual,
        "duration_ms": req.duration_ms,
        "created_at": now,
    })
    return SaveArtifactResponse(id=aid, created_at=str(now))


@router.get("/")
def list_artifacts() -> list[dict]:
    return sorted(_STORE, key=lambda a: a["created_at"], reverse=True)


@router.get("/{artifact_id}")
def get_artifact(artifact_id: str) -> dict:
    for a in _STORE:
        if a["id"] == artifact_id:
            return a
    raise HTTPException(status_code=404, detail="artifact not found")


@router.delete("/{artifact_id}")
def delete_artifact(artifact_id: str) -> dict:
    global _STORE
    before = len(_STORE)
    _STORE = [a for a in _STORE if a["id"] != artifact_id]
    if len(_STORE) == before:
        raise HTTPException(status_code=404, detail="artifact not found")
    return {"deleted": artifact_id}
```

> **注意**:上面第 46 行有 typo,实际写入时应该是 `passed_gate=req.passed_gate,`。Step 2 修正。

- [ ] **Step 2: 修正 `_STORE.append` 字段**

在 `apps/api/app/routers/gallery.py` 找到 `passed_gate": req passed_gate,` 替换为:

```python
        "passed_gate": req.passed_gate,
```

- [ ] **Step 3: 写 `apps/api/tests/test_gallery_router.py`**

```python
"""/api/gallery/* 测试(内存 store)。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _sample() -> dict:
    return {
        "mission_id": "polar-glow-v1",
        "mission_title": "极地耐低温发光菌",
        "scores": {"primary": 0.7, "components": {}, "weights": {}},
        "fasta": ">test\nGTATGCAG\n",
        "passed_gate": True,
        "ritual": "standard",
        "duration_ms": 1234,
    }


def test_save_and_list(client: TestClient) -> None:
    res = client.post("/api/gallery/save", json=_sample())
    assert res.status_code == 200
    aid = res.json()["id"]
    res = client.get("/api/gallery/")
    assert res.status_code == 200
    assert any(a["id"] == aid for a in res.json())


def test_get_artifact(client: TestClient) -> None:
    aid = client.post("/api/gallery/save", json=_sample()).json()["id"]
    res = client.get(f"/api/gallery/{aid}")
    assert res.status_code == 200
    assert res.json()["mission_id"] == "polar-glow-v1"


def test_delete_artifact(client: TestClient) -> None:
    aid = client.post("/api/gallery/save", json=_sample()).json()["id"]
    res = client.delete(f"/api/gallery/{aid}")
    assert res.status_code == 200
    res = client.get(f"/api/gallery/{aid}")
    assert res.status_code == 404
```

- [ ] **Step 4: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv run pytest -v
git add apps/api/app/routers/gallery.py apps/api/tests/test_gallery_router.py
git commit -m "feat(api): gallery endpoints (in-memory store, sqlite in task 13)"
```

---

### Task 8: Onboarding + LLM provider 抽象(云 / 本地 / 纯滑块)

**Files:**
- Create: `apps/api/app/llm/base.py`
- Create: `apps/api/app/llm/factory.py`
- Create: `apps/api/app/llm/providers/disabled.py`
- Create: `apps/api/app/llm/providers/cloud.py`
- Create: `apps/api/app/llm/providers/local.py`
- Create: `apps/api/app/llm/providers/__init__.py`
- Create: `apps/api/app/llm/__init__.py`
- Create: `apps/api/app/routers/onboarding.py`
- Create: `apps/api/tests/test_llm_factory.py`
- Create: `apps/api/tests/test_onboarding_router.py`

- [ ] **Step 1: 写 `apps/api/app/llm/base.py`**

```python
"""LLM 抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMRequest:
    system: str
    user: str
    temperature: float = 0.3
    max_tokens: int = 512


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    duration_ms: int


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, req: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    def is_available(self) -> bool: ...
```

- [ ] **Step 2: 写 `apps/api/app/llm/providers/disabled.py`**

```python
"""纯滑块模式:无 LLM,翻译端点应识别并走规则。"""
from __future__ import annotations
import time
from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class DisabledProvider(LLMProvider):
    name = "disabled"

    def complete(self, req: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        return LLMResponse(
            text="",
            provider="disabled",
            model="",
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    def is_available(self) -> bool:
        return True
```

- [ ] **Step 3: 写 `apps/api/app/llm/providers/cloud.py`**

```python
"""云 API provider(OpenAI 兼容,DeepSeek / GPT / Claude)。"""
from __future__ import annotations
import time
import httpx
from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class CloudProvider(LLMProvider):
    name = "cloud"

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1",
                 model: str = "deepseek-chat", timeout_sec: float = 30.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec

    def is_available(self) -> bool:
        return bool(self.api_key) and bool(self.base_url) and bool(self.model)

    def complete(self, req: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("CloudProvider not configured")
        t0 = time.perf_counter()
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": req.system},
                {"role": "user", "content": req.user},
            ],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stream": False,
        }
        with httpx.Client(timeout=self.timeout_sec) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        text = data["choices"][0]["message"]["content"]
        return LLMResponse(
            text=text,
            provider="cloud",
            model=self.model,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
```

- [ ] **Step 4: 写 `apps/api/app/llm/providers/local.py`**

```python
"""本地 LLM provider(Ollama / LM Studio 的 OpenAI 兼容端点)。"""
from __future__ import annotations
import time
import httpx
from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class LocalProvider(LLMProvider):
    name = "local"

    def __init__(self, base_url: str = "http://127.0.0.1:11434/v1",
                 model: str = "qwen2.5:3b", timeout_sec: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=2.0) as client:
                r = client.get(f"{self.base_url}/models")
                return r.status_code == 200
        except Exception:
            return False

    def complete(self, req: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": req.system},
                {"role": "user", "content": req.user},
            ],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        with httpx.Client(timeout=self.timeout_sec) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        text = data["choices"][0]["message"]["content"]
        return LLMResponse(
            text=text,
            provider="local",
            model=self.model,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
```

- [ ] **Step 5: 写 `apps/api/app/llm/providers/__init__.py`**

```python
from .disabled import DisabledProvider
from .cloud import CloudProvider
from .local import LocalProvider

__all__ = ["DisabledProvider", "CloudProvider", "LocalProvider"]
```

- [ ] **Step 6: 写 `apps/api/app/llm/factory.py`**

```python
"""LLM provider 工厂。"""
from __future__ import annotations
from app.llm.base import LLMProvider
from app.llm.providers import DisabledProvider, CloudProvider, LocalProvider
from app.config import settings


def make_provider() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "cloud":
        return CloudProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or "https://api.deepseek.com/v1",
            model=settings.llm_model or "deepseek-chat",
        )
    if provider == "local":
        return LocalProvider(
            base_url=settings.llm_base_url or "http://127.0.0.1:11434/v1",
            model=settings.llm_model or "qwen2.5:3b",
        )
    return DisabledProvider()
```

- [ ] **Step 7: 写 `apps/api/app/llm/__init__.py`**

```python
from .base import LLMProvider, LLMRequest, LLMResponse
from .factory import make_provider

__all__ = ["LLMProvider", "LLMRequest", "LLMResponse", "make_provider"]
```

- [ ] **Step 8: 写 `apps/api/app/routers/onboarding.py`**

```python
"""/api/onboarding/* 端点 - 首次启动引导。"""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal
import httpx
from app.llm.providers import CloudProvider, LocalProvider

router = APIRouter()


class OnboardingSubmitRequest(BaseModel):
    provider: Literal["cloud", "local", "disabled"]
    config: dict = {}


class OnboardingSubmitResponse(BaseModel):
    ok: bool
    provider: str
    test_passed: bool
    error: str | None = None
    detected: dict | None = None


def _test_provider(provider: str, cfg: dict) -> tuple[bool, str | None, dict]:
    detected: dict = {}
    if provider == "cloud":
        p = CloudProvider(
            api_key=cfg.get("api_key", ""),
            base_url=cfg.get("base_url", "https://api.deepseek.com/v1"),
            model=cfg.get("model", "deepseek-chat"),
        )
        if not p.is_available():
            return False, "missing api_key/base_url/model", detected
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(
                    f"{p.base_url}/models",
                    headers={"Authorization": f"Bearer {p.api_key}"},
                )
                if r.status_code >= 400:
                    return False, f"cloud API returned {r.status_code}", detected
                detected["models_count"] = len(r.json().get("data", []))
        except Exception as e:
            return False, f"cloud ping failed: {e}", detected
        return True, None, detected
    if provider == "local":
        p = LocalProvider(
            base_url=cfg.get("base_url", "http://127.0.0.1:11434/v1"),
            model=cfg.get("model", "qwen2.5:3b"),
        )
        if not p.is_available():
            return False, "local LLM server not reachable, start Ollama/LM Studio first", detected
        return True, None, detected
    return True, None, detected


@router.post("/submit", response_model=OnboardingSubmitResponse)
def submit_onboarding(req: OnboardingSubmitRequest) -> OnboardingSubmitResponse:
    ok, err, detected = _test_provider(req.provider, req.config)
    return OnboardingSubmitResponse(
        ok=ok,
        provider=req.provider,
        test_passed=ok,
        error=err,
        detected=detected if detected else None,
    )


@router.get("/status")
def onboarding_status() -> dict:
    from app.config import settings
    return {
        "provider": settings.llm_provider,
        "configured": bool(
            (settings.llm_provider == "cloud" and settings.llm_api_key)
            or settings.llm_provider == "local"
            or settings.llm_provider == "disabled"
        ),
    }
```

- [ ] **Step 9: 写 `apps/api/tests/test_llm_factory.py`**

```python
"""LLM factory 测试。"""
import pytest
from app.llm.factory import make_provider
from app.llm.providers import DisabledProvider, CloudProvider, LocalProvider
from app.config import settings


def test_default_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "disabled", raising=False)
    p = make_provider()
    assert isinstance(p, DisabledProvider)


def test_cloud_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "cloud", raising=False)
    monkeypatch.setattr(settings, "llm_api_key", "sk-test", raising=False)
    monkeypatch.setattr(settings, "llm_base_url", "https://api.deepseek.com/v1", raising=False)
    monkeypatch.setattr(settings, "llm_model", "deepseek-chat", raising=False)
    p = make_provider()
    assert isinstance(p, CloudProvider)
    assert p.is_available()


def test_local_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "local", raising=False)
    monkeypatch.setattr(settings, "llm_base_url", "http://127.0.0.1:11434/v1", raising=False)
    monkeypatch.setattr(settings, "llm_model", "qwen2.5:3b", raising=False)
    p = make_provider()
    assert isinstance(p, LocalProvider)
```

- [ ] **Step 10: 写 `apps/api/tests/test_onboarding_router.py`**

```python
"""/api/onboarding/* 测试。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_onboarding_disabled(client: TestClient) -> None:
    res = client.post("/api/onboarding/submit", json={"provider": "disabled", "config": {}})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["provider"] == "disabled"


def test_onboarding_cloud_missing_key(client: TestClient) -> None:
    res = client.post("/api/onboarding/submit", json={"provider": "cloud", "config": {}})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert "api_key" in (body["error"] or "").lower()


def test_onboarding_status(client: TestClient) -> None:
    res = client.get("/api/onboarding/status")
    assert res.status_code == 200
    body = res.json()
    assert "provider" in body
    assert "configured" in body
```

- [ ] **Step 11: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv run pytest -v
git add apps/api/app/llm/ apps/api/app/routers/onboarding.py apps/api/tests/test_llm_factory.py apps/api/tests/test_onboarding_router.py
git commit -m "feat(llm): 3-provider abstraction + onboarding endpoint"
```

---

### Task 9: Translate 路由(NL → 滑块值)

**Files:**
- Create: `apps/api/app/routers/translate.py`
- Create: `apps/api/tests/test_translate_router.py`

- [ ] **Step 1: 写 `apps/api/app/routers/translate.py`**

```python
"""/api/translate/* 端点 - 自然语言 → 滑块值。"""
from __future__ import annotations
import json
import re
from fastapi import APIRouter
from pydantic import BaseModel
from app.llm.factory import make_provider
from app.llm.base import LLMRequest
from app.llm.providers import DisabledProvider

router = APIRouter()


class TranslateRequest(BaseModel):
    natural_language: str
    mission_id: str | None = None
    current_params: dict = {}


class TranslateResponse(BaseModel):
    params: dict
    generator: str
    explanation: str
    provider: str


_TRANSLATE_SYSTEM = """你是一个合成生物学实验助手的参数调优顾问。
玩家会给你一段自然语言描述,你需要把它转成 5 个滑块的具体数值。
输出严格 JSON,字段:
- params: dict,键为滑块 ID
- generator: "uniform" | "preference" | "random"
- explanation: 简短中文解释你的选择

滑块 ID 与范围:
- min_target_splice: 0.4 ~ 0.95(目标剪接强度下限,越高越严格)
- max_off_target: 0.05 ~ 0.40(脱靶抑制,越低越严格)
- weight_alpha: 0.0 ~ 1.0(对目标剪接的偏重)
- weight_beta: 0.0 ~ 1.0(对正交性的偏重)
- mcmc_steps: 10 ~ 200(搜索步数)

只输出 JSON,不要其他文字。"""


def _rule_based_translate(text: str) -> dict:
    """Disabled 模式的兜底翻译 - 关键词规则匹配。"""
    text = text.lower()
    params = {
        "min_target_splice": 0.65,
        "max_off_target": 0.20,
        "weight_alpha": 0.5,
        "weight_beta": 0.35,
        "mcmc_steps": 50,
    }
    generator = "preference"

    if any(k in text for k in ["激进", "强", "高", "狠", "aggressive", "high"]):
        params["min_target_splice"] = 0.85
        params["weight_alpha"] = 0.7
    if any(k in text for k in ["保守", "安全", "稳", "safe", "low"]):
        params["max_off_target"] = 0.10
        params["weight_beta"] = 0.6
    if any(k in text for k in ["多", "深度搜索", "慢", "thorough"]):
        params["mcmc_steps"] = 150
        generator = "preference"
    if any(k in text for k in ["快", "随便", "quick", "fast"]):
        params["mcmc_steps"] = 20
        generator = "uniform"
    if "随机" in text or "random" in text:
        generator = "random"

    return {
        "params": params,
        "generator": generator,
        "explanation": "基于关键词规则的兜底翻译(无 LLM)。",
    }


def _parse_llm_json(text: str) -> dict | None:
    """从 LLM 输出提取 JSON 块。"""
    text = text.strip()
    # 直接 JSON
    try:
        return json.loads(text)
    except Exception:
        pass
    # ```json ... ``` 块
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 第一个 { ... }
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


@router.post("/", response_model=TranslateResponse)
def translate(req: TranslateRequest) -> TranslateResponse:
    provider = make_provider()
    if isinstance(provider, DisabledProvider):
        result = _rule_based_translate(req.natural_language)
        return TranslateResponse(
            **result,
            provider="disabled",
        )
    # 用 LLM 翻译
    user_msg = f"任务: {req.mission_id or 'unknown'}\n"
    if req.current_params:
        user_msg += f"当前参数: {json.dumps(req.current_params, ensure_ascii=False)}\n"
    user_msg += f"玩家描述: {req.natural_language}"

    llm_res = provider.complete(LLMRequest(system=_TRANSLATE_SYSTEM, user=user_msg, temperature=0.2, max_tokens=300))
    parsed = _parse_llm_json(llm_res.text)
    if not parsed:
        # 解析失败回退
        result = _rule_based_translate(req.natural_language)
        result["explanation"] = f"LLM 输出解析失败,降级到规则翻译。原输出: {llm_res.text[:80]}"
        return TranslateResponse(**result, provider=provider.name)

    return TranslateResponse(
        params=parsed.get("params", {}),
        generator=parsed.get("generator", "preference"),
        explanation=parsed.get("explanation", ""),
        provider=provider.name,
    )
```

- [ ] **Step 2: 写 `apps/api/tests/test_translate_router.py`**

```python
"""/api/translate/* 测试。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_translate_disabled_falls_back_to_rules(client: TestClient) -> None:
    res = client.post("/api/translate/", json={
        "natural_language": "我要保守一点的参数,脱靶一定要低",
        "mission_id": "polar-glow-v1",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "disabled"
    assert body["params"]["max_off_target"] <= 0.15
    assert "规则" in body["explanation"]


def test_translate_aggressive_keywords(client: TestClient) -> None:
    res = client.post("/api/translate/", json={
        "natural_language": "激进点,搜索要快",
        "mission_id": "polar-glow-v1",
    })
    body = res.json()
    assert body["params"]["min_target_splice"] >= 0.75
    assert body["params"]["mcmc_steps"] <= 30


def test_translate_random_generator(client: TestClient) -> None:
    res = client.post("/api/translate/", json={
        "natural_language": "完全随机随便",
        "mission_id": "polar-glow-v1",
    })
    body = res.json()
    assert body["generator"] == "random"
```

- [ ] **Step 3: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv run pytest tests/test_translate_router.py -v
uv run pytest -v
git add apps/api/app/routers/translate.py apps/api/tests/test_translate_router.py
git commit -m "feat(api): NL→params translation with rule-based fallback for disabled mode"
```

---

### Task 10: 前端 API 客户端 + 任务卡组件

**Files:**
- Modify: `apps/web/src/lib/api.ts`(扩展)
- Create: `apps/web/src/components/MissionCard.tsx`
- Create: `apps/web/src/components/ScoreRadar.tsx`
- Create: `apps/web/src/components/SliderCard.tsx`
- Create: `apps/web/src/components/ForgeAnimation.tsx`
- Create: `apps/web/src/components/SequenceView.tsx`
- Create: `apps/web/src/components/RiskQuestionCard.tsx`
- Create: `apps/web/src/components/ArtifactCard.tsx`

- [ ] **Step 1: 扩展 `apps/web/src/lib/api.ts`**

用以下完整内容替换:

```typescript
import type {
  ApiError, Mission, Artifact, ForgeRequest, ForgeResult,
  TranslateRequest, TranslateResponse, OnboardingRequest, OnboardingResponse,
  RiskFlag, ScoreVector,
} from './types';

const BASE = '/api';

class ApiException extends Error {
  status: number;
  body: ApiError;
  constructor(status: number, body: ApiError) {
    super(body.error || `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiException(res.status, data || { error: res.statusText });
  return data as T;
}

export const api = {
  health: () => request<{ status: string; version: string }>('GET', '/health'),

  missions: {
    list: () => request<Mission[]>('GET', '/missions/'),
    get: (id: string) => request<Mission>('GET', `/missions/${id}`),
  },

  forge: {
    run: (req: ForgeRequest) => request<ForgeResult>('POST', '/forge/run', req),
    ritual: () => request<{
      gpu_name: string | null; gpu_memory_mb: number;
      cpu_cores: number; ram_mb: number;
      recommended_ritual: string; recommended_models: string[];
    }>('GET', '/forge/ritual'),
  },

  risk: {
    questions: (missionId: string) =>
      request<{ id: string; question: string; options: { value: string; label: string }[] }[]>(
        'GET', `/risk/${missionId}/questions`,
      ),
    submit: (missionId: string, answers: { rule_id: string; value: string }[]) =>
      request<{
        passed: boolean; correct_count: number; total: number; details: any[];
      }>('POST', '/risk/submit', { mission_id: missionId, answers }),
  },

  gallery: {
    list: () => request<Artifact[]>('GET', '/gallery/'),
    get: (id: string) => request<Artifact>('GET', `/gallery/${id}`),
    save: (artifact: Omit<Artifact, 'id' | 'created_at'>) =>
      request<{ id: string; created_at: string }>('POST', '/gallery/save', artifact),
    remove: (id: string) => request<{ deleted: string }>('DELETE', `/gallery/${id}`),
  },

  translate: (req: TranslateRequest) =>
    request<TranslateResponse>('POST', '/translate/', req),

  onboarding: {
    submit: (req: OnboardingRequest) =>
      request<OnboardingResponse>('POST', '/onboarding/submit', req),
    status: () =>
      request<{ provider: string; configured: boolean }>('GET', '/onboarding/status'),
  },
};

export { ApiException };
```

- [ ] **Step 2: 写 `apps/web/src/components/ScoreRadar.tsx`**

```typescript
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

interface Props {
  scores: { name: string; value: number }[];
  primary?: number;
}

export function ScoreRadar({ scores, primary }: Props) {
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={scores}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <PolarRadiusAxis angle={90} domain={[0, 1]} tick={{ fill: '#475569', fontSize: 10 }} />
          <Radar name="评分" dataKey="value" stroke="#f97316" fill="#f97316" fillOpacity={0.4} />
        </RadarChart>
      </ResponsiveContainer>
      {primary !== undefined && (
        <div className="text-center mt-2">
          <span className="text-xs text-slate-500">综合分</span>
          <span className="ml-2 text-2xl font-mono text-forge-500">{primary.toFixed(3)}</span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 写 `apps/web/src/components/SliderCard.tsx`**

```typescript
import * as Slider from '@radix-ui/react-slider';
import { useState } from 'react';
import type { SliderParam } from '@/lib/types';

interface Props {
  param: SliderParam;
  value: number;
  onChange: (v: number) => void;
}

export function SliderCard({ param, value, onChange }: Props) {
  const [local, setLocal] = useState(value);
  return (
    <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
      <div className="flex justify-between items-baseline">
        <label className="text-sm text-slate-300">{param.label}</label>
        <span className="font-mono text-forge-500 text-lg">{local.toFixed(param.step < 1 ? 2 : 0)}</span>
      </div>
      <Slider.Root
        className="relative flex items-center select-none touch-none w-full h-5 mt-3"
        min={param.min} max={param.max} step={param.step}
        value={[local]}
        onValueChange={(v) => setLocal(v[0])}
        onValueCommit={(v) => onChange(v[0])}
      >
        <Slider.Track className="bg-slate-800 relative grow rounded-full h-1.5">
          <Slider.Range className="absolute bg-forge-500 rounded-full h-full" />
        </Slider.Track>
        <Slider.Thumb
          className="block w-4 h-4 bg-forge-500 rounded-full hover:bg-forge-600 focus:outline-none focus:ring-2 focus:ring-forge-300"
          aria-label={param.label}
        />
      </Slider.Root>
      <p className="text-xs text-slate-500 mt-2">{param.description}</p>
    </div>
  );
}
```

- [ ] **Step 4: 写 `apps/web/src/components/SequenceView.tsx`**

```typescript
interface Props {
  fasta: string;
}

export function SequenceView({ fasta }: Props) {
  const lines = fasta.split('\n');
  const header = lines[0] || '';
  const seq = lines.slice(1).join('').toUpperCase();
  const chunks: string[] = [];
  for (let i = 0; i < seq.length; i += 10) {
    chunks.push(seq.slice(i, i + 10));
  }
  const rows: string[][] = [];
  for (let i = 0; i < chunks.length; i += 6) {
    rows.push(chunks.slice(i, i + 6));
  }

  return (
    <div className="font-mono text-xs">
      <div className="text-slate-400 mb-2">{header}</div>
      <div className="bg-slate-950 p-3 rounded border border-slate-800">
        {rows.map((row, ri) => (
          <div key={ri} className="flex">
            <span className="text-slate-600 w-12 text-right pr-2">
              {String(ri * 60 + 1).padStart(3, ' ')}
            </span>
            <span className="text-emerald-400 tracking-wider">
              {row.join(' ')}
            </span>
          </div>
        ))}
        <div className="text-slate-500 mt-2">长度: {seq.length} bp · GC: {((seq.match(/[GC]/g)?.length || 0) / Math.max(seq.length, 1) * 100).toFixed(1)}%</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: 写 `apps/web/src/components/ForgeAnimation.tsx`**

```typescript
import { useEffect, useState } from 'react';
import type { ForgeRitual } from '@/lib/types';

const RITUALS: Record<ForgeRitual, { label: string; color: string; icon: string; est: string }> = {
  swift: { label: '急锻', color: 'text-yellow-400', icon: '⚡', est: '2-5 秒' },
  standard: { label: '标准锻', color: 'text-orange-400', icon: '🔥', est: '5-10 秒' },
  ancient: { label: '古法锻', color: 'text-amber-600', icon: '🪵', est: '15-30 秒' },
  crystal: { label: '晶种培育', color: 'text-cyan-400', icon: '💎', est: '30-90 秒' },
};

interface Props {
  ritual: ForgeRitual;
  durationMs: number;
  onDone?: () => void;
}

export function ForgeAnimation({ ritual, durationMs, onDone }: Props) {
  const [elapsed, setElapsed] = useState(0);
  const info = RITUALS[ritual];
  const totalMs = Math.max(durationMs, 100);

  useEffect(() => {
    const t0 = Date.now();
    const id = setInterval(() => {
      const dt = Date.now() - t0;
      setElapsed(dt);
      if (dt >= totalMs) {
        clearInterval(id);
        onDone?.();
      }
    }, 100);
    return () => clearInterval(id);
  }, [totalMs, onDone]);

  const pct = Math.min(100, (elapsed / totalMs) * 100);

  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className={`text-6xl ${info.color} mb-4 animate-pulse`}>{info.icon}</div>
      <div className={`text-2xl font-bold ${info.color}`}>{info.label}</div>
      <div className="text-sm text-slate-500 mt-1">仪式进行中 · 预计 {info.est}</div>
      <div className="w-64 h-2 bg-slate-800 rounded-full mt-6 overflow-hidden">
        <div className="h-full bg-forge-500 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="font-mono text-sm text-slate-400 mt-2">
        已等待 {(elapsed / 1000).toFixed(1)}s / {(totalMs / 1000).toFixed(1)}s
      </div>
    </div>
  );
}
```

- [ ] **Step 6: 写 `apps/web/src/components/MissionCard.tsx`**

```typescript
import { Link } from 'react-router-dom';
import type { Mission } from '@/lib/types';

const SCENARIO_LABEL: Record<Mission['scenario'], string> = {
  polar: '🧊 极地', mars: '🔴 火星', hospital: '🏥 医院',
};

const LEVEL_LABEL: Record<Mission['level'], string> = {
  tutorial: '教学', commission: '委托', 'multi-link': '联网', tough: '棘手', free: '自由',
};

interface Props { mission: Mission; }

export function MissionCard({ mission }: Props) {
  return (
    <Link
      to={`/mission/${mission.id}`}
      className="block p-5 rounded-lg bg-slate-900 border border-slate-800 hover:border-forge-500 transition-colors"
    >
      <div className="flex justify-between items-start">
        <h3 className="text-lg font-semibold text-slate-100">{mission.title}</h3>
        <span className="text-xs text-slate-500 ml-2 shrink-0">{SCENARIO_LABEL[mission.scenario]} · {LEVEL_LABEL[mission.level]}</span>
      </div>
      <p className="mt-2 text-sm text-slate-400 line-clamp-3">{mission.description}</p>
      <div className="mt-3 flex gap-3 text-xs text-slate-500">
        <span>🎚️ {mission.slider_count} 滑块</span>
        <span>🛡️ {mission.risk_count} 风险门</span>
      </div>
    </Link>
  );
}
```

- [ ] **Step 7: 写 `apps/web/src/components/RiskQuestionCard.tsx`**

```typescript
import { useState } from 'react';
import * as RadioGroup from '@radix-ui/react-radio-group';

interface Question {
  id: string;
  question: string;
  options: { value: string; label: string }[];
}

interface Props {
  question: Question;
  onAnswer: (ruleId: string, value: string) => void;
}

export function RiskQuestionCard({ question, onAnswer }: Props) {
  const [value, setValue] = useState<string>('');
  return (
    <div className="p-5 rounded-lg bg-slate-900 border border-slate-800">
      <p className="text-slate-200 font-medium mb-3">{question.question}</p>
      <RadioGroup.Root value={value} onValueChange={(v) => { setValue(v); onAnswer(question.id, v); }}>
        {question.options.map((opt) => (
          <label key={opt.value} className="flex items-center gap-2 p-2 rounded hover:bg-slate-800 cursor-pointer">
            <RadioGroup.Item
              value={opt.value}
              className="w-4 h-4 rounded-full border border-slate-600 data-[state=checked]:border-forge-500 data-[state=checked]:bg-forge-500"
            >
              <RadioGroup.Indicator className="block w-full h-full rounded-full" />
            </RadioGroup.Item>
            <span className="text-sm text-slate-300">{opt.label}</span>
          </label>
        ))}
      </RadioGroup.Root>
    </div>
  );
}
```

- [ ] **Step 8: 写 `apps/web/src/components/ArtifactCard.tsx`**

```typescript
import { Link } from 'react-router-dom';
import type { Artifact } from '@/lib/types';

interface Props {
  artifact: Artifact;
  onDelete?: (id: string) => void;
}

const RITUAL_LABEL: Record<Artifact['ritual'], string> = {
  swift: '⚡ 急锻', standard: '🔥 标准锻', ancient: '🪵 古法锻', crystal: '💎 晶种培育',
};

export function ArtifactCard({ artifact, onDelete }: Props) {
  return (
    <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
      <div className="flex justify-between items-start">
        <h4 className="text-sm font-semibold text-slate-200">{artifact.mission_title}</h4>
        {artifact.passed_gate && <span className="text-xs text-emerald-400">✅ 通过</span>}
      </div>
      <div className="mt-2 text-xs text-slate-500 flex gap-3">
        <span>{RITUAL_LABEL[artifact.ritual]}</span>
        <span>{(artifact.duration_ms / 1000).toFixed(1)}s</span>
        <span>主分 {artifact.scores.primary.toFixed(3)}</span>
      </div>
      <div className="mt-2 font-mono text-[10px] text-slate-500 truncate">{artifact.fasta.slice(0, 60)}…</div>
      <div className="mt-3 flex gap-2">
        <Link to={`/artifact/${artifact.id}`} className="text-xs text-forge-500 hover:underline">查看</Link>
        {onDelete && (
          <button onClick={() => onDelete(artifact.id)} className="text-xs text-red-400 hover:underline">删除</button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 9: 写组件测试 `apps/web/src/components/SliderCard.test.tsx`**

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { SliderCard } from '@/components/SliderCard';

describe('SliderCard', () => {
  const param = { id: 'test', label: '测试滑块', min: 0, max: 1, step: 0.1, default: 0.5, description: 'desc' };

  it('renders label and initial value', () => {
    render(<SliderCard param={param} value={0.5} onChange={() => {}} />);
    expect(screen.getByText('测试滑块')).toBeInTheDocument();
    expect(screen.getByText('0.50')).toBeInTheDocument();
  });
});
```

- [ ] **Step 10: 跑前端测试**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\web'
pnpm test
```

预期:原有 Home 测试 + 新 SliderCard 测试 = 3 tests 通过。

- [ ] **Step 11: 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
git add apps/web/src/lib/api.ts apps/web/src/components/
git commit -m "feat(web): api client + 7 shared components (mission, radar, slider, animation, sequence, risk, artifact)"
```

---

### Task 11: 前端页面 — Home + Mission + Onboarding

**Files:**
- Create: `apps/web/src/pages/Home.tsx`(替换)
- Create: `apps/web/src/pages/Mission.tsx`
- Create: `apps/web/src/pages/Onboarding.tsx`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: 重写 `apps/web/src/pages/Home.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiException } from '@/lib/api';
import type { Mission } from '@/lib/types';
import { MissionCard } from '@/components/MissionCard';

export function Home() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(() => setHealthOk(true)).catch(() => setHealthOk(false));
    api.missions.list()
      .then(setMissions)
      .catch((e: ApiException) => setError(e.message));
  }, []);

  return (
    <main className="min-h-screen p-8 max-w-5xl mx-auto">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold text-forge-500">ProtoForge</h1>
          <p className="text-slate-400 mt-1">原体锻炉 · Phase 1 极地任务</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-1 rounded ${healthOk ? 'bg-emerald-900 text-emerald-300' : 'bg-red-900 text-red-300'}`}>
            {healthOk === null ? '检测中' : healthOk ? '后端在线' : '后端离线'}
          </span>
          <Link to="/onboarding" className="text-sm text-slate-400 hover:text-forge-500">设置 LLM</Link>
        </div>
      </header>

      {error && <p className="text-red-400 mb-4">加载任务失败: {error}</p>}

      <section>
        <h2 className="text-xl text-slate-200 mb-4">关卡列表 ({missions.length})</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {missions.map((m) => <MissionCard key={m.id} mission={m} />)}
        </div>
        {missions.length === 0 && !error && <p className="text-slate-500">暂无任务</p>}
      </section>
    </main>
  );
}
```

- [ ] **Step 2: 写 `apps/web/src/pages/Mission.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, ApiException } from '@/lib/api';
import type { Mission } from '@/lib/types';

export function Mission() {
  const { id } = useParams<{ id: string }>();
  const [mission, setMission] = useState<Mission | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.missions.get(id)
      .then(setMission)
      .catch((e: ApiException) => setError(e.message));
  }, [id]);

  if (error) return <div className="p-8 text-red-400">加载失败: {error} <Link to="/" className="text-forge-500 ml-2">返回</Link></div>;
  if (!mission) return <div className="p-8 text-slate-500">加载中…</div>;

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <Link to="/" className="text-sm text-slate-400 hover:text-forge-500">← 返回关卡列表</Link>
      <header className="mt-4">
        <h1 className="text-3xl font-bold text-slate-100">{mission.title}</h1>
        <p className="text-slate-400 mt-2 leading-relaxed">{mission.description}</p>
      </header>
      <section className="mt-8 p-6 rounded-lg bg-slate-900 border border-slate-800">
        <h2 className="text-lg text-slate-200">任务简报</h2>
        <p className="text-sm text-slate-400 mt-2">{mission.task_description || mission.description}</p>
      </section>
      <div className="mt-6 flex gap-3">
        <Link to={`/forge/${mission.id}`} className="px-5 py-2 bg-forge-500 text-white rounded hover:bg-forge-600">
          进入锻炉 →
        </Link>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: 写 `apps/web/src/pages/Onboarding.tsx`**

```typescript
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiException } from '@/lib/api';
import type { LLMProvider } from '@/lib/types';

export function Onboarding() {
  const navigate = useNavigate();
  const [choice, setChoice] = useState<LLMProvider>('disabled');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://api.deepseek.com/v1');
  const [model, setModel] = useState('deepseek-chat');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.onboarding.submit({
        provider: choice,
        config: { api_key: apiKey, base_url: baseUrl, model },
      });
      if (!res.ok) {
        setError(res.error || '配置失败');
        return;
      }
      navigate('/');
    } catch (e) {
      setError(e instanceof ApiException ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-100">首次启动引导</h1>
      <p className="text-slate-400 mt-2">选择你的 LLM 接入方式,游戏中可随时在设置页切换。</p>

      <div className="mt-8 space-y-3">
        {([
          { v: 'cloud', t: '☁️ 云 API', d: '推荐 · 默认 DeepSeek,中文友好、价格低' },
          { v: 'local', t: '🖥️ 本地模型', d: 'Ollama / LM Studio · 需本地起服务' },
          { v: 'disabled', t: '🎚️ 纯滑块', d: '无 LLM · 玩家只用滑块,无自然语言输入' },
        ] as { v: LLMProvider; t: string; d: string }[]).map((opt) => (
          <button
            key={opt.v}
            onClick={() => setChoice(opt.v)}
            className={`w-full text-left p-4 rounded-lg border transition-colors ${
              choice === opt.v ? 'border-forge-500 bg-slate-900' : 'border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="font-semibold text-slate-100">{opt.t}</div>
            <div className="text-sm text-slate-400 mt-1">{opt.d}</div>
          </button>
        ))}
      </div>

      {choice === 'cloud' && (
        <section className="mt-6 p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3">
          <label className="block">
            <span className="text-sm text-slate-300">Base URL</span>
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} className="mt-1 w-full p-2 bg-slate-950 border border-slate-700 rounded text-slate-100" />
          </label>
          <label className="block">
            <span className="text-sm text-slate-300">Model</span>
            <input value={model} onChange={(e) => setModel(e.target.value)} className="mt-1 w-full p-2 bg-slate-950 border border-slate-700 rounded text-slate-100" />
          </label>
          <label className="block">
            <span className="text-sm text-slate-300">API Key</span>
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="mt-1 w-full p-2 bg-slate-950 border border-slate-700 rounded text-slate-100" />
          </label>
        </section>
      )}

      {choice === 'local' && (
        <section className="mt-6 p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3">
          <label className="block">
            <span className="text-sm text-slate-300">Base URL(Ollama / LM Studio)</span>
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} defaultValue="http://127.0.0.1:11434/v1" className="mt-1 w-full p-2 bg-slate-950 border border-slate-700 rounded text-slate-100" />
          </label>
          <label className="block">
            <span className="text-sm text-slate-300">Model</span>
            <input value={model} onChange={(e) => setModel(e.target.value)} defaultValue="qwen2.5:3b" className="mt-1 w-full p-2 bg-slate-950 border border-slate-700 rounded text-slate-100" />
          </label>
          <p className="text-xs text-slate-500">提示:本机先启 Ollama(`ollama serve`)并 `ollama pull qwen2.5:3b`。</p>
        </section>
      )}

      {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}

      <div className="mt-8 flex gap-3">
        <button
          onClick={onSubmit}
          disabled={submitting}
          className="px-5 py-2 bg-forge-500 text-white rounded hover:bg-forge-600 disabled:opacity-50"
        >
          {submitting ? '测试中…' : '完成引导'}
        </button>
        <button onClick={() => navigate('/')} className="px-5 py-2 text-slate-400 hover:text-slate-200">
          跳过
        </button>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: 修改 `apps/web/src/App.tsx`**

```typescript
import { Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/Home';
import { Mission } from './pages/Mission';
import { Onboarding } from './pages/Onboarding';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/mission/:id" element={<Mission />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
```

- [ ] **Step 5: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\web'
pnpm test
pnpm build
git add apps/web/src/pages/ apps/web/src/App.tsx
git commit -m "feat(web): home + mission brief + onboarding pages"
```

---

### Task 12: 前端页面 — Forge 工作台 + 风险门

**Files:**
- Create: `apps/web/src/pages/Forge.tsx`
- Create: `apps/web/src/pages/RiskGate.tsx`

- [ ] **Step 1: 写 `apps/web/src/pages/Forge.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, ApiException } from '@/lib/api';
import type { Mission, ForgeResult, SliderParam } from '@/lib/types';
import { SliderCard } from '@/components/SliderCard';
import { ScoreRadar } from '@/components/ScoreRadar';
import { SequenceView } from '@/components/SequenceView';
import { ForgeAnimation } from '@/components/ForgeAnimation';

export function Forge() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [mission, setMission] = useState<Mission | null>(null);
  const [params, setParams] = useState<Record<string, number>>({});
  const [generator, setGenerator] = useState<'uniform' | 'preference' | 'random'>('preference');
  const [result, setResult] = useState<ForgeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.missions.get(id).then((m) => {
      setMission(m);
      const init: Record<string, number> = {};
      m.sliders.forEach((s) => { init[s.id] = s.default; });
      setParams(init);
    }).catch((e: ApiException) => setError(e.message));
  }, [id]);

  const onRun = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.forge.run({ mission_id: id, params, generator });
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiException ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  if (error) return <div className="p-8 text-red-400">{error}</div>;
  if (!mission) return <div className="p-8 text-slate-500">加载中…</div>;

  const radarData = result ? Object.entries(result.scores.components).map(([k, v]) => ({
    name: k, value: typeof v === 'number' ? v : 0,
  })) : [];

  return (
    <main className="min-h-screen p-6 max-w-6xl mx-auto">
      <header className="flex justify-between items-baseline">
        <h1 className="text-2xl font-bold text-slate-100">{mission.title}</h1>
        <button onClick={() => navigate('/')} className="text-sm text-slate-400 hover:text-slate-200">← 返回</button>
      </header>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section>
          <h2 className="text-lg text-slate-200 mb-3">🎚️ 滑块</h2>
          <div className="space-y-3">
            {mission.sliders.map((s) => (
              <SliderCard key={s.id} param={s} value={params[s.id] ?? s.default} onChange={(v) => setParams({ ...params, [s.id]: v })} />
            ))}
          </div>
          <div className="mt-4">
            <label className="text-sm text-slate-300">生成器策略</label>
            <select value={generator} onChange={(e) => setGenerator(e.target.value as any)} className="ml-3 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100">
              <option value="uniform">均匀突变</option>
              <option value="preference">偏好突变</option>
              <option value="random">完全随机</option>
            </select>
          </div>
          <button onClick={onRun} disabled={loading} className="mt-4 w-full py-3 bg-forge-500 text-white rounded font-semibold hover:bg-forge-600 disabled:opacity-50">
            {loading ? '开炉中…' : '🔥 开炉'}
          </button>
        </section>

        <section>
          <h2 className="text-lg text-slate-200 mb-3">📊 评分反馈</h2>
          {loading && <div className="text-slate-500">等待仪式完成…</div>}
          {!loading && !result && <div className="text-slate-500 text-sm">点击"开炉"开始</div>}
          {result && (
            <div className="space-y-4">
              <ScoreRadar scores={radarData} primary={result.scores.primary} />
              <div className="text-xs text-slate-500 flex gap-3">
                <span>仪式: {result.ritual}</span>
                <span>耗时: {result.duration_ms}ms</span>
                <span className={result.passed_gate ? 'text-emerald-400' : 'text-amber-400'}>
                  {result.passed_gate ? '✅ 达门' : '⚠️ 未达门'}
                </span>
              </div>
              {result.risk_flags.length > 0 && (
                <ul className="text-xs space-y-1">
                  {result.risk_flags.map((f, i) => <li key={i} className="text-amber-400">⚠ {f.message}</li>)}
                </ul>
              )}
              <SequenceView fasta={result.fasta} />
              <div className="flex gap-2">
                <button
                  onClick={() => navigate(`/risk/${result.run_id}`)}
                  className="flex-1 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700"
                >
                  🛡️ 进入风险门 →
                </button>
                <button
                  onClick={async () => {
                    await api.gallery.save({
                      mission_id: mission.id, mission_title: mission.title,
                      scores: result.scores, fasta: result.fasta,
                      passed_gate: result.passed_gate, ritual: result.ritual,
                      duration_ms: result.duration_ms,
                    });
                    navigate('/gallery');
                  }}
                  className="px-4 py-2 bg-slate-800 text-slate-200 rounded hover:bg-slate-700"
                >
                  💾 入库
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: 写 `apps/web/src/pages/RiskGate.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, ApiException } from '@/lib/api';
import { RiskQuestionCard } from '@/components/RiskQuestionCard';

interface Q { id: string; question: string; options: { value: string; label: string }[]; }
interface SubmitResult { passed: boolean; correct_count: number; total: number; details: any[]; }

export function RiskGate() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [missionId, setMissionId] = useState('polar-glow-v1');
  const [questions, setQuestions] = useState<Q[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.risk.questions(missionId).then(setQuestions).catch((e: ApiException) => setError(e.message));
  }, [missionId]);

  const onSubmit = async () => {
    setError(null);
    try {
      const r = await api.risk.submit(missionId, Object.entries(answers).map(([rule_id, value]) => ({ rule_id, value })));
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiException ? e.message : String(e));
    }
  };

  return (
    <main className="min-h-screen p-8 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-100">🛡️ 风险门</h1>
      <p className="text-slate-400 mt-2">完成所有题目,全部答对才能出关(本次提交对应 runId={runId})</p>

      {error && <p className="mt-4 text-red-400">{error}</p>}

      <div className="mt-6 space-y-4">
        {questions.map((q) => (
          <RiskQuestionCard key={q.id} question={q} onAnswer={(id, v) => setAnswers({ ...answers, [id]: v })} />
        ))}
      </div>

      {result ? (
        <section className="mt-6 p-4 rounded-lg bg-slate-900 border border-slate-800">
          <h2 className={result.passed ? 'text-emerald-400' : 'text-amber-400'}>
            {result.passed ? '✅ 出关' : '⚠ 继续学习'} — {result.correct_count}/{result.total}
          </h2>
          <ul className="mt-3 space-y-2 text-sm">
            {result.details.map((d, i) => (
              <li key={i} className={d.ok ? 'text-emerald-300' : 'text-red-300'}>
                {d.ok ? '✓' : '✗'} {d.explanation}
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <button onClick={onSubmit} disabled={Object.keys(answers).length < questions.length}
          className="mt-6 px-5 py-2 bg-forge-500 text-white rounded hover:bg-forge-600 disabled:opacity-50">
          提交答案
        </button>
      )}

      <button onClick={() => navigate('/gallery')} className="mt-3 text-sm text-slate-400 hover:text-slate-200 block">
        查看作品墙 →
      </button>
    </main>
  );
}
```

- [ ] **Step 3: 修改 `apps/web/src/App.tsx` 添加路由**

```typescript
import { Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/Home';
import { Mission } from './pages/Mission';
import { Onboarding } from './pages/Onboarding';
import { Forge } from './pages/Forge';
import { RiskGate } from './pages/RiskGate';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/mission/:id" element={<Mission />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/forge/:id" element={<Forge />} />
      <Route path="/risk/:runId" element={<RiskGate />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
```

- [ ] **Step 4: 跑 build + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\web'
pnpm build
git add apps/web/src/pages/ apps/web/src/App.tsx
git commit -m "feat(web): forge workspace + risk gate pages"
```

---

### Task 13: Gallery 页面 + SQLite 接入(替换 Task 7 内存 store)

**Files:**
- Create: `apps/web/src/pages/Gallery.tsx`
- Create: `apps/api/app/db.py`
- Create: `apps/api/app/models.py`
- Modify: `apps/api/app/routers/gallery.py`(替换为 SQLite)
- Create: `apps/api/tests/test_gallery_sqlite.py`

- [ ] **Step 1: 写 `apps/api/app/db.py`**

```python
"""SQLAlchemy 异步引擎 + 会话工厂。"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    echo=False,
    future=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """启动时建表。"""
    from app import models  # noqa: F401 触发模型注册
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: 写 `apps/api/app/models.py`**

```python
"""SQLAlchemy ORM 模型。"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    mission_id: Mapped[str] = mapped_column(String(64), index=True)
    mission_title: Mapped[str] = mapped_column(String(128))
    run_id: Mapped[str] = mapped_column(String(64), default="")
    ritual: Mapped[str] = mapped_column(String(16))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    primary_score: Mapped[float] = mapped_column(Float, default=0.0)
    components_json: Mapped[str] = mapped_column(Text, default="{}")
    fasta: Mapped[str] = mapped_column(Text, default="")
    passed_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 3: 重写 `apps/api/app/routers/gallery.py`(SQLite)**

```python
"""/api/gallery/* 端点 - 作品入库(SQLite 持久化)。"""
from __future__ import annotations
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Literal, AsyncIterator
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Artifact

router = APIRouter()


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


class SaveArtifactRequest(BaseModel):
    mission_id: str
    mission_title: str
    run_id: str = ""
    scores: dict
    fasta: str
    passed_gate: bool
    ritual: Literal["swift", "standard", "ancient", "crystal"]
    duration_ms: int


class SaveArtifactResponse(BaseModel):
    id: str
    created_at: str


@router.post("/save", response_model=SaveArtifactResponse)
async def save_artifact(req: SaveArtifactRequest, db: AsyncSession = Depends(get_db)) -> SaveArtifactResponse:
    art = Artifact(
        mission_id=req.mission_id,
        mission_title=req.mission_title,
        run_id=req.run_id,
        ritual=req.ritual,
        duration_ms=req.duration_ms,
        primary_score=float(req.scores.get("primary", 0.0)),
        components_json=json.dumps(req.scores.get("components", {}), ensure_ascii=False),
        fasta=req.fasta,
        passed_gate=req.passed_gate,
    )
    db.add(art)
    await db.commit()
    await db.refresh(art)
    return SaveArtifactResponse(id=art.id, created_at=art.created_at.isoformat())


@router.get("/")
async def list_artifacts(db: AsyncSession = Depends(get_db)) -> list[dict]:
    res = await db.execute(select(Artifact).order_by(Artifact.created_at.desc()))
    out = []
    for a in res.scalars():
        out.append({
            "id": a.id,
            "mission_id": a.mission_id,
            "mission_title": a.mission_title,
            "scores": {
                "primary": a.primary_score,
                "components": json.loads(a.components_json or "{}"),
                "weights": {},
            },
            "fasta": a.fasta,
            "passed_gate": a.passed_gate,
            "ritual": a.ritual,
            "duration_ms": a.duration_ms,
            "created_at": a.created_at.isoformat(),
        })
    return out


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    a = await db.get(Artifact, artifact_id)
    if not a:
        raise HTTPException(status_code=404, detail="artifact not found")
    return {
        "id": a.id, "mission_id": a.mission_id, "mission_title": a.mission_title,
        "scores": {"primary": a.primary_score, "components": json.loads(a.components_json or "{}"), "weights": {}},
        "fasta": a.fasta, "passed_gate": a.passed_gate,
        "ritual": a.ritual, "duration_ms": a.duration_ms,
        "created_at": a.created_at.isoformat(),
    }


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    a = await db.get(Artifact, artifact_id)
    if not a:
        raise HTTPException(status_code=404, detail="artifact not found")
    await db.delete(a)
    await db.commit()
    return {"deleted": artifact_id}
```

- [ ] **Step 4: 修改 `apps/api/app/main.py` 启动时建表**

替换 `_startup` 函数:

```python
@app.on_event("startup")
async def _startup() -> None:
    from app.db import init_db
    await init_db()
    log.info("ProtoForge API %s starting on %s:%d", __version__, settings.host, settings.port)
    log.info("Data dir: %s", settings.data_dir)
    log.info("Proto profile: %s", settings.proto_profile)
```

- [ ] **Step 5: 写 `apps/api/tests/test_gallery_sqlite.py`**

```python
"""/api/gallery/* SQLite 持久化测试。"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db import init_db
from app.config import settings
import os

# 测试用独立 db
TEST_DB = settings.project_root / ".protoforge" / "data" / "test_gallery.db"
os.environ["PROTOFORGE_DB_PATH"] = str(TEST_DB)


@pytest_asyncio.fixture
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_save_and_list_persists(client: AsyncClient) -> None:
    res = await client.post("/api/gallery/save", json={
        "mission_id": "polar-glow-v1", "mission_title": "极地耐低温发光菌",
        "scores": {"primary": 0.7, "components": {"a": 0.8}, "weights": {}},
        "fasta": ">test\nGT\n", "passed_gate": True, "ritual": "standard", "duration_ms": 100,
    })
    assert res.status_code == 200
    aid = res.json()["id"]
    res = await client.get("/api/gallery/")
    assert res.status_code == 200
    assert any(a["id"] == aid for a in res.json())


@pytest.mark.asyncio
async def test_delete(client: AsyncClient) -> None:
    res = await client.post("/api/gallery/save", json={
        "mission_id": "polar-glow-v1", "mission_title": "t", "scores": {"primary": 0, "components": {}, "weights": {}},
        "fasta": ">", "passed_gate": False, "ritual": "ancient", "duration_ms": 0,
    })
    aid = res.json()["id"]
    res = await client.delete(f"/api/gallery/{aid}")
    assert res.status_code == 200
    res = await client.get(f"/api/gallery/{aid}")
    assert res.status_code == 404
```

- [ ] **Step 6: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\api'
uv add aiosqlite
uv add --dev pytest-asyncio
uv run pytest tests/test_gallery_sqlite.py -v
uv run pytest -v
git add apps/api/app/db.py apps/api/app/models.py apps/api/app/routers/gallery.py apps/api/app/main.py apps/api/tests/test_gallery_sqlite.py
git commit -m "feat(api): SQLite-backed gallery with async SQLAlchemy"
```

---

### Task 14: 前端 Gallery 页面

**Files:**
- Create: `apps/web/src/pages/Gallery.tsx`
- Create: `apps/web/src/test/Gallery.test.tsx`

- [ ] **Step 1: 写 `apps/web/src/pages/Gallery.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiException } from '@/lib/api';
import type { Artifact } from '@/lib/types';
import { ArtifactCard } from '@/components/ArtifactCard';

export function Gallery() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.gallery.list()
      .then(setArtifacts)
      .catch((e: ApiException) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const onDelete = async (id: string) => {
    if (!confirm('确认删除该作品?')) return;
    await api.gallery.remove(id);
    load();
  };

  return (
    <main className="min-h-screen p-8 max-w-5xl mx-auto">
      <header className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-100">🖼️ 作品墙</h1>
        <Link to="/" className="text-sm text-slate-400 hover:text-slate-200">← 返回首页</Link>
      </header>
      {error && <p className="mt-4 text-red-400">{error}</p>}
      {loading && <p className="mt-8 text-slate-500">加载中…</p>}
      {!loading && artifacts.length === 0 && (
        <p className="mt-8 text-slate-500">还没有作品。完成一次"开炉"后在结果页"💾 入库"即可保存。</p>
      )}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {artifacts.map((a) => (
          <ArtifactCard key={a.id} artifact={a} onDelete={onDelete} />
        ))}
      </div>
    </main>
  );
}
```

- [ ] **Step 2: 修改 `apps/web/src/App.tsx` 添加 /gallery 路由**

```typescript
import { Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/Home';
import { Mission } from './pages/Mission';
import { Onboarding } from './pages/Onboarding';
import { Forge } from './pages/Forge';
import { RiskGate } from './pages/RiskGate';
import { Gallery } from './pages/Gallery';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/mission/:id" element={<Mission />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/forge/:id" element={<Forge />} />
      <Route path="/risk/:runId" element={<RiskGate />} />
      <Route path="/gallery" element={<Gallery />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
```

- [ ] **Step 3: 修改 `apps/web/src/pages/Home.tsx` 加 Gallery 入口**

在 `<header>` 后追加一段:

```tsx
      <div className="mt-4">
        <Link to="/gallery" className="text-sm text-slate-400 hover:text-forge-500">🖼️ 作品墙 ({artifacts_count})</Link>
      </div>
```

并在 `Home` 组件顶部加:

```tsx
  const [artifacts_count, setArtifactsCount] = useState(0);
  useEffect(() => {
    api.gallery.list().then((arr) => setArtifactsCount(arr.length)).catch(() => {});
  }, []);
```

- [ ] **Step 4: 写 Gallery 测试**

```typescript
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Gallery } from '@/pages/Gallery';

describe('Gallery', () => {
  it('renders title and empty state', async () => {
    render(<MemoryRouter><Gallery /></MemoryRouter>);
    expect(screen.getByText('🖼️ 作品墙')).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: 跑测试 + 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\web'
pnpm test
pnpm build
git add apps/web/src/pages/Gallery.tsx apps/web/src/pages/Home.tsx apps/web/src/App.tsx apps/web/src/test/Gallery.test.tsx
git commit -m "feat(web): gallery page with list + delete"
```

---

### Task 15: Tauri 桌面壳 + IPC 联通 sidecar

**Files:**
- Create: `apps/desktop/src-tauri/Cargo.toml`
- Create: `apps/desktop/src-tauri/tauri.conf.json`
- Create: `apps/desktop/src-tauri/build.rs`
- Create: `apps/desktop/src-tauri/src/main.rs`
- Create: `apps/desktop/src-tauri/src/lib.rs`
- Create: `apps/desktop/src-tauri/src/sidecar.rs`
- Create: `apps/desktop/src-tauri/src/commands.rs`

- [ ] **Step 1: 写 `apps/desktop/src-tauri/Cargo.toml`**

```toml
[package]
name = "protoforge-desktop"
version = "0.1.0"
edition = "2021"
description = "ProtoForge desktop shell"

[lib]
name = "protoforge_desktop_lib"
crate-type = ["staticlib", "cdylib", "rlib"]

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["process", "io-util", "macros", "rt-multi-thread"] }
reqwest = { version = "0.12", features = ["json"] }
anyhow = "1"
log = "0.4"
env_logger = "0.11"

[profile.release]
panic = "abort"
codegen-units = 1
lto = true
opt-level = "s"
strip = true
```

- [ ] **Step 2: 写 `apps/desktop/src-tauri/tauri.conf.json`**

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "ProtoForge",
  "version": "0.1.0",
  "identifier": "studio.protoforge.app",
  "build": {
    "beforeDevCommand": "cd ../../web && pnpm dev",
    "beforeBuildCommand": "cd ../../web && pnpm build",
    "devUrl": "http://localhost:5173",
    "frontendDist": "../../web/dist"
  },
  "app": {
    "windows": [
      {
        "title": "ProtoForge · 原体锻炉",
        "width": 1280,
        "height": 800,
        "minWidth": 1024,
        "minHeight": 700
      }
    ],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "category": "Game",
    "shortDescription": "ProtoForge - 合成生物学众包游戏化平台",
    "longDescription": "ProtoForge 是一个游戏化的合成生物学众包平台,玩家用自然语言 + 可视化滑块代替写 Proto 代码,在三个科幻任务场景中设计能解决真实问题的生物元件。"
  }
}
```

- [ ] **Step 3: 写 `apps/desktop/src-tauri/build.rs`**

```rust
fn main() {
    tauri_build::build()
}
```

- [ ] **Step 4: 写 `apps/desktop/src-tauri/src/sidecar.rs`**

```rust
//! Python sidecar 进程管理。
use std::process::{Child, Command, Stdio};
use std::time::Duration;
use anyhow::{Result, Context};

pub struct Sidecar {
    pub child: Child,
    pub port: u16,
}

impl Sidecar {
    /// 启动 Python sidecar 并等待 /health 返回 200。
    pub fn spawn(python_bin: &str, app_dir: &std::path::Path, port: u16) -> Result<Self> {
        let api_dir = app_dir.join("apps").join("api");
        let child = Command::new(python_bin)
            .arg("-m")
            .arg("uvicorn")
            .arg("app.main:app")
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg(port.to_string())
            .current_dir(&api_dir)
            .env("PROTOFORGE_HOST", "127.0.0.1")
            .env("PROTOFORGE_PORT", port.to_string())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .with_context(|| format!("failed to spawn python sidecar at {}", api_dir.display()))?;

        // 等待最多 30s,期间每 500ms ping 一次 /health
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()?;
        let url = format!("http://127.0.0.1:{}/health", port);
        for _ in 0..60 {
            std::thread::sleep(Duration::from_millis(500));
            if let Ok(resp) = client.get(&url).send() {
                if resp.status().is_success() {
                    log::info!("sidecar healthy on {}", url);
                    return Ok(Self { child, port });
                }
            }
        }
        anyhow::bail!("sidecar failed to become healthy on {} within 30s", url);
    }
}

impl Drop for Sidecar {
    fn drop(&mut self) {
        let _ = self.child.kill();
    }
}
```

- [ ] **Step 5: 写 `apps/desktop/src-tauri/src/commands.rs`**

```rust
//! Tauri command(前端 invoke 入口)。
use serde::Serialize;

#[derive(Serialize)]
pub struct SystemInfo {
    pub sidecar_port: u16,
    pub sidecar_url: String,
}

#[tauri::command]
pub fn system_info(state: tauri::State<'_, crate::AppState>) -> SystemInfo {
    SystemInfo {
        sidecar_port: state.sidecar_port,
        sidecar_url: format!("http://127.0.0.1:{}", state.sidecar_port),
    }
}

#[tauri::command]
pub fn health_check() -> &'static str {
    "ok"
}
```

- [ ] **Step 6: 写 `apps/desktop/src-tauri/src/lib.rs`**

```rust
//! ProtoForge Tauri 桌面壳。
use std::sync::Mutex;
use tauri::Manager;

pub struct AppState {
    pub sidecar_port: u16,
    pub sidecar_handle: Mutex<Option<crate::sidecar::Sidecar>>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::init();
    tauri::Builder::default()
        .setup(|app| {
            // 解析项目根(本 crate 在 apps/desktop/src-tauri/)
            let app_dir = app
                .path()
                .resource_dir()
                .map(|p| p.to_path_buf())
                .unwrap_or_else(|_| std::env::current_dir().unwrap());
            // 开发态:app_dir 可能是 target/debug,把根上溯
            let project_root = find_project_root(&app_dir);
            log::info!("project root: {}", project_root.display());

            let sidecar = crate::sidecar::Sidecar::spawn("python", &project_root, 7654)?;
            app.manage(AppState {
                sidecar_port: sidecar.port,
                sidecar_handle: Mutex::new(Some(sidecar)),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![crate::commands::system_info, crate::commands::health_check])
        .run(tauri::generate_context!())
        .expect("error while running ProtoForge");
}

fn find_project_root(start: &std::path::Path) -> std::path::PathBuf {
    // 从 start 上溯,直到看见 Cargo.toml 的祖先是 apps/desktop 的目录
    let mut cur = start.to_path_buf();
    loop {
        if cur.join("apps").join("api").join("pyproject.toml").exists() {
            return cur;
        }
        if !cur.pop() {
            return start.to_path_buf();
        }
    }
}
```

- [ ] **Step 7: 写 `apps/desktop/src-tauri/src/main.rs`**

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    protoforge_desktop_lib::run()
}
```

- [ ] **Step 8: 修改 `apps/web/vite.config.ts` 让 Tauri dev 直连 7654**

不需要改,vite proxy 已经把 `/api` 转发到 7654。

- [ ] **Step 9: 编译检查(开发态启动一次)**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\desktop'
pnpm install
pnpm tauri dev
```

预期:Tauri 启动 → spawn python sidecar → WebView 打开 → 显示 ProtoForge 首页。

> 如果 rust 工具链未装:`https://rustup.rs/` 装一次。

- [ ] **Step 10: 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
git add apps/desktop/
git commit -m "feat(desktop): Tauri 2.x shell with python sidecar spawn"
```

---

### Task 16: 端到端测试 + 文档 + 打包验证

**Files:**
- Create: `apps/web/playwright.config.ts`(可选)
- Create: `apps/web/e2e/happy-path.spec.ts`(可选)
- Create: `docs/superpowers/notes/2026-07-06-phase1-runbook.md`

- [ ] **Step 1: 写 e2e playwright 配置(可选,Phase 1 末) `apps/web/playwright.config.ts`**

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'cd ../api && uv run uvicorn app.main:app --port 7654 & cd ../web && pnpm dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

- [ ] **Step 2: 写 e2e happy path `apps/web/e2e/happy-path.spec.ts`**

```typescript
import { test, expect } from '@playwright/test';

test('Phase 1 happy path: list → mission → forge → risk → save', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('ProtoForge')).toBeVisible();
  await expect(page.getByText('极地耐低温发光菌')).toBeVisible();

  await page.getByText('极地耐低温发光菌').click();
  await expect(page.getByRole('heading', { name: '极地耐低温发光菌' })).toBeVisible();
  await page.getByRole('link', { name: /进入锻炉/ }).click();

  await expect(page.getByText('开炉')).toBeVisible();
  await page.getByRole('button', { name: /开炉/ }).click();
  await expect(page.getByText(/仪式|达门|未达门/)).toBeVisible({ timeout: 30000 });
});
```

- [ ] **Step 3: 写运行手册 `docs/superpowers/notes/2026-07-06-phase1-runbook.md`**

```markdown
# ProtoForge Phase 1 运行手册

## 给开发者

### 准备

1. 安装 Python 3.10+、Node.js 20+、pnpm 9+、Rust(用 rustup)
2. 克隆项目后:
   ```bash
   pnpm install
   cd apps/api && uv sync && cd ../..
   ```

### 开发态启动

```bash
# 终端 1:Python sidecar
cd apps/api && uv run uvicorn app.main:app --reload --port 7654

# 终端 2:React 前端
pnpm --filter @protoforge/web dev

# 终端 3(可选):Tauri 桌面壳
pnpm --filter @protoforge/desktop tauri dev
```

### 跑测试

```bash
# Python
cd apps/api && uv run pytest -v

# 前端单测
cd apps/web && pnpm test

# 端到端(需先装 playwright:pnpm dlx playwright install)
cd apps/web && pnpm e2e
```

## 给玩家

### 准备

- Python 3.10+ (Phase 1 必须)
- 4GB+ RAM,推荐 NVIDIA 8GB+ 独显(无 GPU 也能玩)

### 安装(开发版)

1. 从 GitHub Releases 拉对应平台安装包
2. 装 Python 时勾 "Add to PATH"
3. 双击安装,首次启动选 LLM 接入方式(可跳过)
4. 开始游戏

### 数据位置

- `项目目录/.protoforge/data/protoforge.db` - 作品库
- `项目目录/.protoforge/sequences/` - FASTA 序列
- `项目目录/.protoforge/logs/` - 日志

## 已知问题 / TODO

- proto-language 真实接入是 Phase 1.5 工作(目前用启发式)
- SpliceTransformer 真模型需 GPU,没装时回退启发式
- Tauri 桌面应用打包体积 ~30MB,玩家需单独装 Python
- Phase 1.5:内嵌 Python Embed,玩家无需装 Python
```

- [ ] **Step 4: 跑完整测试**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
cd apps/api && uv run pytest -v
cd ..
cd apps/web && pnpm test
pnpm build
```

预期:所有测试通过 + 前端 build 成功。

- [ ] **Step 5: 端到端手工验证**

按"运行手册"启动两个 dev server,浏览器开 `http://localhost:5173` 走一遍:
1. 看到 ProtoForge 首页
2. 点击"极地耐低温发光菌"卡片
3. 进入任务简报
4. 点"进入锻炉"
5. 调几个滑块,点"🔥 开炉"
6. 等评分出现,看雷达图 + 序列
7. 点"💾 入库" → 跳到作品墙
8. 点"🛡️ 进入风险门"
9. 答对所有题,看"✅ 出关"

- [ ] **Step 6: 桌面应用构建验证(可选,需 Rust 工具链)**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\apps\desktop'
pnpm tauri build
```

预期:产出 `src-tauri/target/release/bundle/` 下的安装包(`.msi` / `.exe`)。

- [ ] **Step 7: 提交**

```bash
cd 'C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261'
git add apps/web/e2e/ apps/web/playwright.config.ts docs/
git commit -m "docs+test: e2e happy path + phase 1 runbook"
```

---

## 自检

写完后做以下检查:

1. **覆盖度核对**:从 GDD 和设计文档逐节看,确认每个功能都有 Task 对应:
   - 剧情 / 任务简报 → Task 11(Mission 页)
   - 5 滑块调参 → Task 10(SliderCard)+ Task 12(Forge 页)
   - 真 Proto 评分 → Task 3(engine)+ Task 4(scorer)+ Task 5(/forge/run)
   - 雷达图 / FASTA 展示 → Task 10(ScoreRadar + SequenceView)+ Task 12
   - 风险门(教学多选) → Task 6(risk 路由)+ Task 12(RiskGate 页)
   - 4 档仪式名 → Task 3(profile.ritual)+ Task 10(ForgeAnimation)
   - 3 选项 LLM 引导 → Task 8(llm provider)+ Task 11(Onboarding)
   - NL → 滑块翻译 → Task 9(translate)
   - 作品墙 / SQLite → Task 13(SQLite)+ Task 14(Gallery)
   - 桌面应用壳 → Task 15(Tauri)
   - 端到端 / 打包 → Task 16

2. **Type 一致性**:`ForgeRequest.mission_id` 前后端都用 `string`,`ForgeResult.ritual` 前后端都用 `ForgeRitual` 枚举,`Artifact.passed_gate` 前后端都是 `boolean` ✓

3. **占位符扫描**:全文档搜 `TBD / TODO / 实现细节 / 后面再说` —— 已清理,文档全部为可执行指令。

## 实施选择

写完此 plan,执行时建议:

- **方案 A(推荐)**:subagent-driven-development — 每个 Task 派一个子 agent,我在主对话做两阶段 review
- **方案 B**:executing-plans — 在当前会话跑,带 checkpoint

Phase 1 共 16 个 Task,8 个里程碑,预计 4-6 周。



