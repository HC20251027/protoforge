"""Task 7 + 13: Gallery 内存/SQLite 双 backend + 路由测试。"""
import pytest
from fastapi.testclient import TestClient

from app import gallery_store
from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _memory_backend(tmp_path, monkeypatch):
    """强制 memory backend,避免测试落盘污染真实数据目录。"""
    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(settings, "db_path", test_dir / "test.db")
    gallery_store.set_backend("memory")
    gallery_store.reset()
    yield
    gallery_store.reset()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _sample_artifact(**overrides) -> dict:
    body = {
        "mission_id": "polar-glow-v1",
        "title": "Run #1",
        "intron": "GT" + "ATGC" * 30 + "AG",
        "fasta": ">test\nGTATGCATGCAG\n",
        "scores": {"primary": 0.7, "components": {}, "weights": {}},
        "ritual": "standard",
        "notes": None,
        "risk_passed": True,
    }
    body.update(overrides)
    return body


def test_create_and_list_roundtrip(client):
    create = client.post("/api/gallery", json=_sample_artifact())
    assert create.status_code == 200
    artifact = create.json()
    assert artifact["id"].startswith("art_")
    assert artifact["mission_id"] == "polar-glow-v1"

    listed = client.get("/api/gallery").json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == artifact["id"]


def test_get_artifact_by_id(client):
    created = client.post("/api/gallery", json=_sample_artifact()).json()
    resp = client.get(f"/api/gallery/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_artifact_404(client):
    resp = client.get("/api/gallery/art_nope")
    assert resp.status_code == 404


def test_listing_orders_newest_first(client):
    a = client.post("/api/gallery", json=_sample_artifact(title="A")).json()
    b = client.post("/api/gallery", json=_sample_artifact(title="B")).json()
    listing = client.get("/api/gallery").json()
    assert [x["title"] for x in listing["items"]] == [b["title"], a["title"]]
