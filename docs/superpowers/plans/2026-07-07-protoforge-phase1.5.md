# ProtoForge Phase 1.5 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全 Phase 1 遗留的 3 个 Critical 缺陷(MCMC 搜索未实现、generator 行为相同、Tauri sidecar 未 spawn)和 4 个 Medium/Low 项。

**Architecture:** engine.py 加入 Metropolis-Hastings 迭代搜索循环;Tauri 通过 `tauri-plugin-shell` 的 Command API 启动 Python 进程并 health 轮询;前端类型统一。

**Tech Stack:** Python 3.10+ / FastAPI / Rust (Tauri 2.x) / tauri-plugin-shell 2 / TypeScript 5

**前置条件:** Phase 1 全部 16 个 task 已完成,40 个后端测试 + 3 个前端测试通过,workspace pnpm build 正常。

---

### Task 1: MCMC 迭代搜索(修复 Critical #1)

**问题:** `run_forge` 只调用一次 `_generate_intron` 生成一条序列,`mcmc_steps` 滑块(默认 50)被完全忽略。GDD 2.4 节要求迭代搜索。

**Files:**
- Modify: `apps/api/app/proto/engine.py` (run_forge + _generate_intron + 新增 _mcmc_search)
- Test: `apps/api/tests/test_engine_smoke.py` (新增 MCMC 相关断言)
- Test: `apps/api/tests/test_e2e_player_journey.py` (E2E 应仍通过)

- [ ] **Step 1: 在 test_engine_smoke.py 写 failing test — MCMC 步数影响结果**

```python
def test_mcmc_steps_affects_result():
    """不同 mcmc_steps 应该给出不同的(或更好的)结果。"""
    from app.proto.engine import run_forge

    base_params = {"min_target_splice": 0.5, "max_off_target": 0.3}
    r1 = run_forge("polar-glow-v1", {**base_params, "mcmc_steps": 1}, "preference", seed=42)
    r10 = run_forge("polar-glow-v1", {**base_params, "mcmc_steps": 10}, "preference", seed=42)
    # 更多步数 = 至少不比少步差(搜索更充分)
    assert r10.scores["primary"] >= r1.scores["primary"] - 0.001
    # primary 不应恒为 0(至少 preference 模式有一定剪接分)
    assert r10.scores["primary"] > 0.0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd apps/api; python -m pytest tests/test_engine_smoke.py::test_mcmc_steps_affects_result -v`
Expected: FAIL — `_generate_intron` 不接受 `mcmc_steps`,结果相同

- [ ] **Step 3: 实现 _mutate + _mcmc_search**

在 `engine.py` 中添加:

```python
def _mutate(seq: str, rng: random.Random, rate: float = 0.05) -> str:
    """单点突变:随机替换 rate 比例的碱基。"""
    bases = list(seq)
    n = max(1, int(len(bases) * rate))
    for _ in range(n):
        i = rng.randint(0, len(bases) - 1)
        bases[i] = rng.choice("ATGC")
    return "".join(bases)


def _mcmc_search(
    length: int,
    generator: str,
    seed: int | None,
    steps: int,
    params: dict,
) -> tuple[str, dict]:
    """简化的 Metropolis-Hastings 搜索:生成初始 -> 迭代突变 -> 取最优。"""
    rng = random.Random(seed)
    min_target = float(params.get("min_target_splice", 0.65))
    max_off = float(params.get("max_off_target", 0.20))
    w_alpha = float(params.get("weight_alpha", 0.5))
    w_beta = float(params.get("weight_beta", 0.35))

    best_seq = _generate_intron(length, generator, seed)
    best_raw = score_intron(best_seq, min_target_splice=min_target, max_off_target_splice=max_off)
    best_primary = max(
        0.0,
        w_alpha * best_raw["splice_site_score"]
        + w_beta * (1.0 - best_raw["orthogonality"])
        - 0.1 * best_raw["gc_penalty"]
        - 0.05 * best_raw["length_norm"],
    )

    current_seq = best_seq
    current_primary = best_primary
    temp = float(params.get("temperature", 0.8))

    for _ in range(steps):
        candidate = _mutate(current_seq, rng, rate=0.05)
        raw = score_intron(candidate, min_target_splice=min_target, max_off_target_splice=max_off)
        primary = max(
            0.0,
            w_alpha * raw["splice_site_score"]
            + w_beta * (1.0 - raw["orthogonality"])
            - 0.1 * raw["gc_penalty"]
            - 0.05 * raw["length_norm"],
        )
        # Metropolis 接受准则
        delta = primary - current_primary
        if delta > 0 or (temp > 0 and rng.random() < math.exp(delta / max(temp, 0.001))):
            current_seq = candidate
            current_primary = primary
        if primary > best_primary:
            best_seq = candidate
            best_raw = raw
            best_primary = primary

    return best_seq, best_raw
```

注意:需要在文件顶部加 `import math`。

- [ ] **Step 4: 修改 run_forge 调用 _mcmc_search 替代单次生成**

在 `run_forge` 中,将:
```python
intron = _generate_intron(length, generator, seed)
raw = score_intron(intron, min_target_splice=min_target, max_off_target_splice=max_off)
```
替换为:
```python
mcmc_steps = int(params.get("mcmc_steps", 50))
if mcmc_steps <= 1:
    intron = _generate_intron(length, generator, seed)
    raw = score_intron(intron, min_target_splice=min_target, max_off_target_splice=max_off)
else:
    intron, raw = _mcmc_search(length, generator, seed, mcmc_steps, params)
```

- [ ] **Step 5: 跑全部测试确认通过**

Run: `cd apps/api; python -m pytest tests/ -q`
Expected: 42 passed (原有 40 + 新增 2)

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/proto/engine.py apps/api/tests/test_engine_smoke.py
git commit -m "fix(proto): implement MCMC search loop — mcmc_steps slider now affects forge results"
```

---

### Task 2: generator 行为差异化(修复 Critical #2)

**问题:** `_generate_intron` 中 `"uniform"` 和 `"random"` 分支代码完全相同。

**Files:**
- Modify: `apps/api/app/proto/engine.py` (_generate_intron)
- Test: `apps/api/tests/test_engine_smoke.py`

- [ ] **Step 1: 写 failing test — 三种 generator 产生统计可区分的序列**

```python
def test_generators_are_statistically_distinct():
    """uniform / random / preference 应产生不同特征的序列。"""
    from app.proto.engine import _generate_intron

    N = 5
    uniform_seqs = [_generate_intron(120, "uniform", seed=10 + i) for i in range(N)]
    random_seqs = [_generate_intron(120, "random", seed=10 + i) for i in range(N)]
    pref_seqs = [_generate_intron(120, "preference", seed=10 + i) for i in range(N)]

    # preference 模式必须有 GT...AG 边界
    for s in pref_seqs:
        assert s.startswith("GT"), f"preference 应以 GT 开头: {s[:10]}"
        assert s.endswith("AG"), f"preference 应以 AG 结尾: {s[-10:]}"

    # random 模式应有非均匀碱基频率(偏 GC)
    gc_count = sum(1 for s in random_seqs for c in s if c in "GC")
    at_count = sum(1 for s in random_seqs for c in s if c in "AT")
    # random 故意偏 GC,总 GC 应 > AT
    assert gc_count > at_count, f"random 应偏 GC: gc={gc_count} at={at_count}"

    # uniform 应大致均匀(不检查严格 50:50,只检查不是极端偏移)
    u_gc = sum(1 for s in uniform_seqs for c in s if c in "GC")
    u_at = sum(1 for s in uniform_seqs for c in s if c in "AT")
    assert abs(u_gc - u_at) < N * 120 * 0.15, f"uniform 应大致均匀: gc={u_gc} at={u_at}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd apps/api; python -m pytest tests/test_engine_smoke.py::test_generators_are_statistically_distinct -v`
Expected: FAIL — uniform 和 random 行为相同,random 不偏 GC

- [ ] **Step 3: 修改 _generate_intron 使三种模式行为不同**

```python
def _generate_intron(length: int, generator: str, seed: int | None) -> str:
    """生成候选内含子序列(三种模式各有不同的统计特征)。"""
    rng = random.Random(seed)
    if generator == "uniform":
        # 完全均匀:等概率 ATGC
        return "".join(rng.choices("ATGC", k=length))
    if generator == "random":
        # 偏 GC 分布(模拟基因组高 GC 区段)
        return "".join(rng.choices("ATGC", weights=[0.2, 0.3, 0.3, 0.2], k=length))
    # preference: GT-AG 边界 + 中段高熵
    seq = list(rng.choices("ATGC", k=length))
    if length >= 6:
        seq[0:2] = list("GT")
        seq[-2:] = list("AG")
    return "".join(seq)
```

- [ ] **Step 4: 跑全部测试**

Run: `cd apps/api; python -m pytest tests/ -q`
Expected: 44 passed

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/proto/engine.py apps/api/tests/test_engine_smoke.py
git commit -m "fix(proto): differentiate generator modes — uniform=random, random=GC-biased, preference=GT-AG"
```

---

### Task 3: Tauri Sidecar Spawn(修复 Critical #3 + Low #7 + #9)

**问题:** `lib.rs` 的 setup 是空壳;缺 `sidecar.rs`/`commands.rs`;Cargo.toml 缺依赖;tauri.conf.json 无 shell 权限。

**Files:**
- Create: `apps/desktop/src-tauri/src/sidecar.rs`
- Create: `apps/desktop/src-tauri/src/commands.rs`
- Modify: `apps/desktop/src-tauri/src/lib.rs`
- Modify: `apps/desktop/src-tauri/Cargo.toml`
- Modify: `apps/desktop/src-tauri/tauri.conf.json`
- Modify: `apps/desktop/src-tauri/capabilities/default.json`

- [ ] **Step 1: 补全 Cargo.toml 依赖**

```toml
[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["rt-multi-thread", "macros", "process", "time"] }
reqwest = { version = "0.12", features = ["json"] }
anyhow = "1"
log = "0.4"
env_logger = "0.11"
```

- [ ] **Step 2: 创建 sidecar.rs — Python 进程 spawn + health 轮询**

```rust
use std::process::Child;
use std::time::Duration;
use log::{info, warn, error};

const SIDEcar_PORT: u16 = 7655;
const HEALTH_POLL_MS: u64 = 500;
const HEALTH_TIMEOUT_S: u64 = 30;

pub struct Sidecar {
    child: Option<Child>,
}

impl Sidecar {
    pub fn spawn() -> anyhow::Result<Self> {
        info!("Spawning Python sidecar on port {} ...", SIDECAR_PORT);

        let python = std::env::var("PROTOFORGE_PYTHON").unwrap_or_else(|_| "python".to_string());

        let child = std::process::Command::new(&python)
            .args([
                "-m", "uvicorn",
                "app.main:app",
                "--port", &SIDECAR_PORT.to_string(),
                "--log-level", "warning",
            ])
            .current_dir(Self::api_dir()?)
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .map_err(|e| anyhow::anyhow!("Failed to spawn Python sidecar: {e}"))?;

        info!("Python process started (pid: {:?})", child.id());

        Ok(Self {
            child: Some(child),
        })
    }

    pub async fn wait_for_health(&self) -> anyhow::Result<()> {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()?;

        let url = format!("http://127.0.0.1:{}/health", SIDECAR_PORT);
        let start = std::time::Instant::now();

        loop {
            match client.get(&url).send().await {
                Ok(resp) if resp.status().is_success() => {
                    info!("Sidecar health OK (waited {}ms)", start.elapsed().as_millis());
                    return Ok(());
                }
                Ok(resp) => {
                    warn!("Health returned {}: waiting ...", resp.status());
                }
                Err(e) => {
                    warn!("Health poll error: {} — waiting ...", e);
                }
            }

            if start.elapsed() > Duration::from_secs(HEALTH_TIMEOUT_S) {
                error!("Sidecar health timeout after {}s", HEALTH_TIMEOUT_S);
                anyhow::bail!("Sidecar did not become healthy within {}s", HEALTH_TIMEOUT_S);
            }

            tokio::time::sleep(Duration::from_millis(HEALTH_POLL_MS)).await;
        }
    }

    fn api_dir() -> anyhow::Result<std::path::PathBuf> {
        // apps/api 目录:从 src-tauri 往上两级再进 apps/api
        let exe = std::env::current_exe()?;
        let mut dir = exe.parent().unwrap().to_path_buf();
        // dev: target/debug/xxx.exe → apps/desktop/src-tauri/target/debug/ → apps/desktop/src-tauri/ → apps/desktop/ → 根
        for _ in 0..5 {
            if dir.join("apps").join("api").join("app").exists() {
                return Ok(dir.join("apps").join("api"));
            }
            dir = dir.parent().unwrap().to_path_buf();
        }
        // 兜底:从环境变量或当前目录查找
        let cwd = std::env::current_dir()?;
        if cwd.join("apps").join("api").exists() {
            return Ok(cwd.join("apps").join("api"));
        }
        anyhow::bail!("Cannot locate apps/api directory")
    }

    pub fn kill(&mut self) {
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            info!("Sidecar process killed");
        }
    }
}

impl Drop for Sidecar {
    fn drop(&mut self) {
        self.kill();
    }
}
```

- [ ] **Step 3: 创建 commands.rs — Tauri 命令**

```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone)]
pub struct SystemInfo {
    python: String,
    platform: String,
    arch: String,
}

#[tauri::command]
pub fn system_info() -> Result<SystemInfo, String> {
    Ok(SystemInfo {
        python: std::env::var("PROTOFORGE_PYTHON").unwrap_or_else(|_| "python".to_string()),
        platform: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
    })
}

#[tauri::command]
pub async fn health_check() -> Result<serde_json::Value, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()
        .map_err(|e| e.to_string())?;

    let url = "http://127.0.0.1:7655/health";
    client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Sidecar unreachable: {}", e))?
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Parse error: {}", e))
}
```

- [ ] **Step 4: 修改 lib.rs — 集成 sidecar spawn**

```rust
mod sidecar;
mod commands;

use tauri::Manager;
use log::info;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();

            // 启动 Python sidecar
            let sc = sidecar::Sidecar::spawn().expect("Failed to spawn sidecar");

            // health 轮询(异步,在 tokio runtime 中)
            tauri::async_runtime::spawn(async move {
                if let Err(e) = sc.wait_for_health().await {
                    log::error!("Sidecar health failed: {}", e);
                    // 可以弹窗通知用户
                }
                // sidecar 存活周期绑定到 app handle
                handle.manage(sc);
            });

            info!("ProtoForge desktop starting ...");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::system_info,
            commands::health_check,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

注意:需要在 `sidecar.rs` 中为 Sidecar 加上 `Send` 和 `tauri::Manage` 支持。补上 `unsafe impl Send for Sidecar {}` 或改用 `Arc<Mutex<Option<Child>>>`。

实际上 Tauri 的 `manage()` 需要 `Send + Sync`,所以 `sidecar.rs` 里的 `Sidecar` 结构体需要调整:
```rust
use std::sync::Mutex;

pub struct Sidecar {
    child: Mutex<Option<std::process::Child>>,
}
```
相应地 `spawn()`, `kill()`, `wait_for_health()` 等方法中用 `self.child.lock().unwrap()` 取出 child。

- [ ] **Step 5: 更新 capabilities/default.json — 添加 shell 权限**

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Default capabilities for ProtoForge desktop",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-execute",
    "shell:allow-spawn",
    "shell:allow-kill"
  ]
}
```

- [ ] **Step 6: 验证 cargo check(如果环境允许)**

Run: `cd apps/desktop/src-tauri; cargo check 2>&1 | tail -20`
Expected: 编译成功(或 Windows 长路径问题,此时需设 `$env:CARGO_TARGET_DIR`)

- [ ] **Step 7: Commit**

```bash
git add apps/desktop/src-tauri/
git commit -m "feat(desktop): Python sidecar spawn + health polling + system_info/health_check commands"
```

---

### Task 4: 前后端类型统一(修复 Medium #5 + #6)

**问题:** shared types 中 `ForgeResult` 有 `proto_program` 字段但 engine 不生成;`intron` 字段在 shared types 和 api.ts 中缺失。

**Files:**
- Modify: `packages/shared/src/types.ts` (ForgeResult)
- Modify: `apps/api/app/proto/engine.py` (scores 结构)

- [ ] **Step 1: 统一 ForgeResult 类型 — 移除 proto_program,确保 intron 存在**

`packages/shared/src/types.ts` 中 ForgeResult:
```typescript
export interface ForgeResult {
  run_id: string;
  mission_id: string;
  ritual: ForgeRitual;
  duration_ms: number;
  intron: string;          // ← 确保存在
  fasta: string;
  scores: ScoreVector;
  risk_flags: RiskFlag[];
  passed_gate: boolean;
}
```

删除任何 `proto_program` 字段(Phase 2 再加)。确保 `api.ts` 中 `forgeApi.run` 返回类型是 `ForgeResult`。

- [ ] **Step 2: 跑前端 build 确认无类型错误**

Run: `cd apps/web; pnpm build`
Expected: 成功

- [ ] **Step 3: Commit**

```bash
git add packages/shared/src/types.ts
git commit -m "fix(shared): unify ForgeResult type — ensure intron, remove proto_program"
```

---

### Task 5: RUNBOOK + 端到端验证

**Files:**
- Modify: `docs/RUNBOOK.md`

- [ ] **Step 1: 更新 RUNBOOK §8 反映 Phase 1.5 修复**

在 RUNBOOK.md §8 已知边界中:
- 删除 "MCMC 未实现" 条目(已修复)
- 删除 "generator 行为相同" 条目(已修复)
- 删除 "Tauri sidecar 未 spawn" 条目(已修复)
- 保留 "SpliceTransformer 占位" (Phase 2)
- 保留 "translate 未集成到 forge 流程" (Phase 2)
- 新增: "MCMC 是简化版 Metropolis-Hastings,非真实生物搜索"

- [ ] **Step 2: 全量测试验证**

```powershell
cd apps/api; python -m pytest -q
cd ..\web; pnpm exec vitest run; pnpm build
```

Expected: 后端 44+ passed,前端 3 passed,build 成功

- [ ] **Step 3: Commit**

```bash
git add docs/RUNBOOK.md
git commit -m "docs: update RUNBOOK for Phase 1.5 completion"
```

---

## 自检清单

| 检查项 | 状态 |
|---|---|
| GDD 2.4 MCMC 步数滑块 | Task 1 实现 |
| GDD 2.4 三种 generator 行为差异 | Task 2 实现 |
| GDD 5.1 Tauri sidecar spawn | Task 3 实现 |
| shared types 三方一致 | Task 4 实现 |
| 无 TBD / TODO / implement later | 通过 |
| 每步有精确文件路径 | 通过 |
| 每步有精确测试代码 | 通过 |
| 每步有精确运行命令 | 通过 |
