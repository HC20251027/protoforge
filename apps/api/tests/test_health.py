"""健康检查测试。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "data_dir" in body


def test_health_includes_proto_profile(client: TestClient) -> None:
    res = client.get("/health")
    assert res.json()["proto_profile"] in ("auto", "gpu_8gb", "gpu_24gb", "cpu")
