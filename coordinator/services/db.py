"""
Lightweight SQLAlchemy setup for coordinator metadata (snapshots, quotas, etc.).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(String(64), primary_key=True)  # content hash (sha256)
    project_path = Column(Text, nullable=False)
    object_key = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    git_commit = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json = Column(Text, nullable=True)


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True, future=True)


def make_session_factory(database_url: str):
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
