"""
Code Review Agent - Automated code review with quality checks
Quick Win #2 from analysis
"""
import re
import ast
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent, ExecutionContext, ExecutionResult, AgentStatus, AgentCapability


class CodeIssue:
    """Code issue found during review"""
    
    def __init__(
        self,
        severity: str,  # critical, error, warning, info
        category: str,
        message: str,
        file_path: str,
        line_number: Optional[int] = None,
        suggestion: Optional[str] = None,
        code_snippet: Optional[str] = None
    ):
        self.severity = severity
        self.category = category
        self.message = message
        self.file_path = file_path
        self.line_number = line_number
        self.suggestion = suggestion
        self.code_snippet = code_snippet
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet,
            "timestamp": self.timestamp
        }


class CodeReviewAgent(BaseAgent):
    """
    Automated code review agent that checks:
    - Code style and formatting
    - Best practices
    - Security patterns
    - Performance anti-patterns
    - Documentation quality
    """
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.CODE_ANALYSIS]
    
    def validate_input(self, request_data: Dict) -> Tuple[bool, Optional[str]]:
        if "code_path" not in request_data:
            return False, "code_path is required"
        return True, None
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Execute code review"""
        code_path = Path(context.request_data["code_path"])
        language = context.request_data.get("language", "auto")
        
        if not code_path.exists():
            return ExecutionResult(
                status=AgentStatus.FAILED,
                output=None,
                errors=[f"Code path does not exist: {code_path}"]
            )
        
        context.add_telemetry("review_started", {"path": str(code_path)})
        
        issues: List[CodeIssue] = []
        
        # Review Python files
        python_files = list(code_path.rglob("*.py"))
        for py_file in python_files:
            issues.extend(self._review_python_file(py_file))
        
        # Review JavaScript/TypeScript files
        js_files = list(code_path.rglob("*.js")) + list(code_path.rglob("*.ts")) + list(code_path.rglob("*.tsx"))
        for js_file in js_files:
            issues.extend(self._review_javascript_file(js_file))
        
        # Review general patterns
        all_files = python_files + js_files
        for file in all_files:
            issues.extend(self._review_general_patterns(file))
        
        # Categorize issues
        critical = [i for i in issues if i.severity == "critical"]
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        info = [i for i in issues if i.severity == "info"]
        
        # Calculate score
        score = 100
        score -= len(critical) * 20
        score -= len(errors) * 10
        score -= len(warnings) * 5
        score -= len(info) * 1
        score = max(0, score)
        
        context.add_telemetry("review_completed", {
            "total_issues": len(issues),
            "critical": len(critical),
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(info),
            "score": score
        })
        
        return ExecutionResult(
            status=AgentStatus.COMPLETED,
            output={
                "issues": [i.to_dict() for i in issues],
                "summary": {
                    "total_issues": len(issues),
                    "critical": len(critical),
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "info": len(info),
                    "score": score,
                    "grade": self._get_grade(score)
                },
                "recommendations": self._generate_recommendations(issues)
            },
            metadata={
                "files_reviewed": len(all_files),
                "python_files": len(python_files),
                "javascript_files": len(js_files)
            }
        )
    
    def _review_python_file(self, file_path: Path) -> List[CodeIssue]:
        """Review Python file"""
        issues = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Check syntax
            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append(CodeIssue(
                    severity="critical",
                    category="syntax",
                    message=f"Syntax error: {str(e)}",
                    file_path=str(file_path),
                    line_number=e.lineno
                ))
                return issues  # Can't continue if syntax is broken
            
            # Check for common issues
            for i, line in enumerate(lines, 1):
                # Long lines
                if len(line) > 120:
                    issues.append(CodeIssue(
                        severity="warning",
                        category="style",
                        message="Line too long (>120 characters)",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Break line into multiple lines",
                        code_snippet=line[:50] + "..."
                    ))
                
                # Bare except
                if re.search(r'except\s*:', line):
                    issues.append(CodeIssue(
                        severity="error",
                        category="best_practice",
                        message="Bare except clause - catch specific exceptions",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Use 'except Exception:' or catch specific exception types",
                        code_snippet=line.strip()
                    ))
                
                # TODO comments
                if 'TODO' in line or 'FIXME' in line:
                    issues.append(CodeIssue(
                        severity="info",
                        category="maintenance",
                        message="TODO/FIXME comment found",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip()
                    ))
                
                # Hardcoded credentials (simple check)
                if re.search(r'(password|secret|api_key)\s*=\s*["\']', line, re.I):
                    issues.append(CodeIssue(
                        severity="critical",
                        category="security",
                        message="Potential hardcoded credential",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Use environment variables for credentials",
                        code_snippet=line.strip()
                    ))
                
                # SQL injection risk
                if re.search(r'execute\s*\([^?]*%s', line) or re.search(r'execute\s*\([^?]*\+', line):
                    issues.append(CodeIssue(
                        severity="critical",
                        category="security",
                        message="Potential SQL injection vulnerability",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Use parameterized queries",
                        code_snippet=line.strip()
                    ))
                
                # Print statements (in production code)
                if re.search(r'\bprint\s*\(', line) and 'debug' not in file_path.name.lower():
                    issues.append(CodeIssue(
                        severity="warning",
                        category="best_practice",
                        message="Print statement in production code",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Use logging instead of print",
                        code_snippet=line.strip()
                    ))
            
            # Check for missing docstrings
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        issues.append(CodeIssue(
                            severity="info",
                            category="documentation",
                            message=f"Missing docstring for {node.name}",
                            file_path=str(file_path),
                            line_number=node.lineno,
                            suggestion="Add docstring to explain purpose and usage"
                        ))
        
        except Exception as e:
            issues.append(CodeIssue(
                severity="error",
                category="review_error",
                message=f"Error reviewing file: {str(e)}",
                file_path=str(file_path)
            ))
        
        return issues
    
    def _review_javascript_file(self, file_path: Path) -> List[CodeIssue]:
        """Review JavaScript/TypeScript file"""
        issues = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Long lines
                if len(line) > 120:
                    issues.append(CodeIssue(
                        severity="warning",
                        category="style",
                        message="Line too long (>120 characters)",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Break line into multiple lines"
                    ))
                
                # console.log in production
                if 'console.log' in line:
                    issues.append(CodeIssue(
                        severity="warning",
                        category="best_practice",
                        message="console.log in production code",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Remove console.log or use proper logging",
                        code_snippet=line.strip()
                    ))
                
                # var instead of const/let
                if re.search(r'\bvar\s+', line):
                    issues.append(CodeIssue(
                        severity="warning",
                        category="best_practice",
                        message="Use const or let instead of var",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Replace 'var' with 'const' or 'let'",
                        code_snippet=line.strip()
                    ))
                
                # == instead of ===
                if re.search(r'[^=!]==[^=]', line) or re.search(r'!=[^=]', line):
                    issues.append(CodeIssue(
                        severity="warning",
                        category="best_practice",
                        message="Use === or !== instead of == or !=",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Use strict equality (===) for type-safe comparisons",
                        code_snippet=line.strip()
                    ))
                
                # Hardcoded API keys
                if re.search(r'(apiKey|api_key|secret|token)\s*[:=]\s*["\']', line, re.I):
                    issues.append(CodeIssue(
                        severity="critical",
                        category="security",
                        message="Potential hardcoded API key or secret",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Use environment variables for secrets",
                        code_snippet=line.strip()
                    ))
                
                # eval usage
                if 'eval(' in line:
                    issues.append(CodeIssue(
                        severity="critical",
                        category="security",
                        message="Use of eval() is a security risk",
                        file_path=str(file_path),
                        line_number=i,
                        suggestion="Avoid eval(), use safer alternatives",
                        code_snippet=line.strip()
                    ))
        
        except Exception as e:
            issues.append(CodeIssue(
                severity="error",
                category="review_error",
                message=f"Error reviewing file: {str(e)}",
                file_path=str(file_path)
            ))
        
        return issues
    
    def _review_general_patterns(self, file_path: Path) -> List[CodeIssue]:
        """Review general patterns across all files"""
        issues = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Check file size
            line_count = len(content.split('\n'))
            if line_count > 500:
                issues.append(CodeIssue(
                    severity="warning",
                    category="maintainability",
                    message=f"File is very large ({line_count} lines)",
                    file_path=str(file_path),
                    suggestion="Consider splitting into smaller, more focused modules"
                ))
            
            # Check for magic numbers
            numbers = re.findall(r'\b\d{4,}\b', content)
            if len(numbers) > 5:
                issues.append(CodeIssue(
                    severity="info",
                    category="maintainability",
                    message="Multiple magic numbers found",
                    file_path=str(file_path),
                    suggestion="Extract magic numbers as named constants"
                ))
            
            # Check for code duplication (simple check)
            lines = content.split('\n')
            line_counts = {}
            for line in lines:
                stripped = line.strip()
                if stripped and len(stripped) > 20:  # Ignore short lines
                    line_counts[stripped] = line_counts.get(stripped, 0) + 1
            
            duplicates = {line: count for line, count in line_counts.items() if count > 3}
            if duplicates:
                issues.append(CodeIssue(
                    severity="info",
                    category="maintainability",
                    message=f"Found {len(duplicates)} duplicated code patterns",
                    file_path=str(file_path),
                    suggestion="Extract duplicated code into reusable functions"
                ))
        
        except Exception:
            pass  # Ignore errors in general pattern review
        
        return issues
    
    def _get_grade(self, score: int) -> str:
        """Convert score to grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _generate_recommendations(self, issues: List[CodeIssue]) -> List[str]:
        """Generate recommendations based on issues"""
        recommendations = []
        
        # Count by category
        categories = {}
        for issue in issues:
            categories[issue.category] = categories.get(issue.category, 0) + 1
        
        # Generate recommendations
        if categories.get("security", 0) > 0:
            recommendations.append("Address security issues immediately - these are critical vulnerabilities")
        
        if categories.get("best_practice", 0) > 5:
            recommendations.append("Review and apply language best practices to improve code quality")
        
        if categories.get("documentation", 0) > 10:
            recommendations.append("Add docstrings/comments to improve code documentation")
        
        if categories.get("maintainability", 0) > 5:
            recommendations.append("Refactor code to improve maintainability")
        
        if categories.get("style", 0) > 10:
            recommendations.append("Run code formatter (black/prettier) to fix style issues")
        
        if not recommendations:
            recommendations.append("Code quality is good! Continue following best practices.")
        
        return recommendations
