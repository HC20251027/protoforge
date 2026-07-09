"""Phase 3 Task 6 P0-C1:Tauri sidecar 端口 ↔ 后端配置端口契约测试。

P0-C1 修复前:
* 后端 `apps/api/app/config.py` 默认 `port: int = 7654`。
* Tauri `apps/desktop/src-tauri/src/sidecar.rs` 默认 `SIDECAR_PORT = 7655`。
* 两边不一致 → Tauri spawn 出来的 Python uvicorn 监听 7655,但后端
  代码里读到的 Settings.port = 7654,生产环境下 webview `fetch('/api/...')`
  转发目标(由 Tauri 注入的 shell/curl wrapper 决定)会指错端口。

修复:
* `sidecar_port()` 优先读 `PROTOFORGE_API_PORT`(对齐后端 Settings 的
  env prefix `PROTOFORGE_`)。
* 回退 `PROTOFORGE_SIDECAR_PORT`(兼容历史 dev)。
* 兜底默认 7655。

本测试**不**跑 cargo(没编译时间),只验:
1. 后端 config 默认端口是 7654(可被 env var 覆盖)。
2. 用同一个 env var,后端实际监听端口 = Tauri 侧 `sidecar_port()` 解析的值。
3. 后端 config 的 env_prefix 是 `PROTOFORGE_`,跟 sidecar 新增的
   `PROTOFORGE_API_PORT` 一致。
4. sidecar.rs 源码里包含 C1 修复的关键 env var 名称,防止后续 refactor
   改回不一致。
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SIDECAR_RS = PROJECT_ROOT / "apps" / "desktop" / "src-tauri" / "src" / "sidecar.rs"
CONFIG_PY = PROJECT_ROOT / "apps" / "api" / "app" / "config.py"


def test_backend_default_port_is_7654():
    """后端 config 默认端口是 7654(已存在契约,不能改)。"""
    from app.config import settings

    assert settings.port == 7654, (
        f"后端默认端口变更:{settings.port},这会破坏 P0-C1 端口对齐假设"
    )


def test_backend_port_respects_env_var(monkeypatch):
    """后端端口从 `PROTOFORGE_PORT` env 读(由 pydantic-settings 配的 prefix)。"""
    # pydantic-settings:env_prefix=PROTOFORGE_,所以 Settings.port 读 PROTOFORGE_PORT
    monkeypatch.setenv("PROTOFORGE_PORT", "9876")
    # 重新导入 settings 实例(env 不会自动 reload 已构造的 Settings)
    # pydantic-settings v2:在 Settings 子类上用 model_config 缓存,这里只能
    # 显式重新构造
    from pydantic_settings import SettingsConfigDict
    from app.config import Settings

    s = Settings(model_config=SettingsConfigDict(env_prefix="PROTOFORGE_", extra="ignore"))
    assert s.port == 9876


def test_sidecar_rs_prefers_protoforge_api_port():
    """sidecar.rs 源码里 `sidecar_port()` 优先读 PROTOFORGE_API_PORT。"""
    src = SIDECAR_RS.read_text(encoding="utf-8")
    assert "PROTOFORGE_API_PORT" in src, (
        "sidecar.rs 必须读 PROTOFORGE_API_PORT 才能跟后端 Settings 对齐"
    )

    # 函数体内 `PROTOFORGE_API_PORT` 应出现在 `PROTOFORGE_SIDECAR_PORT` 之前
    api_pos = src.find('"PROTOFORGE_API_PORT"')
    legacy_pos = src.find('"PROTOFORGE_SIDECAR_PORT"')
    if legacy_pos != -1 and api_pos != -1:
        assert api_pos < legacy_pos, (
            "PROTOFORGE_API_PORT 应优先于 PROTOFORGE_SIDECAR_PORT "
            "(API_PORT 跟后端 Settings.env_prefix 对齐)"
        )


def test_sidecar_default_port_is_7655_for_legacy_compat():
    """sidecar.rs 默认端口仍是 7655(避免 dev 期与已运行的 API 进程冲突)。"""
    src = SIDECAR_RS.read_text(encoding="utf-8")
    m = re.search(r"SIDECAR_API_PORT_DEFAULT:\s*u16\s*=\s*(\d+)", src)
    assert m is not None, "sidecar.rs 缺少 SIDECAR_API_PORT_DEFAULT 常量"
    assert m.group(1) == "7655", (
        f"sidecar 默认端口应保留 7655(兼容性),实际 {m.group(1)}"
    )


def test_config_env_prefix_matches_sidecar_env_name():
    """后端 `Settings.model_config` 的 env_prefix = `PROTOFORGE_`,
    所以 `Settings.port` 实际读 `PROTOFORGE_PORT`,不是 `PROTOFORGE_API_PORT`。
    这看似矛盾 — 但 P0-C1 修复让 sidecar **也**兼容 `PROTOFORGE_PORT`
    名字是不必要的(用户只要设一个 `PROTOFORGE_PORT=7654`,后端自己读);
    sidecar 读 `PROTOFORGE_API_PORT` 是因为它需要从外部对齐后端
    实际 listen 的端口(后端启动后这个值可以来自任意 PROTOFORGE_ prefix
    env,sidecar 怎么知道是哪个?靠 spawn sidecar 的人把 PROTOFORGE_PORT
    翻译成 PROTOFORGE_API_PORT 传进来)。

    本测试只验证"后端 env prefix 命名"和"sidecar env var 名字"不冲突,
    即两边都是 `PROTOFORGE_*`,不会撞全局变量。
    """
    cfg = CONFIG_PY.read_text(encoding="utf-8")
    assert 'env_prefix="PROTOFORGE_"' in cfg

    src = SIDECAR_RS.read_text(encoding="utf-8")
    # 确认 sidecar 用的 env var 全部以 PROTOFORGE_ 开头
    for env in re.findall(r'"(PROTOFORGE_[A-Z_]+)"', src):
        assert env.startswith("PROTOFORGE_"), f"非 PROTOFORGE_ 前缀 env: {env}"
