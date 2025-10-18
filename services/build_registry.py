"""
Build Registry Service - Persistent build metadata storage
Tracks all builds across application lifecycle with searchable metadata
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from threading import Lock


class BuildRegistry:
    """
    Centralized build registry for tracking application builds
    Provides persistent storage and querying of build metadata
    """
    
    def __init__(self, base_path: Path):
        """
        Initialize build registry
        
        Args:
            base_path: Root directory for storing build registry
        """
        self.base_path = Path(base_path)
        self.registry_dir = self.base_path / ".sb_artifacts" / "build_registry"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "builds.json"
        self._lock = Lock()
        self._cache: Dict[str, dict] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from disk into memory cache"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._cache = {item["build_id"]: item for item in data.get("builds", [])}
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[BuildRegistry] Warning: Could not load registry: {e}")
                self._cache = {}
    
    def _save_registry(self):
        """Persist registry cache to disk"""
        try:
            data = {
                "builds": list(self._cache.values()),
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            # Write atomically with temp file
            temp_file = self.registry_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.registry_file)
        except Exception as e:
            print(f"[BuildRegistry] Error saving registry: {e}")
    
    def register_build(self, metadata: dict) -> bool:
        """
        Register or update a build in the registry
        
        Args:
            metadata: Build metadata including build_id, project_name, status, etc.
            
        Returns:
            True if successful
        """
        build_id = metadata.get("build_id")
        if not build_id:
            print("[BuildRegistry] Error: build_id is required")
            return False
        
        with self._lock:
            # Merge with existing record if present
            existing = self._cache.get(build_id, {})
            record = {
                **existing,
                **metadata,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            # Set created_at if new
            if "created_at" not in record:
                record["created_at"] = record["updated_at"]
            
            self._cache[build_id] = record
            self._save_registry()
            return True
    
    def get(self, build_id: str) -> Optional[dict]:
        """
        Get build metadata by ID
        
        Args:
            build_id: Build identifier
            
        Returns:
            Build metadata or None if not found
        """
        with self._lock:
            return self._cache.get(build_id)
    
    def remove(self, build_id: str) -> bool:
        """
        Remove a build from the registry
        
        Args:
            build_id: Build identifier
            
        Returns:
            True if build was found and removed
        """
        with self._lock:
            if build_id in self._cache:
                del self._cache[build_id]
                self._save_registry()
                return True
            return False
    
    def load_all(self) -> List[dict]:
        """
        Load all builds from registry
        
        Returns:
            List of all build records
        """
        with self._lock:
            return list(self._cache.values())
    
    def search(
        self,
        status: Optional[str] = None,
        project_name: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """
        Search builds with filters
        
        Args:
            status: Filter by build status
            project_name: Filter by project name (partial match)
            limit: Maximum results to return
            
        Returns:
            List of matching build records
        """
        with self._lock:
            results = list(self._cache.values())
            
            if status:
                results = [r for r in results if r.get("status") == status]
            
            if project_name:
                project_name_lower = project_name.lower()
                results = [
                    r for r in results 
                    if project_name_lower in r.get("project_name", "").lower()
                ]
            
            # Sort by updated_at descending
            results.sort(
                key=lambda x: x.get("updated_at", ""),
                reverse=True
            )
            
            return results[:limit]
    
    def get_stats(self) -> dict:
        """
        Get registry statistics
        
        Returns:
            Dictionary with counts by status and totals
        """
        with self._lock:
            builds = list(self._cache.values())
            
            stats = {
                "total_builds": len(builds),
                "by_status": {},
                "recent_builds": []
            }
            
            # Count by status
            for build in builds:
                status = build.get("status", "unknown")
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Get 10 most recent
            recent = sorted(
                builds,
                key=lambda x: x.get("updated_at", ""),
                reverse=True
            )[:10]
            
            stats["recent_builds"] = [
                {
                    "build_id": b["build_id"],
                    "project_name": b.get("project_name"),
                    "status": b.get("status"),
                    "updated_at": b.get("updated_at")
                }
                for b in recent
            ]
            
            return stats
    
    def bootstrap_from_generated(self, generated_dir: Path):
        """
        Bootstrap registry from existing generated apps directory
        Scans for projects and creates registry entries
        
        Args:
            generated_dir: Path to generated apps directory
        """
        if not generated_dir.exists():
            return
        
        count = 0
        for project_dir in generated_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            # Check if already registered
            existing = self.search(project_name=project_dir.name)
            if existing:
                continue
            
            # Create new registry entry
            build_id = str(uuid.uuid4())
            metadata = {
                "build_id": build_id,
                "project_name": project_dir.name,
                "status": "success",
                "progress": 100,
                "current_step": "Complete",
                "source_path": str(project_dir.resolve()),
                "created_at": datetime.fromtimestamp(
                    project_dir.stat().st_ctime
                ).isoformat() + "Z"
            }
            
            if self.register_build(metadata):
                count += 1
        
        if count > 0:
            print(f"[BuildRegistry] Bootstrapped {count} existing projects")
    
    def cleanup_old_builds(self, days: int = 30) -> int:
        """
        Remove builds older than specified days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of builds removed
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_str = cutoff.isoformat() + "Z"
        
        with self._lock:
            old_builds = [
                build_id for build_id, build in self._cache.items()
                if build.get("updated_at", "") < cutoff_str
            ]
            
            for build_id in old_builds:
                del self._cache[build_id]
            
            if old_builds:
                self._save_registry()
            
            return len(old_builds)
