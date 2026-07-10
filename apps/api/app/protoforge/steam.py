"""Steam Workshop 适配层(Phase 3 Task 5)。

**本任务用 mock,不接真实 steamworks**。

为什么 mock:
- 真实 Steam Workshop 上传需要:
  1. 玩家登录 Steam 客户端(本任务运行环境是 dev,可能没装)
  2. ProtoForge 自己的 Steam App ID(还没注册)
  3. `steamworks` Python 包(本任务禁止装新依赖)
- Phase 4 会:
  1. 装 `steamworks` (pip install steamworks)
  2. 改 `upload_item` 内部用 `Steamworks().workshop.create_item()` 替换 mock
  3. 改 `is_steam_running` 用真 `Steamworks().is_steam_running()`
  4. 改 `get_app_id` 返回真实 App ID
  5. 改 `get_item_url` 用 `https://steamcommunity.com/sharedfiles/filedetails/?id={real_id}`

详见 `steam.md`。

**设计意图**:
- 适配层(Adapter Pattern)把"游戏逻辑调用"和"Steam SDK 调用"解耦
- Phase 4 改适配层内部实现,业务代码(router / packager)零修改
- 玩家和 Steam 之间仍然有"游戏方注册 Steam App"这一关 — 跟具体实现无关
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("protoforge.steam")

# ProtoForge 自己的 Steam App ID(占位 0,真实发布时改)
DEFAULT_PROTOFORGE_APP_ID = 0


class SteamWorkshopUploader:
    """Steam Workshop 上传适配层(本任务用 mock)。

    使用方式:
        uploader = SteamWorkshopUploader()
        if uploader.is_steam_running():
            workshop_id = uploader.upload_item(path, title, description, tags)
        else:
            # 入队,等联网后重试
            ...
    """

    def __init__(self, app_id: int = DEFAULT_PROTOFORGE_APP_ID) -> None:
        self._app_id = app_id

    # ---------- Steam 环境检测 ----------

    def is_steam_running(self) -> bool:
        """检测 Steam 客户端是否在运行(Windows 下用 psutil 找 steam.exe 进程)。

        真实实现(Phase 4):用 `Steamworks().is_steam_running()`(steamworks 包)
        """
        try:
            import psutil  # type: ignore
        except ImportError:
            log.warning("psutil 不可用,is_steam_running 永远返回 False")
            return False

        try:
            for proc in psutil.process_iter(["name"]):
                name = (proc.info.get("name") or "").lower()
                # Windows 上 steam.exe;Linux 上 steam;macOS 上 Steam Helper
                if name in ("steam.exe", "steam", "steam helper"):
                    return True
        except Exception as exc:  # noqa: BLE001
            # psutil 在某些受限环境可能抛 AccessDenied
            log.debug("psutil process_iter 失败(降级为 False): %s", exc)
            return False
        return False

    # ---------- 配置 ----------

    def get_app_id(self) -> int:
        """返回 ProtoForge 自己的 Steam App ID(占位 0)。"""
        return self._app_id

    # ---------- 上传(mock) ----------

    def upload_item(
        self,
        file_path: Path,
        title: str,
        description: str,
        tags: list[str],
    ) -> str:
        """上传 .protoforge 文件到 Steam Workshop。

        **本任务用 mock** — 真实 steamworks 调用见 `steam.md`。
        Mock 实现:仅做基本校验(文件存在),然后生成 `mock_{uuid16}` 当 workshop_id。

        Args:
            file_path: 要上传的文件路径
            title: Workshop 标题
            description: Workshop 描述
            tags: 标签列表(Steam 上限 5 个)

        Returns:
            str: workshop_id(本任务里形如 `mock_abc123def456`)

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: tags 超过 5 个
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"file not found: {file_path}")

        # Steam Workshop 标签上限 5 个(防御性,玩家传多了截断)
        if len(tags) > 5:
            log.warning("tags 数量 %d 超过 5,截断", len(tags))
            tags = tags[:5]

        # Mock: 生成伪 workshop_id
        workshop_id = f"mock_{uuid.uuid4().hex[:16]}"

        log.info(
            "[MOCK STEAM] upload_item app_id=%d title=%r tags=%r workshop_id=%s file=%s",
            self._app_id,
            title,
            tags,
            workshop_id,
            file_path.name,
        )
        return workshop_id

    # ---------- URL 构造 ----------

    def get_item_url(self, workshop_id: str) -> str:
        """返回 Steam Workshop item URL。

        Args:
            workshop_id: Steam Workshop item ID

        Returns:
            str: 形如 `https://steamcommunity.com/sharedfiles/filedetails/?id=xxx`
        """
        return (
            f"https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}"
        )


# ---------------------------------------------------------------------------
# 单例(给 router 用,避免每次都 new)
# ---------------------------------------------------------------------------

_default_uploader: Optional[SteamWorkshopUploader] = None


def get_default_uploader() -> SteamWorkshopUploader:
    """单例 getter。"""
    global _default_uploader
    if _default_uploader is None:
        _default_uploader = SteamWorkshopUploader()
    return _default_uploader


def reset_default_uploader() -> None:
    """重置单例(测试用)。"""
    global _default_uploader
    _default_uploader = None


__all__ = [
    "SteamWorkshopUploader",
    "DEFAULT_PROTOFORGE_APP_ID",
    "get_default_uploader",
    "reset_default_uploader",
]
