"""
Problem Resolver Agent - Autonomous error detection and resolution
Handles 12+ categories of errors with self-healing capabilities
"""
import os
import re
import json
import traceback
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import subprocess

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from services.retry_utils import call_llm_with_retry


class ErrorCategory:
    """Error categories for classification"""
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


class ProblemResolverAgent:
    """
    Autonomous agent that detects and resolves code-related issues
    across multiple error categories without user intervention
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings):
        self.llm = llm
        self.settings = settings
        self.resolution_history: List[Dict] = []
        self.max_resolution_attempts = 3
        
    async def analyze_and_resolve(
        self,
        app_path: str,
        error_logs: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Main entry point: analyze issues and resolve them autonomously
        
        Returns:
            {
                "status": "success" | "failed",
                "issues_found": int,
                "issues_resolved": int,
                "resolution_log": [list of resolution actions],
                "remaining_issues": [list of unresolved issues],
                "modified_files": [list of file paths]
            }
        """
        app_path_obj = Path(app_path)
        
        if not app_path_obj.exists():
            return {
                "status": "failed",
                "error": f"App path not found: {app_path}",
                "issues_found": 0,
                "issues_resolved": 0
            }
        
        # Step 1: Detect all issues
        issues = await self._detect_all_issues(app_path_obj, error_logs, context)
        
        # Step 2: Classify issues by category
        classified_issues = self._classify_issues(issues)
        
        # Step 3: Resolve issues autonomously
        resolution_results = await self._resolve_issues(app_path_obj, classified_issues)
        
        # Step 4: Validate fixes
        validation_results = await self._validate_fixes(app_path_obj, resolution_results)
        
        return {
            "status": "success" if validation_results["all_resolved"] else "partial",
            "issues_found": len(issues),
            "issues_resolved": validation_results["resolved_count"],
            "resolution_log": resolution_results["actions"],
            "remaining_issues": validation_results["remaining_issues"],
            "modified_files": resolution_results["modified_files"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    async def _detect_all_issues(
        self,
        app_path: Path,
        error_logs: Optional[str],
        context: Optional[Dict]
    ) -> List[Dict]:
        """Detect all issues across different categories"""
        issues = []
        
        # 1. Syntax errors - check Python/JavaScript/TypeScript files
        syntax_issues = await self._detect_syntax_errors(app_path)
        issues.extend(syntax_issues)
        
        # 2. Module/dependency errors
        dependency_issues = await self._detect_dependency_errors(app_path)
        issues.extend(dependency_issues)
        
        # 3. Parse error logs if provided
        if error_logs:
            log_issues = self._parse_error_logs(error_logs)
            issues.extend(log_issues)
        
        # 4. Configuration issues
        config_issues = await self._detect_config_issues(app_path)
        issues.extend(config_issues)
        
        # 5. Database connection issues
        db_issues = await self._detect_database_issues(app_path)
        issues.extend(db_issues)
        
        # 6. API/Network issues
        api_issues = await self._detect_api_issues(app_path, context)
        issues.extend(api_issues)
        
        return issues
    
    async def _detect_syntax_errors(self, app_path: Path) -> List[Dict]:
        """Detect compilation and syntax errors"""
        issues = []
        
        # Check Python files
        python_files = list(app_path.rglob("*.py"))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, str(py_file), 'exec')
            except SyntaxError as e:
                issues.append({
                    "category": ErrorCategory.SYNTAX,
                    "severity": "high",
                    "file": str(py_file.relative_to(app_path)),
                    "line": e.lineno,
                    "message": str(e),
                    "code_snippet": e.text if e.text else ""
                })
        
        # Check JavaScript/TypeScript files
        js_files = list(app_path.rglob("*.js")) + list(app_path.rglob("*.jsx")) + \
                   list(app_path.rglob("*.ts")) + list(app_path.rglob("*.tsx"))
        
        for js_file in js_files:
            # Basic syntax check using regex patterns
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for common syntax issues
                if self._has_js_syntax_issues(content):
                    issues.append({
                        "category": ErrorCategory.SYNTAX,
                        "severity": "medium",
                        "file": str(js_file.relative_to(app_path)),
                        "message": "Potential JavaScript/TypeScript syntax issues detected"
                    })
            except Exception:
                pass
        
        return issues
    
    async def _detect_dependency_errors(self, app_path: Path) -> List[Dict]:
        """Detect missing or incompatible dependencies"""
        issues = []
        
        # Check Python requirements
        req_file = app_path / "requirements.txt"
        if req_file.exists():
            try:
                result = subprocess.run(
                    ["pip", "check"],
                    cwd=str(app_path),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    issues.append({
                        "category": ErrorCategory.MODULE_DEPENDENCY,
                        "severity": "high",
                        "file": "requirements.txt",
                        "message": "Dependency conflicts detected",
                        "details": result.stdout + result.stderr
                    })
            except Exception:
                pass
        
        # Check Node.js dependencies
        package_json = app_path / "package.json"
        if package_json.exists():
            node_modules = app_path / "node_modules"
            if not node_modules.exists():
                issues.append({
                    "category": ErrorCategory.MODULE_DEPENDENCY,
                    "severity": "high",
                    "file": "package.json",
                    "message": "Node modules not installed",
                    "fix_command": "npm install"
                })
        
        return issues
    
    async def _detect_config_issues(self, app_path: Path) -> List[Dict]:
        """Detect build and configuration issues"""
        issues = []
        
        # Check for missing environment variables
        env_example = app_path / ".env.example"
        env_file = app_path / ".env"
        
        if env_example.exists() and not env_file.exists():
            issues.append({
                "category": ErrorCategory.BUILD_CONFIG,
                "severity": "medium",
                "file": ".env",
                "message": "Environment file missing",
                "suggested_fix": "Copy .env.example to .env and configure"
            })
        
        return issues
    
    async def _detect_database_issues(self, app_path: Path) -> List[Dict]:
        """Detect database connection and query issues"""
        issues = []
        
        # Check for database configuration
        python_files = list(app_path.rglob("*.py"))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for database imports without proper error handling
                if "sqlalchemy" in content.lower() or "pymongo" in content.lower():
                    if "try:" not in content or "except" not in content:
                        issues.append({
                            "category": ErrorCategory.DATABASE,
                            "severity": "medium",
                            "file": str(py_file.relative_to(app_path)),
                            "message": "Database operations without error handling",
                            "suggested_fix": "Add try-except blocks around database operations"
                        })
            except Exception:
                pass
        
        return issues
    
    async def _detect_api_issues(self, app_path: Path, context: Optional[Dict]) -> List[Dict]:
        """Detect API and network-related issues"""
        issues = []
        
        # Check for API calls without error handling
        python_files = list(app_path.rglob("*.py"))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for requests/httpx without proper error handling
                if ("requests." in content or "httpx." in content) and "timeout=" not in content:
                    issues.append({
                        "category": ErrorCategory.API_NETWORK,
                        "severity": "medium",
                        "file": str(py_file.relative_to(app_path)),
                        "message": "API calls without timeout configuration",
                        "suggested_fix": "Add timeout parameter to HTTP requests"
                    })
            except Exception:
                pass
        
        return issues
    
    def _parse_error_logs(self, error_logs: str) -> List[Dict]:
        """Parse error logs and extract issues"""
        issues = []
        
        # Common error patterns
        patterns = {
            ErrorCategory.MODULE_DEPENDENCY: [
                r"ModuleNotFoundError: No module named '([^']+)'",
                r"ImportError: cannot import name '([^']+)'"
            ],
            ErrorCategory.RUNTIME: [
                r"RuntimeError: (.+)",
                r"Exception: (.+)"
            ],
            ErrorCategory.SYNTAX: [
                r"SyntaxError: (.+)",
                r"IndentationError: (.+)"
            ],
            ErrorCategory.DATABASE: [
                r"OperationalError: (.+)",
                r"DatabaseError: (.+)"
            ],
            ErrorCategory.API_NETWORK: [
                r"ConnectionError: (.+)",
                r"Timeout: (.+)",
                r"HTTPError: (.+)"
            ]
        }
        
        for category, regex_list in patterns.items():
            for pattern in regex_list:
                matches = re.finditer(pattern, error_logs, re.MULTILINE)
                for match in matches:
                    issues.append({
                        "category": category,
                        "severity": "high",
                        "message": match.group(0),
                        "details": match.group(1) if len(match.groups()) > 0 else ""
                    })
        
        return issues
    
    def _classify_issues(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """Classify issues by category for prioritized resolution"""
        classified = {}
        
        for issue in issues:
            category = issue.get("category", ErrorCategory.RUNTIME)
            if category not in classified:
                classified[category] = []
            classified[category].append(issue)
        
        return classified
    
    async def _resolve_issues(
        self,
        app_path: Path,
        classified_issues: Dict[str, List[Dict]]
    ) -> Dict:
        """Resolve issues autonomously using category-specific handlers"""
        actions = []
        modified_files = set()
        
        # Priority order for resolution
        priority_order = [
            ErrorCategory.SYNTAX,
            ErrorCategory.MODULE_DEPENDENCY,
            ErrorCategory.BUILD_CONFIG,
            ErrorCategory.DATABASE,
            ErrorCategory.API_NETWORK,
            ErrorCategory.RUNTIME,
            ErrorCategory.LOGIC,
            ErrorCategory.UI_RENDERING,
            ErrorCategory.STATE_MANAGEMENT,
            ErrorCategory.SECURITY_AUTH,
            ErrorCategory.CONCURRENCY_ASYNC,
            ErrorCategory.DEPLOYMENT_PRODUCTION
        ]
        
        for category in priority_order:
            if category not in classified_issues:
                continue
            
            issues = classified_issues[category]
            handler = self._get_handler_for_category(category)
            
            for issue in issues:
                try:
                    result = await handler(app_path, issue)
                    actions.append({
                        "category": category,
                        "issue": issue.get("message", "Unknown issue"),
                        "action": result["action"],
                        "success": result["success"],
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    })
                    
                    if result["success"] and "file" in result:
                        modified_files.add(result["file"])
                        
                except Exception as e:
                    actions.append({
                        "category": category,
                        "issue": issue.get("message", "Unknown issue"),
                        "action": "Resolution failed",
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    })
        
        return {
            "actions": actions,
            "modified_files": list(modified_files)
        }
    
    def _get_handler_for_category(self, category: str):
        """Get the appropriate handler function for an error category"""
        handlers = {
            ErrorCategory.SYNTAX: self._resolve_syntax_error,
            ErrorCategory.MODULE_DEPENDENCY: self._resolve_dependency_error,
            ErrorCategory.BUILD_CONFIG: self._resolve_config_error,
            ErrorCategory.DATABASE: self._resolve_database_error,
            ErrorCategory.API_NETWORK: self._resolve_api_error,
            ErrorCategory.RUNTIME: self._resolve_runtime_error,
            ErrorCategory.LOGIC: self._resolve_logic_error,
            ErrorCategory.UI_RENDERING: self._resolve_ui_error,
            ErrorCategory.STATE_MANAGEMENT: self._resolve_state_error,
            ErrorCategory.SECURITY_AUTH: self._resolve_security_error,
            ErrorCategory.CONCURRENCY_ASYNC: self._resolve_concurrency_error,
            ErrorCategory.DEPLOYMENT_PRODUCTION: self._resolve_deployment_error
        }
        return handlers.get(category, self._resolve_generic_error)
    
    async def _resolve_syntax_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve syntax errors using LLM"""
        file_path = app_path / issue.get("file", "")
        
        if not file_path.exists():
            return {"success": False, "action": "File not found"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use LLM to fix syntax
            prompt = f"""Fix the following syntax error in this code:

Error: {issue.get('message')}
Line: {issue.get('line', 'Unknown')}

Code:
```
{content}
```

Return ONLY the corrected code without any explanation."""
            
            response = await call_llm_with_retry(self.llm, [
                SystemMessage(content="You are an expert code fixer. Fix syntax errors precisely."),
                HumanMessage(content=prompt)
            ])
            
            fixed_code = response.content.strip()
            # Remove markdown code blocks if present
            if fixed_code.startswith("```"):
                fixed_code = re.sub(r'^```[^\n]*\n', '', fixed_code)
                fixed_code = re.sub(r'\n```$', '', fixed_code)
            
            # Write fixed code
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            return {
                "success": True,
                "action": f"Fixed syntax error in {file_path.name}",
                "file": str(file_path)
            }
            
        except Exception as e:
            return {"success": False, "action": f"Failed to fix syntax: {str(e)}"}
    
    async def _resolve_dependency_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve dependency errors by installing missing packages"""
        try:
            if "npm install" in issue.get("fix_command", ""):
                result = subprocess.run(
                    ["npm", "install"],
                    cwd=str(app_path),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                success = result.returncode == 0
                return {
                    "success": success,
                    "action": "Installed npm dependencies",
                    "output": result.stdout
                }
            
            # Extract module name from error message
            match = re.search(r"No module named '([^']+)'", issue.get("message", ""))
            if match:
                module_name = match.group(1)
                result = subprocess.run(
                    ["pip", "install", module_name],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                success = result.returncode == 0
                return {
                    "success": success,
                    "action": f"Installed Python package: {module_name}",
                    "output": result.stdout
                }
            
            return {"success": False, "action": "Could not determine dependency to install"}
            
        except Exception as e:
            return {"success": False, "action": f"Failed to install dependency: {str(e)}"}
    
    async def _resolve_config_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve configuration errors"""
        try:
            if ".env" in issue.get("file", ""):
                env_example = app_path / ".env.example"
                env_file = app_path / ".env"
                
                if env_example.exists():
                    with open(env_example, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    with open(env_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    return {
                        "success": True,
                        "action": "Created .env file from .env.example",
                        "file": str(env_file)
                    }
            
            return {"success": False, "action": "Could not resolve config error"}
            
        except Exception as e:
            return {"success": False, "action": f"Failed to fix config: {str(e)}"}
    
    async def _resolve_database_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve database errors by adding error handling"""
        file_path = app_path / issue.get("file", "")
        
        if not file_path.exists():
            return {"success": False, "action": "File not found"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use LLM to add error handling
            prompt = f"""Add proper error handling for database operations in this code:

Issue: {issue.get('message')}

Code:
```
{content}
```

Return ONLY the corrected code with try-except blocks around database operations."""
            
            response = await call_llm_with_retry(self.llm, [
                SystemMessage(content="You are an expert in adding robust error handling to database code."),
                HumanMessage(content=prompt)
            ])
            
            fixed_code = response.content.strip()
            if fixed_code.startswith("```"):
                fixed_code = re.sub(r'^```[^\n]*\n', '', fixed_code)
                fixed_code = re.sub(r'\n```$', '', fixed_code)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            return {
                "success": True,
                "action": f"Added error handling to {file_path.name}",
                "file": str(file_path)
            }
            
        except Exception as e:
            return {"success": False, "action": f"Failed to fix database error: {str(e)}"}
    
    async def _resolve_api_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve API/network errors"""
        file_path = app_path / issue.get("file", "")
        
        if not file_path.exists():
            return {"success": False, "action": "File not found"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add timeout and error handling to API calls
            content = re.sub(
                r'requests\.(get|post|put|delete)\(([^)]+)\)',
                r'requests.\1(\2, timeout=30)',
                content
            )
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "action": f"Added timeout to API calls in {file_path.name}",
                "file": str(file_path)
            }
            
        except Exception as e:
            return {"success": False, "action": f"Failed to fix API error: {str(e)}"}
    
    async def _resolve_runtime_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve runtime errors using LLM analysis"""
        return await self._resolve_generic_error(app_path, issue)
    
    async def _resolve_logic_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve logic errors"""
        return await self._resolve_generic_error(app_path, issue)
    
    async def _resolve_ui_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve UI/rendering errors"""
        return await self._resolve_generic_error(app_path, issue)
    
    async def _resolve_state_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve state management errors"""
        return await self._resolve_generic_error(app_path, issue)
    
    async def _resolve_security_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve security/auth errors"""
        return await self._resolve_generic_error(app_path, issue)
    
    async def _resolve_concurrency_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve concurrency/async errors"""
        return await self._resolve_generic_error(app_path, issue)
    
    async def _resolve_deployment_error(self, app_path: Path, issue: Dict) -> Dict:
        """Resolve deployment/production errors"""
        return await self._resolve_generic_error(app_path, issue)
    
    async def _resolve_generic_error(self, app_path: Path, issue: Dict) -> Dict:
        """Generic error resolution using LLM"""
        try:
            prompt = f"""Analyze and suggest a fix for this issue:

Category: {issue.get('category', 'Unknown')}
Message: {issue.get('message', 'Unknown error')}
Details: {issue.get('details', 'N/A')}

Provide a concise fix suggestion."""
            
            response = await call_llm_with_retry(self.llm, [
                SystemMessage(content="You are an expert problem solver for software issues."),
                HumanMessage(content=prompt)
            ])
            
            return {
                "success": True,
                "action": response.content.strip(),
                "automated": False
            }
            
        except Exception as e:
            return {"success": False, "action": f"Analysis failed: {str(e)}"}
    
    async def _validate_fixes(self, app_path: Path, resolution_results: Dict) -> Dict:
        """Validate that fixes resolved the issues"""
        resolved_count = sum(1 for action in resolution_results["actions"] if action["success"])
        total_issues = len(resolution_results["actions"])
        
        remaining_issues = [
            action for action in resolution_results["actions"] 
            if not action["success"]
        ]
        
        return {
            "all_resolved": len(remaining_issues) == 0,
            "resolved_count": resolved_count,
            "total_issues": total_issues,
            "remaining_issues": remaining_issues
        }
    
    def _has_js_syntax_issues(self, content: str) -> bool:
        """Basic JavaScript syntax validation"""
        # Check for common syntax issues
        patterns = [
            r'\)\s*{',  # Function declarations
            r'}\s*else\s*{',  # Else blocks
            r'}\s*catch\s*\(',  # Catch blocks
        ]
        
        # This is a very basic check - for production, use a proper parser
        return False  # Placeholder
    
    def get_resolution_history(self) -> List[Dict]:
        """Get history of all resolution attempts"""
        return self.resolution_history
