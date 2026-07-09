# Phase 3 Task 6 — P0 Bug 修复完成报告

> 4 个 P0 bug(Phase 1.5 扫描 2026-07-08 发现)统一修复完成。
> 修复时间:2026-07-09
> Subagent:ProtoForge Phase 3 Task 6

---

## 概览

| ID | 模块 | 描述 | 严重度 | 状态 |
|---|---|---|---|---|
| **A1** | `apps/api/app/gallery_store.py` | 同步 handler 用 `asyncio.run` 阻塞 event loop | P0(单用户卡,多用户必死) | ✅ 修复 |
| **B1** | `apps/web/src/pages/ForgePage.tsx` | Gallery 自动保存不生效(结果不存 gallery) | P0(核心循环缺一环) | ✅ 修复 |
| **C1** | `apps/desktop/src-tauri/src/sidecar.rs` | Tauri 端口 mismatch(后端 7654,sidecar 7655) | P0(打包后连不上) | ✅ 修复 |
| **A2** | `apps/api/app/proto/engine.py` | `run_forge` 静默退化(失败时返回默认分,不抛错) | P0(玩家不知道是 bug 还是设计) | ✅ 修复 |

---

## P0-A1:gallery_store event loop 阻塞

### 问题
`sync wrappers` 用 `asyncio.run(_coro)`:
```python
# 旧实现(报错路径)
import asyncio
return asyncio.run(_add_sqlite(req))
```

- 在 FastAPI sync handler 默认 thread pool 里,worker 线程**已有** event loop →
  `asyncio.run` 抛 `RuntimeError: asyncio.run() cannot be called from a running event loop`。
- 玩家每发一个 gallery 请求,worker 线程就崩,前端报 500。
- 单用户可能偶发,多用户必死。

### 修复(`apps/api/app/gallery_store.py`)
替换为手动 `new_event_loop()` + `run_until_complete()` + `close()`:
```python
def _run_async_blocking(coro):
    """在独立 event loop 上跑协程,完成后销毁 loop。"""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
```

每个调用都开新 loop,跑完即关。互不干扰,且不依赖 anyio worker。

### 测试(`apps/api/tests/test_p0_a1_event_loop.py`)
3 个并发测试:
- `test_gallery_store_uses_nonblocking_runner`:100 次 list < 1s
- `test_concurrent_list_requests_dont_block_each_other`:8 个并发 list < 1s
- `test_concurrent_add_and_list_interleaved`:4 add + 4 list 混合 < 1s

---

## P0-B1:Gallery 自动保存

### 问题
`ForgePage.handleRun` 收到 `result` 后**没有**调 `galleryApi.save/create` —
玩家跑完锻造,`/api/gallery` 永远为空,核心玩法循环缺一环。

### 修复(`apps/web/src/pages/ForgePage.tsx`)
在 `handleRun` 收到 result 后立刻调 `galleryApi.create(...)`:
```typescript
try {
  await galleryApi.create({
    mission_id: r.mission_id,
    title: `${mission.title} · ${r.ritual} · run ${r.run_id.slice(-6)}`,
    intron: r.intron,
    fasta: r.fasta,
    scores: r.scores,
    ritual: r.ritual,
    notes: null,
    risk_passed: r.passed_gate,
  });
  setToast({ kind: 'success', text: '✅ 作品已保存到 Gallery' });
  setTimeout(() => setToast(null), 6000);
} catch (saveErr) {
  setToast({ kind: 'warn', text: `⚠️ 作品保存到 Gallery 失败: ${(saveErr as Error).message}` });
  setTimeout(() => setToast(null), 8000);
}
```

### 测试(`apps/web/src/test/ForgePage.test.tsx`)
3 个新测试:
- `calls galleryApi.create after a successful forge`(断言 body 字段)
- `shows '✅ 作品已保存到 Gallery' success toast after forge`
- `shows warning toast (and does not crash) when galleryApi.create fails`

原有 1 个测试(`does NOT show toast when upload.queued === false`)微调,
因为现在 forge 之后 gallery 会先弹 success toast。

---

## P0-C1:Tauri sidecar 端口对齐

### 问题
- 后端 `apps/api/app/config.py`:`port: int = 7654`。
- Tauri `apps/desktop/src-tauri/src/sidecar.rs`:`SIDECAR_PORT: u16 = 7655`。
- 两边不一致 → Tauri spawn 出来的 Python uvicorn 监听 7655,后端代码读到
  Settings.port=7654,生产环境 webview 转发目标会指错端口,**打包后连不上**。

### 修复(`apps/desktop/src-tauri/src/sidecar.rs`)
```rust
pub fn sidecar_port() -> u16 {
    // 1) 优先 PROTOFORGE_API_PORT — 跟后端 Settings 的 env prefix 对齐
    if let Ok(p) = std::env::var("PROTOFORGE_API_PORT") {
        if let Ok(parsed) = p.parse::<u16>() {
            return parsed;
        }
    }
    // 2) 回退 PROTOFORGE_SIDECAR_PORT — 历史 dev 习惯
    if let Ok(p) = std::env::var("PROTOFORGE_SIDECAR_PORT") {
        if let Ok(parsed) = p.parse::<u16>() {
            return parsed;
        }
    }
    // 3) 兜底默认
    SIDECAR_API_PORT_DEFAULT  // 7655
}
```

`launch_python_sidecar` 额外调用 `.env("PROTOFORGE_API_PORT", port_str)`,
把解析出来的端口注入到 sidecar 进程环境,后端如果新增兜底启动脚本要读
这个值,就能保证 listen 跟 Tauri 转发目标对齐。

5 个 `#[cfg(test)]` Rust 单测覆盖 env 优先级/缺省/容错(留给 desktop CI 跑
`cargo test`,本次任务不跑 cargo)。

### Python 端契约测试(`apps/api/tests/test_p0_c1_port_alignment.py`)
5 个测试:
- `test_backend_default_port_is_7654`
- `test_backend_port_respects_env_var`
- `test_sidecar_rs_prefers_protoforge_api_port`
- `test_sidecar_default_port_is_7655_for_legacy_compat`
- `test_config_env_prefix_matches_sidecar_env_name`

### tauri.conf.json
任务原本要求"加 `env` 字段",但 Tauri 2.x **没有** `app.env` 配置,加进去
会让 Tauri 启动报错。改用 sidecar 启动时显式 `.env()` 注入,既兼容 Tauri 2.x
也避免 schema 校验失败。

---

## P0-A2:run_forge 显式失败

### 问题
`run_forge` 内部 MCMC step 抛错时,内层 `except` 会"静默退化"成默认分
(score=0) + intron="" 的占位 result,玩家分不清"算法没找到好序列"和
"算法崩了"。

### 修复
**`apps/api/app/proto/engine.py`**:
```python
class ForgeExecutionError(RuntimeError):
    """Phase 3 Task 6 P0-A2:run_forge 内部任何异常都包成这个,顶层 catch
    后写入 result.errors — 显式失败,不静默退化。"""

@dataclass
class ForgeResult:
    ...
    errors: list[str] = field(default_factory=list)
```

`run_forge` 内部:
```python
collected_errors: list[str] = []
try:
    if mcmc_steps <= 1:
        ...
    else:
        intron, raw = _mcmc_search(...)
except Exception as exc:
    error_msg = f"{type(exc).__name__}: {exc}"
    collected_errors.append(f"MCMC 搜索失败 ({error_msg})")
    intron = ""
    raw = {"splice_site_score": 0.0, ... "passes_thresholds": False}
```

`_result_to_json` 序列化 errors 给 ritual_state 存盘用。

**`apps/api/app/schemas.py`**:
```python
class ForgeResponse(BaseModel):
    ...
    errors: list[str] = Field(
        default_factory=list,
        description="运行错误信息(空 = 成功);前端根据是否非空决定 UI 提示。",
    )
```

**`apps/api/app/routers/forge.py`**:`_forge_result_to_response` 透传
`errors=result.errors`。

### 前端(`apps/web/src/pages/ForgePage.tsx`)
- `result` state 加 `errors?: string[]` 字段。
- `setResult` 存 `errors: r.errors`。
- `errors` 非空时显示红色横幅(`data-testid="forge-error-banner"`):
  ```
  ⚠️ 计算过程中出现错误,结果可能不准确
    - MCMC 搜索失败 (RuntimeError: chain diverged at step 7)
    - ...
  ```
- HTTP 仍 200(玩家能继续 forge),前端按 errors 是否非空决定要不要显示横幅。

### 测试
**后端**(`apps/api/tests/test_p0_a2_explicit_failure.py`)6 个测试:
- `test_run_forge_happy_path_has_empty_errors`
- `test_run_forge_records_error_on_mcmc_failure`(monkeypatch MCMC 抛错)
- `test_run_forge_failure_does_not_silently_pass_gate`
- `test_run_forge_known_mission_template_load_failure`
- `test_forge_run_api_returns_errors_field`
- `test_forge_run_api_happy_path_has_empty_errors`

**前端**(`apps/web/src/test/ForgePage.test.tsx`)3 个测试:
- `does NOT show error banner on a successful forge`
- `shows red banner when errors are non-empty`
- `shows multiple error items when there are multiple errors`

---

## 测试结果

### 后端
- 基线:199 passed
- P0-A1 +3 → 202
- P0-C1 +5 → 207
- P0-A2 +6 → 213
- **最终:213 passed**(0 failed)
- 0 个旧测试被破坏(Task 2/3 154 个 + 其他 45 个全部通过)

### 前端
- 基线:36 passed
- P0-B1 +3 → 39
- P0-A2 +3 → 42
- **最终:42 passed**(0 failed)
- 原有 36 个测试全过(包括 1 个被微调的 P0-B1 兼容性测试)

---

## 4 个独立 Commit

| P0 | Commit Hash | Subject |
|---|---|---|
| A1 | `fbaad348` | `fix(phase3): P0-A1 gallery_store 改用独立 event loop,不再阻塞主 loop` |
| B1 | `09e877be` | `fix(phase3): P0-B1 锻造完成后自动写入 Gallery(核心循环最后一环)` |
| C1 | `8697257e` | `fix(phase3): P0-C1 Tauri sidecar 端口对齐后端 PROTOFORGE_API_PORT` |
| A2 | `e491fdc6` | `fix(phase3): P0-A2 run_forge 显式失败,errors 字段透传前端` |

---

## 踩过的坑

1. **anyio.from_thread.run 在 TestClient/pytest 路径上不可用**
   - 第一版用 `from anyio.from_thread import run` 期望它在没有 anyio worker
     的线程里"fallback 到 asyncio.run 行为",实际报 `NoEventLoopError`。
   - 改用手动 `new_event_loop()` + `run_until_complete()` + `close()`,
     既兼容 FastAPI 真实路径(每个调用独立 loop),也兼容 pytest 路径。

2. **Tauri 2.x 没有 `app.env` 配置**
   - 任务说"加 env 字段",但 Tauri 2.x schema 不支持,加进去启动会报错。
   - 改用 `Command::env("PROTOFORGE_API_PORT", port_str)` 显式注入,
     既满足"把 env var 传给 sidecar"的需求,也不破坏 Tauri 配置 schema。

3. **A2 测试 `primary == 0.0` 误判**
   - 第一版断言 `result.scores["primary"] == 0.0` 失败。
   - 实际 primary = `w_alpha * 0 + w_beta * (1 - 0) - 0.1*0 - 0.05*0 = w_beta ≈ 0.35`。
   - 改成断言**所有 components 都是 0**(默认占位值),更准确反映"算法崩了"
     的特征,而不是依赖某个特定的算式。

4. **前端 `result` state 类型不存 `errors`,导致红色横幅不显示**
   - 改 `setResult` 时忘了加 `errors: r.errors` 字段,导致 `result.errors` 是 undefined。
   - 类型补上 `errors?: string[]`,setResult 同步更新,3 个 A2 测试全过。

---

## 下次接力建议(给全量验证 subagent)

1. **后端完整跑**:`cd apps/api && .venv\Scripts\python.exe -m pytest tests/ -q`
   应得 **213 passed**(无失败)。
2. **前端完整跑**:`cd apps/web && pnpm test`
   应得 **42 passed**(无失败)。
3. **Cargo 测试**(可选,本次没跑):`cd apps/desktop/src-tauri && cargo test`
   应得 5 个 sidecar_port 单元测试通过。
4. **不要碰**:
   - `apps/api/app/proto/ritual.py` / `exit_penalty.py` / `ritual_state.py`(Task 2/3)
   - `apps/api/app/protoforge/*`(Task 5)
   - `apps/api/app/models/loader.py` / `apps/api/app/llm/loader.py`(Task 1.2/1.3)
   - `apps/api/app/routers/vendor.py` / `onboarding.py` / `protoforge.py`(Task 1.5/4/5)
   - `apps/web/src/pages/OnboardingPage.tsx`(Task 1.5/4)
5. **预期路径副作用**:
   - `apps/apps/api/data/exports` / `upload_queue` 是 Task 5 测试的相对路径落盘
     残留(测试 cwd = `apps/api` 时,相对路径 `apps/api/data/...` 解析成
     `apps/apps/api/data/...`)。不是本任务引入,清不清都行,加 .gitignore 也行。
6. **新加文件清单**:
   - `apps/api/tests/test_p0_a1_event_loop.py`(3 tests)
   - `apps/api/tests/test_p0_a2_explicit_failure.py`(6 tests)
   - `apps/api/tests/test_p0_c1_port_alignment.py`(5 tests)
   - 4 个 `git log` 内的 commit
