"""
Enhanced Problem Resolver Agent - Phase 2 Implementation
Implements permission-first, sandbox-based problem resolution with branch/PR creation
"""
import os
import re
import json
import uuid
import asyncio
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from services.retry_utils import call_llm_with_retry


class RunMode(str, Enum):
    DIAGNOSE_ONLY = "diagnose-only"
    ATTEMPT_FIX = "attempt-fix"


class ErrorCategory(str, Enum):
    SYNTAX = "syntax"
    MODULE_DEPENDENCY = "module_dependency"
    RUNTIME = "runtime"
    LOGIC = "logic"
    API_NETWORK = "api_network"
    DATABASE = "database"
    UI_RENDERING = "ui_rendering"
    STATE_MANAGEMENT = "state_management"
    SECURITY_AUTH = "security_auth"
    CONCURRENCY_ASYNC = "concurrency_async"
    BUILD_CONFIG = "build_config"
    DEPLOYMENT_PRODUCTION = "deployment_production"
    COMPILATION = "compilation"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolverRun:
    """Represents a single problem resolver run"""
    def __init__(self, run_id: str, session_id: str, app_path: str, commands: Dict, run_mode: RunMode):
        self.run_id = run_id
        self.session_id = session_id
        self.app_path = app_path
        self.commands = commands
        self.run_mode = run_mode
        self.status = "pending"
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict] = None
        self.logs: List[str] = []
        self.artifacts: List[Dict] = []


class EnhancedProblemResolverAgent:
    """
    Phase 2 compliant Problem Resolver Agent
    - Permission-first: requires approval before operations
    - Non-destructive: uses auto/* branches
    - Sandbox-based: runs commands in isolated environment
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings, sandbox_orchestrator=None):
        self.llm = llm
        self.settings = settings
        self.sandbox_orchestrator = sandbox_orchestrator
        self.active_runs: Dict[str, ResolverRun] = {}
        self.run_history: List[ResolverRun] = []

    async def analyze_and_resolve(
        self,
        app_path: str,
        error_logs: Optional[str] = None,
        context: Optional[Dict] = None,
        run_mode: RunMode = RunMode.ATTEMPT_FIX,
        timeout_seconds: int = 180,
    ) -> Dict:
        """Convenience API used by CollaborationManager to diagnose and (optionally) fix.

        Starts a resolver run with sensible defaults, waits for completion (up to timeout),
        and returns a compact summary including run_id and final result.
        """
        # Determine context dir and defaults similar to start_resolver_run
        app_path_obj = Path(app_path)
        context_dir = app_path_obj
        if not (app_path_obj / "package.json").exists() and (app_path_obj / "frontend" / "package.json").exists():
            context_dir = app_path_obj / "frontend"
        elif not (app_path_obj / "requirements.txt").exists() and (app_path_obj / "backend" / "requirements.txt").exists():
            context_dir = app_path_obj / "backend"

        commands: Dict[str, List[str]] = {"build": [], "run": [], "test": []}
        if (context_dir / "package.json").exists():
            commands["build"] = ["npm", "ci", "&&", "npm", "run", "build"]
            commands["run"] = ["npm", "run", "preview", "--", "--port", "3000", "--host", "0.0.0.0"]
        elif (context_dir / "requirements.txt").exists():
            commands["build"] = ["pip", "install", "-r", "requirements.txt"]
            commands["run"] = ["python", "main.py"]

        run_id = await self.start_resolver_run(
            session_id=context.get("session_id", "resolver-session") if context else "resolver-session",
            app_path=str(context_dir),
            commands=commands,
            run_mode=run_mode,
        )

        # Poll for completion
        deadline = datetime.utcnow().timestamp() + timeout_seconds
        status = None
        result_payload: Optional[Dict] = None
        while datetime.utcnow().timestamp() < deadline:
            info = self.get_run_result(run_id)
            if info and info.get("status") in {"completed", "failed"}:
                status = info.get("status")
                result_payload = info.get("result")
                break
            await asyncio.sleep(1)

        # Build summary
        issues_found = 0
        issues_resolved = 0
        if result_payload:
            issues_found = len(result_payload.get("issues", []) or [])
            repairs = result_payload.get("repairs", []) or []
            issues_resolved = len([r for r in repairs if r.get("success")])

        return {
            "run_id": run_id,
            "status": status or "running",
            "issues_found": issues_found,
            "issues_resolved": issues_resolved,
            "result": result_payload,
        }
        
    async def start_resolver_run(
        self,
        session_id: str,
        app_path: str,
        commands: Dict[str, List[str]],
        run_mode: RunMode = RunMode.DIAGNOSE_ONLY
    ) -> str:
        """
        Start a new problem resolver run
        
        Args:
            session_id: Session identifier
            app_path: Path to the application
            commands: {"build": [...], "run": [...], "test": [...]}
            run_mode: "diagnose-only" or "attempt-fix"
            
        Returns:
            run_id: Unique identifier for this run
        """
        # Resolve monorepo context: prefer frontend/backend subdirs when appropriate
        app_path_obj = Path(app_path)
        context_dir = app_path_obj
        if not (app_path_obj / "package.json").exists() and (app_path_obj / "frontend" / "package.json").exists():
            context_dir = app_path_obj / "frontend"
        elif not (app_path_obj / "requirements.txt").exists() and (app_path_obj / "backend" / "requirements.txt").exists():
            context_dir = app_path_obj / "backend"

        # Provide sensible defaults if commands are missing
        commands = commands or {"build": [], "run": [], "test": []}
        if not commands.get("build"):
            if (context_dir / "package.json").exists():
                commands["build"] = ["npm", "ci", "&&", "npm", "run", "build"]
            elif (context_dir / "requirements.txt").exists():
                commands["build"] = ["pip", "install", "-r", "requirements.txt"]
        if not commands.get("run"):
            if (context_dir / "package.json").exists():
                commands["run"] = ["npm", "run", "preview", "--", "--port", "3000", "--host", "0.0.0.0"]
            elif (context_dir / "requirements.txt").exists():
                commands["run"] = ["python", "main.py"]

        run_id = str(uuid.uuid4())
        
        run = ResolverRun(
            run_id=run_id,
            session_id=session_id,
            app_path=str(context_dir),
            commands=commands,
            run_mode=run_mode
        )
        
        self.active_runs[run_id] = run
        
        # Start async processing
        asyncio.create_task(self._execute_resolver_run(run))
        
        return run_id
    
    async def _execute_resolver_run(self, run: ResolverRun):
        """Execute the problem resolver run"""
        try:
            run.status = "running"
            run.logs.append(f"[{datetime.utcnow().isoformat()}] Starting resolver run: {run.run_id}")
            
            # Step 1: Reproduce the issue
            reproduction_result = await self._reproduce_issue(run)
            run.artifacts.append({
                "type": "reproduction",
                "data": reproduction_result,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
            # Step 2: Diagnose issues
            diagnosis_result = await self._diagnose_issues(run, reproduction_result)
            run.artifacts.append({
                "type": "diagnosis",
                "data": diagnosis_result,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
            # Step 3: If run_mode is attempt-fix, try to fix
            if run.run_mode == RunMode.ATTEMPT_FIX:
                repair_result = await self._attempt_repairs(run, diagnosis_result)
                run.artifacts.append({
                    "type": "repair",
                    "data": repair_result,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
            else:
                repair_result = {"status": "skipped", "reason": "diagnose-only mode"}
            
            # Step 4: Build final result
            run.result = await self._build_final_result(run, diagnosis_result, repair_result)
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            
        except Exception as e:
            run.status = "failed"
            run.result = {
                "summary": f"Resolver run failed: {str(e)}",
                "status": "failed",
                "error": str(e)
            }
            run.completed_at = datetime.utcnow()
        finally:
            # Move to history
            if run.run_id in self.active_runs:
                del self.active_runs[run.run_id]
            self.run_history.append(run)
    
    async def _reproduce_issue(self, run: ResolverRun) -> Dict:
        """Reproduce the issue by running build/run/test commands in sandbox"""
        run.logs.append(f"[{datetime.utcnow().isoformat()}] Reproducing issue...")
        
        result = {
            "build_output": None,
            "run_output": None,
            "test_output": None,
            "errors_detected": []
        }
        
        app_path = Path(run.app_path)
        
        # Run build command if provided
        if run.commands.get("build"):
            try:
                build_cmd = " ".join(run.commands["build"])
                run.logs.append(f"Executing build: {build_cmd}")
                
                proc = await asyncio.create_subprocess_shell(
                    build_cmd,
                    cwd=str(app_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
                
                result["build_output"] = {
                    "stdout": stdout.decode('utf-8', errors='ignore'),
                    "stderr": stderr.decode('utf-8', errors='ignore'),
                    "returncode": proc.returncode
                }
                
                if proc.returncode != 0:
                    result["errors_detected"].append({
                        "stage": "build",
                        "error": stderr.decode('utf-8', errors='ignore')
                    })
                    
            except asyncio.TimeoutError:
                result["build_output"] = {"error": "Build command timed out"}
                result["errors_detected"].append({"stage": "build", "error": "Timeout"})
            except Exception as e:
                result["build_output"] = {"error": str(e)}
                result["errors_detected"].append({"stage": "build", "error": str(e)})
        
        # Run test command if provided
        if run.commands.get("test"):
            try:
                test_cmd = " ".join(run.commands["test"])
                run.logs.append(f"Executing tests: {test_cmd}")
                
                proc = await asyncio.create_subprocess_shell(
                    test_cmd,
                    cwd=str(app_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
                
                result["test_output"] = {
                    "stdout": stdout.decode('utf-8', errors='ignore'),
                    "stderr": stderr.decode('utf-8', errors='ignore'),
                    "returncode": proc.returncode
                }
                
                if proc.returncode != 0:
                    result["errors_detected"].append({
                        "stage": "test",
                        "error": stderr.decode('utf-8', errors='ignore')
                    })
                    
            except asyncio.TimeoutError:
                result["test_output"] = {"error": "Test command timed out"}
            except Exception as e:
                result["test_output"] = {"error": str(e)}
        
        run.logs.append(f"Reproduction complete. Errors detected: {len(result['errors_detected'])}")
        return result
    
    async def _diagnose_issues(self, run: ResolverRun, reproduction_result: Dict) -> Dict:
        """Diagnose issues from reproduction output"""
        run.logs.append(f"[{datetime.utcnow().isoformat()}] Diagnosing issues...")
        
        issues = []
        
        # Parse errors from reproduction
        for error_info in reproduction_result.get("errors_detected", []):
            error_text = error_info.get("error", "")
            category = self._classify_error(error_text)
            risk = self._assess_risk(category, error_text)
            
            issue = {
                "id": str(uuid.uuid4()),
                "category": category.value,
                "severity": "high" if risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] else "medium",
                "stage": error_info.get("stage"),
                "message": error_text[:500],  # Truncate long errors
                "risk_level": risk.value,
                "suggested_fix": await self._generate_fix_suggestion(category, error_text),
                "confidence": 0.7 if category != ErrorCategory.RUNTIME else 0.5
            }
            issues.append(issue)
        
        # Also scan code for potential issues
        code_issues = await self._static_code_analysis(run.app_path)
        issues.extend(code_issues)
        
        diagnosis = {
            "total_issues": len(issues),
            "issues": issues,
            "categories": self._group_by_category(issues),
            "high_severity_count": sum(1 for i in issues if i["severity"] == "high"),
            "requires_escalation": any(i["risk_level"] in ["high", "critical"] for i in issues)
        }
        
        run.logs.append(f"Diagnosis complete. Found {len(issues)} issues.")
        return diagnosis
    
    def _classify_error(self, error_text: str) -> ErrorCategory:
        """Classify error into a category"""
        error_lower = error_text.lower()
        
        if any(keyword in error_lower for keyword in ["syntaxerror", "indentationerror", "unexpected token"]):
            return ErrorCategory.SYNTAX
        elif any(keyword in error_lower for keyword in ["modulenotfounderror", "cannot find module", "importerror"]):
            return ErrorCategory.MODULE_DEPENDENCY
        elif any(keyword in error_lower for keyword in ["database", "connection", "sqlalchemy", "mongodb"]):
            return ErrorCategory.DATABASE
        elif any(keyword in error_lower for keyword in ["timeout", "connectionerror", "httperror", "fetch"]):
            return ErrorCategory.API_NETWORK
        elif any(keyword in error_lower for keyword in ["authentication", "authorization", "401", "403"]):
            return ErrorCategory.SECURITY_AUTH
        elif any(keyword in error_lower for keyword in ["async", "await", "promise", "concurrent"]):
            return ErrorCategory.CONCURRENCY_ASYNC
        elif any(keyword in error_lower for keyword in ["render", "jsx", "component", "react", "vue"]):
            return ErrorCategory.UI_RENDERING
        elif any(keyword in error_lower for keyword in ["build", "webpack", "vite", "compilation", "returned a non-zero code: 2"]):
            return ErrorCategory.BUILD_CONFIG
        else:
            return ErrorCategory.RUNTIME
    
    def _assess_risk(self, category: ErrorCategory, error_text: str) -> RiskLevel:
        """Assess risk level of an issue"""
        error_lower = error_text.lower()
        
        # Critical: DB migrations, prod access, secrets
        if any(keyword in error_lower for keyword in ["migration", "production", "secret", "password", "api_key"]):
            return RiskLevel.CRITICAL
        
        # High: Auth, security, data loss
        if category in [ErrorCategory.SECURITY_AUTH, ErrorCategory.DATABASE]:
            return RiskLevel.HIGH
        
        # Medium: API, config, state
        if category in [ErrorCategory.API_NETWORK, ErrorCategory.BUILD_CONFIG, ErrorCategory.STATE_MANAGEMENT]:
            return RiskLevel.MEDIUM
        
        # Low: Syntax, dependency (reversible)
        if category in [ErrorCategory.SYNTAX, ErrorCategory.MODULE_DEPENDENCY]:
            return RiskLevel.LOW
        
        return RiskLevel.MEDIUM
    
    async def _generate_fix_suggestion(self, category: ErrorCategory, error_text: str) -> str:
        """Generate a fix suggestion using LLM"""
        try:
            prompt = f"""Analyze this error and provide a concise fix suggestion (max 2 sentences):

Category: {category.value}
Error: {error_text[:300]}

Provide only the fix suggestion, no explanation."""
            
            response = await call_llm_with_retry(self.llm, [
                SystemMessage(content="You are an expert debugger. Provide concise, actionable fix suggestions."),
                HumanMessage(content=prompt)
            ])
            
            return response.content.strip()[:200]
        except:
            return "Manual investigation required."
    
    async def _static_code_analysis(self, app_path: str) -> List[Dict]:
        """Perform static code analysis to find potential issues"""
        issues = []
        app_path_obj = Path(app_path)
        
        # Check for missing .env when .env.example exists
        if (app_path_obj / ".env.example").exists() and not (app_path_obj / ".env").exists():
            issues.append({
                "id": str(uuid.uuid4()),
                "category": ErrorCategory.BUILD_CONFIG.value,
                "severity": "medium",
                "message": "Missing .env file (found .env.example)",
                "risk_level": RiskLevel.LOW.value,
                "suggested_fix": "Copy .env.example to .env and configure variables",
                "confidence": 0.9
            })
        
        # Check for package.json without node_modules
        if (app_path_obj / "package.json").exists() and not (app_path_obj / "node_modules").exists():
            issues.append({
                "id": str(uuid.uuid4()),
                "category": ErrorCategory.MODULE_DEPENDENCY.value,
                "severity": "high",
                "message": "Node modules not installed",
                "risk_level": RiskLevel.LOW.value,
                "suggested_fix": "Run: npm install",
                "confidence": 0.95
            })
        
        # Node/vite ESM config validations
        try:
            pkg_path = app_path_obj / "package.json"
            pkg_type_module = False
            if pkg_path.exists():
                pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
                pkg_type_module = (pkg.get("type") == "module")

            # postcss.config.js should be ESM under type=module
            postcss_path = app_path_obj / "postcss.config.js"
            if pkg_type_module and postcss_path.exists():
                content = postcss_path.read_text(encoding="utf-8")
                if "module.exports" in content:
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "category": ErrorCategory.BUILD_CONFIG.value,
                        "severity": "medium",
                        "message": "postcss.config.js uses CommonJS under type=module",
                        "risk_level": RiskLevel.LOW.value,
                        "suggested_fix": "Rewrite postcss.config.js to use ESM export default",
                        "confidence": 0.95,
                        "kind": "postcss_esm"
                    })

            # tailwind.config.js should be ESM under type=module
            tailwind_path = app_path_obj / "tailwind.config.js"
            if pkg_type_module and tailwind_path.exists():
                tcontent = tailwind_path.read_text(encoding="utf-8")
                if "module.exports" in tcontent:
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "category": ErrorCategory.BUILD_CONFIG.value,
                        "severity": "low",
                        "message": "tailwind.config.js uses CommonJS under type=module",
                        "risk_level": RiskLevel.LOW.value,
                        "suggested_fix": "Rewrite tailwind.config.js to use ESM export default",
                        "confidence": 0.9,
                        "kind": "tailwind_esm"
                    })

            # tsconfig.node.json missing while referenced or typical Vite project
            tsconfig_path = app_path_obj / "tsconfig.json"
            ts_node_path = app_path_obj / "tsconfig.node.json"
            if tsconfig_path.exists() and not ts_node_path.exists():
                try:
                    tsconfig = json.loads(tsconfig_path.read_text(encoding="utf-8"))
                    refs = tsconfig.get("references", [])
                    ref_names = [r.get("path") for r in refs if isinstance(r, dict)]
                    if "./tsconfig.node.json" in ref_names or (app_path_obj / "vite.config.ts").exists():
                        issues.append({
                            "id": str(uuid.uuid4()),
                            "category": ErrorCategory.BUILD_CONFIG.value,
                            "severity": "medium",
                            "message": "Missing tsconfig.node.json required by Vite/TypeScript setup",
                            "risk_level": RiskLevel.LOW.value,
                            "suggested_fix": "Create tsconfig.node.json with moduleResolution 'bundler' and vite/client types",
                            "confidence": 0.95,
                            "kind": "tsconfig_node_missing"
                        })
                except Exception:
                    pass
        except Exception:
            pass
        
        return issues

    def get_run_artifacts(self, run_id: str) -> Optional[List[Dict]]:
        """Get artifacts for a resolver run"""
        if run_id in self.active_runs:
            return self.active_runs[run_id].artifacts
        for run in self.run_history:
            if run.run_id == run_id:
                return run.artifacts
        return None
    
    async def _attempt_repairs(self, run: ResolverRun, diagnosis: Dict) -> Dict:
        """Attempt to repair issues (only low-risk fixes)"""
        run.logs.append(f"[{datetime.utcnow().isoformat()}] Attempting repairs...")
        
        repairs = []
        branch_name = None
        pr_url = None
        preview_url = None
        
        # Filter to only low-risk issues
        low_risk_issues = [i for i in diagnosis["issues"] if i["risk_level"] == RiskLevel.LOW.value]
        
        if not low_risk_issues:
            run.logs.append("No low-risk issues to auto-fix. Escalation plan generated.")
            return {
                "status": "escalation_required",
                "escalation_plan": await self._generate_escalation_plan(diagnosis),
                "repairs": []
            }
        
        # Create a new branch for fixes
        branch_name = await self._create_fix_branch(run.app_path, low_risk_issues)
        
        # Attempt fixes
        for issue in low_risk_issues[:3]:  # Limit to 3 fixes per run
            repair_result = await self._apply_fix(run.app_path, issue)
            repairs.append(repair_result)
            
            if repair_result["success"]:
                run.logs.append(f"✓ Fixed: {issue['message'][:50]}")
            else:
                run.logs.append(f"✗ Failed: {issue['message'][:50]}")
        
        # Validate fixes
        validation = await self._validate_fixes(run, repairs)
        
        # If validation passed, create PR
        if validation["passed"] and branch_name:
            pr_url = await self._create_pull_request(run.app_path, branch_name, repairs, validation)
            preview_url = await self._generate_preview_url(run.session_id, branch_name)
        
        return {
            "status": "completed" if validation["passed"] else "partial",
            "repairs": repairs,
            "branch": branch_name,
            "pr_url": pr_url,
            "preview_url": preview_url,
            "validation": validation
        }
    
    async def _create_fix_branch(self, app_path: str, issues: List[Dict]) -> Optional[str]:
        """Create a new branch for auto-fixes"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            category = issues[0]["category"] if issues else "fix"
            branch_name = f"auto/fix-{category}-{timestamp}"
            
            # Check if git repo exists
            git_dir = Path(app_path) / ".git"
            if not git_dir.exists():
                # Initialize git repo
                subprocess.run(["git", "init"], cwd=app_path, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "bot@autobuilder.dev"], cwd=app_path, check=True)
                subprocess.run(["git", "config", "user.name", "AutoBuilder Bot"], cwd=app_path, check=True)
                subprocess.run(["git", "add", "."], cwd=app_path, check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=app_path, check=True)
            
            # Create and checkout new branch
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=app_path, check=True, capture_output=True)
            
            return branch_name
        except Exception as e:
            return None
    
    async def _apply_fix(self, app_path: str, issue: Dict) -> Dict:
        """Apply a single fix to the codebase"""
        try:
            category = ErrorCategory(issue["category"])
            
            if category == ErrorCategory.MODULE_DEPENDENCY:
                return await self._fix_dependency(app_path, issue)
            elif category == ErrorCategory.BUILD_CONFIG:
                return await self._fix_config(app_path, issue)
            elif category == ErrorCategory.SYNTAX:
                return await self._fix_syntax(app_path, issue)
            else:
                return {"success": False, "action": "Unsupported category for auto-fix"}
                
        except Exception as e:
            return {"success": False, "action": f"Fix failed: {str(e)}", "error": str(e)}
    
    async def _fix_dependency(self, app_path: str, issue: Dict) -> Dict:
        """Fix dependency issues"""
        if "npm install" in issue.get("suggested_fix", "").lower():
            try:
                proc = await asyncio.create_subprocess_shell(
                    "npm install",
                    cwd=app_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(proc.communicate(), timeout=120)
                return {"success": proc.returncode == 0, "action": "Installed npm dependencies"}
            except:
                return {"success": False, "action": "npm install failed"}
        
        return {"success": False, "action": "No automated fix available"}
    
    async def _fix_config(self, app_path: str, issue: Dict) -> Dict:
        """Fix configuration issues"""
        # Create .env from .env.example
        if ".env" in issue.get("message", "") and "example" in issue.get("message", ""):
            try:
                env_example = Path(app_path) / ".env.example"
                env_file = Path(app_path) / ".env"
                
                if env_example.exists():
                    import shutil
                    shutil.copy(env_example, env_file)
                    return {"success": True, "action": "Created .env from .env.example"}
            except:
                pass
        
        kind = issue.get("kind", "")
        try:
            if kind == "postcss_esm":
                postcss_path = Path(app_path) / "postcss.config.js"
                if postcss_path.exists():
                    postcss_path.write_text(
                        """export default {\n  plugins: {\n    tailwindcss: {},\n    autoprefixer: {},\n  },\n}\n""",
                        encoding="utf-8",
                    )
                    return {"success": True, "action": "Converted postcss.config.js to ESM"}
            elif kind == "tailwind_esm":
                tailwind_path = Path(app_path) / "tailwind.config.js"
                if tailwind_path.exists():
                    tailwind_path.write_text(
                        """export default {\n  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],\n  theme: {\n    extend: {},\n  },\n  plugins: [],\n}\n""",
                        encoding="utf-8",
                    )
                    return {"success": True, "action": "Converted tailwind.config.js to ESM"}
            elif kind == "tsconfig_node_missing":
                ts_node_path = Path(app_path) / "tsconfig.node.json"
                ts_node_path.write_text(
                    json.dumps({
                        "compilerOptions": {
                            "composite": True,
                            "skipLibCheck": True,
                            "module": "ESNext",
                            "moduleResolution": "bundler",
                            "resolveJsonModule": True,
                            "allowSyntheticDefaultImports": True,
                            "types": ["vite/client"],
                        },
                        "include": ["vite.config.ts"],
                    }, indent=2),
                    encoding="utf-8",
                )
                return {"success": True, "action": "Added tsconfig.node.json"}
        except Exception as e:
            return {"success": False, "action": f"Config fix failed: {str(e)}"}
        
        return {"success": False, "action": "No automated fix available"}
    
    async def _fix_syntax(self, app_path: str, issue: Dict) -> Dict:
        """Fix syntax issues using LLM"""
        # For Phase 2, we'll skip auto syntax fixes as they're risky
        return {"success": False, "action": "Syntax fixes require manual review"}
    
    async def _validate_fixes(self, run: ResolverRun, repairs: List[Dict]) -> Dict:
        """Validate that fixes work by re-running build/tests"""
        try:
            # Re-run build command
            if run.commands.get("build"):
                build_cmd = " ".join(run.commands["build"])
                proc = await asyncio.create_subprocess_shell(
                    build_cmd,
                    cwd=run.app_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
                
                passed = proc.returncode == 0
                return {
                    "passed": passed,
                    "build_output": stdout.decode('utf-8', errors='ignore')[:500],
                    "errors": stderr.decode('utf-8', errors='ignore')[:500] if not passed else None
                }
            
            return {"passed": True, "message": "No validation commands configured"}
        except:
            return {"passed": False, "error": "Validation failed"}
    
    async def _create_pull_request(self, app_path: str, branch: str, repairs: List[Dict], validation: Dict) -> Optional[str]:
        """Create a pull request with fixes"""
        try:
            # Commit changes
            subprocess.run(["git", "add", "."], cwd=app_path, check=True)
            
            commit_msg = f"Auto-fix: {len([r for r in repairs if r['success']])} issues resolved\n\n"
            for repair in repairs:
                if repair["success"]:
                    commit_msg += f"- {repair['action']}\n"
            
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=app_path, check=True)
            
            # In a real implementation, this would push and create PR via GitHub API
            # For now, return a mock URL
            return f"https://github.com/mock/pr/{branch}"
            
        except:
            return None
    
    async def _generate_preview_url(self, session_id: str, branch: str) -> Optional[str]:
        """Generate a preview URL for the fixed branch"""
        # In real implementation, this would deploy to a preview environment
        return f"https://preview-{session_id[:8]}.autobuilder.dev"
    
    async def _generate_escalation_plan(self, diagnosis: Dict) -> Dict:
        """Generate an escalation plan for high-risk issues"""
        high_risk_issues = [i for i in diagnosis["issues"] if i["risk_level"] in ["high", "critical"]]
        
        plan = {
            "priority": "high" if any(i["risk_level"] == "critical" for i in high_risk_issues) else "medium",
            "issues": high_risk_issues,
            "recommended_actions": [],
            "requires_manual_review": True
        }
        
        for issue in high_risk_issues:
            plan["recommended_actions"].append({
                "issue_id": issue["id"],
                "action": issue["suggested_fix"],
                "requires_approval": True,
                "risk_mitigation": "Manual review and testing required"
            })
        
        return plan
    
    async def _build_final_result(self, run: ResolverRun, diagnosis: Dict, repair_result: Dict) -> Dict:
        """Build the final structured result"""
        return {
            "id": run.run_id,
            "summary": f"Found {diagnosis['total_issues']} issues, " + 
                      (f"fixed {len([r for r in repair_result.get('repairs', []) if r.get('success')])} issues" 
                       if repair_result.get("repairs") else "diagnosis only"),
            "status": repair_result.get("status", "completed"),
            "category": diagnosis["categories"][0] if diagnosis.get("categories") else "mixed",
            "confidence": sum(i.get("confidence", 0.5) for i in diagnosis["issues"]) / max(len(diagnosis["issues"]), 1),
            "branch": repair_result.get("branch"),
            "prUrl": repair_result.get("pr_url"),
            "previewUrl": repair_result.get("preview_url"),
            "logsUrl": f"/api/agent/problem-resolver/{run.run_id}/logs",
            "artifacts": run.artifacts,
            "issues": diagnosis["issues"],
            "repairs": repair_result.get("repairs", []),
            "validation": repair_result.get("validation"),
            "escalation_plan": repair_result.get("escalation_plan"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def _group_by_category(self, issues: List[Dict]) -> List[str]:
        """Group issues by category"""
        categories = set(i["category"] for i in issues)
        return sorted(list(categories))
    
    def get_run_result(self, run_id: str) -> Optional[Dict]:
        """Get the result of a resolver run"""
        # Check active runs
        if run_id in self.active_runs:
            run = self.active_runs[run_id]
            return {
                "run_id": run.run_id,
                "status": run.status,
                "result": run.result,
                "logs": run.logs[-10:],  # Last 10 log entries
                "created_at": run.created_at.isoformat() + "Z",
                "completed_at": run.completed_at.isoformat() + "Z" if run.completed_at else None
            }
        
        # Check history
        for run in self.run_history:
            if run.run_id == run_id:
                return {
                    "run_id": run.run_id,
                    "status": run.status,
                    "result": run.result,
                    "logs": run.logs[-10:],
                    "created_at": run.created_at.isoformat() + "Z",
                    "completed_at": run.completed_at.isoformat() + "Z" if run.completed_at else None
                }
        
        return None
    
    def get_run_logs(self, run_id: str) -> Optional[List[str]]:
        """Get full logs for a run"""
        if run_id in self.active_runs:
            return self.active_runs[run_id].logs
        
        for run in self.run_history:
            if run.run_id == run_id:
                return run.logs
        
        return None
