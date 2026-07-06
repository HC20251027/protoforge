"""Task 13: SQLite backend 集成测试。"""
import asyncio

import pytest


@pytest.fixture()
def _isolated_db(tmp_path, monkeypatch):
    from app import db, gallery_store
    from app.config import settings

    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(settings, "db_path", test_dir / "test.db")

    # 重置 engine + session(因为它们模块级单例)
    db._engine = None
    db._Session = None
    gallery_store.set_backend("sqlite")
    asyncio.run(db.init_db())
    yield
    db._engine = None
    db._Session = None
    gallery_store.set_backend("memory")


def test_sqlite_create_list_get(_isolated_db):
    from app.schemas import ArtifactCreate
    from app import gallery_store

    req = ArtifactCreate(
        mission_id="polar-glow-v1",
        title="Run #1",
        intron="GTATGC" * 10 + "AG",
        fasta=">x\nGTATGCAG\n",
        scores={"primary": 0.7, "components": {}, "weights": {}},
        ritual="standard",
        notes=None,
        risk_passed=True,
    )
    created = gallery_store.add(req)
    assert created.id.startswith("art_")
    assert created.mission_id == "polar-glow-v1"

    listing = gallery_store.list_all()
    assert listing.total == 1
    assert listing.items[0].id == created.id

    fetched = gallery_store.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_sqlite_reset_clears_rows(_isolated_db):
    from app.schemas import ArtifactCreate
    from app import gallery_store

    gallery_store.add(
        ArtifactCreate(
            mission_id="x",
            title="t",
            intron="ATGC",
            fasta=">x\nATGC\n",
            scores={},
            ritual="swift",
            notes=None,
            risk_passed=True,
        )
    )
    assert gallery_store.list_all().total == 1
    gallery_store.reset()
    assert gallery_store.list_all().total == 0
