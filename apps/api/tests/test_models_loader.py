"""Phase 3 Task 1.2 — ML 模型加载器测试。

覆盖点:
- 三个 loader 实例化后属性正确(name / model_size_mb / vendor_dir 指向正确子目录)
- is_available() 在 vendor 目录为空时返回 False
- try_load() 在权重不存在时返回 None 不抛异常
- summary() 至少包含 3 个模型的 key
- override_vendor_root() 让 loader 切到临时目录后 is_available() 重新求值
- 真实小文件落盘后 is_available() / try_load() 都应返回 positive
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from app.models.loader import (
    ESM2Loader,
    SpliceAILoader,
    SpliceTransformerLoader,
    _MAGIC_BYTES,
    all_loaders,
    get_loader,
    get_vendor_root,
    override_vendor_root,
    reset_vendor_root,
    summary,
)


@pytest.fixture(autouse=True)
def _isolate_vendor_root():
    """每个 case 前后重置 vendor root,避免上一个测试改 _vendor_root_holder 后污染。"""
    reset_vendor_root()
    yield
    reset_vendor_root()


# ---------------------------------------------------------------------------
# 1. 基础结构 / 属性
# ---------------------------------------------------------------------------

def test_all_loaders_returns_three_instances():
    loaders = all_loaders()
    names = {l.name for l in loaders}
    assert names == {"esm2-150m", "spliceai", "splice-transformer"}


def test_each_loader_has_expected_size_budget():
    """打包预算已经在 plan 里写明,这里 pin 一下,防被无意改大。"""
    esm2 = ESM2Loader()
    spliceai = SpliceAILoader()
    st = SpliceTransformerLoader()
    assert esm2.model_size_mb == 640
    assert spliceai.model_size_mb == 50
    assert st.model_size_mb == 400


def test_each_loader_vendor_dir_under_models_root():
    esm2 = ESM2Loader()
    spliceai = SpliceAILoader()
    st = SpliceTransformerLoader()
    for loader in (esm2, spliceai, st):
        assert loader.vendor_dir.parent == get_vendor_root()
    assert esm2.vendor_dir.name == "esm2-150m"
    assert spliceai.vendor_dir.name == "spliceai"
    assert st.vendor_dir.name == "splice-transformer"


def test_get_loader_by_name():
    assert get_loader("esm2-150m").name == "esm2-150m"
    assert get_loader("spliceai").name == "spliceai"
    assert get_loader("splice-transformer").name == "splice-transformer"
    assert get_loader("nope") is None


# ---------------------------------------------------------------------------
# 2. 空 vendor 目录时 is_available / try_load 优雅降级
# ---------------------------------------------------------------------------

def test_is_available_false_when_vendor_dir_missing(tmp_path, monkeypatch):
    """指向一个肯定不存在的 vendor root,所有 loader 都应 False。"""
    override_vendor_root(tmp_path / "empty_vendor")
    loaders = all_loaders()
    for loader in loaders:
        assert loader.is_available() is False
        assert loader.try_load() is None


def test_try_load_returns_none_when_dir_exists_but_empty(tmp_path):
    """目录存在但是没文件 → is_available False, try_load None。"""
    override_vendor_root(tmp_path / "empty_subdirs")
    for loader in all_loaders():
        loader.vendor_dir.mkdir(parents=True, exist_ok=True)
        assert loader.is_available() is False
        assert loader.try_load() is None


def test_try_load_raises_nothing_on_missing_files(tmp_path):
    """try_load 在缺失权重时**绝对不能**抛异常 — 这是降级设计。"""
    override_vendor_root(tmp_path / "nothing")
    for loader in all_loaders():
        # 不调用 is_available(),直接 try_load;若实现里先检查再 load,也应该 OK
        result = loader.try_load()
        assert result is None


# ---------------------------------------------------------------------------
# 3. 真有合法权重文件时(用 tmp_path 写小文件模拟) try_load 应成功
# ---------------------------------------------------------------------------

def _make_fake_safetensors(path: Path, size_mb: int = 2) -> None:
    """写一个 2MB 二进制占位文件(Phase 4 L4:阈值已注入 1MB,写 2MB 通过 _check_magic 的 size > 1MB 检查)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    os.truncate(path, size_mb * 1024 * 1024)


def _make_fake_h5(path: Path, size_mb: int = 1) -> None:
    """写一个 1MB HDF5 magic 占位文件(Phase 4 L4)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    magic = b"\x89HDF\r\n\x1a\n"
    path.write_bytes(magic)
    os.truncate(path, size_mb * 1024 * 1024)


def _make_fake_pt(path: Path, size_mb: int = 1) -> None:
    """写一个 1MB zip magic 占位文件(Phase 4 L4)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("dummy.txt", "x")
    os.truncate(path, size_mb * 1024 * 1024)


def test_try_load_succeeds_with_fake_esm2(tmp_path, monkeypatch):
    override_vendor_root(tmp_path / "vendor_models")
    # L4:临时降阈值到 1MB,case 写 1MB 即可触发
    monkeypatch.setattr(ESM2Loader, "min_size_mb", 1)
    esm2 = ESM2Loader()
    _make_fake_safetensors(esm2.vendor_dir / "model.safetensors")  # 默认 1MB

    handle = esm2.try_load()
    assert handle is not None
    assert handle.name == "esm2-150m"
    assert handle.format_hint == "safetensors"
    assert handle.size_bytes >= 1 * 1024 * 1024


def test_try_load_succeeds_with_fake_spliceai(tmp_path, monkeypatch):
    override_vendor_root(tmp_path / "vendor_models")
    monkeypatch.setattr(SpliceAILoader, "min_size_mb", 1)
    spliceai = SpliceAILoader()
    _make_fake_h5(spliceai.vendor_dir / "SpliceAI_hg38_model.h5")  # 默认 1MB

    assert spliceai.is_available() is True
    handle = spliceai.try_load()
    assert handle is not None
    assert handle.format_hint == "h5"


def test_try_load_succeeds_with_fake_splice_transformer(tmp_path, monkeypatch):
    override_vendor_root(tmp_path / "vendor_models")
    monkeypatch.setattr(SpliceTransformerLoader, "min_size_mb", 1)
    st = SpliceTransformerLoader()
    _make_fake_pt(st.vendor_dir / "model.pt")  # 默认 1MB

    assert st.is_available() is True
    handle = st.try_load()
    assert handle is not None
    assert handle.format_hint == "pt"


# ---------------------------------------------------------------------------
# 4. summary() 报告结构稳定
# ---------------------------------------------------------------------------

def test_summary_keys_present(tmp_path):
    override_vendor_root(tmp_path / "empty")
    s = summary()
    assert "esm2-150m" in s
    assert "spliceai" in s
    assert "splice-transformer" in s
    for name, info in s.items():
        assert "available" in info
        assert info["available"] is False
        assert "model_size_mb_expected" in info
        assert "vendor_dir" in info


def test_summary_marks_available_when_file_present(tmp_path):
    override_vendor_root(tmp_path / "vendor")
    esm2 = ESM2Loader()
    _make_fake_safetensors(esm2.vendor_dir / "model.safetensors", size_mb=600)

    s = summary()
    assert s["esm2-150m"]["available"] is True
    assert s["spliceai"]["available"] is False
    assert s["splice-transformer"]["available"] is False
    assert s["esm2-150m"]["file_count"] == 1


# ---------------------------------------------------------------------------
# 5. Phase 4 A2:GGUF magic byte bug + 加载失败显式化
# ---------------------------------------------------------------------------

def test_gguf_magic_correct_is_v3():
    """GGUF v3 真文件头 = b"\x03GGUF"(version_byte + "GGUF")。

    之前的 b"GGUF" 漏了版本号,真模型加载会失败。本测试 pin 住正确值。
    """
    assert _MAGIC_BYTES[".gguf"] == b"\x03GGUF"
    # 其它扩展名不应被这次修改影响
    assert _MAGIC_BYTES[".h5"] == b"\x89HDF\r\n\x1a\n"
    assert _MAGIC_BYTES[".hdf5"] == b"\x89HDF\r\n\x1a\n"
    assert _MAGIC_BYTES[".pt"] == b"PK\x03\x04"
    assert _MAGIC_BYTES[".pth"] == b"PK\x03\x04"
    assert _MAGIC_BYTES[".keras"] == b"PK\x03\x04"


def test_gguf_try_load_wrong_magic_raises(tmp_path):
    """Phase 4 A2: 写一个 magic 错的 .gguf 文件(模拟下载中断 / 文件损坏),
    基类 `try_load` 必须显式抛 LLMUnavailable,**不能**静默返回 None。

    之前 magic 不匹配是 `continue` + warn,玩家根本不知道文件坏了。
    修复后跟 P0-A2 一致:不静默退化,显式抛错让上游 router 区分
    "文件损坏" vs "未下载"。
    """
    from app.llm.loader import LLMUnavailable
    from app.models.loader import ModelLoader

    class _FakeGGUFLoader(ModelLoader):
        """最小 loader,只为了触发基类 try_load 的 GGUF magic 校验分支。"""

        name = "fake-gguf"
        subdir_name = "fake-gguf"
        model_size_mb = 100
        min_size_mb = 1  # 1MB 即可触发 is_available()

        def _candidate_files(self) -> list[Path]:
            return [self.vendor_dir / "model.gguf"]

    override_vendor_root(tmp_path / "vendor")
    loader = _FakeGGUFLoader()
    loader.vendor_dir.mkdir(parents=True, exist_ok=True)

    # 写一个 2MB 的"假 GGUF":magic 用 b"GGUF"(老错误值)模拟损坏
    fake_path = loader.vendor_dir / "model.gguf"
    fake_path.write_bytes(b"GGUF" + b"\x00" * (2 * 1024 * 1024 - 4))

    # is_available 应为 True(大小 >= 1MB)
    assert loader.is_available() is True
    # try_load 必须显式抛 LLMUnavailable,**不是** warn + return None
    with pytest.raises(LLMUnavailable, match="magic"):
        loader.try_load()
