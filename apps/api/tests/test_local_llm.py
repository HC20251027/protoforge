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

    因为我们 loader 把 vendor_dir 写死为模块级常量,而不是走 get_vendor_root(),
    这里直接 monkeypatch。
    """
    fake = tmp_path / "vendor_llm"
    monkeypatch.setattr(llm_loader_mod, "_DEFAULT_VENDOR_LLM", fake)
    yield fake
    # 恢复:让后面的 test 不被污染(虽然没 module-level state 残留,
    # 但 monkeypatch 在 case 退出时自动还原)


def _make_fake_gguf(path: Path, size_mb: int) -> None:
    """写一个带 GGUF v3 magic 的 N MB 文件。

    与 `app.models.loader._MAGIC_BYTES[".gguf"]` 对齐:真 GGUF v3 文件头 4 字节是
    `b"\x03GGUF"`(version_byte=0x03 在前,后跟 ASCII "GGUF")。
    Phase 4 A2 之前 magic 是错的 `b"GGUF"`,测试辅助函数也同步用旧值,
    导致所有"合法 GGUF"测试用例在新 magic 下静默失败。现在统一改成 `b"\x03GGUF"`。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    magic = b"\x03GGUF"
    with path.open("wb") as f:
        f.write(magic)
        chunk = b"\x00" * (1024 * 1024)
        written = 0
        for _ in range(size_mb):
            f.write(chunk)
            written += 1


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
    loader = LocalLLMLoader()
    # min_size_mb=3500 → 测试用 3600MB 触发
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m.gguf", size_mb=3600)

    assert loader.is_available() is True
    handle = loader.try_load()
    assert handle is not None
    assert handle.name == "qwen2.5-7b-instruct-q4-k-m"
    assert handle.format_hint == "gguf"
    assert handle.size_bytes >= 3500 * 1024 * 1024


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
    loader = LocalLLMLoader()
    # min_size_mb = 3500;两个 1800MB 文件 = 3600MB(超过阈值)
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf", size_mb=1800)
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf", size_mb=1800)

    assert loader.is_available() is True
    handle = loader.try_load()
    assert handle is not None
    # size 是两个分片总和
    assert handle.size_bytes >= 2 * 1800 * 1024 * 1024
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
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m.gguf", size_mb=3600)

    loader = LocalLLMLoader()

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
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m.gguf", size_mb=3600)
    loader = LocalLLMLoader()
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


def test_summary_reports_shard_files(_isolate_loader_path):
    fake = _isolate_loader_path
    fake.mkdir(parents=True, exist_ok=True)
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf", size_mb=1800)
    _make_fake_gguf(fake / "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf", size_mb=1800)
    s = llm_summary()
    assert s["available"] is True
    assert s["file_count"] == 2
    assert s["total_mb_on_disk"] >= 3600
    assert "00001-of-00002.gguf" in s["files"][0]
