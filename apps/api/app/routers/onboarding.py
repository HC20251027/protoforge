"""Onboarding 路由:列出 provider / 探测 / 持久化。"""
from __future__ import annotations

import time

from fastapi import APIRouter

from app.llm import (
    OnboardingState,
    ProviderConfig,
    describe_providers,
    load_state,
    save_state,
    test_provider,
)
from app.schemas import OnboardingSave, OnboardingStatus, OnboardingTestRequest

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


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
