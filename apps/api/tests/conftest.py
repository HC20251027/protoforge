"""pytest fixtures。

包含一个 session-scope 共享 fake 模型文件 fixture,
跑一次 pytest 只写 1 次 3.6GB sparse 文件,
所有测试 case 复用,不再每个 case 写 4GB 假文件。
"""
import os
import sys
from pathlib import Path

import pytest

# 把 apps/api 加到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def shared_fake_gguf(tmp_path_factory) -> Path:
    """session 级共享 fake GGUF 所在目录(隔离子目录,不影响 vendor_dir 行为)。

    预写 3 个 sparse 文件(单文件 + 2 分片)到 `_shared/` 子目录,
    不污染 `_isolate_loader_path` 指向的 vendor 目录(那个目录测试假定为空)。

    实现:
      - 用 tmp_path_factory.mktemp 拿 session 级临时目录
      - 写 4 字节 magic + os.truncate 伸长(NTFS sparse,不真占盘)
      - yield _shared/ 目录路径
      - session 结束 tmp_path_factory 自动清理整个目录

    历史:Phase 4 C 段之前每个 case function-scope 写 4GB 假文件,
    单次跑 pytest = 15GB 假文件 × N 次跑 = 上百 GB,把 C 盘顶到 2GB。
    """
    base = tmp_path_factory.mktemp("shared_fake_gguf")
    shared_dir = base / "_shared"
    shared_dir.mkdir()
    files = {
        "single": shared_dir / "qwen2.5-7b-instruct-q4_k_m.gguf",
        "shard1": shared_dir / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
        "shard2": shared_dir / "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf",
    }
    for name, p in files.items():
        p.write_bytes(b"\x03GGUF")
        size_mb = 3600 if name == "single" else 1800
        os.truncate(p, size_mb * 1024 * 1024)
    yield shared_dir


# 注意:_isolate_loader_path 由 test_local_llm.py 内的 autouse fixture 负责
# conftest.py 只提供 session-scope shared_fake_gguf (供未来需要复用时显式注入)
