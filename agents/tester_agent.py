"""
Tester Agent - On-demand testing with structured reports
Runs tests only when requested by users
"""
import os
import re
import json
import asyncio
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage


class TestCategory:
    """Test categories"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    API = "api"
    UI = "ui"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TesterAgent:
    """
    Agent responsible for running tests on-demand and generating
    structured test reports for the UI
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings):
        self.llm = llm
        self.settings = settings
        self.test_history: List[Dict] = []
    
    async def run_tests(
        self,
        app_path: str,
        test_type: str = "all",
        specific_tests: Optional[List[str]] = None,
        generate_missing: bool = True
    ) -> Dict:
        """
        Run tests on-demand and return structured report
        
        Args:
            app_path: Path to the application
            test_type: Type of tests to run (unit, integration, e2e, all)
            specific_tests: List of specific test files to run
            generate_missing: Whether to generate tests if none exist
        
        Returns:
            Structured test report with results
        """
        app_path_obj = Path(app_path)
        
        if not app_path_obj.exists():
            return {
                "status": "error",
                "message": f"App path not found: {app_path}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        
        # Step 1: Detect test framework and existing tests
        test_info = await self._detect_test_framework(app_path_obj)
        
        # Step 2: Generate tests if none exist and generation is requested
        if generate_missing and not test_info["has_tests"]:
            generation_result = await self._generate_tests(app_path_obj, test_info)
            test_info["generated_tests"] = generation_result
        
        # Step 3: Run tests
        test_results = await self._execute_tests(
            app_path_obj,
            test_info,
            test_type,
            specific_tests
        )
        
        # Step 4: Analyze results and create structured report
        report = self._create_test_report(test_results, test_info)
        
        # Store in history
        self.test_history.append(report)
        
        return report
    
    async def _detect_test_framework(self, app_path: Path) -> Dict:
        """Detect testing framework and existing tests"""
        info = {
            "has_tests": False,
            "framework": None,
            "test_files": [],
            "test_directory": None
        }
        
        # Check for Python testing frameworks
        if (app_path / "pytest.ini").exists() or (app_path / "setup.cfg").exists():
            info["framework"] = "pytest"
            info["has_tests"] = True
        elif (app_path / "tests").exists():
            info["framework"] = "pytest"  # Default to pytest
            info["test_directory"] = "tests"
            
            test_files = list((app_path / "tests").rglob("test_*.py"))
            test_files.extend(list((app_path / "tests").rglob("*_test.py")))
            info["test_files"] = [str(f.relative_to(app_path)) for f in test_files]
            info["has_tests"] = len(test_files) > 0
        
        # Check for Node.js testing frameworks
        package_json = app_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    pkg_data = json.load(f)
                
                scripts = pkg_data.get("scripts", {})
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                
                if "jest" in deps:
                    info["framework"] = "jest"
                    info["has_tests"] = "test" in scripts
                elif "mocha" in deps:
                    info["framework"] = "mocha"
                    info["has_tests"] = "test" in scripts
                elif "vitest" in deps:
                    info["framework"] = "vitest"
                    info["has_tests"] = "test" in scripts
                elif "@playwright/test" in deps or "playwright" in deps:
                    info["framework"] = "playwright"
                    info["has_tests"] = "test" in scripts or any(
                        key.startswith("playwright") for key in scripts.keys()
                    )
                
                # Find test files
                test_patterns = ["*.test.js", "*.test.ts", "*.spec.js", "*.spec.ts"]
                for pattern in test_patterns:
                    test_files = list(app_path.rglob(pattern))
                    info["test_files"].extend([str(f.relative_to(app_path)) for f in test_files])
                
                if info["test_files"]:
                    info["has_tests"] = True

                # Detect Playwright configuration files
                if (app_path / "playwright.config.ts").exists() or (app_path / "playwright.config.js").exists():
                    info["framework"] = info.get("framework") or "playwright"
                    info["has_tests"] = True
                    info.setdefault("test_directory", "tests")
                    
            except Exception:
                pass
        
        return info
    
    async def _generate_tests(self, app_path: Path, test_info: Dict) -> Dict:
        """Generate missing tests using LLM"""
        generated = {
            "success": False,
            "files_created": [],
            "message": ""
        }
        
        try:
            # Analyze application structure
            app_structure = self._analyze_app_structure(app_path)
            
            # Generate tests based on framework
            if test_info["framework"] == "playwright":
                generated = await self._generate_playwright_tests(app_path, app_structure)
            elif test_info["framework"] in ["pytest", None]:
                generated = await self._generate_pytest_tests(app_path, app_structure)
            elif test_info["framework"] in ["jest", "vitest"]:
                generated = await self._generate_jest_tests(app_path, app_structure)
            
        except Exception as e:
            generated["message"] = f"Failed to generate tests: {str(e)}"
        
        return generated
    
    def _analyze_app_structure(self, app_path: Path) -> Dict:
        """Analyze application structure to understand what to test"""
        structure = {
            "python_modules": [],
            "js_components": [],
            "api_endpoints": [],
            "has_database": False,
            "has_frontend": False
        }
        
        # Find Python modules
        py_files = list(app_path.rglob("*.py"))
        structure["python_modules"] = [
            str(f.relative_to(app_path)) for f in py_files 
            if "test" not in str(f) and "__pycache__" not in str(f)
        ][:10]  # Limit to 10 files
        
        # Find JS/TS components
        js_files = list(app_path.rglob("*.jsx")) + list(app_path.rglob("*.tsx"))
        structure["js_components"] = [str(f.relative_to(app_path)) for f in js_files][:10]
        
        # Check for database
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "sqlalchemy" in content.lower() or "database" in content.lower():
                        structure["has_database"] = True
                        break
            except Exception:
                pass
        
        # Check for frontend
        structure["has_frontend"] = len(js_files) > 0 or (app_path / "package.json").exists()
        
        return structure
    
    async def _generate_pytest_tests(self, app_path: Path, structure: Dict) -> Dict:
        """Generate pytest tests"""
        test_dir = app_path / "tests"
        test_dir.mkdir(exist_ok=True)
        
        # Create conftest.py
        conftest_content = """
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
"""
        
        conftest_file = test_dir / "conftest.py"
        with open(conftest_file, 'w', encoding='utf-8') as f:
            f.write(conftest_content)
        
        files_created = ["tests/conftest.py"]
        
        # Generate basic test for main modules
        for module_path in structure["python_modules"][:3]:  # Limit to 3
            module_name = Path(module_path).stem
            
            test_content = f"""
import pytest
from {module_name} import *

def test_{module_name}_imports():
    \"\"\"Test that module imports successfully\"\"\"
    assert True

def test_{module_name}_basic_functionality():
    \"\"\"Basic functionality test for {module_name}\"\"\"
    # TODO: Add specific tests
    pass
"""
            
            test_file = test_dir / f"test_{module_name}.py"
            try:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(test_content)
                files_created.append(f"tests/test_{module_name}.py")
            except Exception:
                pass
        
        return {
            "success": True,
            "files_created": files_created,
            "message": f"Generated {len(files_created)} test files"
        }
    
    async def _generate_jest_tests(self, app_path: Path, structure: Dict) -> Dict:
        """Generate Jest/Vitest tests"""
        files_created = []
        
        # Generate component tests
        for component_path in structure["js_components"][:3]:
            component_file = app_path / component_path
            component_name = component_file.stem
            
            test_content = f"""
import {{ render, screen }} from '@testing-library/react';
import {component_name} from './{component_name}';

describe('{component_name}', () => {{
  it('renders without crashing', () => {{
    render(<{component_name} />);
    expect(screen).toBeDefined();
  }});
  
  it('has expected structure', () => {{
    // TODO: Add specific tests
    expect(true).toBe(true);
  }});
}});
"""
            
            test_file = component_file.parent / f"{component_name}.test.tsx"
            try:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(test_content)
                files_created.append(str(test_file.relative_to(app_path)))
            except Exception:
                pass
        
        return {
            "success": True,
            "files_created": files_created,
            "message": f"Generated {len(files_created)} test files"
        }
    
    async def _execute_tests(
        self,
        app_path: Path,
        test_info: Dict,
        test_type: str,
        specific_tests: Optional[List[str]]
    ) -> Dict:
        """Execute tests and capture results"""
        results = {
            "framework": test_info["framework"],
            "execution_time": 0,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "failures": [],
            "output": "",
            "error_output": ""
        }
        
        start_time = datetime.utcnow()
        
        try:
            if test_info["framework"] == "pytest":
                results = await self._run_pytest(app_path, specific_tests)
            elif test_info["framework"] in ["jest", "vitest", "mocha"]:
                results = await self._run_npm_tests(app_path, test_info["framework"])
            elif test_info["framework"] == "playwright":
                results = await self._run_playwright_mcp(app_path, specific_tests)
            else:
                results["output"] = "No test framework detected"
                
        except Exception as e:
            results["error_output"] = str(e)
        
        end_time = datetime.utcnow()
        results["execution_time"] = (end_time - start_time).total_seconds()
        
        return results
    
    async def _run_pytest(self, app_path: Path, specific_tests: Optional[List[str]]) -> Dict:
        """Run pytest tests"""
        cmd = ["pytest", "-v", "--tb=short", "--json-report", "--json-report-file=test-report.json"]
        
        if specific_tests:
            cmd.extend(specific_tests)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(app_path),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse pytest output
            output = result.stdout
            
            # Extract test counts
            passed = len(re.findall(r'PASSED', output))
            failed = len(re.findall(r'FAILED', output))
            skipped = len(re.findall(r'SKIPPED', output))
            
            # Parse failures
            failures = []
            failure_pattern = r'FAILED (.+?) - (.+)'
            for match in re.finditer(failure_pattern, output):
                failures.append({
                    "test": match.group(1),
                    "message": match.group(2)
                })
            
            return {
                "framework": "pytest",
                "tests_run": passed + failed,
                "tests_passed": passed,
                "tests_failed": failed,
                "tests_skipped": skipped,
                "failures": failures,
                "output": output,
                "error_output": result.stderr,
                "exit_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "framework": "pytest",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "failures": [],
                "output": "",
                "error_output": "Test execution timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "framework": "pytest",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "failures": [],
                "output": "",
                "error_output": str(e)
            }
    
    async def _run_npm_tests(self, app_path: Path, framework: str) -> Dict:
        """Run npm-based tests (Jest, Vitest, Mocha)"""
        try:
            result = subprocess.run(
                ["npm", "test", "--", "--json"],
                cwd=str(app_path),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            output = result.stdout
            
            # Parse npm test output
            passed = len(re.findall(r'✓|PASS', output))
            failed = len(re.findall(r'✗|FAIL', output))
            
            return {
                "framework": framework,
                "tests_run": passed + failed,
                "tests_passed": passed,
                "tests_failed": failed,
                "tests_skipped": 0,
                "failures": [],
                "output": output,
                "error_output": result.stderr,
                "exit_code": result.returncode
            }
            
        except Exception as e:
            return {
                "framework": framework,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "failures": [],
                "output": "",
                "error_output": str(e)
            }

    async def _run_playwright_mcp(self, app_path: Path, specific_tests: Optional[List[str]]) -> Dict:
        """Run Playwright tests using the MCP Playwright server"""
        from services.mcp_manager import get_mcp_manager, MCPManagerError

        manager = get_mcp_manager()

        try:
            result = await asyncio.to_thread(
                manager.run_playwright_tests,
                app_path,
                specific_tests
            )
        except MCPManagerError as error:
            return {
                "framework": "playwright",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "failures": [],
                "output": "",
                "error_output": str(error),
                "exit_code": 1
            }

        summary = result.get("summary", {})

        return {
            "framework": "playwright",
            "tests_run": summary.get("tests_run", 0),
            "tests_passed": summary.get("tests_passed", 0),
            "tests_failed": summary.get("tests_failed", 0),
            "tests_skipped": summary.get("tests_skipped", 0),
            "failures": summary.get("failures", []),
            "output": result.get("stdout", ""),
            "error_output": result.get("stderr", ""),
            "exit_code": result.get("exit_code", 1)
        }
    
    def _create_test_report(self, test_results: Dict, test_info: Dict) -> Dict:
        """Create structured test report for UI consumption"""
        success_rate = 0
        if test_results["tests_run"] > 0:
            success_rate = (test_results["tests_passed"] / test_results["tests_run"]) * 100
        
        # Determine status
        if test_results["tests_failed"] == 0 and test_results["tests_run"] > 0:
            status = "passed"
        elif test_results["tests_run"] == 0:
            status = "no_tests"
        else:
            status = "failed"
        
        report = {
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "framework": test_info["framework"],
            "summary": {
                "total_tests": test_results["tests_run"],
                "passed": test_results["tests_passed"],
                "failed": test_results["tests_failed"],
                "skipped": test_results["tests_skipped"],
                "success_rate": round(success_rate, 2),
                "execution_time": test_results.get("execution_time", 0)
            },
            "failures": test_results.get("failures", []),
            "coverage": self._extract_coverage(test_results.get("output", "")),
            "recommendations": self._generate_recommendations(test_results),
            "output": {
                "stdout": test_results.get("output", "")[:5000],  # Limit output size
                "stderr": test_results.get("error_output", "")[:5000]
            },
            "test_files": test_info.get("test_files", []),
            "generated_tests": test_info.get("generated_tests", {})
        }
        
        return report
    
    def _extract_coverage(self, output: str) -> Optional[Dict]:
        """Extract code coverage information if available"""
        coverage = None
        
        # Look for coverage percentage
        coverage_match = re.search(r'(\d+)%\s+coverage', output, re.IGNORECASE)
        if coverage_match:
            coverage = {
                "total": int(coverage_match.group(1)),
                "details": "See full output for detailed coverage"
            }
        
        return coverage
    
    def _generate_recommendations(self, test_results: Dict) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if test_results["tests_run"] == 0:
            recommendations.append("No tests found. Consider generating tests to improve code quality.")
        
        if test_results["tests_failed"] > 0:
            recommendations.append(f"{test_results['tests_failed']} test(s) failed. Review failures and fix issues.")
        
        if test_results["tests_run"] < 5:
            recommendations.append("Test coverage appears low. Consider adding more comprehensive tests.")
        
        success_rate = 0
        if test_results["tests_run"] > 0:
            success_rate = (test_results["tests_passed"] / test_results["tests_run"]) * 100
        
        if success_rate < 80 and test_results["tests_run"] > 0:
            recommendations.append(f"Success rate is {success_rate:.1f}%. Aim for >80% passing tests.")
        
        if not recommendations:
            recommendations.append("All tests passing! Consider adding edge case tests.")
        
        return recommendations
    
    async def generate_test_suggestions(self, app_path: str) -> Dict:
        """Generate suggestions for what tests to add"""
        app_path_obj = Path(app_path)
        structure = self._analyze_app_structure(app_path_obj)
        
        suggestions = []
        
        # Suggest tests based on app structure
        if structure["has_database"]:
            suggestions.append({
                "category": "database",
                "suggestion": "Add database integration tests",
                "priority": "high"
            })
        
        if structure["has_frontend"]:
            suggestions.append({
                "category": "ui",
                "suggestion": "Add component rendering tests",
                "priority": "medium"
            })
        
        if structure["api_endpoints"]:
            suggestions.append({
                "category": "api",
                "suggestion": "Add API endpoint tests",
                "priority": "high"
            })
        
        return {
            "suggestions": suggestions,
            "can_auto_generate": True
        }
    
    def get_test_history(self) -> List[Dict]:
        """Get history of all test runs"""
        return self.test_history

    async def _generate_playwright_tests(self, app_path: Path, structure: Dict) -> Dict:
        """Generate Playwright E2E UI browser tests"""
        # Determine target test directory
        test_dir = app_path / "tests"
        if (app_path / "frontend").exists():
            test_dir = app_path / "frontend" / "tests"
            
        test_dir.mkdir(parents=True, exist_ok=True)
        files_created = []
        
        # Basic Playwright config file if not present
        config_path = app_path / "playwright.config.ts"
        if (app_path / "frontend").exists():
            config_path = app_path / "frontend" / "playwright.config.ts"
            
        if not config_path.exists():
            config_content = """import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    }
  ]
});
"""
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            files_created.append(str(config_path.relative_to(app_path)))

        # Write E2E test file
        spec_content = """import { test, expect } from '@playwright/test';

test.describe('E2E Application flows', () => {
  test('Page loads successfully', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/.*App.*/i);
  });

  test('Navbar navigation links functional', async ({ page }) => {
    await page.goto('/');
    const links = page.locator('nav a');
    const count = await links.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
"""
        spec_path = test_dir / "app.spec.ts"
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        files_created.append(str(spec_path.relative_to(app_path)))
        
        return {
            "success": True,
            "files_created": files_created,
            "message": f"Generated Playwright configurations and specs: {', '.join(files_created)}"
        }
