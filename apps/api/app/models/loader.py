"""ML model weight loaders for ProtoForge Phase 3 Task 1.2.

设计目标:
- 物理 vendor 落地:不依赖 ML 框架(torch/biotite/transformers 都不要求安装)
- 优雅降级:`try_load()` 在权重文件不存在时返回 `None`,不抛异常
- 接口稳定:为 Phase 1.5/2 的真实 import 铺路,接口保持不变

每个 loader 内部:
- `is_available()`:文件存在 + 大小在合理区间
- `try_load()`:读取一小段 header(不加载全部)验证文件可读
- `model_size_mb`:声明预期大小(供打包预算计算)
"""
from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 路径常量(集中管理,避免散落)
# ---------------------------------------------------------------------------

# apps/api/app/models/loader.py → apps/api/
_API_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_VENDOR_MODELS = _API_ROOT / "vendor" / "models"

# 可被 override_vendor_root() 改写的当前 vendor root
# 注意:这里用一个 list 当 mutable holder,避免 global 在 import 时被 freeze
_vendor_root_holder: list[Path] = [_DEFAULT_VENDOR_MODELS]


def get_vendor_root() -> Path:
    """返回当前生效的 vendor root(测试可注入)。"""
    return _vendor_root_holder[0]


# 向后兼容:旧的 VENDOR_MODELS 名字仍可用,但实际是函数调用
def __getattr__(name: str) -> Any:
    if name == "VENDOR_MODELS":
        return get_vendor_root()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def override_vendor_root(path: str | os.PathLike[str]) -> None:
    """把 vendor root 重定向到指定路径(测试夹具用)。"""
    _vendor_root_holder[0] = Path(path)


def reset_vendor_root() -> None:
    """重置回默认路径(测试 teardown 用)。"""
    _vendor_root_holder[0] = _DEFAULT_VENDOR_MODELS


def sha256_first_mb(path: Path, mb: int = 1) -> str:
    """读取文件前 N MB 的 SHA256(用于完整性校验)。"""
    h = hashlib.sha256()
    chunk = 1024 * 1024
    target = mb * 1024 * 1024
    with path.open("rb") as f:
        read = 0
        while read < target:
            data = f.read(min(chunk, target - read))
            if not data:
                break
            h.update(data)
            read += len(data)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------

class ModelLoader(ABC):
    """统一 ML 模型加载器接口。

    三个实现:
    - `ESM2Loader`: facebook/esm2_t30_150M_UR50D
    - `SpliceAILoader`: Illumina/SpliceAI
    - `SpliceTransformerLoader`: biomap-research/SpliceTransformer

    本次 Phase 3 Task 1.2 只要求"权重物理落地 + 接口稳定",
    **不要求真的 import torch/biotite/transformers**。
    真实推理(把权重喂进模型)留给 Phase 1.5/2。
    """

    name: str = "abstract"
    subdir_name: str = ""
    vendor_dir: Path
    model_size_mb: int          # 预期大小(MB),用于 size check
    min_size_mb: int = 1        # 最小接受大小(MB),防止"零字节文件"被认作 OK

    def __init__(self) -> None:
        self.vendor_dir = get_vendor_root() / self.subdir_name

    @abstractmethod
    def _candidate_files(self) -> list[Path]:
        """返回这个模型目录里所有应该被识别的权重文件(glob 模式)。"""

    def is_available(self) -> bool:
        """权重文件存在 + 至少一个文件 size >= min_size_mb。"""
        if not self.vendor_dir.exists():
            return False
        for f in self._candidate_files():
            if f.is_file() and f.stat().st_size >= self.min_size_mb * 1024 * 1024:
                return True
        return False

    def model_files(self) -> list[Path]:
        """返回已落地的权重文件(供调试/打包脚本使用)。"""
        if not self.vendor_dir.exists():
            return []
        return [f for f in self._candidate_files() if f.is_file()]

    def try_load(self) -> Optional[Any]:
        """尝试读取权重文件并验证格式,失败返回 None。

        本次实现:
        - 读 1 MB header
        - 校验扩展名 + magic bytes(.safetensors / .h5 / .pt / .bin / .keras)
        - 不真加载全部权重(留给 Phase 1.5/2)
        """
        if not self.is_available():
            return None

        for f in self.model_files():
            try:
                if not _check_magic(f):
                    # magic 不匹配 → 显式失败(跟 P0-A2 一致:不静默退化)。
                    # 之前这里是 continue + warn,真 GGUF/H5/PT 损坏时会悄悄
                    # 退到"weights missing"分支,玩家根本不知道是文件坏了。
                    # 这里抛 LLMUnavailable,让上游 router 把"文件损坏"和
                    # "未下载"走不同分支处理。
                    # 注意:仅对 _check_magic 已知 magic 的扩展名(非 safetensors/
                    # bin/onnx/未知扩展名)走 raise 路径;后者 fallback 走 size 检查。
                    from app.llm.loader import LLMUnavailable
                    raise LLMUnavailable(
                        f"权重文件 magic 校验失败: {f} "
                        f"(扩展名 {f.suffix!r},期望 magic {_MAGIC_BYTES.get(f.suffix.lower())!r})"
                    )
                # 1MB 校验就够了,真加载留给后续阶段
                _ = sha256_first_mb(f, mb=1)
            except OSError:
                continue
            # 成功:返回"占位句柄",代表这个模型可用
            return ModelHandle(
                name=self.name,
                path=str(f),
                size_bytes=f.stat().st_size,
                format_hint=f.suffix.lstrip("."),
            )

        return None


class ModelHandle:
    """占位句柄,代表 try_load() 成功。Phase 1.5/2 会替换为真实模型对象。"""

    __slots__ = ("name", "path", "size_bytes", "format_hint")

    def __init__(self, name: str, path: str, size_bytes: int, format_hint: str) -> None:
        self.name = name
        self.path = path
        self.size_bytes = size_bytes
        self.format_hint = format_hint

    def __repr__(self) -> str:
        return f"<ModelHandle {self.name} path={self.path} size={self.size_bytes}>"


# ---------------------------------------------------------------------------
# 通用 magic-bytes 校验
# ---------------------------------------------------------------------------

_MAGIC_BYTES: dict[str, bytes] = {
    # safetensors: 8 字节小端无符号整数表示 header 长度,后跟 JSON
    # 没有固定 magic,但文件 >= 1MB 才认
    # h5 / hdf5: 固定 magic "\x89HDF\r\n\x1a\n"
    ".h5": b"\x89HDF\r\n\x1a\n",
    ".hdf5": b"\x89HDF\r\n\x1a\n",
    # pytorch .pt / .pth 通常是 zip header "PK\x03\x04"
    ".pt": b"PK\x03\x04",
    ".pth": b"PK\x03\x04",
    # ggml / gguf: 真 GGUF v3 文件头结构:
    #   4 字节 magic = version_byte(1 byte) + "GGUF"(3 bytes)
    #   例:GGUF v3 → b"\x03GGUF"  (版本号 3 在前,后跟 ASCII "GGUF")
    #   旧版 GGUF v1/v2 → b"\x01GGUF" / b"\x02GGUF"(已被 llama.cpp 弃用)
    # 之前的 b"GGUF" 是错的(漏了版本号),真模型加载时静默失败。
    ".gguf": b"\x03GGUF",
    # tensorflow keras: 也是 zip
    ".keras": b"PK\x03\x04",
}


def _check_magic(path: Path) -> bool:
    """检查文件头几个字节。空文件立刻拒。"""
    ext = path.suffix.lower()
    try:
        with path.open("rb") as f:
            header = f.read(8)
    except OSError:
        return False
    if not header:
        return False
    if ext in (".safetensors", ".bin", ".onnx"):
        # 没固定 magic,只要文件非空 + > 1MB 就当 OK
        return path.stat().st_size > 1024 * 1024
    if ext not in _MAGIC_BYTES:
        # 未知扩展名:只看文件大小
        return path.stat().st_size > 1024 * 1024
    expected = _MAGIC_BYTES[ext]
    return header.startswith(expected)


# ---------------------------------------------------------------------------
# 三个具体实现
# ---------------------------------------------------------------------------

class ESM2Loader(ModelLoader):
    """ESM2-150M safetensors(facebook/esm2_t30_150M_UR50D)。

    预期:
    - 文件:model.safetensors(~640 MB)
    - 大小:600-700 MB
    """

    name = "esm2-150m"
    subdir_name = "esm2-150m"
    model_size_mb = 640
    min_size_mb = 500

    def _candidate_files(self) -> list[Path]:
        return [
            self.vendor_dir / "model.safetensors",
            self.vendor_dir / "pytorch_model.bin",
            self.vendor_dir / "model.bin",
        ]


class SpliceAILoader(ModelLoader):
    """Illumina SpliceAI Keras 模型(基因组 hg38 / 100nt context)。

    预期:
    - 文件:SpliceAI_hg38_model.h5(~50 MB)
    - 大小:40-80 MB
    """

    name = "spliceai"
    subdir_name = "spliceai"
    model_size_mb = 50
    min_size_mb = 20

    def _candidate_files(self) -> list[Path]:
        return [
            self.vendor_dir / "SpliceAI_hg38_model.h5",
            self.vendor_dir / "spliceai.h5",
            self.vendor_dir / "model.h5",
        ]


class SpliceTransformerLoader(ModelLoader):
    """SpliceTransformer-base PyTorch checkpoint(biomap-research)。

    预期:
    - 文件:splice-transformer-base.ckpt 或 model.pt(~400 MB)
    - 大小:300-500 MB
    """

    name = "splice-transformer"
    subdir_name = "splice-transformer"
    model_size_mb = 400
    min_size_mb = 200

    def _candidate_files(self) -> list[Path]:
        return [
            self.vendor_dir / "model.pt",
            self.vendor_dir / "splice-transformer-base.ckpt",
            self.vendor_dir / "pytorch_model.bin",
        ]


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def all_loaders() -> list[ModelLoader]:
    """返回所有可用的 loader 实例。"""
    return [ESM2Loader(), SpliceAILoader(), SpliceTransformerLoader()]


def get_loader(name: str) -> Optional[ModelLoader]:
    """按名称查找 loader。"""
    for loader in all_loaders():
        if loader.name == name:
            return loader
    return None


def summary() -> dict[str, dict[str, Any]]:
    """返回所有模型的可用性摘要,供 /health 等接口使用。"""
    out: dict[str, dict[str, Any]] = {}
    for loader in all_loaders():
        files = loader.model_files()
        total_bytes = sum(f.stat().st_size for f in files)
        out[loader.name] = {
            "available": loader.is_available(),
            "vendor_dir": str(loader.vendor_dir),
            "model_size_mb_expected": loader.model_size_mb,
            "min_size_mb": loader.min_size_mb,
            "file_count": len(files),
            "total_bytes_on_disk": total_bytes,
            "files": [f.name for f in files],
        }
    return out
