"""
Enhanced State Manager - Robust state persistence with recovery and transactions
Provides atomic operations and crash recovery for build states
"""
import json
import os
import shutil
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

try:  # pragma: no cover - platform dependent
    import fcntl  # type: ignore
    _HAS_FCNTL = True
except ImportError:  # Windows fallback
    fcntl = None  # type: ignore
    _HAS_FCNTL = False
    try:  # pragma: no cover - windows specific
        import msvcrt  # type: ignore
        import time
        _HAS_MSVCRT = True
    except ImportError:  # pragma: no cover - extremely rare
        msvcrt = None  # type: ignore
        _HAS_MSVCRT = False


class StateTransaction:
    """Context manager for atomic state updates"""
    
    def __init__(self, manager: 'EnhancedStateManager', build_id: str):
        self.manager = manager
        self.build_id = build_id
        self.original_state = None
        self.committed = False
    
    def __enter__(self):
        self.original_state = self.manager.get_state(self.build_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and not self.committed:
            # Rollback on exception
            if self.original_state:
                self.manager._write_state(self.build_id, self.original_state)
        return False


class EnhancedStateManager:
    """
    Enhanced state manager with:
    - Atomic operations
    - Crash recovery
    - State versioning
    - Lock-based concurrency control
    - Automatic backups
    """
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.states_dir = self.base_dir / ".state"
        self.backups_dir = self.base_dir / ".state_backups"
        self.locks_dir = self.base_dir / ".state_locks"
        
        # Create directories
        self.states_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache with thread-safe access
        self._cache: Dict[str, Dict] = {}
        self._cache_lock = threading.RLock()
        
        # Recovery on startup
        self._recover_incomplete_transactions()
    
    def get_state(self, build_id: str) -> Optional[Dict]:
        """Get state with caching"""
        with self._cache_lock:
            # Check cache first
            if build_id in self._cache:
                return self._cache[build_id].copy()
        
        # Load from disk
        state = self._read_state(build_id)
        if state:
            with self._cache_lock:
                self._cache[build_id] = state.copy()
        return state
    
    def save_state(self, build_id: str, state: Dict) -> bool:
        """Save state atomically with backup"""
        try:
            # Validate state
            if not self._validate_state(state):
                raise ValueError("Invalid state structure")
            
            # Add metadata
            state["_metadata"] = {
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "version": state.get("_metadata", {}).get("version", 0) + 1
            }
            
            # Create backup of existing state
            existing = self._read_state(build_id)
            if existing:
                self._create_backup(build_id, existing)
            
            # Write atomically
            success = self._write_state(build_id, state)
            
            if success:
                with self._cache_lock:
                    self._cache[build_id] = state.copy()
            
            return success
            
        except Exception as e:
            print(f"Error saving state for {build_id}: {e}")
            return False
    
    def update_state(self, build_id: str, updates: Dict) -> bool:
        """Update specific fields in state"""
        state = self.get_state(build_id)
        if not state:
            return False
        
        # Deep merge updates
        self._deep_merge(state, updates)
        return self.save_state(build_id, state)
    
    @contextmanager
    def transaction(self, build_id: str):
        """Context manager for transactional updates"""
        transaction = StateTransaction(self, build_id)
        try:
            yield transaction
            transaction.committed = True
        except Exception:
            raise
    
    def delete_state(self, build_id: str) -> bool:
        """Delete state with archival"""
        try:
            # Archive before deletion
            state = self._read_state(build_id)
            if state:
                archive_path = self.backups_dir / f"{build_id}_archived_{int(datetime.utcnow().timestamp())}.json"
                with open(archive_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2)
            
            # Delete state file
            state_file = self._get_state_file(build_id)
            if state_file.exists():
                state_file.unlink()
            
            # Remove from cache
            with self._cache_lock:
                self._cache.pop(build_id, None)
            
            return True
            
        except Exception as e:
            print(f"Error deleting state for {build_id}: {e}")
            return False
    
    def list_all_states(self) -> List[Dict]:
        """List all available states"""
        states = []
        for state_file in self.states_dir.glob("*.json"):
            build_id = state_file.stem
            state = self.get_state(build_id)
            if state:
                states.append({
                    "build_id": build_id,
                    "status": state.get("build_status", "unknown"),
                    "last_updated": state.get("_metadata", {}).get("last_updated"),
                    "version": state.get("_metadata", {}).get("version", 0)
                })
        return states
    
    def recover_state(self, build_id: str) -> Optional[Dict]:
        """Recover state from latest backup"""
        try:
            backups = sorted(
                self.backups_dir.glob(f"{build_id}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if backups:
                with open(backups[0], 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                # Restore
                self.save_state(build_id, state)
                return state
            
            return None
            
        except Exception as e:
            print(f"Error recovering state for {build_id}: {e}")
            return None
    
    def cleanup_old_backups(self, keep_last: int = 10):
        """Cleanup old backups, keeping only recent ones per build"""
        build_backups = {}
        
        for backup_file in self.backups_dir.glob("*.json"):
            # Extract build_id from filename
            parts = backup_file.stem.split('_')
            if len(parts) >= 2:
                build_id = parts[0]
                if build_id not in build_backups:
                    build_backups[build_id] = []
                build_backups[build_id].append(backup_file)
        
        # Keep only recent backups
        for build_id, backups in build_backups.items():
            sorted_backups = sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)
            for old_backup in sorted_backups[keep_last:]:
                try:
                    old_backup.unlink()
                except Exception:
                    pass
    
    def _read_state(self, build_id: str) -> Optional[Dict]:
        """Read state from disk with locking"""
        state_file = self._get_state_file(build_id)
        
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                self._lock_file(f, shared=True)
                try:
                    return json.load(f)
                finally:
                    self._unlock_file(f)
        except Exception as e:
            print(f"Error reading state for {build_id}: {e}")
            return None
    
    def _write_state(self, build_id: str, state: Dict) -> bool:
        """Write state atomically with locking"""
        state_file = self._get_state_file(build_id)
        temp_file = state_file.with_suffix('.tmp')
        
        try:
            # Write to temporary file first
            with open(temp_file, 'w', encoding='utf-8') as f:
                self._lock_file(f, shared=False)
                try:
                    json.dump(state, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                finally:
                    self._unlock_file(f)
            
            # Atomic rename
            shutil.move(str(temp_file), str(state_file))
            return True
            
        except Exception as e:
            print(f"Error writing state for {build_id}: {e}")
            # Cleanup temp file
            if temp_file.exists():
                temp_file.unlink()
            return False

    def _lock_file(self, file_obj, shared: bool):
        """Cross-platform file locking"""
        if _HAS_FCNTL:
            mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
            fcntl.flock(file_obj.fileno(), mode)
        elif _HAS_MSVCRT:
            # Windows locking does not support shared locks; emulate with exclusive
            retries = 5
            for _ in range(retries):
                try:
                    msvcrt.locking(file_obj.fileno(), msvcrt.LK_NBLCK, 1)
                    file_obj._enhanced_lock = True  # type: ignore[attr-defined]
                    return
                except OSError:
                    time.sleep(0.1)
            # Fallback to blocking lock if non-blocking failed
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK, 1)
            file_obj._enhanced_lock = True  # type: ignore[attr-defined]
        else:
            # As a last resort, no locking (best effort)
            file_obj._enhanced_lock = False  # type: ignore[attr-defined]

    def _unlock_file(self, file_obj):
        """Release file lock"""
        if _HAS_FCNTL:
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
        elif _HAS_MSVCRT:
            if getattr(file_obj, "_enhanced_lock", None):
                msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
                delattr(file_obj, "_enhanced_lock")
    
    def _create_backup(self, build_id: str, state: Dict):
        """Create timestamped backup"""
        timestamp = int(datetime.utcnow().timestamp())
        backup_file = self.backups_dir / f"{build_id}_{timestamp}.json"
        
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to create backup for {build_id}: {e}")
    
    def _get_state_file(self, build_id: str) -> Path:
        """Get state file path"""
        return self.states_dir / f"{build_id}.json"
    
    def _validate_state(self, state: Dict) -> bool:
        """Validate state structure"""
        required_fields = ["build_id", "build_status"]
        return all(field in state for field in required_fields)
    
    def _deep_merge(self, target: Dict, source: Dict):
        """Deep merge source into target"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def _recover_incomplete_transactions(self):
        """Recover from incomplete transactions on startup"""
        # Check for .tmp files
        for temp_file in self.states_dir.glob("*.tmp"):
            try:
                # Remove incomplete transaction files
                temp_file.unlink()
                print(f"Cleaned up incomplete transaction: {temp_file.name}")
            except Exception:
                pass
