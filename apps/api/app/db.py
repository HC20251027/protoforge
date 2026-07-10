"""SQLite 持久化(Phase 1.5 — Gallery 升级)。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


class Base(DeclarativeBase):
    pass


class ArtifactRow(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    intron: Mapped[str] = mapped_column(String(2000))
    fasta: Mapped[str] = mapped_column(String(4000))
    scores: Mapped[dict] = mapped_column(JSON)
    ritual: Mapped[str] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    risk_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


_engine = None
_Session: async_sessionmaker[AsyncSession] | None = None


def _make_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path}"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_engine():
    global _engine
    if _engine is None:
        _ensure_parent(settings.db_path)
        _engine = create_async_engine(_make_url(settings.db_path), echo=False, future=True)
    return _engine


def get_session() -> async_sessionmaker[AsyncSession]:
    global _Session
    if _Session is None:
        _Session = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _Session


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def row_to_dict(row: ArtifactRow) -> dict:
    return {
        "id": row.id,
        "mission_id": row.mission_id,
        "title": row.title,
        "intron": row.intron,
        "fasta": row.fasta,
        "scores": row.scores,
        "ritual": row.ritual,
        "notes": row.notes,
        "risk_passed": row.risk_passed,
        "created_at": row.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
    }
