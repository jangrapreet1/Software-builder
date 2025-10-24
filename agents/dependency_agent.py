"""
Dependency Agent - audits and performs low-risk dependency/config fixes.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Optional, List

from .base_agent import BaseAgent, ExecutionContext, ExecutionResult, AgentStatus, AgentCapability


class DependencyAgent(BaseAgent):
    def get_capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.CODE_ANALYSIS, AgentCapability.PROBLEM_RESOLUTION]

    def validate_input(self, request_data: Dict) -> tuple[bool, Optional[str]]:
        if "project_path" not in request_data:
            return False, "project_path is required"
        return True, None

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        root = Path(context.request_data["project_path"]).resolve()
        fixes_applied: List[str] = []
        warnings: List[str] = []

        # Ensure frontend build script exists
        fe_pkg = root / "frontend" / "package.json"
        if fe_pkg.exists():
            try:
                pkg = json.loads(fe_pkg.read_text(encoding="utf-8"))
                scripts = pkg.setdefault("scripts", {})
                if "build" not in scripts:
                    scripts["build"] = "tsc && vite build"
                    fe_pkg.write_text(json.dumps(pkg, indent=2), encoding="utf-8")
                    fixes_applied.append("frontend.scripts.build")
            except Exception as e:
                warnings.append(f"Could not update frontend/package.json: {e}")

        # Remove suspicious deps from root
        root_pkg = root / "package.json"
        if root_pkg.exists():
            try:
                rpkg = json.loads(root_pkg.read_text(encoding="utf-8"))
                deps = rpkg.get("dependencies") or {}
                bad = [k for k in list(deps.keys()) if k in {"build", "run", "npm"}]
                if bad:
                    for k in bad:
                        deps.pop(k, None)
                    rpkg["dependencies"] = deps
                    root_pkg.write_text(json.dumps(rpkg, indent=2), encoding="utf-8")
                    fixes_applied.append(f"root.remove_deps:{','.join(bad)}")
            except Exception as e:
                warnings.append(f"Could not update root package.json: {e}")

        result = {
            "fixes_applied": fixes_applied,
        }
        return ExecutionResult(
            status=AgentStatus.COMPLETED,
            output=result,
            warnings=warnings,
            telemetry=context.telemetry,
        )
