"""Task 1: LLM chat() 抽象层测试。"""
import pytest

from app.llm import (
    CloudProvider,
    DisabledProvider,
    LocalProvider,
    load_state,
)


def test_all_providers_implement_chat():
    """每个 provider 都必须实现 chat() 方法。"""
    for provider in (CloudProvider(), LocalProvider(), DisabledProvider()):
        assert hasattr(provider, "chat")
        assert callable(provider.chat)


def test_disabled_chat_raises_clear_error():
    """disabled 模式调 chat() 应明确报不支持,而不是静默返回空。"""
    p = DisabledProvider()
    with pytest.raises(RuntimeError, match="disabled"):
        p.chat([{"role": "user", "content": "hi"}])


def test_cloud_chat_calls_chat_completions(monkeypatch):
    """cloud chat() 应走 /chat/completions,带 Bearer token。"""
    import httpx

    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        # 构造一个最小 OpenAI 兼容响应
        resp = httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "{\"k\": 0.5}", "role": "assistant"}}
                ]
            },
            request=httpx.Request("POST", url),
        )
        return resp

    monkeypatch.setattr(httpx, "post", fake_post)

    from app.llm import ProviderConfig
    cfg = ProviderConfig(
        name="cloud",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key="sk-test",
    )
    p = CloudProvider()
    out = p.chat(
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_tokens=10,
        config=cfg,
    )
    assert out == "{\"k\": 0.5}"
    assert "chat/completions" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["json"]["model"] == "deepseek-chat"
    assert captured["json"]["temperature"] == 0.2


def test_local_chat_uses_openai_compatible(monkeypatch):
    """local chat() 也是 OpenAI 兼容,空 api_key 用 ollama 占位。"""
    import httpx

    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok", "role": "assistant"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    from app.llm import ProviderConfig
    cfg = ProviderConfig(
        name="local",
        base_url="http://127.0.0.1:11434/v1",
        model="qwen2.5:7b",
        api_key="",
    )
    out = LocalProvider().chat(
        [{"role": "user", "content": "ping"}],
        temperature=0.1,
        max_tokens=5,
        config=cfg,
    )
    assert out == "ok"
    assert captured["headers"]["Authorization"] == "Bearer ollama"
    assert "11434" in captured["url"]
