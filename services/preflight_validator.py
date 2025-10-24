"""
Preflight Validator - lightweight checks before sandbox build
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List


class PreflightValidator:
    """Run quick, deterministic checks on generated projects.
    - Manifests (package.json scripts/deps)
    - Suspicious dependencies
    - Presence of frontend/backend structure
    """

    def __init__(self) -> None:
        pass

    async def validate(self, project_root: str) -> Dict:
        root = Path(project_root)
        issues: List[Dict] = []
        suggestions: List[Dict] = []

        # Frontend package.json
        fe_pkg = root / "frontend" / "package.json"
        if not fe_pkg.exists():
            issues.append({
                "component": "frontend",
                "issue": "missing_package_json",
                "message": "frontend/package.json is missing",
                "risk": "high",
            })
        else:
            try:
                pkg = json.loads(fe_pkg.read_text(encoding="utf-8"))
                scripts = (pkg.get("scripts") or {})
                if "build" not in scripts:
                    issues.append({
                        "component": "frontend",
                        "issue": "missing_build_script",
                        "message": "frontend/package.json missing scripts.build",
                        "risk": "medium",
                    })
                    suggestions.append({
                        "action": "ensure_script",
                        "component": "frontend",
                        "file": str(fe_pkg),
                        "key": ["scripts", "build"],
                        "value": "tsc && vite build"
                    })
                # Minimal React + Vite expectations
                deps = (pkg.get("dependencies") or {})
                devdeps = (pkg.get("devDependencies") or {})
                missing_deps = [d for d in ["react", "react-dom"] if d not in deps]
                if missing_deps:
                    issues.append({
                        "component": "frontend",
                        "issue": "missing_dependencies",
                        "message": f"Missing dependencies: {missing_deps}",
                        "risk": "medium",
                    })
                missing_dev = [d for d in ["vite", "typescript"] if d not in devdeps]
                if missing_dev:
                    issues.append({
                        "component": "frontend",
                        "issue": "missing_dev_dependencies",
                        "message": f"Missing devDependencies: {missing_dev}",
                        "risk": "low",
                    })
            except Exception as e:
                issues.append({
                    "component": "frontend",
                    "issue": "invalid_package_json",
                    "message": f"Invalid JSON in frontend/package.json: {e}",
                    "risk": "high",
                })

        # Root package.json clean-up (avoid stray deps like 'build', 'run', 'npm')
        root_pkg = root / "package.json"
        if root_pkg.exists():
            try:
                rootp = json.loads(root_pkg.read_text(encoding="utf-8"))
                deps = (rootp.get("dependencies") or {})
                bad = [k for k in deps.keys() if k in {"build", "run", "npm"}]
                if bad:
                    issues.append({
                        "component": "root",
                        "issue": "suspicious_dependencies",
                        "message": f"Root package.json contains suspicious deps: {bad}",
                        "risk": "medium",
                    })
                    suggestions.append({
                        "action": "remove_deps",
                        "component": "root",
                        "file": str(root_pkg),
                        "deps": bad
                    })
            except Exception as e:
                issues.append({
                    "component": "root",
                    "issue": "invalid_package_json",
                    "message": f"Invalid JSON in root package.json: {e}",
                    "risk": "medium",
                })

        # Simple score and summary
        score = max(0, 100 - len(issues) * 10)
        overall = "passed" if score >= 80 and not any(i.get("risk") == "high" for i in issues) else "failed"

        return {
            "overall": overall,
            "score": score,
            "issues": issues,
            "suggestions": suggestions,
        }
