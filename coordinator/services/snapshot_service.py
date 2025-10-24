"""
Snapshot service: create content-addressed snapshots of project directories,
store in object storage, keep metadata in DB, and materialize on demand.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .object_store import BaseObjectStore, ObjectLocation, sha256_bytes
from .db import make_session_factory, Snapshot
from sqlalchemy import select


DEFAULT_EXCLUDES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".DS_Store",
    "*.log",
    ".env",
}


def _match_excluded(relative: Path, excludes: Iterable[str]) -> bool:
    import fnmatch

    rel_str = str(relative).replace("\\", "/")
    for pattern in excludes:
        # Exact dir/file name
        if pattern in {relative.name, rel_str.split("/")[0]}:
            return True
        # Glob patterns
        if fnmatch.fnmatch(relative.name, pattern) or fnmatch.fnmatch(rel_str, pattern):
            return True
    return False


@dataclass
class SnapshotMeta:
    id: str
    object_key: str
    size_bytes: int
    project_path: str
    git_commit: Optional[str]


class SnapshotService:
    def __init__(self, store: BaseObjectStore, session_factory, artifact_prefix: str = "snapshots"):
        self.store = store
        self.session_factory = session_factory
        self.artifact_prefix = artifact_prefix.rstrip("/")

    def _zip_project(self, project_root: Path, excludes: Iterable[str]) -> Tuple[bytes, int]:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for path in project_root.rglob("*"):
                if path.is_file():
                    rel = path.relative_to(project_root)
                    if _match_excluded(rel, excludes):
                        continue
                    zipf.write(path, arcname=str(rel))
        data = buffer.getvalue()
        return data, len(data)

    def _object_key_for(self, snap_id: str) -> str:
        return f"{self.artifact_prefix}/{snap_id[:2]}/{snap_id}.zip"

    def create_snapshot(self, project_path: str, excludes: Optional[Iterable[str]] = None, git_commit: Optional[str] = None) -> SnapshotMeta:
        root = Path(project_path).resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Project path not found: {project_path}")
        ex = set(DEFAULT_EXCLUDES)
        if excludes:
            ex |= set(excludes)

        data, size = self._zip_project(root, ex)
        snap_id = sha256_bytes(data)
        key = self._object_key_for(snap_id)
        self.store.put_bytes(key, data, content_type="application/zip")

        with self.session_factory() as session:
            # Upsert-like behavior: if exists, keep first record
            existing = session.get(Snapshot, snap_id)
            if not existing:
                s = Snapshot(
                    id=snap_id,
                    project_path=str(root),
                    object_key=key,
                    size_bytes=size,
                    git_commit=git_commit,
                    metadata_json=None,
                )
                session.add(s)
                session.commit()
        return SnapshotMeta(id=snap_id, object_key=key, size_bytes=size, project_path=str(root), git_commit=git_commit)

    def list_snapshots(self, project_path: str) -> List[SnapshotMeta]:
        root = str(Path(project_path).resolve())
        with self.session_factory() as session:
            rows = session.execute(select(Snapshot).where(Snapshot.project_path == root).order_by(Snapshot.created_at.desc())).scalars().all()
            return [SnapshotMeta(r.id, r.object_key, r.size_bytes, r.project_path, r.git_commit) for r in rows]

    def get_snapshot(self, snap_id: str) -> Optional[SnapshotMeta]:
        with self.session_factory() as session:
            s = session.get(Snapshot, snap_id)
            if not s:
                return None
            return SnapshotMeta(s.id, s.object_key, s.size_bytes, s.project_path, s.git_commit)

    def materialize(self, snap_id: str) -> Path:
        meta = self.get_snapshot(snap_id)
        if not meta:
            raise FileNotFoundError("Snapshot not found")
        # Download zip into temp dir and extract
        tmpdir = Path(tempfile.mkdtemp(prefix=f"snap-{snap_id[:8]}-"))
        with self.store.open_read(meta.object_key) as f:
            data = f.read()
        with zipfile.ZipFile(io.BytesIO(data), "r") as zipf:
            zipf.extractall(tmpdir)
        return tmpdir

    def delete_snapshot(self, snap_id: str) -> bool:
        with self.session_factory() as session:
            s = session.get(Snapshot, snap_id)
            if not s:
                return False
            self.store.delete_object(s.object_key)
            session.delete(s)
            session.commit()
            return True
