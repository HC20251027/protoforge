# Steam Workshop 适配层 — Phase 4 切换指南

本文件说明:`apps/api/app/protoforge/steam.py` 当前是 **mock 实现**,
Phase 4 切换到真实 Steam Workshop 上传时,改哪几行。

## 1. 装依赖

```bash
cd apps/api
.venv/Scripts/python.exe -m pip install steamworks
```

`steamworks` 包的 GitHub:https://github.com/philippj/steamworks

> Windows 上 `steamworks` 走 `pywin32` + `vdf` 路径,需先装 Visual Studio Build Tools。

## 2. 改 `apps/api/app/protoforge/steam.py`

### 2.1 改 `DEFAULT_PROTOFORGE_APP_ID`

```python
# 旧(占位):
DEFAULT_PROTOFORGE_APP_ID = 0

# 新(ProtoForge 在 Steamworks 注册后的真实 App ID):
DEFAULT_PROTOFORGE_APP_ID = 1234560  # 例子,实际填你申请到的
```

### 2.2 改 `is_steam_running()`

```python
def is_steam_running(self) -> bool:
    """Phase 4:用 steamworks 包的 is_steam_running() 替代 psutil 进程扫描。"""
    try:
        from steamworks import STEAMWORKS  # type: ignore
        return bool(STEAMWORKS.is_steam_running())
    except Exception as exc:
        log.warning("steamworks 调用失败(is_steam_running 降级为 False): %s", exc)
        return False
```

### 2.3 改 `upload_item()`

```python
def upload_item(
    self,
    file_path: Path,
    title: str,
    description: str,
    tags: list[str],
) -> str:
    """Phase 4:真实调用 ISteamUGC::SubmitItemUpdate。"""
    from steamworks import STEAMWORKS  # type: ignore

    if not file_path.exists():
        raise FileNotFoundError(f"file not found: {file_path}")

    # 1) 创建 Workshop item
    item_id = STEAMWORKS.workshop.create_item(
        app_id=self._app_id,
        title=title,
        description=description,
        tags=tags[:5],
    )
    if not item_id:
        raise RuntimeError("Steam Workshop create_item 返回空 id")

    # 2) 上传文件内容
    STEAMWORKS.workshop.update_item(
        item_id=item_id,
        content_path=str(file_path),
    )

    return str(item_id)
```

### 2.4 `get_item_url()` 不动

真实实现下,`workshop_id` 是 Steam 分配的整数字符串,URL 拼法不变。

## 3. 业务代码 0 改动

- `app/routers/forge.py` 里的通关上传 hook 不变 — 它只调适配层接口
- `app/routers/protoforge.py` 里的 queue retry 不变
- `app/protoforge/queue.py` 持久化不变
- `app/protoforge/packager.py` 打包不变

## 4. 验收清单(Phase 4)

- [ ] `pip install steamworks` 装好
- [ ] 修改 `DEFAULT_PROTOFORGE_APP_ID` 为真实 ID
- [ ] 实现 `is_steam_running()` 用 steamworks 包
- [ ] 实现 `upload_item()` 走 create_item + update_item
- [ ] 测试:Steam 没运行 → `is_steam_running` 返回 False(玩家会进队列)
- [ ] 测试:Steam 运行中 + 已登录 → 上传成功,返回真实 ID
- [ ] 测试:Steam 运行中 + 未登录 → 抛 `RuntimeError`,队列标 failed
- [ ] 本任务所有 189 passed 仍然通过
