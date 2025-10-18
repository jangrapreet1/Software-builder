"""Unified service package exports bridging legacy coordinator modules."""

from importlib import import_module
import sys


def _bridge_legacy_services():
    """Expose coordinator service modules under the `services` namespace."""
    legacy_modules = {
        "repository_detector": ["RepositoryDetector"],
        "sandbox_orchestrator": ["SandboxOrchestrator"],
        "session_manager": ["SessionManager"],
        "permission_manager": ["PermissionManager"],
        "build_registry": ["BuildRegistry"],
        "audit_logger": ["AuditLogger", "AuditEventType", "audit_logger"],
        "run_audit_logger": ["RunAuditLogger"],
        "agent_collaboration_manager": ["CollaborationManager", "LivePreviewBridge"],
    }
    package_name = __name__

    for module_name, attributes in legacy_modules.items():
        try:
            module = import_module(f"coordinator.services.{module_name}")
        except ImportError:  # pragma: no cover - optional module
            for attr in attributes:
                globals()[attr] = None  # type: ignore[assignment]
            continue

        # Register alias so `import services.<module>` works
        sys.modules[f"{package_name}.{module_name}"] = module

        # Re-export selected attributes
        for attr in attributes:
            globals()[attr] = getattr(module, attr)


_bridge_legacy_services()


# Enhanced robustness services remain first-class exports
from .metrics_collector import MetricsCollector, get_metrics_collector
from .error_feedback_system import ErrorFeedbackSystem
from .enhanced_state_manager import EnhancedStateManager
from .build_validator import BuildValidator


__all__ = [
    # Legacy coordinator services
    "RepositoryDetector",
    "SandboxOrchestrator",
    "SessionManager",
    "PermissionManager",
    "BuildRegistry",
    "AuditLogger",
    "AuditEventType",
    "audit_logger",
    "RunAuditLogger",
    "CollaborationManager",
    "LivePreviewBridge",
    # Enhanced services
    "MetricsCollector",
    "get_metrics_collector",
    "ErrorFeedbackSystem",
    "EnhancedStateManager",
    "BuildValidator",
]
