"""Phase 3 Task 5: SteamWorkshopUploader (mock) 测试。"""
from pathlib import Path

import pytest

from app.protoforge.steam import (
    DEFAULT_PROTOFORGE_APP_ID,
    SteamWorkshopUploader,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def uploader() -> SteamWorkshopUploader:
    return SteamWorkshopUploader()


@pytest.fixture()
def fake_item(tmp_path: Path) -> Path:
    p = tmp_path / "test.protoforge"
    p.write_bytes(b"fake zip content")
    return p


# ---------------------------------------------------------------------------
# 测试 1:is_steam_running 在 mock 环境下返回 False
# ---------------------------------------------------------------------------


def test_is_steam_running_returns_false_in_test_env(uploader: SteamWorkshopUploader):
    """测试环境(没有真正的 Steam 客户端)→ 返回 False。"""
    # pytest 跑的时候不会有 steam.exe / steam 进程
    result = uploader.is_steam_running()
    assert result is False


# ---------------------------------------------------------------------------
# 测试 2:upload_item 返回 mock_workshop_id
# ---------------------------------------------------------------------------


def test_upload_item_returns_mock_workshop_id(uploader: SteamWorkshopUploader, fake_item: Path):
    """upload_item 必须返回 `mock_` 开头的 workshop_id。"""
    wid = uploader.upload_item(
        file_path=fake_item,
        title="Test Item",
        description="desc",
        tags=["protoforge", "test"],
    )
    assert wid.startswith("mock_")
    assert len(wid) == len("mock_") + 16  # mock_ + 16 hex chars


def test_upload_item_missing_file_raises(uploader: SteamWorkshopUploader):
    """upload_item 传入不存在的文件应抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        uploader.upload_item(
            file_path=Path("/tmp/does_not_exist.protoforge"),
            title="x",
            description="y",
            tags=[],
        )


# ---------------------------------------------------------------------------
# 测试 3:get_item_url 拼出正确 URL
# ---------------------------------------------------------------------------


def test_get_item_url_formats_correctly(uploader: SteamWorkshopUploader):
    """get_item_url 必须返回 Steam Workshop 标准 URL。"""
    url = uploader.get_item_url("1234567890")
    assert url == "https://steamcommunity.com/sharedfiles/filedetails/?id=1234567890"

    url2 = uploader.get_item_url("mock_abcdef1234567890")
    assert url2 == "https://steamcommunity.com/sharedfiles/filedetails/?id=mock_abcdef1234567890"


# ---------------------------------------------------------------------------
# 测试 4:get_app_id 默认 0(占位)
# ---------------------------------------------------------------------------


def test_get_app_id_default_is_placeholder(uploader: SteamWorkshopUploader):
    """默认 app_id 是 0(ProtoForge 还没在 Steam 注册,占位)。"""
    assert uploader.get_app_id() == 0
    assert DEFAULT_PROTOFORGE_APP_ID == 0


def test_get_app_id_custom():
    """可以传自定义 app_id。"""
    u = SteamWorkshopUploader(app_id=7654321)
    assert u.get_app_id() == 7654321


# ---------------------------------------------------------------------------
# 测试 5:tags 超过 5 个被截断
# ---------------------------------------------------------------------------


def test_upload_item_truncates_tags_over_limit(uploader: SteamWorkshopUploader, fake_item: Path):
    """Steam Workshop 标签上限 5 个,超过应截断(不抛错)。"""
    # 7 个 tag → 应截断到 5 个(不抛错)
    wid = uploader.upload_item(
        file_path=fake_item,
        title="t",
        description="d",
        tags=["a", "b", "c", "d", "e", "f", "g"],
    )
    assert wid.startswith("mock_")
