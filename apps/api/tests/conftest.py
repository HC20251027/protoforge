"""pytest fixtures。"""
import sys
from pathlib import Path

# 把 apps/api 加到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
