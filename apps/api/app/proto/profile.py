"""硬件档位检测与仪式推荐。"""
from __future__ import annotations
import subprocess
import shutil
import os
from dataclasses import dataclass


@dataclass
class HardwareProfile:
    gpu_name: str | None
    gpu_memory_mb: int
    cpu_cores: int
    ram_mb: int
    recommended_ritual: str
    recommended_models: list[str]


def detect_hardware() -> HardwareProfile:
    """探测本机硬件,推荐仪式名(急锻/标准锻/古法锻/晶种培育)。"""
    gpu_name = None
    gpu_mem = 0
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                timeout=5,
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            if out:
                name, mem = out.split(",")
                gpu_name = name.strip()
                gpu_mem = int(mem.strip().split()[0])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, IndexError):
            pass

    cpu_cores = os.cpu_count() or 4

    try:
        import psutil  # type: ignore
        ram_mb = psutil.virtual_memory().total // (1024 * 1024)
    except ImportError:
        ram_mb = 8192

    if gpu_mem >= 24000:
        ritual, models = "swift", ["Evo2-1B", "ESM2-650M", "AlphaGenome", "SpliceTransformer"]
    elif gpu_mem >= 8000:
        ritual, models = "standard", ["Evo2-1B", "ESM2-650M", "SpliceTransformer"]
    elif gpu_mem >= 4000:
        ritual, models = "ancient", ["SpliceTransformer", "ESM2-650M"]
    else:
        ritual, models = "crystal", ["SpliceTransformer"]

    return HardwareProfile(
        gpu_name=gpu_name,
        gpu_memory_mb=gpu_mem,
        cpu_cores=cpu_cores,
        ram_mb=ram_mb,
        recommended_ritual=ritual,
        recommended_models=models,
    )


def recommend_ritual(gpu_memory_mb: int) -> str:
    if gpu_memory_mb >= 24000:
        return "swift"
    if gpu_memory_mb >= 8000:
        return "standard"
    if gpu_memory_mb >= 4000:
        return "ancient"
    return "crystal"
