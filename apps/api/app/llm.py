"""LLM provider 抽象层:cloud (DeepSeek) / local (Ollama) / disabled。

设计原则:
- 不在仓库里写任何 API Key;通过 onboarding 让用户填,然后写到 settings 目录的 llm.json。
- test() 用最少 token 验证可达;save() 写盘;load() 启动时读。
- Phase 1 重点是接口形态,真实 LLM 翻译留到 Task 9。
"""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import httpx

from app.config import settings

ProviderName = Literal["cloud", "local", "disabled"]


@dataclass
class ProviderConfig:
    """单个 provider 的配置。"""
    name: ProviderName
    base_url: str
    model: str
    api_key: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class OnboardingState:
    """当前 LLM onboarding 的整体状态。"""
    active: ProviderName
    providers: dict[str, ProviderConfig]
    last_test_at: str | None = None
    last_test_ok: bool | None = None
    last_test_message: str = ""

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "providers": {
                k: {**asdict(v), "name": v.name}
                for k, v in self.providers.items()
            },
            "last_test_at": self.last_test_at,
            "last_test_ok": self.last_test_ok,
            "last_test_message": self.last_test_message,
        }


class LLMProvider(ABC):
    """统一的 LLM provider 接口。"""
    name: ProviderName

    @abstractmethod
    def describe(self) -> dict:
        """返回给前端展示的元信息:label/desc/required fields。"""

    @abstractmethod
    def test(self, config: ProviderConfig) -> tuple[bool, str]:
        """用最少 token 探测可达性。返回 (ok, message)。"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
        config: "ProviderConfig | None" = None,
    ) -> str:
        """调用 LLM 一次 chat completion,返回 message content(纯文本)。

        参数:
        - messages: OpenAI 协议格式 [{"role": ..., "content": ...}]
        - temperature/max_tokens: 采样参数
        - config: ProviderConfig 实例;若为 None 则从 load_state() 读
        """


# ---------------------------------------------------------------------------
# Cloud (DeepSeek / OpenAI 兼容)
# ---------------------------------------------------------------------------

class CloudProvider(LLMProvider):
    name = "cloud"

    def describe(self) -> dict:
        return {
            "label": "云端 API(推荐 DeepSeek / OpenAI 兼容)",
            "description": "默认推荐 DeepSeek,OpenAI/Anthropic 等同 OpenAI 协议的也可用。",
            "fields": [
                {"key": "base_url", "label": "Base URL", "default": "https://api.deepseek.com/v1"},
                {"key": "model", "label": "Model", "default": "deepseek-chat"},
                {"key": "api_key", "label": "API Key", "secret": True},
            ],
        }

    def test(self, config: ProviderConfig) -> tuple[bool, str]:
        if not config.api_key:
            return False, "缺少 api_key"
        try:
            r = httpx.post(
                f"{config.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            return False, f"网络错误: {exc}"
        if r.status_code == 200:
            return True, "云端 API 可达"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
        config: "ProviderConfig | None" = None,
    ) -> str:
        cfg = config or self._default_config()
        if not cfg.api_key:
            raise RuntimeError("cloud provider 缺少 api_key,请先在 onboarding 页配置")
        r = httpx.post(
            f"{cfg.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"cloud LLM HTTP {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _default_config() -> "ProviderConfig":
        from app.llm import ProviderConfig
        return ProviderConfig(
            name="cloud",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key="",
        )


# ---------------------------------------------------------------------------
# Local (Ollama / LM Studio 兼容 OpenAI 协议)
# ---------------------------------------------------------------------------

class LocalProvider(LLMProvider):
    name = "local"

    def describe(self) -> dict:
        return {
            "label": "本地模型(Ollama / LM Studio)",
            "description": "完全离线。Ollama 默认 http://127.0.0.1:11434/v1。",
            "fields": [
                {"key": "base_url", "label": "Base URL", "default": "http://127.0.0.1:11434/v1"},
                {"key": "model", "label": "Model", "default": "qwen2.5:7b"},
                {"key": "api_key", "label": "API Key(可留空)", "secret": True},
            ],
        }

    def test(self, config: ProviderConfig) -> tuple[bool, str]:
        try:
            r = httpx.get(
                f"{config.base_url.rstrip('/')}/models",
                headers={
                    "Authorization": f"Bearer {config.api_key or 'ollama'}",
                },
                timeout=5.0,
            )
        except httpx.HTTPError as exc:
            return False, f"本地服务不可达: {exc}"
        if r.status_code == 200:
            return True, "本地服务可达"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
        config: "ProviderConfig | None" = None,
    ) -> str:
        from app.llm import ProviderConfig
        cfg = config or ProviderConfig(
            name="local",
            base_url="http://127.0.0.1:11434/v1",
            model="qwen2.5:7b",
            api_key="",
        )
        r = httpx.post(
            f"{cfg.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg.api_key or 'ollama'}",
                "Content-Type": "application/json",
            },
            json={
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=60.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"local LLM HTTP {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Disabled
# ---------------------------------------------------------------------------

class DisabledProvider(LLMProvider):
    name = "disabled"

    def describe(self) -> dict:
        return {
            "label": "不使用 LLM(纯滑块模式)",
            "description": "完全离线 + 不联网,玩家只能靠预设滑块组合,Phase 1 的安全默认。",
            "fields": [],
        }

    def test(self, config: ProviderConfig) -> tuple[bool, str]:
        return True, "disabled 模式不需要探测"

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 256,
        config: "ProviderConfig | None" = None,
    ) -> str:
        raise RuntimeError(
            "LLM 当前为 disabled 模式,无法 chat。请在 onboarding 页切换到 cloud 或 local。"
        )


_PROVIDERS: dict[ProviderName, LLMProvider] = {
    "cloud": CloudProvider(),
    "local": LocalProvider(),
    "disabled": DisabledProvider(),
}


# ---------------------------------------------------------------------------
# 持久化
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(settings.data_dir) / "llm.json"


def _default_state() -> OnboardingState:
    return OnboardingState(
        active="disabled",
        providers={
            "cloud": ProviderConfig(
                name="cloud",
                base_url="https://api.deepseek.com/v1",
                model="deepseek-chat",
                api_key="",
            ),
            "local": ProviderConfig(
                name="local",
                base_url="http://127.0.0.1:11434/v1",
                model="qwen2.5:7b",
                api_key="",
            ),
            "disabled": ProviderConfig(
                name="disabled",
                base_url="",
                model="",
                api_key="",
            ),
        },
    )


def load_state() -> OnboardingState:
    if not _CONFIG_PATH.exists():
        return _default_state()
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_state()
    state = _default_state()
    state.active = data.get("active", state.active)  # type: ignore[assignment]
    for key, cfg in data.get("providers", {}).items():
        if key in state.providers:
            state.providers[key] = ProviderConfig(
                name=cfg.get("name", key),
                base_url=cfg.get("base_url", ""),
                model=cfg.get("model", ""),
                api_key=cfg.get("api_key", ""),
                extra=cfg.get("extra", {}),
            )
    state.last_test_at = data.get("last_test_at")
    state.last_test_ok = data.get("last_test_ok")
    state.last_test_message = data.get("last_test_message", "")
    return state


def save_state(state: OnboardingState) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def describe_providers() -> list[dict]:
    return [_PROVIDERS[name].describe() for name in ("cloud", "local", "disabled")]


def test_provider(name: ProviderName, config: ProviderConfig) -> tuple[bool, str]:
    if name not in _PROVIDERS:
        return False, f"未知 provider: {name}"
    return _PROVIDERS[name].test(config)
