"""ML model loader package。

本包集中管理 ProtoForge Phase 3 Task 1.2 中 vendor 的 ML 模型权重:
- ESM2-150M(facebook)
- SpliceAI(Illumina)
- SpliceTransformer-base(biomap-research)

本次 vendor 只要求"权重物理落地 + 加载器接口稳定",**不要求真加载**。
Phase 1.5/2 再接 torch/transformers/biotite 实现真实推理。
"""
from __future__ import annotations

from app.models.loader import (
    ESM2Loader,
    ModelHandle,
    ModelLoader,
    SpliceAILoader,
    SpliceTransformerLoader,
    all_loaders,
    get_loader,
    get_vendor_root,
    override_vendor_root,
    reset_vendor_root,
    summary,
)

__all__ = [
    "ESM2Loader",
    "ModelHandle",
    "ModelLoader",
    "SpliceAILoader",
    "SpliceTransformerLoader",
    "all_loaders",
    "get_loader",
    "get_vendor_root",
    "override_vendor_root",
    "reset_vendor_root",
    "summary",
]
