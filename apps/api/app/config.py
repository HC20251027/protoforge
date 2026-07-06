"""应用配置。所有路径必须在项目目录内,不读 C 盘 AppData。"""
from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """解析项目根目录(避免硬编码绝对路径)。"""
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROTOFORGE_", env_file=".env", extra="ignore")

    # 服务
    host: str = "127.0.0.1"
    port: int = 7654

    # 路径(全部在项目目录)
    project_root: Path = _project_root()
    data_dir: Path = _project_root() / ".protoforge" / "data"
    programs_dir: Path = _project_root() / ".protoforge" / "programs"
    sequences_dir: Path = _project_root() / ".protoforge" / "sequences"
    models_dir: Path = _project_root() / ".protoforge" / "models"
    logs_dir: Path = _project_root() / ".protoforge" / "logs"
    db_path: Path = _project_root() / ".protoforge" / "data" / "protoforge.db"

    # Proto
    proto_profile: str = "auto"  # auto / gpu_8gb / gpu_24gb / cpu
    forge_timeout_sec: int = 120

    # LLM
    llm_provider: str = "disabled"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    def ensure_dirs(self) -> None:
        for d in [self.data_dir, self.programs_dir, self.sequences_dir, self.models_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
