"""Onboarding 路由:列出 provider / 探测 / 持久化 / 引导页 3 步配置。

路由清单(按前缀 `/api/onboarding`):
- GET  /status            旧 Task 1.5 接口,列出 provider / 当前状态(LLM 调试用)
- POST /test              旧 Task 1.5 接口,探测某个 provider 可达性
- POST /save              旧 Task 1.5 接口,保存 provider 配置
- POST /reset             旧 Task 1.5 接口,重置 llm.json
- GET  /state             Phase 3 Task 4 — 引导页 3 步配置用:返回当前玩家状态
- POST /complete          Phase 3 Task 4 — 引导页 3 步配置用:接受 3 步表单提交
"""
from __future__ import annotations

import base64
import json
import os
import time
import warnings
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.llm import (
    OnboardingState,
    ProviderConfig,
    describe_providers,
    load_state,
    save_state,
    test_provider,
)
from app.schemas import (
    OnboardingCompleteResponse,
    OnboardingSave,
    OnboardingState as OnboardingStateSchema,
    OnboardingStatus,
    OnboardingSubmission,
    OnboardingTestRequest,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


# ---------------------------------------------------------------------------
# 旧 Task 1.5 接口(保持原样,不动)
# ---------------------------------------------------------------------------


def _state_to_status(state: OnboardingState) -> OnboardingStatus:
    return OnboardingStatus(
        active=state.active,
        providers=describe_providers(),
        config={
            name: {
                "name": cfg.name,
                "base_url": cfg.base_url,
                "model": cfg.model,
                "api_key_set": bool(cfg.api_key),
            }
            for name, cfg in state.providers.items()
        },
        last_test_at=state.last_test_at,
        last_test_ok=state.last_test_ok,
        last_test_message=state.last_test_message,
    )


@router.get("/status", response_model=OnboardingStatus)
def status() -> OnboardingStatus:
    return _state_to_status(load_state())


@router.post("/test")
def test(req: OnboardingTestRequest) -> dict:
    cfg = ProviderConfig(
        name=req.name,
        base_url=req.config.get("base_url", ""),
        model=req.config.get("model", ""),
        api_key=req.config.get("api_key", ""),
    )
    ok, msg = test_provider(req.name, cfg)  # type: ignore[arg-type]

    state = load_state()
    state.last_test_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    state.last_test_ok = ok
    state.last_test_message = msg
    save_state(state)
    return {"ok": ok, "message": msg, "tested_at": state.last_test_at}


@router.post("/save", response_model=OnboardingStatus)
def save(req: OnboardingSave) -> OnboardingStatus:
    state = load_state()
    state.active = req.active  # type: ignore[assignment]
    for name, raw in req.providers.items():
        if name in state.providers:
            existing = state.providers[name]
            state.providers[name] = ProviderConfig(
                name=name,  # type: ignore[arg-type]
                base_url=raw.get("base_url", existing.base_url),
                model=raw.get("model", existing.model),
                # 留空时保留旧 key(避免误清)
                api_key=raw.get("api_key") or existing.api_key,
                extra=raw.get("extra", existing.extra),
            )
    save_state(state)
    return _state_to_status(state)


@router.post("/reset", response_model=OnboardingStatus)
def reset() -> OnboardingStatus:
    from app.llm import _default_state, _CONFIG_PATH

    if _CONFIG_PATH.exists():
        _CONFIG_PATH.unlink()
    state = _default_state()
    save_state(state)
    return _state_to_status(state)


# ---------------------------------------------------------------------------
# Phase 3 Task 4: 引导页 3 步配置 + 持久化
# ---------------------------------------------------------------------------
#
# 设计决策:
# - 文件存到 `<settings.data_dir>/onboarding/{user_id}.json` (即 `<项目根>/.protoforge/data/onboarding/{user_id}.json`)
#   — 不写 C 盘,符合 "所有东西放在项目里面" 的规则
# - API key 必须加密或至少 base64 + 警告;本环境没装 cryptography,所以走 base64 降级路径
#   并在启动时打 UserWarning,README 写明
# - user_id 暂时从 query 参数读(`?user_id=...`),允许前端任意切账号;后续 Task 接 user system 时
#   改为 JWT 即可,不影响本接口的契约
# - 跨 user 隔离靠文件名,所有读/写都强校验 user_id 只能含字母数字下划线连字符
#

_ONBOARDING_DIR_NAME = "onboarding"
_KEY_FILE_NAME = ".protoforge_key"

# 这些字符之外不允许出现在 user_id 中(防止路径穿越)
_SAFE_USER_ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")


def _validate_user_id(user_id: str) -> str:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id 不能为空")
    if not all(c in _SAFE_USER_ID_CHARS for c in user_id):
        raise HTTPException(
            status_code=400, detail="user_id 只能包含字母数字下划线连字符点"
        )
    if len(user_id) > 64:
        raise HTTPException(status_code=400, detail="user_id 过长(>64)")
    return user_id


def _onboarding_dir() -> Path:
    """引导数据目录:<settings.data_dir>/onboarding/。"""
    d = Path(settings.data_dir) / _ONBOARDING_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _user_path(user_id: str) -> Path:
    """单用户的 onboarding 状态文件路径。"""
    return _onboarding_dir() / f"{user_id}.json"


# ---------------------------------------------------------------------------
# 加密层:优先 cryptography.fernet,降级到 base64 + 启动期 warning
# ---------------------------------------------------------------------------
#
# 降级策略:
# - 启动时尝试 import cryptography;成功 → 用 fernet
# - 失败 → 写 .protoforge_key 文本(包含 'BASE64_FALLBACK' 标记),用 base64 编码,启动期打 UserWarning
# - fernet key 也写到同文件,内容第一行以 'FERNET' 开头
#

_KEY_PATH = _onboarding_dir().parent / _KEY_FILE_NAME


def _ensure_key() -> tuple[str, bytes]:
    """确保 key 文件存在,返回 (mode, key_bytes)。

    mode = "fernet" | "base64"
    """
    env_key = os.environ.get("PROTOFORGE_KEY", "").strip()
    if env_key:
        # 环境变量优先:检测是不是 fernet key(44 字符 url-safe base64)
        try:
            from cryptography.fernet import Fernet  # type: ignore

            try:
                Fernet(env_key.encode("ascii"))
                return ("fernet", env_key.encode("ascii"))
            except Exception:  # noqa: BLE001
                # 不是合法的 fernet key → 当 base64 raw 字节用
                return ("base64", env_key.encode("utf-8"))
        except ImportError:
            return ("base64", env_key.encode("utf-8"))

    # 没环境变量 → 文件
    if _KEY_PATH.exists():
        text = _KEY_PATH.read_text(encoding="utf-8").strip()
        if text.startswith("FERNET:"):
            return ("fernet", text[len("FERNET:") :].strip().encode("ascii"))
        return ("base64", text.encode("utf-8"))

    # 文件不存在 → 尝试新建 fernet key,失败则 base64
    try:
        from cryptography.fernet import Fernet  # type: ignore

        new_key = Fernet.generate_key()
        _KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _KEY_PATH.write_text(f"FERNET:{new_key.decode('ascii')}\n", encoding="utf-8")
        try:
            os.chmod(_KEY_PATH, 0o600)
        except OSError:
            pass  # Windows 不一定支持
        return ("fernet", new_key)
    except ImportError:
        # 降级:用一个静态 warning 字符串当 "key",仅 base64
        warnings.warn(
            "[ProtoForge] cryptography 模块未安装,API key 降级为 base64 编码存储。"
            "生产环境请 `pip install cryptography` 并设置 PROTOFORGE_KEY 环境变量。"
            f"已写入占位 key 到 {_KEY_PATH}(文本,非加密)。",
            stacklevel=2,
        )
        fallback = base64.urlsafe_b64encode(b"PROTOFORGE_BASE64_FALLBACK_KEY_DO_NOT_USE_IN_PROD").decode(
            "ascii"
        )
        _KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _KEY_PATH.write_text(fallback + "\n", encoding="utf-8")
        try:
            os.chmod(_KEY_PATH, 0o600)
        except OSError:
            pass
        return ("base64", fallback.encode("ascii"))


def _encrypt_secret(plain: str) -> str:
    mode, key = _ensure_key()
    if mode == "fernet":
        from cryptography.fernet import Fernet  # type: ignore

        token = Fernet(key).encrypt(plain.encode("utf-8"))
        return "fernet:" + base64.urlsafe_b64encode(token).decode("ascii")
    # base64 fallback — 仍然混淆一下前缀,方便 grep 验证明文不出现
    return "b64:" + base64.urlsafe_b64encode(plain.encode("utf-8")).decode("ascii")


def _decrypt_secret(encoded: str) -> str:
    mode, key = _ensure_key()
    if encoded.startswith("fernet:"):
        from cryptography.fernet import Fernet  # type: ignore

        token = base64.urlsafe_b64decode(encoded[len("fernet:") :].encode("ascii"))
        return Fernet(key).decrypt(token).decode("utf-8")
    if encoded.startswith("b64:"):
        return base64.urlsafe_b64decode(encoded[len("b64:") :].encode("ascii")).decode("utf-8")
    # 兼容旧明文(读出来直接返回,不再加密回去,下次写入会重新加密)
    return encoded


def _read_user_state(user_id: str) -> dict:
    """读单用户的 onboarding 状态;文件不存在返回空 dict。"""
    p = _user_path(user_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_user_state(user_id: str, data: dict) -> None:
    p = _user_path(user_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_vendor_status() -> dict[str, Any]:
    """复用 vendor.py 的判定逻辑,直接 import 避免重写。"""
    try:
        from app.routers import vendor as vendor_router

        # vendor.py 的 _proto_language_status / _ml_models_status / _local_llm_status 是模块级私有函数
        return {
            "proto_language": vendor_router._proto_language_status(),
            "ml_models": vendor_router._ml_models_status(),
            "local_llm": vendor_router._local_llm_status(),
        }
    except Exception as exc:  # noqa: BLE001
        # vendor 状态拉失败不能阻塞引导页(玩家可能没 vendor)
        return {"error": f"vendor status unavailable: {exc}"}


def _normalize_llm_provider(value: Optional[str]) -> str:
    """把 user_state 里的 llm_provider 规整成 state 端契约的枚举。"""
    if value in ("cloud", "local-bundled", "disabled"):
        return value
    if value == "local":
        # 旧 Task 1.5 用的 'local' = Ollama,新约定下没有这一档;降级为 disabled
        return "disabled"
    return "disabled"


def _state_from_user_data(user_id: str) -> OnboardingStateSchema:
    """从磁盘读 user 状态,组装成 OnboardingState。"""
    data = _read_user_state(user_id)
    if not data:
        return OnboardingStateSchema(
            completed=False,
            llm_provider="disabled",
            cloud_provider=None,
            has_api_key=False,
            vendor_status=_get_vendor_status(),
        )
    return OnboardingStateSchema(
        completed=bool(data.get("completed", False)),
        llm_provider=_normalize_llm_provider(data.get("llm_provider")),  # type: ignore[arg-type]
        cloud_provider=data.get("cloud_provider"),
        has_api_key=bool(data.get("api_key_enc")),
        vendor_status=data.get("vendor_status") or _get_vendor_status(),
    )


# ---------------------------------------------------------------------------
# 路由:GET /state  /  POST /complete
# ---------------------------------------------------------------------------


@router.get("/state", response_model=OnboardingStateSchema)
def get_state(user_id: str = Query(..., description="玩家 ID(任意非空字符串)")) -> OnboardingStateSchema:
    """GET /api/onboarding/state?user_id=xxx

    引导页启动时调用,判断是否要展示 3 步流程;完成后返回 `completed=true`,
    前端据此跳转到 /forge。
    """
    user_id = _validate_user_id(user_id)
    return _state_from_user_data(user_id)


@router.post("/complete", response_model=OnboardingCompleteResponse)
def post_complete(
    sub: OnboardingSubmission,
    user_id: str = Query(..., description="玩家 ID"),
) -> OnboardingCompleteResponse:
    """POST /api/onboarding/complete?user_id=xxx

    接收 3 步流程的最后一步提交,做字段校验,加密 api_key,落盘。
    """
    user_id = _validate_user_id(user_id)

    # ---- 字段校验 ----
    if sub.llm_provider == "cloud":
        if not sub.cloud_provider:
            raise HTTPException(
                status_code=422, detail="选择云 API 时必须指定 cloud_provider"
            )
        if not sub.api_key or not sub.api_key.strip():
            raise HTTPException(
                status_code=422, detail="选择云 API 时必须填 api_key"
            )
    elif sub.llm_provider == "local-bundled":
        # vendor 资源要求
        vendor = _get_vendor_status()
        local_llm = vendor.get("local_llm", {}) if isinstance(vendor, dict) else {}
        if not local_llm.get("available"):
            raise HTTPException(
                status_code=422,
                detail="本地内置模式需要 vendor.local_llm.available=true,当前不可用",
            )
    elif sub.llm_provider == "disabled":
        # 纯滑块模式,不要求任何额外字段
        pass
    else:
        raise HTTPException(status_code=422, detail=f"未知 llm_provider: {sub.llm_provider}")

    # ---- 持久化 ----
    data = _read_user_state(user_id)
    data["user_id"] = user_id
    data["completed"] = True
    data["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    data["llm_provider"] = sub.llm_provider
    data["cloud_provider"] = sub.cloud_provider
    if sub.llm_provider == "cloud" and sub.api_key:
        data["api_key_enc"] = _encrypt_secret(sub.api_key.strip())
        data["api_key_provider"] = sub.cloud_provider
        # 永远不存明文
        data.pop("api_key", None)
    else:
        data["api_key_enc"] = None
        data["api_key_provider"] = None
    data["vendor_status"] = _get_vendor_status()

    _write_user_state(user_id, data)

    return OnboardingCompleteResponse(ok=True, message="欢迎来到 ProtoForge!")
