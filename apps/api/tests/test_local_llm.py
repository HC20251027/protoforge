"""Phase 3 Task 1.3 — 本地 LLM 加载器测试。

覆盖点(>= 4 测试):
1. `LocalLLMLoader.is_available()` 在 vendor 目录不存在时 → False
2. `LocalLLMLoader.is_available()` 在只有 stub(0 字节/小文件)时 → False
3. `LocalLLMLoader.is_available()` 在有合法的 GGUF(带 magic + >= min_size_mb)时 → True
4. `LocalLLMProvider.chat()` 在权重不可用时 → 抛 `LLMUnavailable`(不静默)
5. `LocalLLMProvider.chat()` 注入 mock runner 后能返回内容
6. `LocalLLMProvider.chat()` 注入模拟 "llama_cpp 没装" runner → 抛 `LLMUnavailable`
7. `LocalLLMLoader` 多分片场景:两个 < min_size_mb 的分片加总后 >= 阈值也算 OK
8. `LocalLLMLoader.describe()` / `llm_summary()` 返回稳定结构
"""
from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path

import pytest

from app.llm import loader as llm_loader_mod
from app.llm.loader import (
    LLMUnavailable,
    LocalLLMLoader,
    LocalLLMProvider,
    llm_summary,
)


# ---------------------------------------------------------------------------
# 路径隔离:每个 case 跑完重置 vendor_dir 路径(loader 用模块级常量,不能 reset)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_loader_path(monkeypatch, tmp_path):
    """重置 LocalLLMLoader._DEFAULT_VENDOR_LLM → tmp_path,避免污染真实 vendor。

    Phase 4 L4 优化:本 fixture 不再传 min_size_mb,让 case 自己显式构造
    `LocalLLMLoader(min_size_mb=1)` 走低阈值,不再需要写真 3600MB 假文件。
    真实占盘 ≈ 1MB × N cases ≈ 10MB(对比之前 15GB+)。
    """
    fake = tmp_path / "vendor_llm"
    monkeypatch.setattr(llm_loader_mod, "_DEFAULT_VENDOR_LLM", fake)
    yield fake
    # 恢复:monkeypatch 在 case 退出时自动还原


def _make_fake_gguf(path: Path, size_mb: int = 1) -> None:
    """写一个带 GGUF v3 magic 的小文件(Phase 4 L4:测试用 1MB 占位即可)。

    关键变化(Phase 4 L4):之前为触发 `min_size_mb=3500` 阈值,要写 3600MB 真
    文件,单次跑 pytest 写 15GB+。现在通过 `LocalLLMLoader(min_size_mb=1)`
    注入低阈值,case 写 1MB 文件即可,真实占盘几乎 0。

    实现:1MB sparse (NTFS truncate 仍会分配,1MB 量级可接受)。
    magic = b"\\x03GGUF" 与 `app.models.loader._MAGIC_BYTES[".gguf"]` 对齐。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x03GGUF")
    os.truncate(path, size_mb * 1024 * 1024)


# ---------------------------------------------------------------------------
# 1. vendor 目录不存在时 is_available False
# ---------------------------------------------------------------------------


def test_is_available_false_when_vendor_dir_missing(_isolate_loader_path):
    fake = _isolate_loader_path
    # 目录压根不创建
    loader = LocalLLMLoader()
    assert loader.vendor_dir == fake
    assert fake.exists() is False
    assert loader.is_available() is False
    assert loader.try_load() is None


# ---------------------------------------------------------------------------
# 2. 目录存在但没文件 / 有零字节文件 → False
# ---------------------------------------------------------------------------


def test_is_available_false_when_dir_empty(_isolate_loader_path):
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    loader = LocalLLMLoader()
    assert loader.is_available() is False
    assert loader.model_files() == []


def test_is_available_false_when_only_stub_file(_isolate_loader_path):
    """0 字节文件 + 1MB 文件 + 不带 magic 的 1MB 文件都应 False。"""
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    loader = LocalLLMLoader()

    # (a) 0 字节
    (fake / "qwen2.5-7b-instruct-q4_k_m.gguf").write_bytes(b"")
    assert loader.is_available() is False

    # (b) 1MB 但不带 magic — magic 校验失败
    (fake / "qwen2.5-7b-instruct-q4_k_m.gguf").write_bytes(b"X" * (1024 * 1024))
    assert loader.is_available() is False


# ---------------------------------------------------------------------------
# 3. 合法 GGUF(magic + >= min_size_mb)→ True
# ---------------------------------------------------------------------------


def test_is_available_true_with_fake_gguf_single_file(_isolate_loader_path):
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    loader = LocalLLMLoader(min_size_mb=1)  # L4:测试用低阈值,不再写真 3600MB
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m.gguf")  # 默认 1MB

    assert loader.is_available() is True
    handle = loader.try_load()
    assert handle is not None
    assert handle.name == "qwen2.5-7b-instruct-q4-k-m"
    assert handle.format_hint == "gguf"
    assert handle.size_bytes >= 1 * 1024 * 1024  # 1MB 占位即可触发


# ---------------------------------------------------------------------------
# 4. 真实 vendor/llm/ 下的分片(由 subagent 跑下载时已经放在那)
#    单独跑这个 case 不会失败:就算没真实文件,我们也覆盖"目录为空"分支
# ---------------------------------------------------------------------------


def test_real_vendor_dir_or_empty(_isolate_loader_path, tmp_path):
    """看真实 vendor/llm(可能不存在)的状态,仅做记录式断言。"""
    # 真实路径不在 _isolate_loader_path,而是固定的 apps/api/vendor/llm/
    real_loader = LocalLLMLoader.__new__(LocalLLMLoader)
    real_loader.vendor_dir = llm_loader_mod._DEFAULT_VENDOR_LLM
    # _DEFAULT_VENDOR_LLM 已经被 monkeypatch 成 tmp_path,这里反向取真实路径
    # 用模块原始常量:
    real_path = llm_loader_mod._API_ROOT / "vendor" / "llm"
    real_loader.vendor_dir = real_path
    # 不强制断言,只确保调用不抛异常
    _ = real_loader.is_available()
    _ = real_loader.model_files()
    _ = real_loader.describe()


# ---------------------------------------------------------------------------
# 5. 多分片场景:两个 < min_size_mb 的文件加总后 >= 阈值,也算 OK
# ---------------------------------------------------------------------------


def test_sharded_gguf_combined_size_passes_threshold(_isolate_loader_path):
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    loader = LocalLLMLoader(min_size_mb=1)  # L4:低阈值,各写 1MB 分片
    # 2 个 1MB 分片 = 2MB(超过 1MB 阈值)
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf")
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf")

    assert loader.is_available() is True
    handle = loader.try_load()
    assert handle is not None
    # size 是两个分片总和
    assert handle.size_bytes >= 2 * 1024 * 1024
    # 文件列表两个
    files = loader.model_files()
    assert len(files) == 2


# ---------------------------------------------------------------------------
# 6. Provider.chat() 在权重不可用时 → 抛 LLMUnavailable(不静默退化)
# ---------------------------------------------------------------------------


def test_provider_chat_raises_when_weights_missing(_isolate_loader_path):
    """核心安全保证:缺权重时 provider 必须抛 LLMUnavailable,不能返回假字符串。"""
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)  # 存在但空
    loader = LocalLLMLoader()
    provider = LocalLLMProvider(loader=loader)
    # 注入一个 mock runner 验证"就算 runner 不抛,我们也应在更早 fail"
    def fake_runner(model_path: str):
        raise AssertionError("runner 不该被调用 — 权重缺失应当先抛 LLMUnavailable")

    provider_no_runner = LocalLLMProvider(loader=loader, runner=fake_runner)
    with pytest.raises(LLMUnavailable, match="(权重|本地 LLM|vendor|llm|不可用)"):
        provider_no_runner.chat([{"role": "user", "content": "hi"}])

    # 默认 provider(不传 runner)也要在 import 阶段之前就抛,不会去 import llama_cpp
    # import 阶段不会被触发,因为 _resolve_model_path 先跑
    with pytest.raises(LLMUnavailable):
        provider.chat([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# 7. Provider.chat() 注入 mock runner 后能正常返回内容
# ---------------------------------------------------------------------------


def test_provider_chat_with_mock_runner_returns_content(_isolate_loader_path):
    """正常路径:有合法 GGUF + 注入 mock runner → 返回 OpenAI 协议 content。"""
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m.gguf")  # 1MB 占位

    loader = LocalLLMLoader(min_size_mb=1)

    captured: dict = {}

    class FakeLlama:
        def __init__(self, model_path: str):
            captured["model_path"] = model_path

        def create_chat_completion(self, messages, temperature, max_tokens):
            captured["messages"] = messages
            captured["temperature"] = temperature
            captured["max_tokens"] = max_tokens
            return {
                "choices": [
                    {"message": {"role": "assistant", "content": "pong"}}
                ]
            }

    provider = LocalLLMProvider(loader=loader, runner=FakeLlama)
    out = provider.chat(
        [{"role": "user", "content": "ping"}],
        temperature=0.1,
        max_tokens=16,
    )
    assert out == "pong"
    # 验证参数透传
    assert captured["temperature"] == 0.1
    assert captured["max_tokens"] == 16
    assert captured["messages"] == [{"role": "user", "content": "ping"}]
    assert "qwen2.5-7b-instruct-q4_k_m.gguf" in captured["model_path"]


# ---------------------------------------------------------------------------
# 8. llama-cpp 没装时(provider 没注入 runner)→ 抛 LLMUnavailable
# ---------------------------------------------------------------------------


def test_provider_chat_when_llama_cpp_missing_raises(_isolate_loader_path, monkeypatch):
    """模拟 'pip install 失败' 场景:provider 应当捕获 ImportError 转 LLMUnavailable。"""
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m.gguf")  # 1MB 占位
    loader = LocalLLMLoader(min_size_mb=1)
    provider = LocalLLMProvider(loader=loader, runner=None)  # 走 import 路径

    # 把 sys.modules['llama_cpp'] 屏蔽掉,模拟未安装
    monkeypatch.setitem(sys.modules, "llama_cpp", None)  # type: ignore[arg-type]

    # _import_llama_cpp 的 try-import 会失败 → 抛 LLMUnavailable
    with pytest.raises(LLMUnavailable, match="(llama-cpp-python|未安装|pip install)"):
        provider.chat([{"role": "user", "content": "ping"}])


# ---------------------------------------------------------------------------
# 9. summary / describe 报告结构稳定
# ---------------------------------------------------------------------------


def test_summary_keys_present(_isolate_loader_path):
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    s = llm_summary()
    assert s["name"] == "qwen2.5-7b-instruct-q4-k-m"
    assert s["available"] is False
    assert "vendor_dir" in s
    assert s["vendor_dir"] == str(fake)
    assert s["min_size_mb"] == 3500
    assert s["model_size_mb_expected"] == 4500
    assert s["file_count"] == 0
    assert s["total_bytes_on_disk"] == 0
    assert s["files"] == []


def test_summary_reports_shard_files(_isolate_loader_path, monkeypatch):
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf")
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf")
    # L4:llm_summary 走单例 loader,需要 monkeypatch 阈值才能让 2MB 通过
    import app.llm.loader as _loader_mod
    monkeypatch.setattr(_loader_mod, "_DEFAULT_VENDOR_LLM", fake)
    # 临时给 LocalLLMLoader 类属性改 1,跑完还原
    original = LocalLLMLoader.min_size_mb
    LocalLLMLoader.min_size_mb = 1
    try:
        s = llm_summary()
        assert s["available"] is True
        assert s["file_count"] == 2
        assert s["total_mb_on_disk"] >= 2
        assert "00001-of-00002.gguf" in s["files"][0]
    finally:
        LocalLLMLoader.min_size_mb = original
