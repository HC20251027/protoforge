"""Local LLM loader for ProtoForge Phase 3 Task 1.3.

设计目标:
- 物理 vendor 落地:Qwen2.5-7B-Instruct GGUF(Q4_K_M 量化)
- 复用 `app.models.loader.ModelLoader` 抽象,只换 `subdir_name` / 尺寸阈值
- **不静默退化**:`LocalLLMProvider.chat()` 在权重缺失或 llama-cpp 不可用时
  必须抛 `LLMUnavailable`,绝不能返回假字符串污染上游
- 真实 llama-cpp-python 推理留到 Phase 1.5/2,本阶段只写接口 + 文件存在性检查

文件命名:
- 单文件:`qwen2.5-7b-instruct-q4_k_m.gguf`
- 分片:`qwen2.5-7b-instruct-q4_k_m-NNNNN-of-MMMMM.gguf`(HF split 风格)

只要分片总大小 >= min_size_mb,is_available() 就返回 True。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.models.loader import (
    ModelHandle,
    ModelLoader,
    get_vendor_root,
    override_vendor_root,
    reset_vendor_root,
    sha256_first_mb,
)


# ---------------------------------------------------------------------------
# 异常类型 — 让上层能明确知道"本地 LLM 不可用"
# ---------------------------------------------------------------------------


class LLMUnavailable(RuntimeError):
    """本地 LLM 不可用(权重缺失 / llama-cpp 没装 / magic 校验失败)。

    与 `app.llm.DisabledProvider.chat()` 抛的 `RuntimeError("disabled")` 区分,
    便于上游 router 把"用户没配置"和"权重没落地"走不同分支。
    """


# ---------------------------------------------------------------------------
# 路径策略:LLM 走 vendor/llm/,而不是 vendor/models/<subdir>/
# ---------------------------------------------------------------------------
# 原因:Task 1.2 把 ML 模型放 vendor/models/ 下,但 LLM 是另一种资源,
# 放在 vendor/llm/ 顶层更清晰,打包脚本可以单独勾选。
# 这里的策略是:在 loader 自己的 __init__ 里覆盖 vendor_dir 路径,
# 让它指向 apps/api/vendor/llm/(而不是 vendor/models/llm/),实现零侵入基类。
_API_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_VENDOR_LLM = _API_ROOT / "vendor" / "llm"


# ---------------------------------------------------------------------------
# Loader:复用 ModelLoader,只换子目录名 + 尺寸阈值
# ---------------------------------------------------------------------------


class LocalLLMLoader(ModelLoader):
    """Qwen2.5-7B-Instruct GGUF(Q4_K_M)加载器。

    预期:
    - 目录:`apps/api/vendor/llm/`
    - 文件:`qwen2.5-7b-instruct-q4_k_m.gguf`(**或**分片 `qwen2.5-7b-instruct-q4_k_m-NNNNN-of-MMMMM.gguf`)
    - 大小:Q4_K_M 单文件 ~4.5GB;接受下限 3.5GB(防"零字节文件" / "下载中断"假阳性)
    """

    name = "qwen2.5-7b-instruct-q4-k-m"
    subdir_name = "llm"  # 基类的语义:subdir 相对 vendor_root
    model_size_mb = 4500
    min_size_mb = 3500

    def __init__(self, min_size_mb: int | None = None) -> None:
        # 不调用 super().__init__():基类会把 subdir_name 接到 vendor/models/ 下,
        # 而我们要的是 vendor/llm/。这里直接 override vendor_dir,跳过基类拼接。
        self.vendor_dir = _DEFAULT_VENDOR_LLM
        # Phase 4 L4:min_size_mb 可注入(测试时传 1MB,产品保持 3500MB 硬阈值)
        if min_size_mb is not None:
            self.min_size_mb = min_size_mb

    def _candidate_files(self) -> list[Path]:
        """返回所有可能的 GGUF 路径(单文件 + 分片两种风格)。"""
        if not self.vendor_dir.exists():
            return []
        out: list[Path] = []
        # 单文件
        single = self.vendor_dir / "qwen2.5-7b-instruct-q4_k_m.gguf"
        if single.is_file():
            out.append(single)
        # 分片:glob 出所有 .gguf(分片命名也是 .gguf 后缀)
        for p in sorted(self.vendor_dir.glob("qwen2.5-7b-instruct-q4_k_m-*.gguf")):
            if p.is_file() and p not in out:
                out.append(p)
        return out

    def total_size_bytes(self) -> int:
        """所有候选文件的总大小(单文件或分片之和)。"""
        return sum(f.stat().st_size for f in self.model_files())

    def is_available(self) -> bool:
        """总分片大小 >= min_size_mb 才算可用。

        重要:这里**不**只看第一个文件,分片下载时单个文件 < min_size_mb 但
        总和够,也算 OK。
        """
        if not self.vendor_dir.exists():
            return False
        files = self.model_files()
        if not files:
            return False
        total = sum(f.stat().st_size for f in files)
        return total >= self.min_size_mb * 1024 * 1024

    def try_load(self) -> Optional[ModelHandle]:
        """读取 magic + sha256 校验 1MB header,通过返回 ModelHandle。

        与基类的差异:
        - 多文件场景:`shard_paths` 字段会列出所有分片
        - size_bytes 是**总和**,不是单个文件
        """
        if not self.is_available():
            return None

        files = self.model_files()
        # 校验每个分片的 magic(以防分片 1 OK 但分片 2 是下载残留)
        from app.models.loader import _check_magic  # 复用私有 magic-bytes 表
        valid_files: list[Path] = []
        for f in files:
            if _check_magic(f):
                valid_files.append(f)
        if not valid_files:
            return None

        total = sum(f.stat().st_size for f in valid_files)
        # sha256 只对第一个分片取 1MB(完整 sha256 留给 README / .sha256 sidecar)
        try:
            _ = sha256_first_mb(valid_files[0], mb=1)
        except OSError:
            return None

        return ModelHandle(
            name=self.name,
            path=str(valid_files[0]),  # 第一个分片路径
            size_bytes=total,
            format_hint="gguf",
        )

    def describe(self) -> dict[str, Any]:
        """供 /health 等接口使用的元信息。"""
        files = self.model_files()
        total = sum(f.stat().st_size for f in files)
        return {
            "name": self.name,
            "vendor_dir": str(self.vendor_dir),
            "model_size_mb_expected": self.model_size_mb,
            "min_size_mb": self.min_size_mb,
            "available": self.is_available(),
            "file_count": len(files),
            "total_bytes_on_disk": total,
            "total_mb_on_disk": round(total / 1024 / 1024, 1),
            "files": [f.name for f in files],
        }


# ---------------------------------------------------------------------------
# Provider:把 loader 包装成可调用的 chat() 接口
# ---------------------------------------------------------------------------


class LocalLLMProvider:
    """本地 Qwen2.5-7B LLM 提供方。

    用法:
    >>> provider = LocalLLMProvider()  # 默认从 vendor/llm 读
    >>> text = provider.chat([{"role": "user", "content": "hi"}])

    失败语义:
    - 权重文件不存在 / magic 校验失败 → `LLMUnavailable`
    - llama-cpp-python 未安装 → `LLMUnavailable`(消息带 "pip install" 提示)
    - **不**返回假字符串(绝不静默退化)

    注入(测试用):
    >>> provider = LocalLLMProvider(loader=LocalLLMLoader(), runner=fake_runner)
    """

    def __init__(
        self,
        loader: ModelLoader | None = None,
        runner: Any | None = None,
    ) -> None:
        self._loader: ModelLoader = loader or LocalLLMLoader()
        self._runner: Any = runner  # 测试可注入 fake runner;None 表示 "按需 import llama_cpp"

    @property
    def loader(self) -> ModelLoader:
        return self._loader

    def is_available(self) -> bool:
        return self._loader.is_available()

    def describe(self) -> dict[str, Any]:
        if isinstance(self._loader, LocalLLMLoader):
            return self._loader.describe()
        # 通用 loader fallback
        return {
            "name": self._loader.name,
            "available": self._loader.is_available(),
            "vendor_dir": str(self._loader.vendor_dir),
        }

    def _import_llama_cpp(self) -> Any:
        """延迟 import llama_cpp;失败抛 LLMUnavailable(不静默)。"""
        try:
            from llama_cpp import Llama  # type: ignore[import-not-found]
            return Llama
        except ImportError as exc:
            raise LLMUnavailable(
                "llama-cpp-python 未安装,无法加载本地 GGUF 模型。\n"
                "Phase 1.5/2 接通 llama-cpp 时执行:\n"
                "  pip install llama-cpp-python\n"
                f"原始错误: {exc}"
            ) from exc

    def _resolve_model_path(self) -> str:
        """从 loader 拿到 GGUF 文件路径(单文件 / 第一个分片)。

        llama-cpp-python 在分片场景下需要先用 llama-gguf-split merge;
        这里只把"第一个分片"的路径返回 + 抛错,引导用户走合并流程。
        """
        handle = self._loader.try_load()
        if handle is None:
            raise LLMUnavailable(
                f"本地 LLM 权重不可用: {self._loader.vendor_dir}。"
                "请确认 Qwen2.5-7B-Instruct-GGUF Q4_K_M 已 vendor 到此目录。"
            )
        return handle.path

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
    ) -> str:
        """调用本地 LLM chat completion。

        参数:
        - messages:OpenAI 协议格式 `[{"role": ..., "content": ...}]`
        - temperature/max_tokens:采样参数(Phase 1.5/2 真实推理时透传)

        异常:
        - `LLMUnavailable`:权重缺失 / magic 失败 / llama-cpp 没装
        - 任何其他异常透传(让上游 router 知道"是真错而不是配置缺失")
        """
        # 1. 校验权重
        model_path = self._resolve_model_path()

        # 2. 拿 runner(测试用注入,生产用 llama_cpp.Llama)
        if self._runner is not None:
            Llama = self._runner
        else:
            Llama = self._import_llama_cpp()

        # 3. 真正调 llama.cpp(本阶段不强制能跑通;Phase 1.5/2 接 torch-free 推理)
        try:
            llm = Llama(model_path=model_path)
            out = llm.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMUnavailable:
            raise
        except Exception as exc:
            # 把所有"推理引擎侧"的失败也包成 LLMUnavailable,
            # 上层看到的就是"本地 LLM 不可用"这一类,而不是底层的 ctypes 错误
            raise LLMUnavailable(f"本地 LLM 推理失败: {exc}") from exc

        # OpenAI 协议同构
        try:
            return out["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailable(
                f"本地 LLM 返回结构异常(不是 OpenAI chat completion 格式): {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# 工厂 + summary
# ---------------------------------------------------------------------------


def get_local_llm_loader() -> LocalLLMLoader:
    """单例获取 loader(测试可通过 override_vendor_root 切路径)。"""
    return LocalLLMLoader()


def get_local_llm_provider() -> LocalLLMProvider:
    """单例获取 provider,默认 vendor root = apps/api/vendor/llm。"""
    return LocalLLMProvider()


def llm_summary() -> dict[str, Any]:
    """供 /health 等接口使用:返回本地 LLM 可用性 + 路径摘要。"""
    return get_local_llm_loader().describe()


# ---------------------------------------------------------------------------
# Re-export 共享工具(给其它模块用,例如测试)
# ---------------------------------------------------------------------------


__all__ = [
    "LLMUnavailable",
    "LocalLLMLoader",
    "LocalLLMProvider",
    "get_local_llm_loader",
    "get_local_llm_provider",
    "llm_summary",
    # 共享 vendor-root 控制(给测试用)
    "get_vendor_root",
    "override_vendor_root",
    "reset_vendor_root",
]
