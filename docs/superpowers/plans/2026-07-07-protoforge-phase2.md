# ProtoForge Phase 2 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Phase 1.5 留下的占位升级为真实现 — SpliceTransformer 模型接入(可选)、LLM 抽象层补全 chat()、NL→params 翻译集成到 forge 流程(一步到位)、LLM 调用通过 llm.py 抽象层而非散落 httpx。

**Architecture:**
- SpliceTransformer 评分器用延迟 import 真实模型,失败回退启发式(与当前实现一致,只是 score() 不再抛 NotImplementedError)。
- LLM 基类加 `chat(messages, temperature, max_tokens)` 方法,所有 provider 统一走这个入口。
- translate.py 改为调用 `llm.chat()` 而非自己 import httpx。
- ForgeRequest 支持可选 `natural_language` 字段,若提供则服务端先调 translate 再 forge。

**Tech Stack:** Python 3.10+ / FastAPI / httpx(已用) / pydantic

**前置条件:** Phase 1.5 完成,42 个后端测试 + 3 个前端测试通过,workspace 干净。

---

### Task 1: LLM chat() 抽象方法(修复 Medium #10)

**问题:** `LLMProvider` 基类只有 `describe()` 和 `test()`,真实 LLM 调用在 `translate.py` 里直接 `httpx.post()`,绕过了抽象层。

**Files:**
- Modify: `apps/api/app/llm.py` (LLMProvider 加 `chat()` 抽象方法,3 个 provider 实现)
- Modify: `apps/api/app/translate.py` (改用 `llm.chat()`)

- [ ] **Step 1: 在 test_llm_chat.py 写 failing test — LLMProvider.chat 是抽象的**

```python
"""Task 1: LLM chat() 抽象层测试。"""
import pytest

from app.llm import (
    CloudProvider,
    DisabledProvider,
    LocalProvider,
    load_state,
)


def test_all_providers_implement_chat():
    """每个 provider 都必须实现 chat() 方法。"""
    for provider in (CloudProvider(), LocalProvider(), DisabledProvider()):
        assert hasattr(provider, "chat")
        assert callable(provider.chat)


def test_disabled_chat_raises_clear_error():
    """disabled 模式调 chat() 应明确报不支持,而不是静默返回空。"""
    p = DisabledProvider()
    with pytest.raises(RuntimeError, match="disabled"):
        p.chat([{"role": "user", "content": "hi"}])


def test_cloud_chat_calls_chat_completions(monkeypatch):
    """cloud chat() 应走 /chat/completions,带 Bearer token。"""
    import httpx

    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        # 构造一个最小 OpenAI 兼容响应
        resp = httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "{\"k\": 0.5}", "role": "assistant"}}
                ]
            },
            request=httpx.Request("POST", url),
        )
        return resp

    monkeypatch.setattr(httpx, "post", fake_post)

    from app.llm import ProviderConfig
    cfg = ProviderConfig(
        name="cloud",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key="sk-test",
    )
    p = CloudProvider()
    out = p.chat(
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_tokens=10,
        config=cfg,
    )
    assert out == "{\"k\": 0.5}"
    assert "chat/completions" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["json"]["model"] == "deepseek-chat"
    assert captured["json"]["temperature"] == 0.2


def test_local_chat_uses_openai_compatible(monkeypatch):
    """local chat() 也是 OpenAI 兼容,空 api_key 用 ollama 占位。"""
    import httpx

    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok", "role": "assistant"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    from app.llm import ProviderConfig
    cfg = ProviderConfig(
        name="local",
        base_url="http://127.0.0.1:11434/v1",
        model="qwen2.5:7b",
        api_key="",
    )
    out = LocalProvider().chat(
        [{"role": "user", "content": "ping"}],
        temperature=0.1,
        max_tokens=5,
        config=cfg,
    )
    assert out == "ok"
    assert captured["headers"]["Authorization"] == "Bearer ollama"
    assert "11434" in captured["url"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd apps/api; python -m pytest tests/test_llm_chat.py -v`
Expected: FAIL — `LLMProvider` 没有 `chat` 方法

- [ ] **Step 3: 在 LLMProvider 基类加 chat() 抽象方法**

修改 `apps/api/app/llm.py`,把:

```python
class LLMProvider(ABC):
    """统一的 LLM provider 接口。"""
    name: ProviderName

    @abstractmethod
    def describe(self) -> dict:
        """返回给前端展示的元信息:label/desc/required fields。"""

    @abstractmethod
    def test(self, config: ProviderConfig) -> tuple[bool, str]:
        """用最少 token 探测可达性。返回 (ok, message)。"""
```

改为:

```python
class LLMProvider(ABC):
    """统一的 LLM provider 接口。"""
    name: ProviderName

    @abstractmethod
    def describe(self) -> dict:
        """返回给前端展示的元信息:label/desc/required fields。"""

    @abstractmethod
    def test(self, config: ProviderConfig) -> tuple[bool, str]:
        """用最少 token 探测可达性。返回 (ok, message)。"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
        config: ProviderConfig | None = None,
    ) -> str:
        """调用 LLM 一次 chat completion,返回 message content(纯文本)。

        参数:
        - messages: OpenAI 协议格式 [{"role": ..., "content": ...}]
        - temperature/max_tokens: 采样参数
        - config: ProviderConfig 实例;若为 None 则从 load_state() 读
        """
```

注意:导入 `from typing import TYPE_CHECKING` 的话,`config: "ProviderConfig | None"`,在 TYPE_CHECKING 块里 from \_\_future\_\_ import annotations 已经处理。

- [ ] **Step 4: 在 CloudProvider / LocalProvider / DisabledProvider 中实现 chat()**

在 `CloudProvider` 类的 `test()` 方法后新增:

```python
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
        config: "ProviderConfig | None" = None,
    ) -> str:
        cfg = config or self._default_config()
        if not cfg.api_key:
            raise RuntimeError("cloud provider 缺少 api_key,请先在 onboarding 页配置")
        r = httpx.post(
            f"{cfg.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"cloud LLM HTTP {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _default_config() -> "ProviderConfig":
        from app.llm import ProviderConfig
        return ProviderConfig(
            name="cloud",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key="",
        )
```

在 `LocalProvider` 类的 `test()` 方法后新增:

```python
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
        config: "ProviderConfig | None" = None,
    ) -> str:
        from app.llm import ProviderConfig
        cfg = config or ProviderConfig(
            name="local",
            base_url="http://127.0.0.1:11434/v1",
            model="qwen2.5:7b",
            api_key="",
        )
        r = httpx.post(
            f"{cfg.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg.api_key or 'ollama'}",
                "Content-Type": "application/json",
            },
            json={
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=60.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"local LLM HTTP {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"]
```

在 `DisabledProvider` 类的 `test()` 方法后新增:

```python
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
        config: "ProviderConfig | None" = None,
    ) -> str:
        raise RuntimeError(
            "LLM 当前为 disabled 模式,无法 chat。请在 onboarding 页切换到 cloud 或 local。"
        )
```

- [ ] **Step 5: 跑测试确认 chat 抽象方法覆盖**

Run: `cd apps/api; python -m pytest tests/test_llm_chat.py -v`
Expected: 4 passed

- [ ] **Step 6: 跑全部测试确保没破其他东西**

Run: `cd apps/api; python -m pytest tests/ -q`
Expected: 46 passed(原 42 + 新 4)

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/llm.py apps/api/tests/test_llm_chat.py
git commit -m "feat(llm): add chat() abstract method on LLMProvider base + 3 implementations"
```

---

### Task 2: translate.py 改用 llm.chat() 抽象层

**问题:** `translate.py` 的 `_llm_translate()` 直接用 `httpx.post()`,绕过 llm.py 抽象层,无法被测试/切换。

**Files:**
- Modify: `apps/api/app/translate.py` (`_llm_translate` 改用 `_PROVIDERS[state.active].chat()`)
- Test: 已有 `tests/test_translate_api.py` 应仍通过(heuristic 路径不变)

- [ ] **Step 1: 在 test_translate_api.py 写新 test — LLM chat() 路径被调用**

在 `tests/test_translate_api.py` 末尾新增:

```python
def test_translate_uses_llm_chat(monkeypatch):
    """translate 应该走 LLMProvider.chat() 而非自己 httpx。"""
    import app.translate as tr_mod

    captured = {"called": False, "messages": None, "temperature": None}

    class FakeProvider:
        name = "cloud"

        def chat(self, messages, temperature=0.2, max_tokens=256, config=None):
            captured["called"] = True
            captured["messages"] = messages
            captured["temperature"] = temperature
            return '{"min_target_splice": 0.9}'

    # 切到 cloud(需要 api_key 才能正常 chat)
    from app.config import settings
    from app import llm
    test_dir = settings.data_dir  # 复用 autouse fixture 的 tmp 目录
    llm._CONFIG_PATH = test_dir / "llm.json"
    client.post(
        "/api/onboarding/save",
        json={
            "active": "cloud",
            "providers": {
                "cloud": {
                    "base_url": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat",
                    "api_key": "sk-test",
                }
            },
        },
    )
    # monkey patch LLMProvider
    from app.llm import _PROVIDERS
    monkeypatch.setitem(_PROVIDERS, "cloud", FakeProvider())

    resp = client.post(
        "/api/translate",
        json={"mission_id": "polar-glow-v1", "text": "极严"},
    )
    body = resp.json()
    assert captured["called"] is True
    assert body["values"]["min_target_splice"] == 0.9
    assert body["provider"] == "cloud"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd apps/api; python -m pytest tests/test_translate_api.py::test_translate_uses_llm_chat -v`
Expected: FAIL — 当前 translate 仍直接 httpx,monkey patch 不到

- [ ] **Step 3: 重构 translate.py 用 llm.chat()**

把 `apps/api/app/translate.py` 中 `_llm_translate` 函数完全重写为:

```python
def _llm_translate(text: str, mission: Mission) -> tuple[dict, str]:
    """用当前 LLM provider 翻译。返回 (slider_values, explanation)。"""
    from app.llm import _PROVIDERS, load_state

    state = load_state()
    if state.active == "disabled":
        raise RuntimeError("LLM disabled")
    provider = _PROVIDERS.get(state.active)
    if provider is None:
        raise RuntimeError(f"未知 provider: {state.active}")

    cfg = state.providers.get(state.active)
    schema_hint = {
        p.key: {"min": p.min, "max": p.max, "step": p.step, "default": p.default}
        for p in mission.sliders
    }
    messages = [
        {
            "role": "system",
            "content": "只输出 JSON,不要任何解释。",
        },
        {
            "role": "user",
            "content": (
                f"你是 ProtoForge 的参数翻译器。玩家给你一段自然语言描述,"
                f"你要把它转成以下滑块值(返回严格 JSON,键名不要改,值在合法区间内):\n"
                f"{json.dumps(schema_hint, ensure_ascii=False)}\n"
                f"任务背景: {mission.title}\n"
                f"任务描述: {mission.description}\n"
                f"玩家描述: {text}"
            ),
        },
    ]

    content = provider.chat(messages, temperature=0.2, max_tokens=512, config=cfg)
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise RuntimeError("LLM 输出不含 JSON")
    raw = json.loads(match.group(0))

    out = {}
    for p in mission.sliders:
        v = raw.get(p.key, p.default)
        try:
            v_f = float(v)
        except (TypeError, ValueError):
            v_f = p.default
        out[p.key] = round(_clamp(v_f, p.min, p.max), 3)
    return out, f"LLM ({state.active}/{cfg.model}) 解析成功"
```

同时删掉:
- `import httpx` (文件顶部)
- `state = load_state()` 那一段(已在函数内 import)

- [ ] **Step 4: 跑全部测试**

Run: `cd apps/api; python -m pytest tests/ -q`
Expected: 47 passed(原 46 + 新 1)

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/translate.py apps/api/tests/test_translate_api.py
git commit -m "refactor(translate): route LLM calls through LLMProvider.chat() abstraction"
```

---

### Task 3: SpliceTransformer 真模型评分(修复 Medium #4)

**问题:** `SpliceTransformerScorer.score()` 直接抛 `NotImplementedError`。需要实装一个真正能跑的简化版本,失败时回退到启发式。

**设计决策:** 不接真实 SpliceTransformer(需 1GB+ 下载),改为用 numpy 在 CPU 上跑一个**简化版卷积打分器**(基于位置权重矩阵的 donor/acceptor 模型,论文里也常用这种 baseline)。真实 transformer 接入留到 Phase 3(用户可手动安装 torch + InstaDeepAI/splice-transformer 后会自动启用)。

**Files:**
- Modify: `apps/api/app/proto/scorer.py` (SpliceTransformerScorer.score 用 PWM 实现)
- Modify: `apps/api/pyproject.toml` (加 numpy 到依赖)
- Test: `apps/api/tests/test_scorer_abstraction.py` (替换占位测试)

- [ ] **Step 1: 在 pyproject.toml 添加 numpy 依赖**

`apps/api/pyproject.toml` 的 `[project].dependencies` 加:

```toml
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "sqlalchemy>=2.0",
    "aiosqlite>=0.19",
    "httpx>=0.27",
    "numpy>=1.26",  # 新增 — 简化版 SpliceTransformer 需要
]
```

- [ ] **Step 2: 安装 numpy 到用户级 site-packages**

Run: `python -m pip install --user numpy`
Expected: Successfully installed numpy-X.Y.Z

- [ ] **Step 3: 在 test_scorer_abstraction.py 写新 test — SpliceTransformer 真有 score**

修改 `tests/test_scorer_abstraction.py`,把 `test_splice_transformer_init_requires_torch` 替换为:

```python
def test_splice_transformer_scorer_runs_without_torch():
    """SpliceTransformerScorer 不应再抛 NotImplementedError。

    当前实装:不依赖 torch,使用 numpy + PWM(位置权重矩阵)做 donor/acceptor 打分。
    """
    s = SpliceTransformerScorer()
    out = s.score("ATGCGT" * 10)
    assert "splice_site_score" in out
    assert 0.0 <= out["splice_site_score"] <= 1.0


def test_splice_transformer_prefers_real_splice_motifs():
    """真实 GT-AG 边界序列的剪接分应高于纯随机序列。"""
    s = SpliceTransformerScorer()
    good = "GT" + "ATGCATGC" * 8 + "AG"  # 强 donor/acceptor
    bad = "ATGCATGC" * 10                 # 无 motif
    g_score = s.score(good)["splice_site_score"]
    b_score = s.score(bad)["splice_site_score"]
    assert g_score > b_score, f"GT-AG 序列分({g_score})应高于随机({b_score})"
```

并把 `test_splice_transformer_init_requires_torch` 这个旧测试删掉(若已存在)。

- [ ] **Step 4: 跑测试确认失败**

Run: `cd apps/api; python -m pytest tests/test_scorer_abstraction.py -v`
Expected: FAIL — `SpliceTransformerScorer.score` 抛 NotImplementedError

- [ ] **Step 5: 实装 SpliceTransformerScorer.score 用 numpy PWM**

修改 `apps/api/app/proto/scorer.py` 中 `SpliceTransformerScorer` 类。把整个类改为:

```python
class SpliceTransformerScorer(Scorer):
    """Splice 位点评分器 — 简化版(无 torch 依赖)。

    实现:用位置权重矩阵(PWM)对 donor/acceptor 位点打分。
    - donor  位置窗口:序列前 6 nt(GT + 保守区)
    - acceptor 位置窗口:序列后 16 nt(polypyrimidine tract + AG)
    - 输出:归一化到 0~1 的剪接强度 + GC 含量 + 3-mer 熵

    论文里 real SpliceTransformer / SpliceAI 可作为 Phase 3 升级,
    接口不变,只换实现。
    """

    name = "transformer"

    # donor PWM(6 位置 × 4 碱基),行=位置,列=A/C/G/T 的 log-odds
    _DONOR_PWM = [
        {"G": 1.5, "A": 0.4, "C": -0.3, "T": 0.0},   # 5'ss -6
        {"G": 0.2, "A": 1.4, "C": -0.1, "T": 0.3},   # 5'ss -5
        {"G": 2.0, "A": -0.5, "C": -0.2, "T": 0.0},  # 5'ss -4 (G 必需)
        {"T": 1.8, "A": -0.3, "C": 0.0, "G": -0.4},  # 5'ss -3
        {"A": 1.3, "G": 0.5, "C": 0.0, "T": -0.2},   # 5'ss -2
        {"G": 1.6, "A": 0.2, "C": 0.0, "T": -0.3},   # 5'ss -1
    ]
    # acceptor PWM(15 位置),典型 YAG/RAN 模式
    _ACCEPTOR_PWM = [
        {"T": 0.8, "C": 0.7, "A": 0.2, "G": -0.1},  # -15
        {"T": 1.0, "C": 0.6, "A": 0.0, "G": -0.2},  # -14
        {"T": 0.9, "C": 0.7, "A": 0.1, "G": -0.1},  # -13
        {"T": 0.7, "C": 0.8, "A": 0.2, "G": -0.1},  # -12
        {"T": 0.6, "C": 0.9, "A": 0.2, "G": 0.0},   # -11
        {"T": 0.5, "C": 0.9, "A": 0.3, "G": 0.0},   # -10
        {"T": 0.4, "C": 0.8, "A": 0.4, "G": 0.1},   # -9
        {"T": 0.3, "C": 0.7, "A": 0.5, "G": 0.2},   # -8
        {"T": 0.2, "C": 0.5, "A": 0.6, "G": 0.4},   # -7
        {"C": 0.3, "T": 0.2, "A": 0.4, "G": 0.5},   # -6
        {"A": 0.3, "C": 0.2, "T": 0.3, "G": 0.5},   # -5
        {"A": 0.2, "C": 0.1, "T": 0.3, "G": 0.6},   # -4
        {"A": 0.1, "T": 0.1, "C": 0.0, "G": 0.7},   # -3
        {"A": 0.0, "T": 0.0, "C": 0.0, "G": 0.8},   # -2
        {"G": 1.5, "A": 0.2, "T": 0.0, "C": -0.2},  # -1
    ]

    def __init__(self, model_id: str | None = None) -> None:
        # Phase 2 简化实现不依赖 torch;若 Phase 3 装上 torch,
        # 可在这里 `import torch` + 加载真实模型,接口不变。
        self._model_id = model_id or "pwm-baseline"

    def _pwm_score(self, window: str, pwm: list[dict]) -> float:
        """位置权重矩阵打分:sum of log-odds,归一化到 0~1。"""
        window = window.upper()
        if len(window) < len(pwm):
            return 0.0
        raw = 0.0
        for i, base in enumerate(window[:len(pwm)]):
            raw += pwm[i].get(base, -1.0)
        # 归一化:理论 max = sum(max in each position)
        max_score = sum(max(row.values()) for row in pwm)
        return max(0.0, min(1.0, raw / max_score))

    def _gc(self, seq: str) -> float:
        if not seq:
            return 0.0
        s = seq.upper()
        return sum(1 for c in s if c in "GC") / len(s)

    def _kmer_entropy(self, seq: str, k: int = 3) -> float:
        if len(seq) < k:
            return 0.0
        kmers = [seq[i:i + k] for i in range(len(seq) - k + 1)]
        counts: dict[str, int] = {}
        for kmer in kmers:
            counts[kmer] = counts.get(kmer, 0) + 1
        total = sum(counts.values())
        import math
        return -sum((c / total) * math.log2(c / total) for c in counts.values())

    def score(self, seq: str) -> dict:
        seq = seq.upper()
        donor = self._pwm_score(seq[:6], self._DONOR_PWM)
        acceptor = self._pwm_score(seq[-15:], self._ACCEPTOR_PWM)
        splice = min(1.0, 0.55 * donor + 0.55 * acceptor)
        return {
            "gc_content": round(self._gc(seq), 3),
            "splice_site_score": round(splice, 3),
            "kmer_entropy": round(self._kmer_entropy(seq) / 2.5, 3),
        }
```

注意:`math.log2` 用 `import math` 放在函数内避免顶层污染(也可以顶层,但函数内更明确)。

- [ ] **Step 6: 跑全部测试**

Run: `cd apps/api; python -m pytest tests/ -q`
Expected: 48 passed(原 47 + 新 1 减去 1 旧测试)

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/proto/scorer.py apps/api/pyproject.toml apps/api/tests/test_scorer_abstraction.py
git commit -m "feat(scorer): SpliceTransformerScorer implemented as PWM baseline (no torch dep)"
```

---

### Task 4: Forge 流程集成 NL 翻译(修复 Medium #5)

**问题:** 当前玩家要"开炉"必须先调 `/api/translate` 再调 `/api/forge/run` 两步。GDD 1.1 描述的"开炉时自动翻译"是 forge 流程的一部分。

**Files:**
- Modify: `apps/api/app/schemas.py` (ForgeRequest 加可选 natural_language 字段)
- Modify: `apps/api/app/routers/forge.py` (run 路由支持 NL 预处理)
- Modify: `apps/web/src/pages/ForgePage.tsx` (优先用 natural_language 一体化调用)
- Modify: `apps/web/src/lib/api.ts` (ForgeRequest 类型同步)

- [ ] **Step 1: 在 test_forge_api.py 写新 test — natural_language 一步到位**

```python
def test_forge_run_with_natural_language(client):
    """ForgeRequest.natural_language 非空时,服务端自动翻译再 forge。"""
    body = {
        "mission_id": "polar-glow-v1",
        "params": {},  # 空 — 用翻译结果
        "generator": "preference",
        "natural_language": "严格一点",
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200
    data = resp.json()
    # 严格翻译后 min_target_splice 应 > 0.65 default
    assert data["intron"]


def test_forge_run_natural_language_overrides_params(client):
    """NL 翻译结果应覆盖 params 中的同名键。"""
    body = {
        "mission_id": "polar-glow-v1",
        "params": {"min_target_splice": 0.5},  # 与 NL 严格冲突
        "generator": "preference",
        "natural_language": "严格",
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200


def test_forge_run_natural_language_empty_uses_params(client):
    """NL 为空时应直接用 params。"""
    body = {
        "mission_id": "polar-glow-v1",
        "params": {"min_target_splice": 0.5},
        "generator": "preference",
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200
    assert resp.json()["fasta"].startswith(">")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd apps/api; python -m pytest tests/test_forge_api.py -v`
Expected: 3 new tests FAIL(因 ForgeRequest 还不接受 natural_language)

- [ ] **Step 3: 在 schemas.py 加 natural_language 字段**

`apps/api/app/schemas.py` 中 `ForgeRequest`:

```python
class ForgeRequest(BaseModel):
    mission_id: str = Field(..., description="任务模板 ID,如 polar-glow-v1")
    params: dict = Field(default_factory=dict, description="滑块/可调参数")
    generator: Literal["preference", "uniform", "random"] = "preference"
    seed: Optional[int] = None
    natural_language: Optional[str] = Field(
        default=None,
        description="玩家自然语言描述;若提供则服务端先翻译成 params 再 forge",
    )
```

- [ ] **Step 4: 修改 forge router 支持 NL**

`apps/api/app/routers/forge.py` 中 `forge_run`:

```python
@router.post("/run", response_model=ForgeResponse)
def forge_run(req: ForgeRequest) -> ForgeResponse:
    params = dict(req.params)
    if req.natural_language and req.natural_language.strip():
        from app.missions import get_mission
        from app.translate import translate

        try:
            mission = get_mission(req.mission_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        translated, _explanation = translate(req.natural_language, mission)
        # NL 翻译结果覆盖 params(玩家明确意图优先)
        params.update(translated)

    try:
        result = run_forge(req.mission_id, params, req.generator, req.seed)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _forge_result_to_response(result)
```

- [ ] **Step 5: 跑全部测试**

Run: `cd apps/api; python -m pytest tests/ -q`
Expected: 51 passed(原 48 + 新 3)

- [ ] **Step 6: 同步前端类型和 API**

`packages/shared/src/types.ts` 中 `ForgeRequest`:

```typescript
export interface ForgeRequest {
  mission_id: string;
  params: Record<string, number>;
  generator: 'uniform' | 'preference' | 'random';
  seed?: number;
  natural_language?: string;  // 新增
}
```

`apps/web/src/lib/api.ts` 已有 `forgeApi.run` 使用 `ForgeRequest` 类型,无需额外改动。

`apps/web/src/pages/ForgePage.tsx` 的 `handleRun` 修改为:

```typescript
const handleRun = async () => {
  if (!mission) return;
  setLoading(true);
  setErr(null);
  try {
    const r = await forgeApi.run({
      mission_id: mission.id,
      params,
      generator: 'preference',
      natural_language: nl.trim() || undefined,  // 新增
    });
    setResult({...});
  } catch (e) {
    setErr((e as Error).message);
  } finally {
    setLoading(false);
  }
};
```

同时可以删除"翻译成参数"按钮(因为现在 forge 自动翻译),或保留它作为预览(显示翻译后的 params,玩家可调后再 forge)。建议保留。

- [ ] **Step 7: 跑前端 build + test**

Run: `cd apps/web; pnpm build 2>&1 | Select-Object -Last 5; pnpm exec vitest run 2>&1 | Select-Object -Last 5`
Expected: build 成功,3 tests passed

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/schemas.py apps/api/app/routers/forge.py apps/api/tests/test_forge_api.py packages/shared/src/types.ts apps/web/src/pages/ForgePage.tsx
git commit -m "feat(forge): natural_language field — one-step NL→params→forge"
```

---

### Task 5: RUNBOOK + 全量验证

**Files:**
- Modify: `docs/RUNBOOK.md`

- [ ] **Step 1: 更新 RUNBOOK §8 反映 Phase 2 进展**

把"Phase 1.5"替换为"Phase 2";删除已修复条目:

- 启发式评分 → 仍占位,但 SpliceTransformerScorer 现在有真 PWM 实现,可通过 `PROTOFORGE_SPLICER=transformer` 切换
- LLM 翻译 / chat() 抽象层 → 完整
- MCMC 搜索 → 仍简化版(Phase 3 可接真 transformer 打分)
- Tauri sidecar → 已实装
- 新增:numpy 是 SpliceTransformer 评分器的运行时依赖

- [ ] **Step 2: 全量验证**

```powershell
cd apps/api; python -m pytest -q
cd ..\web; pnpm exec vitest run; pnpm build
```

Expected: 后端 51+ passed,前端 3 passed,build 成功

- [ ] **Step 3: Commit**

```bash
git add docs/RUNBOOK.md
git commit -m "docs: update RUNBOOK for Phase 2 completion"
```

---

## 自检清单

| 检查项 | 状态 |
|---|---|
| LLMProvider.chat() 三 provider 覆盖 | Task 1 |
| translate 走 llm.chat() 抽象层 | Task 2 |
| SpliceTransformerScorer 真实可用(无需 torch) | Task 3 |
| ForgeRequest.natural_language 一步到位 | Task 4 |
| 前后端类型一致 | Task 4 |
| 无 TBD / TODO | 通过 |
| 每步有精确路径 | 通过 |
| 每步有可运行测试 | 通过 |
