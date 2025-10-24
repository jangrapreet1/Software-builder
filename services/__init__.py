"""Top-level services package.

Provides first-class modules and conditionally bridges coordinator-only modules
without overriding local implementations.
"""

import sys
from importlib import import_module
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent


def _module_exists_locally(name: str) -> bool:
    return (_pkg_dir / f"{name}.py").exists() or (_pkg_dir / name).is_dir()


def _bridge_coordinator_services_if_missing():
    """Expose coordinator service modules only when not present locally."""
    legacy_modules = {
        "repository_detector": ["RepositoryDetector"],
        "sandbox_orchestrator": ["SandboxOrchestrator"],
        "session_manager": ["SessionManager"],
        "permission_manager": ["PermissionManager"],
        # Do NOT include build_registry; it exists locally and must not be overridden
        "audit_logger": ["AuditLogger", "AuditEventType", "audit_logger"],
        "run_audit_logger": ["RunAuditLogger"],
        "agent_collaboration_manager": ["CollaborationManager", "LivePreviewBridge"],
    }

    package_name = __name__

    for module_name, attributes in legacy_modules.items():
        if _module_exists_locally(module_name):
            # Keep local implementation
            continue
        try:
            module = import_module(f"coordinator.services.{module_name}")
        except ImportError:  # optional module
            for attr in attributes:
                globals()[attr] = None  # type: ignore[assignment]
            continue

        # Register alias so `import services.<module>` works for coordinator-only modules
        sys.modules[f"{package_name}.{module_name}"] = module

        # Re-export selected attributes
        for attr in attributes:
            globals()[attr] = getattr(module, attr)


_bridge_coordinator_services_if_missing()


# Explicit re-exports for common local services
from .metrics_collector import MetricsCollector, get_metrics_collector  # noqa: E402
from .error_feedback_system import ErrorFeedbackSystem  # noqa: E402
from .enhanced_state_manager import EnhancedStateManager  # noqa: E402
from .build_validator import BuildValidator  # noqa: E402


__all__ = [
    # Coordinator-only (conditionally bridged)
    "RepositoryDetector",
    "SandboxOrchestrator",
    "SessionManager",
    "PermissionManager",
    "AuditLogger",
    "AuditEventType",
    "audit_logger",
    "RunAuditLogger",
    "CollaborationManager",
    "LivePreviewBridge",
    # Local services
    "MetricsCollector",
    "get_metrics_collector",
    "ErrorFeedbackSystem",
    "EnhancedStateManager",
    "BuildValidator",
]
