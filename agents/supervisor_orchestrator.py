"""
Supervisor Orchestrator - dynamic plan with conditional routing and HITL gates.
Provides a blackboard for cross-step state and helper guards used by the workflow.
"""
from __future__ import annotations
import os
from typing import Dict, Any, List


class SupervisorOrchestrator:
    def __init__(self):
        self.blackboard: Dict[str, Any] = {
            "completed_steps": [],
        }

    def plan(self, goal: Dict[str, Any], flags: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Return a conditional plan DAG as a linearized list with metadata.
        flags: { enable_resolution: bool, run_tests: bool }
        """
        flags = flags or {}
        plan: List[Dict[str, Any]] = [
            {"step": "analyze_brief", "depends_on": []},
            {"step": "generate_specs", "depends_on": ["analyze_brief"]},
            {"step": "plan_tasks", "depends_on": ["generate_specs"]},
            {"step": "generate_backend", "depends_on": ["plan_tasks"]},
            {"step": "generate_frontend", "depends_on": ["plan_tasks"]},
            {"step": "integrate", "depends_on": ["generate_backend", "generate_frontend"]},
            {"step": "preflight", "depends_on": ["integrate"]},
            {"step": "validate", "depends_on": ["preflight"]},
            # Monitoring feeds feedback loop before resolution
            {"step": "monitor", "depends_on": ["validate"]},
        ]

        # Conditionally add resolution/testing steps
        if flags.get("enable_resolution", True):
            plan.append({"step": "resolve", "depends_on": ["validate"]})
        if flags.get("run_tests", False):
            # tests should run after resolve if present, otherwise after validate
            deps = ["resolve"] if flags.get("enable_resolution", True) else ["validate"]
            plan.append({"step": "test", "depends_on": deps})

        return plan

    def should_execute(self, step: str, state: Dict[str, Any], flags: Dict[str, Any] | None = None) -> bool:
        """Gate step execution based on blackboard and state (conditional routing)."""
        flags = flags or {}
        if step == "resolve":
            if not flags.get("enable_resolution", True):
                return False
            # Resolve only if validation failed or warnings/errors exist
            status = (state.get("validation_results", {}) or {}).get("overall_status", "unknown")
            has_errors = bool(state.get("errors"))
            return status in {"failed", "unknown"} or has_errors
        if step == "test":
            return bool(flags.get("run_tests", False))
        if step == "monitor":
            # Enable monitoring by default; can be disabled via env
            return os.getenv("ENABLE_MONITORING", "1").lower() in ("1", "true", "yes")
        # Default: execute
        return True

    def requires_hitl(self, step: str, state: Dict[str, Any]) -> bool:
        """Identify human-in-the-loop checkpoints."""
        hitl_on_resolve = os.getenv("HITL_ON_RESOLVE", "0").lower() in ("1", "true", "yes")
        if step == "resolve" and hitl_on_resolve:
            status = (state.get("validation_results", {}) or {}).get("overall_status", "unknown")
            return status == "failed"
        return False

    def mark_completed(self, step: str) -> None:
        if step not in self.blackboard["completed_steps"]:
            self.blackboard["completed_steps"].append(step)
