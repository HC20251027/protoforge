"""Phase 4 C1 regression:确保 ruff check 0 错,防止未来再堆 F401。"""
import subprocess
import sys
from pathlib import Path


def test_ruff_check_passes():
    repo_root = Path(__file__).resolve().parents[3]
    api_dir = repo_root / "apps" / "api"
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(api_dir / "app")],
        cwd=str(api_dir),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"ruff check failed:\n{result.stdout}\n{result.stderr}\n"
        "Phase 4 C1 验收:此测试必须通过,如失败说明引入了未用 import 或其他 ruff 错误"
    )
