#!/usr/bin/env python3
"""校验 ProtoForge vendor 资源(vendor/proto-language + vendor/models + vendor/llm)的 SHA256。

遍历 `apps/api/vendor/` 找所有 `.sha256` 文件,对每个文件用 GNU `sha256sum -c` 兼容格式
校验(避免重复造哈希实现)。

用法:
    uv run python scripts/verify_vendor.py                  # 跑全部
    uv run python scripts/verify_vendor.py --skip-llm        # 跳过 LLM(快,~几秒)
    uv run python scripts/verify_vendor.py --only esm2-150m  # 只校验某个

注意:
- 不下载 vendor 资源(README.md + sha256 已在 git,实际权重在本地)
- 不生成 sha256(只校验)
- 跳过没有对应权重文件的 sha256(占位 README,例如 SpliceAI / SpliceTransformer)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = REPO_ROOT / "apps" / "api" / "vendor"

# 4.36GB LLM 校验会耗磁盘 IO,默认只跑 ESM2 + proto-language(已写完的部分)。
DEFAULT_SKIP_LLM = False


def parse_sha256_file(sha256_path: Path) -> list[tuple[str, str]]:
    """读 `<hash>   <filename>` 格式(支持多行)。"""
    pairs: list[tuple[str, str]] = []
    for line in sha256_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 格式:<hex64><whitespace><file>
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            print(f"  ⚠️  跳过非法行: {line!r}", file=sys.stderr)
            continue
        pairs.append((parts[0].lower(), parts[1].strip()))
    return pairs


def compute_sha256(file_path: Path, chunk: int = 1024 * 1024) -> str:
    """流式算 SHA256(大文件不爆内存)。"""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def verify_one(sha256_path: Path) -> tuple[int, int, int]:
    """校验一个 .sha256 文件。返回 (ok, missing, mismatch)。"""
    pairs = parse_sha256_file(sha256_path)
    ok = missing = mismatch = 0
    for expected, filename in pairs:
        file_path = sha256_path.parent / filename
        if not file_path.exists():
            print(f"  ✗ 缺失: {filename}")
            missing += 1
            continue
        actual = compute_sha256(file_path)
        if actual.lower() == expected.lower():
            size_mb = file_path.stat().st_size / 1024 / 1024
            print(f"  ✓ {filename} ({size_mb:.1f} MB)")
            ok += 1
        else:
            print(f"  ✗ 不匹配: {filename}")
            print(f"     期望: {expected}")
            print(f"     实际: {actual}")
            mismatch += 1
    return ok, missing, mismatch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="跳过 vendor/llm/ 校验(快,只跑 ESM2 / proto-language)",
    )
    parser.add_argument(
        "--only",
        type=str,
        help="只校验包含此字符串的 vendor 子目录(例如 esm2-150m)",
    )
    args = parser.parse_args()

    if not VENDOR_ROOT.exists():
        print(f"✗ vendor 目录不存在: {VENDOR_ROOT}", file=sys.stderr)
        return 1

    # 找所有 .sha256
    sha256_files = sorted(VENDOR_ROOT.rglob("*.sha256"))
    if not sha256_files:
        print("⚠️  未找到任何 .sha256 文件")
        return 0

    total_ok = total_missing = total_mismatch = 0
    for sha256_path in sha256_files:
        rel = sha256_path.relative_to(VENDOR_ROOT)
        # 过滤
        if args.skip_llm and "llm" in rel.parts:
            print(f"⏭  跳过(LLM): {rel}")
            continue
        if args.only and args.only not in str(rel):
            continue

        print(f"\n📦 {rel}")
        ok, missing, mismatch = verify_one(sha256_path)
        total_ok += ok
        total_missing += missing
        total_mismatch += mismatch

    print(f"\n{'='*50}")
    print(f"✓ {total_ok} 个文件校验通过")
    if total_missing:
        print(f"✗ {total_missing} 个文件缺失(可能权重未下载,README.md 占位)")
    if total_mismatch:
        print(f"✗ {total_mismatch} 个文件哈希不匹配(可能下载损坏,重新下载)")

    return 0 if total_mismatch == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
