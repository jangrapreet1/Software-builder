"""
Sandbox orchestration and security services
"""
import sys
from pathlib import Path

# Extend package path to include top-level 'services' directory so submodules resolve
_pkg_dir = Path(__file__).resolve().parent
_repo_root = _pkg_dir.parent.parent
_top_services = _repo_root / "services"
try:
    if str(_top_services) not in __path__:
        __path__.append(str(_top_services))  # type: ignore[name-defined]
except Exception:
    # Fallback: ensure repo root is on sys.path
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

# Prefer top-level services.build_registry over local coordinator version when available.
# This ensures `from services.build_registry import BuildRegistry` returns the rich implementation
# used by tests, even when `coordinator` is first on sys.path.
try:
    import importlib.util
    import sys as _sys
    top_build_registry = _top_services / "build_registry.py"
    if top_build_registry.exists():
        mod_name = "services.build_registry"
        if mod_name not in _sys.modules:
            spec = importlib.util.spec_from_file_location(mod_name, str(top_build_registry))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                _sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
except Exception:
    pass

from .repository_detector import RepositoryDetector
from .sandbox_orchestrator import SandboxOrchestrator
from .session_manager import SessionManager
from .permission_manager import PermissionManager
from .audit_logger import AuditLogger, AuditEventType, audit_logger

__all__ = [
    "RepositoryDetector",
    "SandboxOrchestrator",
    "SessionManager",
    "PermissionManager",
    "AuditLogger",
    "AuditEventType",
    "audit_logger",
]
