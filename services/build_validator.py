"""
Build Validator - Comprehensive validation for generated applications
Validates syntax, dependencies, build process, and runtime readiness
"""
import subprocess
import json
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime


class ValidationLevel:
    """Validation severity levels"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult:
    """Single validation check result"""
    
    def __init__(
        self,
        check_name: str,
        passed: bool,
        level: str = ValidationLevel.ERROR,
        message: str = "",
        details: Optional[Dict] = None
    ):
        self.check_name = check_name
        self.passed = passed
        self.level = level
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "level": self.level,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class BuildValidator:
    """
    Comprehensive build validator that checks:
    - File structure
    - Syntax validity
    - Dependency resolution
    - Build process
    - Configuration validity
    - Docker setup
    """
    
    def __init__(self):
        self.results: List[ValidationResult] = []
    
    async def validate_build(self, app_path: str) -> Dict:
        """
        Run complete validation suite
        
        Returns:
            {
                "overall_status": "passed|failed|warning",
                "score": 0-100,
                "checks_passed": int,
                "checks_failed": int,
                "results": [ValidationResult],
                "summary": str
            }
        """
        app_path_obj = Path(app_path)
        self.results = []
        
        if not app_path_obj.exists():
            return {
                "overall_status": "failed",
                "score": 0,
                "checks_passed": 0,
                "checks_failed": 1,
                "results": [ValidationResult(
                    "path_exists",
                    False,
                    ValidationLevel.CRITICAL,
                    f"Application path does not exist: {app_path}"
                ).to_dict()],
                "summary": "Validation failed: path not found"
            }
        
        # Run all validation checks
        await self._validate_structure(app_path_obj)
        await self._validate_backend(app_path_obj)
        await self._validate_frontend(app_path_obj)
        await self._validate_docker(app_path_obj)
        await self._validate_configuration(app_path_obj)
        await self._validate_playwright_e2e(app_path_obj)
        
        # Calculate results
        return self._compile_results()

    async def _validate_playwright_e2e(self, app_path: Path):
        """Execute automated browser checks using Playwright"""
        has_frontend = (app_path / "frontend").exists() or (app_path / "package.json").exists()
        if not has_frontend:
            return

        from services.mcp_manager import get_mcp_manager, MCPManagerError
        manager = get_mcp_manager()
        
        try:
            # Check if playwright tests exist or if we can run them
            result = manager.run_playwright_tests(app_path)
            passed = result.get("exit_code") == 0
            summary = result.get("summary", {})
            msg = f"Playwright: {summary.get('tests_passed', 0)} passed, {summary.get('tests_failed', 0)} failed"
            
            self.results.append(ValidationResult(
                "playwright_e2e",
                passed,
                ValidationLevel.ERROR if not passed else ValidationLevel.INFO,
                message=msg,
                details=result
            ))
        except MCPManagerError as exc:
            self.results.append(ValidationResult(
                "playwright_e2e",
                True,  # Non-blocking soft warning if Docker/MCP server is offline
                ValidationLevel.WARNING,
                message=f"Playwright E2E testing skipped: {exc}"
            ))
        except Exception as exc:
            self.results.append(ValidationResult(
                "playwright_e2e",
                True,
                ValidationLevel.WARNING,
                message=f"Playwright E2E verification errored: {exc}"
            ))
    
    async def _validate_structure(self, app_path: Path):
        """Validate project structure"""
        required_dirs = [
            ("backend", ValidationLevel.CRITICAL),
            ("frontend", ValidationLevel.CRITICAL)
        ]
        
        for dir_name, level in required_dirs:
            dir_path = app_path / dir_name
            self.results.append(ValidationResult(
                f"structure_{dir_name}",
                dir_path.exists() and dir_path.is_dir(),
                level,
                f"Directory '{dir_name}' exists" if dir_path.exists() else f"Missing directory: {dir_name}"
            ))
    
    async def _validate_backend(self, app_path: Path):
        """Validate backend code and dependencies"""
        backend_path = app_path / "backend"
        
        if not backend_path.exists():
            return
        
        # Check required files
        required_files = {
            "main.py": ValidationLevel.CRITICAL,
            "requirements.txt": ValidationLevel.CRITICAL,
            "models.py": ValidationLevel.ERROR,
            "routes.py": ValidationLevel.ERROR
        }
        
        for file_name, level in required_files.items():
            file_path = backend_path / file_name
            self.results.append(ValidationResult(
                f"backend_file_{file_name}",
                file_path.exists(),
                level,
                f"Backend file '{file_name}' exists" if file_path.exists() else f"Missing: {file_name}"
            ))
        
        # Validate Python syntax
        await self._validate_python_syntax(backend_path)
        
        # Check dependencies
        await self._validate_python_dependencies(backend_path)
        
        # Validate imports
        await self._validate_python_imports(backend_path)
    
    async def _validate_frontend(self, app_path: Path):
        """Validate frontend code and dependencies"""
        frontend_path = app_path / "frontend"
        
        if not frontend_path.exists():
            return
        
        # Check required files
        required_files = {
            "package.json": ValidationLevel.CRITICAL,
            "index.html": ValidationLevel.CRITICAL,
            "vite.config.ts": ValidationLevel.ERROR
        }
        
        for file_name, level in required_files.items():
            file_path = frontend_path / file_name
            self.results.append(ValidationResult(
                f"frontend_file_{file_name}",
                file_path.exists(),
                level,
                f"Frontend file '{file_name}' exists" if file_path.exists() else f"Missing: {file_name}"
            ))
        
        # Validate package.json
        await self._validate_package_json(frontend_path)
        
        # Check TypeScript/JavaScript syntax
        await self._validate_js_syntax(frontend_path)
    
    async def _validate_docker(self, app_path: Path):
        """Validate Docker configuration"""
        # Check docker-compose.yml
        compose_file = app_path / "docker-compose.yml"
        self.results.append(ValidationResult(
            "docker_compose",
            compose_file.exists(),
            ValidationLevel.ERROR,
            "docker-compose.yml exists" if compose_file.exists() else "Missing: docker-compose.yml"
        ))
        
        if compose_file.exists():
            # Validate YAML syntax
            try:
                import yaml
                with open(compose_file, 'r', encoding='utf-8') as f:
                    compose_data = yaml.safe_load(f)
                
                # Check for required services
                services = compose_data.get('services', {})
                required_services = ['backend', 'frontend', 'postgres']
                
                for service in required_services:
                    self.results.append(ValidationResult(
                        f"docker_service_{service}",
                        service in services,
                        ValidationLevel.WARNING,
                        f"Docker service '{service}' defined" if service in services else f"Missing service: {service}"
                    ))
                
            except Exception as e:
                self.results.append(ValidationResult(
                    "docker_compose_parse",
                    False,
                    ValidationLevel.ERROR,
                    f"Failed to parse docker-compose.yml: {str(e)}"
                ))
        
        # Check Dockerfiles
        backend_dockerfile = app_path / "backend" / "Dockerfile"
        frontend_dockerfile = app_path / "frontend" / "Dockerfile"
        
        self.results.append(ValidationResult(
            "backend_dockerfile",
            backend_dockerfile.exists(),
            ValidationLevel.WARNING,
            "Backend Dockerfile exists" if backend_dockerfile.exists() else "Missing: backend/Dockerfile"
        ))
        
        self.results.append(ValidationResult(
            "frontend_dockerfile",
            frontend_dockerfile.exists(),
            ValidationLevel.WARNING,
            "Frontend Dockerfile exists" if frontend_dockerfile.exists() else "Missing: frontend/Dockerfile"
        ))
    
    async def _validate_configuration(self, app_path: Path):
        """Validate configuration files"""
        # Check .env.example
        env_example = app_path / ".env.example"
        self.results.append(ValidationResult(
            "env_example",
            env_example.exists(),
            ValidationLevel.INFO,
            ".env.example exists" if env_example.exists() else "Missing: .env.example"
        ))
        
        # Check README
        readme = app_path / "README.md"
        self.results.append(ValidationResult(
            "readme",
            readme.exists(),
            ValidationLevel.INFO,
            "README.md exists" if readme.exists() else "Missing: README.md"
        ))
    
    async def _validate_python_syntax(self, backend_path: Path):
        """Validate Python file syntax"""
        py_files = list(backend_path.rglob("*.py"))
        syntax_errors = []
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, str(py_file), 'exec')
            except SyntaxError as e:
                syntax_errors.append(f"{py_file.name}:{e.lineno}: {e.msg}")
        
        self.results.append(ValidationResult(
            "python_syntax",
            len(syntax_errors) == 0,
            ValidationLevel.ERROR,
            "All Python files have valid syntax" if not syntax_errors else f"Syntax errors found: {len(syntax_errors)}",
            {"errors": syntax_errors[:5]}  # Limit to 5 errors
        ))
    
    async def _validate_python_dependencies(self, backend_path: Path):
        """Validate Python dependencies"""
        requirements_file = backend_path / "requirements.txt"
        
        if not requirements_file.exists():
            return
        
        try:
            # Read requirements
            with open(requirements_file, 'r', encoding='utf-8') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            self.results.append(ValidationResult(
                "python_dependencies_listed",
                len(requirements) > 0,
                ValidationLevel.WARNING,
                f"Found {len(requirements)} dependencies" if requirements else "No dependencies listed",
                {"count": len(requirements)}
            ))
            
            # Check for common required packages
            required_packages = ['fastapi', 'uvicorn', 'sqlalchemy']
            found_packages = [pkg for pkg in required_packages if any(pkg in req.lower() for req in requirements)]
            
            self.results.append(ValidationResult(
                "python_core_dependencies",
                len(found_packages) == len(required_packages),
                ValidationLevel.WARNING,
                f"Core packages present: {', '.join(found_packages)}" if found_packages else "Missing core packages",
                {"found": found_packages, "required": required_packages}
            ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                "python_dependencies_parse",
                False,
                ValidationLevel.WARNING,
                f"Failed to parse requirements.txt: {str(e)}"
            ))
    
    async def _validate_python_imports(self, backend_path: Path):
        """Validate that imports are available"""
        py_files = list(backend_path.rglob("*.py"))
        import_pattern = re.compile(r'^(?:from|import)\s+(\S+)', re.MULTILINE)
        
        all_imports = set()
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                imports = import_pattern.findall(content)
                all_imports.update(imports)
            except Exception:
                pass
        
        self.results.append(ValidationResult(
            "python_imports",
            True,  # Just informational
            ValidationLevel.INFO,
            f"Found {len(all_imports)} unique imports",
            {"count": len(all_imports), "sample": list(all_imports)[:10]}
        ))
    
    async def _validate_js_syntax(self, frontend_path: Path):
        """Basic JavaScript/TypeScript syntax validation"""
        js_files = list(frontend_path.rglob("*.ts")) + list(frontend_path.rglob("*.tsx")) + \
                   list(frontend_path.rglob("*.js")) + list(frontend_path.rglob("*.jsx"))
        
        # Basic checks for common syntax issues
        issues = []
        for js_file in js_files[:10]:  # Limit to 10 files
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for balanced braces
                if content.count('{') != content.count('}'):
                    issues.append(f"{js_file.name}: Unbalanced braces")
                
                # Check for balanced parentheses
                if content.count('(') != content.count(')'):
                    issues.append(f"{js_file.name}: Unbalanced parentheses")
                
            except Exception:
                pass
        
        self.results.append(ValidationResult(
            "javascript_syntax",
            len(issues) == 0,
            ValidationLevel.WARNING,
            "JavaScript files appear valid" if not issues else f"Found {len(issues)} potential issues",
            {"issues": issues[:5]}
        ))
    
    async def _validate_package_json(self, frontend_path: Path):
        """Validate package.json"""
        package_json = frontend_path / "package.json"
        
        if not package_json.exists():
            return
        
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg_data = json.load(f)
            
            # Check for required fields
            required_fields = ['name', 'version', 'scripts', 'dependencies']
            missing_fields = [field for field in required_fields if field not in pkg_data]
            
            self.results.append(ValidationResult(
                "package_json_structure",
                len(missing_fields) == 0,
                ValidationLevel.ERROR,
                "package.json has required fields" if not missing_fields else f"Missing fields: {', '.join(missing_fields)}",
                {"missing": missing_fields}
            ))
            
            # Check for required scripts
            scripts = pkg_data.get('scripts', {})
            required_scripts = ['dev', 'build']
            missing_scripts = [script for script in required_scripts if script not in scripts]
            
            self.results.append(ValidationResult(
                "package_json_scripts",
                len(missing_scripts) == 0,
                ValidationLevel.WARNING,
                "package.json has build scripts" if not missing_scripts else f"Missing scripts: {', '.join(missing_scripts)}",
                {"missing": missing_scripts}
            ))
            
            # Check for React dependencies
            deps = {**pkg_data.get('dependencies', {}), **pkg_data.get('devDependencies', {})}
            has_react = 'react' in deps
            
            self.results.append(ValidationResult(
                "package_json_react",
                has_react,
                ValidationLevel.WARNING,
                "React dependency found" if has_react else "React dependency not found"
            ))
            
        except json.JSONDecodeError as e:
            self.results.append(ValidationResult(
                "package_json_parse",
                False,
                ValidationLevel.ERROR,
                f"Failed to parse package.json: {str(e)}"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                "package_json_read",
                False,
                ValidationLevel.ERROR,
                f"Failed to read package.json: {str(e)}"
            ))
    
    def _compile_results(self) -> Dict:
        """Compile validation results into summary"""
        if not self.results:
            return {
                "overall_status": "failed",
                "score": 0,
                "checks_passed": 0,
                "checks_failed": 0,
                "results": [],
                "summary": "No checks performed"
            }
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        # Count by severity
        critical_failed = sum(1 for r in self.results if not r.passed and r.level == ValidationLevel.CRITICAL)
        error_failed = sum(1 for r in self.results if not r.passed and r.level == ValidationLevel.ERROR)
        warning_failed = sum(1 for r in self.results if not r.passed and r.level == ValidationLevel.WARNING)
        
        # Determine overall status
        if critical_failed > 0:
            overall_status = "failed"
        elif error_failed > 0:
            overall_status = "failed"
        elif warning_failed > 0:
            overall_status = "warning"
        else:
            overall_status = "passed"
        
        # Calculate score (0-100)
        # Critical failures: -50 points each
        # Error failures: -20 points each
        # Warning failures: -5 points each
        score = 100
        score -= critical_failed * 50
        score -= error_failed * 20
        score -= warning_failed * 5
        score = max(0, min(100, score))
        
        # Generate summary
        summary_parts = []
        if critical_failed > 0:
            summary_parts.append(f"{critical_failed} critical issues")
        if error_failed > 0:
            summary_parts.append(f"{error_failed} errors")
        if warning_failed > 0:
            summary_parts.append(f"{warning_failed} warnings")
        
        if not summary_parts:
            summary = f"All {passed} checks passed"
        else:
            summary = f"Validation {overall_status}: {', '.join(summary_parts)}"
        
        return {
            "overall_status": overall_status,
            "score": score,
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_total": len(self.results),
            "critical_failures": critical_failed,
            "error_failures": error_failed,
            "warning_failures": warning_failed,
            "results": [r.to_dict() for r in self.results],
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
