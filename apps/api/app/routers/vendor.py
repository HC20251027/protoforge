"""Phase 3 Task 1.5 — vendor 资源状态查询端点。

设计目标:
- 引导页第 1 步需要知道三种 vendor 资源是否就位(proto-language / ML 模型 / 本地 LLM)
- 复用 `app.models.loader` 和 `app.llm.loader` 的 `is_available()` + `model_size_mb`
  抽象,不再发明新路径判定
- proto-language 没有 loader 抽象(Task 1.1 阶段没建),这里直接判定
  `vendor/proto-language/build/lib/proto_language/__init__.py` 是否存在

返回结构严格匹配前端 `VendorStatus` 类型,字段名保持 snake_case 便于
直接 `JSON.parse` 后字段一致。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.llm.loader import LocalLLMLoader
from app.models.loader import all_loaders

router = APIRouter()


# ---------------------------------------------------------------------------
# proto-language 路径策略
# ---------------------------------------------------------------------------
# apps/api/app/routers/vendor.py → apps/api/
_API_ROOT = Path(__file__).resolve().parents[2]
_PROTO_LANGUAGE_VENDOR_DIR = _API_ROOT / "vendor" / "proto-language"
_PROTO_LANGUAGE_BUILD_LIB = _PROTO_LANGUAGE_VENDOR_DIR / "build" / "lib" / "proto_language"


def _proto_language_status() -> dict[str, Any]:
    """检查 proto-language 源码是否 vendor 落地。

    判定逻辑:
    - `build/lib/proto_language/__init__.py` 必须存在(代表 python package 已经构建)
    - 整棵 `build/lib/proto_language/` 目录的总大小(粗略)代表"已就位"
    """
    if not _PROTO_LANGUAGE_BUILD_LIB.exists():
        return {
            "available": False,
            "size_mb": 0,
            "path": "vendor/proto-language/build/lib",
        }
    init_py = _PROTO_LANGUAGE_BUILD_LIB / "__init__.py"
    if not init_py.is_file():
        return {
            "available": False,
            "size_mb": 0,
            "path": "vendor/proto-language/build/lib",
        }

    # 粗略 size:遍历 build/lib 下的 .py 文件总和
    total_bytes = 0
    for p in _PROTO_LANGUAGE_BUILD_LIB.rglob("*.py"):
        try:
            total_bytes += p.stat().st_size
        except OSError:
            continue
    size_mb = round(total_bytes / 1024 / 1024, 1)
    return {
        "available": True,
        "size_mb": size_mb,
        "path": "vendor/proto-language/build/lib",
    }


def _ml_models_status() -> dict[str, dict[str, Any]]:
    """聚合所有 ML loader 的状态。

    返回:
        {
            "esm2-150m": {"available": ..., "size_mb": ..., "path": ...},
            "spliceai": {...},
            "splice-transformer": {...},
        }
    """
    out: dict[str, dict[str, Any]] = {}
    for loader in all_loaders():
        files = loader.model_files()
        total_bytes = sum(f.stat().st_size for f in files)
        size_mb = round(total_bytes / 1024 / 1024, 1) if files else 0
        # path 用相对 vendor 根的相对路径,跟前端约定一致
        try:
            rel_path = loader.vendor_dir.relative_to(_API_ROOT / "vendor").as_posix()
        except ValueError:
            rel_path = str(loader.vendor_dir)
        out[loader.name] = {
            "available": loader.is_available(),
            "size_mb": size_mb,
            "path": f"vendor/{rel_path}",
        }
    return out


def _local_llm_status() -> dict[str, Any]:
    """本地 LLM vendor 状态。复用 `LocalLLMLoader` 的所有逻辑。"""
    llm_loader = LocalLLMLoader()
    files = llm_loader.model_files()
    total_bytes = sum(f.stat().st_size for f in files)
    size_mb = round(total_bytes / 1024 / 1024, 1) if files else 0
    try:
        rel_path = llm_loader.vendor_dir.relative_to(_API_ROOT / "vendor").as_posix()
    except ValueError:
        rel_path = str(llm_loader.vendor_dir)
    return {
        "available": llm_loader.is_available(),
        "size_mb": size_mb,
        "path": f"vendor/{rel_path}",
        "model_name": "Qwen2.5-7B-Instruct-Q4_K_M",
    }


@router.get("/status")
def status() -> dict[str, Any]:
    """GET /api/vendor/status

    一次性返回三种 vendor 资源的状态,供引导页 step 1 渲染指示器使用。
    """
    return {
        "proto_language": _proto_language_status(),
        "ml_models": _ml_models_status(),
        "local_llm": _local_llm_status(),
    }
