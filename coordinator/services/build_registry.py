"""Utility for persisting and loading build metadata."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class BuildRegistry:
    """Persist build metadata to the `.sb_artifacts/builds` directory."""

    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)
        self.registry_dir = self.base_dir / ".sb_artifacts" / "builds"
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def register_build(self, metadata: Dict) -> Dict:
        """Store or update build metadata on disk."""
        if "build_id" not in metadata:
            raise ValueError("build metadata must include build_id")

        record = metadata.copy()
        now = datetime.utcnow().isoformat() + "Z"
        record.setdefault("created_at", now)
        record["updated_at"] = now

        # Normalise paths and defaults
        if record.get("source_path"):
            record["source_path"] = str(Path(record["source_path"]).resolve())
        if not record.get("project_name") and record.get("source_path"):
            record["project_name"] = Path(record["source_path"]).name
        record.setdefault("project_name", record["build_id"])

        target_path = self.registry_dir / f"{record['build_id']}.json"
        with open(target_path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2)
        return record

    def load_all(self) -> List[Dict]:
        """Load every persisted build record."""
        records: List[Dict] = []
        for path in sorted(self.registry_dir.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    record = json.load(handle)
                if record.get("build_id"):
                    records.append(record)
            except Exception:
                # Corrupted file; skip but keep process running
                continue
        records.sort(
            key=lambda r: r.get("updated_at") or r.get("created_at") or "",
            reverse=True,
        )
        return records

    def get(self, build_id: str) -> Optional[Dict]:
        """Load a single build record when available."""
        path = self.registry_dir / f"{build_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def update_build(self, build_id: str, **updates) -> Optional[Dict]:
        """Update selected fields of a persisted build."""
        existing = self.get(build_id)
        if not existing:
            return None
        existing.update(updates)
        return self.register_build(existing)

    def remove(self, build_id: str) -> bool:
        """Remove a persisted build record."""
        path = self.registry_dir / f"{build_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def find_by_source_path(self, source_path: str) -> Optional[Dict]:
        """Locate a build record by its source path if present."""
        candidate = Path(source_path).resolve()
        for record in self.load_all():
            stored = record.get("source_path")
            if not stored:
                continue
            try:
                if Path(stored).resolve() == candidate:
                    return record
            except Exception:
                continue
        return None

    def bootstrap_from_generated(self, generated_dir: Path | str) -> List[Dict]:
        """Ensure every generated project has a persisted record."""
        gen_path = Path(generated_dir)
        if not gen_path.exists():
            return self.load_all()

        for child in gen_path.iterdir():
            if not child.is_dir():
                continue

            existing = self.find_by_source_path(child)
            if existing:
                continue

            base_id = f"generated-{child.name}"
            build_id = base_id
            suffix = 1
            while True:
                current = self.get(build_id)
                if not current:
                    break
                if Path(current.get("source_path", "")).resolve() == child.resolve():
                    break
                suffix += 1
                build_id = f"{base_id}-{suffix}"

            metadata = {
                "build_id": build_id,
                "project_name": child.name,
                "status": "success",
                "progress": 100,
                "source_path": str(child.resolve()),
                "app_url": "",
                "current_step": "Complete",
            }
            self.register_build(metadata)

        return self.load_all()
