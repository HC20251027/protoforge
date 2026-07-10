"""Phase 4 A3 落地验证:删 detect_hardware 残留后,proto 包不应再导出任何
与硬件探测相关的符号。`from app.proto import *` 必须不抛 ImportError。
"""
from __future__ import annotations

import importlib

import pytest


def test_proto_module_exports_no_hardware() -> None:
    """`from app.proto import *` 不抛 ImportError,且不导出硬件相关符号。"""
    # 1) `import *` 走一遍:__all__ 里的每个名字都得能解析,不能 ImportError
    proto = importlib.import_module("app.proto")
    exported_names = list(getattr(proto, "__all__", []))
    for name in exported_names:
        assert hasattr(proto, name), (
            f"app.proto.__all__ 含 {name!r},但模块上找不到该属性"
        )

    # 2) 模拟业务侧 `from app.proto import <hardware_name>`,要求 ImportError。
    #    真实 `from X import Y` 由 CPython 的 _handle_fromlist 处理,这里用
    #    exec 在干净命名空间里直接执行 import 语句,触发真实 ImportError 路径。
    forbidden = ("detect_hardware", "recommend_ritual", "HardwareProfile")
    for name in forbidden:
        ns: dict = {}
        with pytest.raises(ImportError):
            exec(f"from app.proto import {name}", ns)
        # 同时模块上不应再有该属性
        assert not hasattr(proto, name), (
            f"app.proto 不应再暴露 {name!r},但模块属性里仍能找到它"
        )
