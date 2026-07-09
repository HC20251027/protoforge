"""ProtoForge 子包:Phase 3 Task 5 - Steam 创意工坊自动上传。

提供 3 个模块:
- `packager`:`.protoforge` 文件打包/解包(给玩家作品存档用)
- `queue`    :离线待上传队列(JSON 持久化,联网后自动重试)
- `steam`    :Steam Workshop 适配层(本任务用 mock,Phase 4 接 steamworks)

决策:不引入新依赖(`psutil` 已在 venv 里 — 用于检测 steam.exe)。
所有产物在 `apps/api/data/` 目录下(.gitignore 屏蔽)。
"""
